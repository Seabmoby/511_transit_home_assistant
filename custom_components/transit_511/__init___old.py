"""The 511 Transit integration."""
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
    CONF_MONITORING_TYPE,
    CONF_OPERATOR,
    CONF_STOP_CODE,
    CONF_VEHICLE_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MONITORING_TYPE_STOP,
    MONITORING_TYPE_VEHICLE,
    get_vehicle_type,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.DEVICE_TRACKER]

# Key for storing global coordinators in hass.data
GLOBAL_COORDINATORS = "global_coordinators"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up 511 Transit from a config entry."""
    api_key = entry.data[CONF_API_KEY]
    monitoring_type = entry.data[CONF_MONITORING_TYPE]

    # Get scan interval and logging option from options
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    enable_api_logging = entry.options.get(CONF_ENABLE_API_LOGGING, False)

    # Create API client with logging setting
    session = async_get_clientsession(hass)
    client = Transit511ApiClient(api_key, session, enable_api_logging)

    # Create device in device registry
    device_registry = dr.async_get(hass)

    # Initialize global coordinators storage
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(GLOBAL_COORDINATORS, {})

    if monitoring_type == MONITORING_TYPE_STOP:
        operator = entry.data[CONF_OPERATOR]
        stop_code = entry.data[CONF_STOP_CODE]
        stop_name = entry.data.get("stop_name", stop_code)
        operator_name = entry.data.get("operator_name", operator)
        line_id = entry.data.get("line_id")

        # Create device identifier
        device_id = f"{operator}_{stop_code}"
        if line_id:
            device_id += f"_{line_id}"

        # Create or update device
        device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device_id)},
            name=entry.title,
            manufacturer=operator_name,
            model=f"Stop {stop_code}",
            suggested_area="Transit",
        )

        # Get or create global coordinator for this stop
        global_coord_key = f"{operator}_{stop_code}"
        global_coordinators = hass.data[DOMAIN][GLOBAL_COORDINATORS]

        if global_coord_key not in global_coordinators:
            # Create new global coordinator for this stop
            global_coord = GlobalStopCoordinator(
                hass,
                client,
                operator,
                stop_code,
                scan_interval,
                enable_api_logging,
            )
            # Fetch initial data
            await global_coord.async_config_entry_first_refresh()
            global_coordinators[global_coord_key] = global_coord
            if enable_api_logging:
                _LOGGER.info(
                    "✨ Created NEW GlobalStopCoordinator for %s stop %s (scan_interval=%ss)",
                    operator,
                    stop_code,
                    scan_interval,
                )
        else:
            global_coord = global_coordinators[global_coord_key]
            if enable_api_logging:
                _LOGGER.info(
                    "♻️  REUSING existing GlobalStopCoordinator for %s stop %s (no new API calls)",
                    operator,
                    stop_code,
                )

        # Create device-specific coordinator that filters data from global coordinator
        coordinator = StopDeviceCoordinator(
            hass,
            global_coord,
            operator,
            stop_code,
            line_id,
            device_id,
            entry,
        )
    else:
        operator = entry.data[CONF_OPERATOR]
        vehicle_id = entry.data[CONF_VEHICLE_ID]
        operator_name = entry.data.get("operator_name", operator)

        # Create device identifier
        device_id = f"{operator}_vehicle_{vehicle_id}"

        # Create or update device
        device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device_id)},
            name=entry.title,
            manufacturer=operator_name,
            model=f"Vehicle {vehicle_id}",
            suggested_area="Transit",
        )

        coordinator = Transit511VehicleCoordinator(
            hass,
            client,
            operator,
            vehicle_id,
            scan_interval,
            device_id,
            enable_api_logging,
        )
        # Fetch initial data for vehicle coordinator
        await coordinator.async_config_entry_first_refresh()

    # Store coordinator (device-specific for stops, regular for vehicles)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward entry setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


class GlobalStopCoordinator(DataUpdateCoordinator):
    """Global coordinator that fetches data for a stop (shared across devices)."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Transit511ApiClient,
        operator: str,
        stop_code: str,
        scan_interval: int,
        enable_api_logging: bool = False,
    ) -> None:
        """Initialize the global coordinator."""
        self.client = client
        self.operator = operator
        self.stop_code = stop_code
        self.enable_api_logging = enable_api_logging

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_global_{operator}_{stop_code}",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self):
        """Fetch data from API (shared by all devices monitoring this stop)."""
        if self.enable_api_logging:
            _LOGGER.info(
                "🔄 GlobalStopCoordinator UPDATE - Operator: %s, Stop: %s",
                self.operator,
                self.stop_code
            )
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


