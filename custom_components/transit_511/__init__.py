"""The 511 Transit integration - Version 2.0."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Transit511ApiClient, Transit511ApiError
from .const import (
    CONF_API_KEY,
    CONF_ENABLE_API_LOGGING,
    CONF_LINE_ID,
    CONF_MONITORING_TYPE,
    CONF_OPERATOR,
    CONF_STARTUP_DELAY,
    CONF_STOP_CODE,
    CONF_STOPS,
    CONF_VEHICLE_ID,
    CONF_VEHICLES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_STARTUP_DELAY,
    DOMAIN,
    MONITORING_TYPE_STOP,
    MONITORING_TYPE_VEHICLE,
    get_vehicle_type,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.DEVICE_TRACKER]

# Global storage key for shared coordinators
GLOBAL_COORDINATORS = "global_coordinators"


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an old config entry to the current schema.

    v1 stored a single monitored item using top-level keys
    (stop_code/line_id or vehicle_id). v2 stores items as lists under
    CONF_STOPS / CONF_VEHICLES so a single entry can hold many.
    """
    _LOGGER.debug("Migrating config entry %s from version %s", entry.title, entry.version)

    # Refuse to downgrade entries written by a newer version.
    if entry.version > 2:
        _LOGGER.error(
            "Cannot downgrade config entry %s from version %s", entry.title, entry.version
        )
        return False

    if entry.version == 1:
        new_data = dict(entry.data)

        # Determine the monitoring type; fall back to which top-level key is present.
        monitoring_type = new_data.get(CONF_MONITORING_TYPE)
        if monitoring_type is None:
            monitoring_type = (
                MONITORING_TYPE_STOP
                if CONF_STOP_CODE in new_data
                else MONITORING_TYPE_VEHICLE
            )
            new_data[CONF_MONITORING_TYPE] = monitoring_type

        if monitoring_type == MONITORING_TYPE_STOP:
            stop_code = new_data.pop(CONF_STOP_CODE, None)
            line_id = new_data.pop(CONF_LINE_ID, None)
            stop_name = new_data.pop("stop_name", stop_code)
            new_data[CONF_STOPS] = [
                {
                    "stop_code": stop_code,
                    # v2 flow writes line_id as a string; coerce None -> "".
                    "line_id": line_id or "",
                    "stop_name": stop_name if stop_name is not None else stop_code,
                }
            ]
        else:
            vehicle_id = new_data.pop(CONF_VEHICLE_ID, None)
            new_data[CONF_VEHICLES] = [{"vehicle_id": vehicle_id}]

        hass.config_entries.async_update_entry(entry, data=new_data, version=2)
        _LOGGER.info(
            "Migrated config entry %s to version 2 (%s)", entry.title, monitoring_type
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up 511 Transit from a config entry."""
    api_key = entry.data[CONF_API_KEY]
    operator = entry.data[CONF_OPERATOR]
    operator_name = entry.data.get("operator_name", operator)
    monitoring_type = entry.data[CONF_MONITORING_TYPE]

    # Get options
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    startup_delay = entry.options.get(CONF_STARTUP_DELAY, DEFAULT_STARTUP_DELAY)
    enable_api_logging = entry.options.get(CONF_ENABLE_API_LOGGING, False)

    # Create API client
    session = async_get_clientsession(hass)
    client = Transit511ApiClient(api_key, session, enable_api_logging)

    # Initialize storage
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(GLOBAL_COORDINATORS, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})

    device_registry = dr.async_get(hass)
    global_coordinators = hass.data[DOMAIN][GLOBAL_COORDINATORS]
    entry_data = hass.data[DOMAIN][entry.entry_id]

    if monitoring_type == MONITORING_TYPE_STOP:
        stops = entry.data.get(CONF_STOPS, [])

        for stop_config in stops:
            stop_code = stop_config["stop_code"]
            line_id = stop_config.get("line_id", "")
            stop_name = stop_config.get("stop_name", stop_code)

            # Create device ID
            device_id = f"{operator}_{stop_code}"
            if line_id:
                device_id += f"_{line_id}"

            # Create device
            device = device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, device_id)},
                name=f"{stop_name}" + (f" - Line {line_id}" if line_id else ""),
                manufacturer=operator_name,
                model=f"Stop {stop_code}",
                suggested_area="Transit",
            )

            # Get or create global coordinator for this stop
            global_coord_key = f"{operator}_{stop_code}"

            if global_coord_key not in global_coordinators:
                _LOGGER.debug(
                    "Creating NEW GlobalStopCoordinator for %s stop %s (scan_interval=%ss)",
                    operator,
                    stop_code,
                    scan_interval,
                )
                global_coord = GlobalStopCoordinator(
                    hass,
                    client,
                    operator,
                    stop_code,
                    scan_interval,
                    startup_delay,
                    enable_api_logging,
                )
                await global_coord.async_config_entry_first_refresh()
                global_coordinators[global_coord_key] = global_coord
                _LOGGER.debug(
                    "GlobalStopCoordinator created and stored for %s_%s",
                    operator,
                    stop_code,
                )
                if enable_api_logging:
                    _LOGGER.info(
                        "✨ Created NEW GlobalStopCoordinator for %s stop %s (scan_interval=%ss)",
                        operator,
                        stop_code,
                        scan_interval,
                    )
            else:
                _LOGGER.debug(
                    "REUSING existing GlobalStopCoordinator for %s stop %s",
                    operator,
                    stop_code,
                )
                global_coord = global_coordinators[global_coord_key]
                if enable_api_logging:
                    _LOGGER.info(
                        "♻️ REUSING existing GlobalStopCoordinator for %s stop %s (no new API calls)",
                        operator,
                        stop_code,
                    )

            # Create device-specific coordinator
            coordinator = StopDeviceCoordinator(
                hass,
                global_coord,
                operator,
                stop_code,
                line_id,
                device_id,
                entry,
            )

            # Update device name with real stop name from API data
            if global_coord.data and global_coord.data.get("visits"):
                try:
                    visits = global_coord.data.get("visits", [])
                    if visits:
                        journey = visits[0].get("MonitoredVehicleJourney", {})
                        call = journey.get("MonitoredCall", {})
                        real_stop_name = call.get("StopPointName", stop_code)

                        # Update device with real stop name
                        device = device_registry.async_get_device(identifiers={(DOMAIN, device_id)})
                        if device:
                            new_name = f"{real_stop_name}" + (f" - Line {line_id}" if line_id else "")
                            device_registry.async_update_device(
                                device.id,
                                name=new_name,
                            )
                            _LOGGER.debug("Updated device name to: %s", new_name)
                except Exception as err:
                    _LOGGER.debug("Could not update device name immediately: %s", err)

            # Store coordinator
            entry_data[device_id] = coordinator

    else:  # Vehicle monitoring
        vehicles = entry.data.get(CONF_VEHICLES, [])

        for vehicle_config in vehicles:
            vehicle_id = vehicle_config["vehicle_id"]

            # Create device ID
            device_id = f"{operator}_vehicle_{vehicle_id}"

            # Create device
            device = device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, device_id)},
                name=f"Vehicle {vehicle_id}",
                manufacturer=operator_name,
                model=f"Vehicle {vehicle_id}",
                suggested_area="Transit",
            )

            # Create coordinator
            coordinator = Transit511VehicleCoordinator(
                hass,
                client,
                operator,
                vehicle_id,
                scan_interval,
                startup_delay,
                device_id,
                enable_api_logging,
            )
            await coordinator.async_config_entry_first_refresh()

            # Store coordinator
            entry_data[device_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Get the operator from this entry
        operator = entry.data[CONF_OPERATOR]
        monitoring_type = entry.data[CONF_MONITORING_TYPE]

        # Clean up global coordinators that were created for this entry's stops
        # (This prevents zombie coordinators from being reused after reload)
        if monitoring_type == MONITORING_TYPE_STOP:
            stops = entry.data.get(CONF_STOPS, [])
            global_coordinators = hass.data[DOMAIN].get(GLOBAL_COORDINATORS, {})

            for stop_config in stops:
                stop_code = stop_config["stop_code"]
                global_coord_key = f"{operator}_{stop_code}"

                # Only remove the shared global coordinator if no other config
                # entry still monitors the same (operator, stop_code). Otherwise
                # we'd strand a sibling entry that depends on this coordinator.
                other_uses_stop = any(
                    e.entry_id != entry.entry_id
                    and e.data.get(CONF_OPERATOR) == operator
                    and any(
                        s["stop_code"] == stop_code
                        for s in e.data.get(CONF_STOPS, [])
                    )
                    for e in hass.config_entries.async_entries(DOMAIN)
                )

                if not other_uses_stop and global_coord_key in global_coordinators:
                    _LOGGER.debug(
                        "Removing GlobalStopCoordinator for %s stop %s during unload",
                        operator,
                        stop_code,
                    )
                    global_coordinators.pop(global_coord_key, None)

        # Note: Vehicle monitoring doesn't use global coordinators,
        # so no cleanup needed for MONITORING_TYPE_VEHICLE

        # Remove entry-specific data
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow a device to be deleted from the UI and drop it from the entry.

    Without this, Home Assistant blocks manual device deletion while the
    integration is loaded. Removing the matching stop/vehicle from the entry
    data also stops it from being recreated on the next reload.
    """
    operator = entry.data.get(CONF_OPERATOR)
    device_ids = {ident[1] for ident in device_entry.identifiers if ident[0] == DOMAIN}
    if not device_ids:
        return True

    new_data = dict(entry.data)
    removed = False

    if entry.data.get(CONF_MONITORING_TYPE) == MONITORING_TYPE_STOP:
        kept = []
        for stop in new_data.get(CONF_STOPS, []):
            device_id = f"{operator}_{stop['stop_code']}"
            if stop.get("line_id"):
                device_id += f"_{stop['line_id']}"
            if device_id in device_ids:
                removed = True
            else:
                kept.append(stop)
        new_data[CONF_STOPS] = kept
    else:
        kept = []
        for vehicle in new_data.get(CONF_VEHICLES, []):
            device_id = f"{operator}_vehicle_{vehicle['vehicle_id']}"
            if device_id in device_ids:
                removed = True
            else:
                kept.append(vehicle)
        new_data[CONF_VEHICLES] = kept

    if removed:
        hass.config_entries.async_update_entry(entry, data=new_data)
        # Reload so coordinators for the removed device are torn down cleanly.
        hass.config_entries.async_schedule_reload(entry.entry_id)

    return True


class GlobalStopCoordinator(DataUpdateCoordinator):
    """Global coordinator that fetches data for a stop (shared across devices)."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Transit511ApiClient,
        operator: str,
        stop_code: str,
        scan_interval: int,
        startup_delay: int,
        enable_api_logging: bool = False,
    ) -> None:
        """Initialize the global coordinator."""
        self.client = client
        self.operator = operator
        self.stop_code = stop_code
        self.enable_api_logging = enable_api_logging
        self.scan_interval = scan_interval
        self.startup_delay = startup_delay
        self._first_update_done = False

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_global_{operator}_{stop_code}",
            # Start with the startup delay to avoid a rate-limit burst on load;
            # switched to scan_interval after the first successful fetch.
            update_interval=timedelta(seconds=startup_delay),
        )

    async def _async_update_data(self):
        """Fetch data from API (shared by all devices monitoring this stop)."""
        _LOGGER.debug(
            "GlobalStopCoordinator._async_update_data called for %s stop %s",
            self.operator,
            self.stop_code,
        )
        if self.enable_api_logging:
            _LOGGER.info(
                "🔄 GlobalStopCoordinator UPDATE - Operator: %s, Stop: %s",
                self.operator,
                self.stop_code
            )

        # The coordinator starts on the startup_delay interval (set in __init__)
        # so the second fetch is spaced out from the initial startup burst. The
        # flag flips on the immediate first fetch; the one-time switch back to the
        # user's scan_interval then happens on the next (delayed) fetch.
        if not self._first_update_done:
            self._first_update_done = True
        elif self.update_interval == timedelta(seconds=self.startup_delay):
            _LOGGER.debug(
                "Resuming %ss interval for %s stop %s after startup delay",
                self.scan_interval,
                self.operator,
                self.stop_code,
            )
            self.update_interval = timedelta(seconds=self.scan_interval)

        try:
            data = await self.client.get_stop_monitoring(self.operator, self.stop_code)

            # Extract the stop monitoring delivery
            delivery = data.get("ServiceDelivery", {}).get("StopMonitoringDelivery", {})

            # Extract monitored stop visits
            visits = delivery.get("MonitoredStopVisit", [])
            if not isinstance(visits, list):
                visits = [visits] if visits else []

            return {
                "response_timestamp": delivery.get("ResponseTimestamp"),
                "visits": visits,
            }

        except Transit511ApiError as err:
            raise UpdateFailed(f"Error fetching stop data: {err}") from err


class StopDeviceCoordinator(DataUpdateCoordinator):
    """Device-specific coordinator that filters data from global coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        global_coordinator: GlobalStopCoordinator,
        operator: str,
        stop_code: str,
        line_id: str | None,
        device_id: str,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the device coordinator."""
        self.global_coordinator = global_coordinator
        self.operator = operator
        self.stop_code = stop_code
        self.line_id = line_id
        self.device_id = device_id
        self.entry = entry
        self._device_name_updated = False

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{operator}_{stop_code}_{line_id or 'all'}",
            update_interval=None,  # Listener-driven only; never auto-polls
        )

        # Listen to global coordinator (not to self, to avoid infinite recursion)
        global_coordinator.async_add_listener(self._handle_global_coordinator_update)

    def _handle_global_coordinator_update(self) -> None:
        """Handle updates from global coordinator."""
        _LOGGER.debug(
            "StopDeviceCoordinator._handle_global_coordinator_update called for %s stop %s",
            self.operator,
            self.stop_code,
        )
        # Filter and process data
        self.async_set_updated_data(self._filter_data())

    def _filter_data(self):
        """Filter global coordinator data by line_id if specified."""
        if not self.global_coordinator.data:
            return {"response_timestamp": None, "visits": []}

        visits = self.global_coordinator.data.get("visits", [])

        # Filter by line_id if specified
        if self.line_id:
            filtered_visits = []
            for visit in visits:
                journey = visit.get("MonitoredVehicleJourney", {})
                line_ref = journey.get("LineRef", "")
                if line_ref == self.line_id:
                    filtered_visits.append(visit)
            visits = filtered_visits

        # Update device name if needed
        if visits and not self._device_name_updated:
            self._update_device_name(visits)

        return {
            "response_timestamp": self.global_coordinator.data.get("response_timestamp"),
            "visits": visits,
        }

    def _update_device_name(self, visits):
        """Update device name with info from first visit."""
        try:
            journey = visits[0].get("MonitoredVehicleJourney", {})
            call = journey.get("MonitoredCall", {})
            stop_name = call.get("StopPointName", self.stop_code)
            line_ref = journey.get("LineRef", "")
            line_name = journey.get("PublishedLineName", line_ref)

            # Determine vehicle type
            vehicle_type = get_vehicle_type(self.operator, line_ref, journey.get("VehicleMode"))
            vehicle_type_str = "Train" if vehicle_type == "train" else "Bus"

            # Get directions
            directions = set()
            for visit in visits:
                j = visit.get("MonitoredVehicleJourney", {})
                direction = j.get("DirectionRef", "")
                if direction:
                    directions.add(direction)

            direction_str = ""
            if "IB" in directions and "OB" in directions:
                direction_str = " IB/OB"
            elif "IB" in directions:
                direction_str = " IB"
            elif "OB" in directions:
                direction_str = " OB"

            # Update device
            device_registry = dr.async_get(self.hass)
            device = device_registry.async_get_device(identifiers={(DOMAIN, self.device_id)})
            if device:
                new_name = f"{stop_name}{direction_str}"
                if self.line_id:
                    new_name = f"{line_ref} {line_name.title()} {vehicle_type_str} - {new_name}"

                device_registry.async_update_device(
                    device.id,
                    name=new_name,
                )
                _LOGGER.debug("Updated device name to: %s", new_name)

            self._device_name_updated = True
        except Exception as err:
            _LOGGER.debug("Could not update device name: %s", err)

    async def _async_update_data(self):
        """This coordinator doesn't update itself, it listens to global."""
        return self._filter_data()


class Transit511VehicleCoordinator(DataUpdateCoordinator):
    """Coordinator for vehicle monitoring data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Transit511ApiClient,
        operator: str,
        vehicle_id: str,
        scan_interval: int,
        startup_delay: int,
        device_id: str,
        enable_api_logging: bool = False,
    ) -> None:
        """Initialize the coordinator."""
        self.client = client
        self.operator = operator
        self.vehicle_id = vehicle_id
        self.device_id = device_id
        self.enable_api_logging = enable_api_logging
        self.scan_interval = scan_interval
        self.startup_delay = startup_delay
        self._device_name_updated = False
        self._first_update_done = False

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{operator}_vehicle_{vehicle_id}",
            # Start with the startup delay to avoid a rate-limit burst on load;
            # switched to scan_interval after the first successful fetch.
            update_interval=timedelta(seconds=startup_delay),
        )

    async def _async_update_data(self):
        """Fetch data from API."""
        if self.enable_api_logging:
            _LOGGER.info(
                "🔄 VehicleCoordinator UPDATE - Operator: %s, Vehicle: %s",
                self.operator,
                self.vehicle_id
            )

        # The coordinator starts on the startup_delay interval (set in __init__)
        # so the second fetch is spaced out from the initial startup burst. The
        # flag flips on the immediate first fetch; the one-time switch back to the
        # user's scan_interval then happens on the next (delayed) fetch.
        if not self._first_update_done:
            self._first_update_done = True
        elif self.update_interval == timedelta(seconds=self.startup_delay):
            _LOGGER.debug(
                "Resuming %ss interval for %s vehicle %s after startup delay",
                self.scan_interval,
                self.operator,
                self.vehicle_id,
            )
            self.update_interval = timedelta(seconds=self.scan_interval)

        try:
            data = await self.client.get_vehicle_monitoring(
                self.operator, self.vehicle_id
            )

            # Extract the vehicle monitoring delivery
            delivery = data.get("ServiceDelivery", {}).get(
                "VehicleMonitoringDelivery", {}
            )

            # Extract vehicle activities
            activities = delivery.get("VehicleActivity", [])
            if not isinstance(activities, list):
                activities = [activities] if activities else []

            # Update device name if we have data and haven't updated yet
            if activities and not self._device_name_updated:
                self._update_device_name(activities)

            return {
                "response_timestamp": delivery.get("ResponseTimestamp"),
                "activities": activities,
            }

        except Transit511ApiError as err:
            raise UpdateFailed(f"Error fetching vehicle data: {err}") from err

    def _update_device_name(self, activities):
        """Update device name with line information from first activity."""
        try:
            journey = activities[0].get("MonitoredVehicleJourney", {})
            line_ref = journey.get("LineRef", "")
            line_name = journey.get("PublishedLineName", line_ref)

            # Determine vehicle type
            vehicle_type = get_vehicle_type(self.operator, line_ref, journey.get("VehicleMode"))
            vehicle_type_str = "Train" if vehicle_type == "train" else "Bus"

            # Update device
            device_registry = dr.async_get(self.hass)
            device = device_registry.async_get_device(identifiers={(DOMAIN, self.device_id)})
            if device:
                new_name = f"{line_ref} {line_name.title()} {vehicle_type_str} - Vehicle {self.vehicle_id}"
                device_registry.async_update_device(
                    device.id,
                    name=new_name,
                )
                _LOGGER.debug("Updated vehicle device name to: %s", new_name)

            self._device_name_updated = True
        except Exception as err:
            _LOGGER.debug("Could not update vehicle device name: %s", err)