class StopDeviceCoordinator:
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
        self.hass = hass
        self.global_coordinator = global_coordinator
        self.operator = operator
        self.stop_code = stop_code
        self.line_id = line_id
        self.device_id = device_id
        self.entry = entry
        self._device_name_updated = False

        # Register listener for global coordinator updates
        self._unsub_refresh = global_coordinator.async_add_listener(
            self._handle_global_update
        )

    async def _handle_global_update(self) -> None:
        """Handle updates from global coordinator."""
        # Update device name on first successful fetch
        if self.data.get("visits") and not self._device_name_updated:
            await self._update_device_name(self.data["visits"])
            self._device_name_updated = True

    @property
    def data(self) -> dict:
        """Return filtered data for this device."""
        global_data = self.global_coordinator.data
        if not global_data:
            return {"response_timestamp": None, "visits": []}

        visits = global_data.get("visits", [])

        # Filter by line_id if specified
        if self.line_id:
            filtered_visits = []
            for visit in visits:
                journey = visit.get("MonitoredVehicleJourney", {})
                line_ref = journey.get("LineRef")
                if line_ref == self.line_id:
                    filtered_visits.append(visit)
            visits = filtered_visits

        return {
            "response_timestamp": global_data.get("response_timestamp"),
            "visits": visits,
        }

    @property
    def last_update_success(self) -> bool:
        """Return if last update was successful."""
        return self.global_coordinator.last_update_success

    def async_add_listener(self, update_callback, context=None) -> callable:
        """Listen for data updates."""
        return self.global_coordinator.async_add_listener(update_callback, context)

    async def _update_device_name(self, visits: list) -> None:
        """Update device name and entry title with API data."""
        if not visits:
            return

        journey = visits[0].get("MonitoredVehicleJourney", {})
        line_ref = journey.get("LineRef")
        line_name = journey.get("PublishedLineName")
        stop_name = journey.get("MonitoredCall", {}).get("StopPointName")
        mode = journey.get("VehicleMode")

        # Collect all unique directions from visits
        directions = set()
        for visit in visits:
            direction = visit.get("MonitoredVehicleJourney", {}).get("DirectionRef")
            if direction:
                directions.add(direction)

        if line_ref and stop_name:
            # Get vehicle type
            vehicle_type = get_vehicle_type(self.operator, line_ref, mode)
            vehicle_type_title = vehicle_type.title() if vehicle_type else "Transit"

            # Title-case the line name (e.g., "HAIGHT-NORIEGA" -> "Haight-Noriega")
            line_name_formatted = line_name.title() if line_name else ""
            line_name_part = f" {line_name_formatted}" if line_name_formatted else ""

            # Build direction suffix (e.g., "Outbound", "Inbound", "Inbound/Outbound")
            direction_suffix = ""
            if directions:
                direction_names = []
                if "IB" in directions:
                    direction_names.append("Inbound")
                if "OB" in directions:
                    direction_names.append("Outbound")
                if direction_names:
                    direction_suffix = f" {'/'.join(direction_names)}"

            # Build device name: [line] [line_name] [vehicle_type] - [stop_name] [direction]
            device_name = f"{line_ref}{line_name_part} {vehicle_type_title} - {stop_name}{direction_suffix}"

            # Update device in registry
            device_registry = dr.async_get(self.hass)
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, self.device_id)}
            )
            if device:
                device_registry.async_update_device(
                    device.id,
                    name=device_name,
                )

            # Update the config entry title to match
            if self.entry and self.entry.title != device_name:
                self.hass.config_entries.async_update_entry(
                    self.entry,
                    title=device_name,
                )


class Transit511VehicleCoordinator(DataUpdateCoordinator):
    """Coordinator for vehicle monitoring data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Transit511ApiClient,
        operator: str,
        vehicle_id: str,
        scan_interval: int,
        device_id: str,
        enable_api_logging: bool = False,
    ) -> None:
        """Initialize the coordinator."""
        self.client = client
        self.operator = operator
        self.vehicle_id = vehicle_id
        self.device_id = device_id
        self.enable_api_logging = enable_api_logging
        self._device_name_updated = False

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{operator}_vehicle_{vehicle_id}",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self):
        """Fetch data from API."""
        if self.enable_api_logging:
            _LOGGER.info(
                "🔄 VehicleCoordinator UPDATE - Operator: %s, Vehicle: %s",
                self.operator,
                self.vehicle_id
            )
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

            # Update device name with API data on first successful fetch
            if activities and not self._device_name_updated:
                await self._update_device_name(activities)
                self._device_name_updated = True

            return {
                "response_timestamp": delivery.get("ResponseTimestamp"),
                "activities": activities,
            }

        except Transit511ApiError as err:
            raise UpdateFailed(f"Error fetching vehicle data: {err}") from err

    async def _update_device_name(self, activities: list) -> None:
        """Update device name and entry title with API data."""
        if not activities:
            return

        journey = activities[0].get("MonitoredVehicleJourney", {})
        line_ref = journey.get("LineRef")
        line_name = journey.get("PublishedLineName")
        mode = journey.get("VehicleMode")

        if line_ref:
            # Get vehicle type
            vehicle_type = get_vehicle_type(self.operator, line_ref, mode)
            vehicle_type_title = vehicle_type.title() if vehicle_type else "Transit"

            # Title-case the line name (e.g., "HAIGHT-NORIEGA" -> "Haight-Noriega")
            line_name_formatted = line_name.title() if line_name else ""
            line_name_part = f" {line_name_formatted}" if line_name_formatted else ""

            # Build device name: [line] [line_name] [vehicle_type] - Vehicle [vehicle_id]
            device_name = f"{line_ref}{line_name_part} {vehicle_type_title} - Vehicle {self.vehicle_id}"

            # Update device in registry
            device_registry = dr.async_get(self.hass)
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, self.device_id)}
            )
            if device:
                device_registry.async_update_device(
                    device.id,
                    name=device_name,
                )

            # Also update the config entry title to match
            entry = None
            for config_entry in self.hass.config_entries.async_entries(DOMAIN):
                if config_entry.entry_id in self.hass.data.get(DOMAIN, {}):
                    coordinator = self.hass.data[DOMAIN][config_entry.entry_id]
                    if coordinator == self:
                        entry = config_entry
                        break

            if entry and entry.title != device_name:
                self.hass.config_entries.async_update_entry(
                    entry,
                    title=device_name,
                )
