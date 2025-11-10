"""Sensor platform for 511 Transit integration."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import StopDeviceCoordinator
from .const import (
    ATTR_DESTINATION,
    ATTR_DIRECTION,
    ATTR_LAST_UPDATED,
    ATTR_LINE,
    ATTR_LINE_NAME,
    ATTR_OCCUPANCY,
    ATTR_OPERATOR,
    ATTR_OPERATOR_NAME,
    ATTR_STOP_CODE,
    ATTR_STOP_NAME,
    ATTR_VEHICLE_ID,
    ATTR_VEHICLE_TYPE,
    ATTR_VISITS,
    CONF_ENABLED_ENTITIES,
    CONF_LINE_ID,
    CONF_MONITORING_TYPE,
    CONF_OPERATOR,
    CONF_STOP_CODE,
    DEFAULT_ENABLED_ENTITIES,
    DIRECTION_INBOUND,
    DIRECTION_OUTBOUND,
    DOMAIN,
    ENTITY_TYPE_API_OK,
    ENTITY_TYPE_API_TIMESTAMP,
    ENTITY_TYPE_COUNT,
    ENTITY_TYPE_IB_COUNT,
    ENTITY_TYPE_IB_NEXT_ARRIVAL_MIN,
    ENTITY_TYPE_IB_NEXT_ARRIVAL_TIME,
    ENTITY_TYPE_IB_NEXT_THREE,
    ENTITY_TYPE_IB_NEXT_VEHICLE,
    ENTITY_TYPE_NEXT_ARRIVAL_MIN,
    ENTITY_TYPE_NEXT_ARRIVAL_TIME,
    ENTITY_TYPE_NEXT_DESTINATION,
    ENTITY_TYPE_NEXT_OCCUPANCY,
    ENTITY_TYPE_NEXT_THREE,
    ENTITY_TYPE_NEXT_VEHICLE,
    ENTITY_TYPE_OB_COUNT,
    ENTITY_TYPE_OB_NEXT_ARRIVAL_MIN,
    ENTITY_TYPE_OB_NEXT_ARRIVAL_TIME,
    ENTITY_TYPE_OB_NEXT_THREE,
    ENTITY_TYPE_OB_NEXT_VEHICLE,
    MONITORING_TYPE_STOP,
    get_vehicle_icon,
    get_vehicle_type,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up 511 Transit sensors from a config entry."""
    _LOGGER.info("Setting up sensors for entry: %s", entry.title)

    # Only set up sensors for stop monitoring
    if entry.data.get(CONF_MONITORING_TYPE) != MONITORING_TYPE_STOP:
        _LOGGER.info("Skipping sensor setup - not stop monitoring")
        return

    # Get all coordinators for this entry
    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
    _LOGGER.info("Found %d coordinators for entry", len(entry_data))

    # Get enabled entities from options (default to common entities if not set)
    enabled_entities = entry.options.get(CONF_ENABLED_ENTITIES, DEFAULT_ENABLED_ENTITIES)
    _LOGGER.info("Enabled entities: %s", enabled_entities)

    entities: list[SensorEntity | BinarySensorEntity] = []

    # Create sensors for each stop/device in this entry
    for device_id, coordinator in entry_data.items():
        _LOGGER.info("Creating sensors for device: %s", device_id)
        # Create sensors based on enabled entities
        if ENTITY_TYPE_COUNT in enabled_entities:
            entities.append(Transit511CountSensor(coordinator, entry))

        if ENTITY_TYPE_API_TIMESTAMP in enabled_entities:
            entities.append(Transit511ApiTimestampSensor(coordinator, entry))

        if ENTITY_TYPE_NEXT_ARRIVAL_MIN in enabled_entities:
            entities.append(Transit511NextArrivalMinSensor(coordinator, entry))

        if ENTITY_TYPE_NEXT_ARRIVAL_TIME in enabled_entities:
            entities.append(Transit511NextArrivalTimeSensor(coordinator, entry))

        if ENTITY_TYPE_NEXT_VEHICLE in enabled_entities:
            entities.append(Transit511NextVehicleSensor(coordinator, entry))

        if ENTITY_TYPE_NEXT_DESTINATION in enabled_entities:
            entities.append(Transit511NextDestinationSensor(coordinator, entry))

        if ENTITY_TYPE_NEXT_OCCUPANCY in enabled_entities:
            entities.append(Transit511NextOccupancySensor(coordinator, entry))

        if ENTITY_TYPE_NEXT_THREE in enabled_entities:
            entities.append(Transit511NextThreeSensor(coordinator, entry))

        if ENTITY_TYPE_API_OK in enabled_entities:
            entities.append(Transit511ApiOkSensor(coordinator, entry))

        # Direction-filtered entities (IB)
        if ENTITY_TYPE_IB_COUNT in enabled_entities:
            entities.append(Transit511DirectionCountSensor(coordinator, entry, DIRECTION_INBOUND))

        if ENTITY_TYPE_IB_NEXT_ARRIVAL_MIN in enabled_entities:
            entities.append(Transit511DirectionNextArrivalMinSensor(coordinator, entry, DIRECTION_INBOUND))

        if ENTITY_TYPE_IB_NEXT_ARRIVAL_TIME in enabled_entities:
            entities.append(Transit511DirectionNextArrivalTimeSensor(coordinator, entry, DIRECTION_INBOUND))

        if ENTITY_TYPE_IB_NEXT_VEHICLE in enabled_entities:
            entities.append(Transit511DirectionNextVehicleSensor(coordinator, entry, DIRECTION_INBOUND))

        if ENTITY_TYPE_IB_NEXT_THREE in enabled_entities:
            entities.append(Transit511DirectionNextThreeSensor(coordinator, entry, DIRECTION_INBOUND))

        # Direction-filtered entities (OB)
        if ENTITY_TYPE_OB_COUNT in enabled_entities:
            entities.append(Transit511DirectionCountSensor(coordinator, entry, DIRECTION_OUTBOUND))

        if ENTITY_TYPE_OB_NEXT_ARRIVAL_MIN in enabled_entities:
            entities.append(Transit511DirectionNextArrivalMinSensor(coordinator, entry, DIRECTION_OUTBOUND))

        if ENTITY_TYPE_OB_NEXT_ARRIVAL_TIME in enabled_entities:
            entities.append(Transit511DirectionNextArrivalTimeSensor(coordinator, entry, DIRECTION_OUTBOUND))

        if ENTITY_TYPE_OB_NEXT_VEHICLE in enabled_entities:
            entities.append(Transit511DirectionNextVehicleSensor(coordinator, entry, DIRECTION_OUTBOUND))

        if ENTITY_TYPE_OB_NEXT_THREE in enabled_entities:
            entities.append(Transit511DirectionNextThreeSensor(coordinator, entry, DIRECTION_OUTBOUND))

    _LOGGER.info("Adding %d sensor entities", len(entities))
    async_add_entities(entities)


class Transit511BaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for 511 Transit sensors."""

    def __init__(
        self,
        coordinator: StopDeviceCoordinator,
        entry: ConfigEntry,
        entity_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._operator = entry.data[CONF_OPERATOR]
        self._stop_code = entry.data[CONF_STOP_CODE]
        self._line_id = entry.data.get(CONF_LINE_ID)
        self._stop_name = entry.data.get("stop_name", self._stop_code)
        self._operator_name = entry.data.get("operator_name", self._operator)
        self._entity_type = entity_type
        self._entry = entry

        # Set entity attributes
        # Build unique_id with available data at init time
        line_part = f"_{self._line_id}" if self._line_id else ""
        self._attr_unique_id = f"{DOMAIN}_{self._operator}{line_part}_{self._stop_code}_{entity_type}"

        # Name will be dynamically updated based on API data
        self._attr_has_entity_name = False

        # Link to device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
        )

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        # Build name: [stop_name] [directions] | [sensor_type]
        visits = self._get_visits()

        # Get stop name and directions from API
        stop_name = self._stop_name
        directions = set()

        if visits:
            # Get stop name from first visit
            stop_name = (
                visits[0]
                .get("MonitoredVehicleJourney", {})
                .get("MonitoredCall", {})
                .get("StopPointName", self._stop_name)
            )

            # Collect all directions
            for visit in visits:
                direction = visit.get("MonitoredVehicleJourney", {}).get("DirectionRef")
                if direction:
                    directions.add(direction)

        # Build directions string (e.g., "IB OB" or just "IB")
        directions_str = " ".join(sorted(directions)) if directions else ""

        # Convert entity type to readable name (e.g., "next_arrival_min" -> "Next Arrival Min")
        sensor_type = self._entity_type.replace("_", " ").title()

        # Build final name: [stop_name] [directions] | [sensor_type]
        if directions_str:
            return f"{stop_name} {directions_str} | {sensor_type}"
        else:
            return f"{stop_name} | {sensor_type}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        # Get line info from actual API data
        visits = self._get_visits()
        line_ref = None
        line_name = None
        directions = set()

        if visits:
            # Get line info from first visit
            journey = visits[0].get("MonitoredVehicleJourney", {})
            line_ref = journey.get("LineRef")
            line_name = journey.get("PublishedLineName")

            # Collect all directions present in visits
            for visit in visits:
                direction = visit.get("MonitoredVehicleJourney", {}).get("DirectionRef")
                if direction:
                    directions.add(direction)

        attrs = {
            ATTR_OPERATOR: self._operator,
            ATTR_OPERATOR_NAME: self._operator_name,
            ATTR_STOP_CODE: self._stop_code,
            ATTR_STOP_NAME: self._stop_name,
            ATTR_LINE: line_ref or self._line_id,  # Use API data or fallback to config
            ATTR_LINE_NAME: line_name,
            ATTR_LAST_UPDATED: self.coordinator.data.get("response_timestamp"),
        }

        # Add directions if present (e.g., "IB, OB" or just "IB")
        if directions:
            attrs["directions"] = ", ".join(sorted(directions))

        # Add vehicle type if we can determine it
        vehicle_type = self._get_vehicle_type()
        if vehicle_type:
            attrs[ATTR_VEHICLE_TYPE] = vehicle_type

        return attrs

    def _get_visits(self, direction: str | None = None) -> list[dict[str, Any]]:
        """Get visits, optionally filtered by direction."""
        visits = self.coordinator.data.get("visits", [])

        if direction:
            return [
                v
                for v in visits
                if v.get("MonitoredVehicleJourney", {}).get("DirectionRef") == direction
            ]

        return visits

    def _get_next_visit(self, direction: str | None = None) -> dict[str, Any] | None:
        """Get the next visit."""
        visits = self._get_visits(direction)
        return visits[0] if visits else None

    def _get_arrival_time(self, visit: dict[str, Any] | None) -> datetime | None:
        """Extract arrival time from a visit."""
        if not visit:
            return None

        call = visit.get("MonitoredVehicleJourney", {}).get("MonitoredCall", {})
        exp = call.get("ExpectedArrivalTime") or call.get("AimedArrivalTime")

        if exp:
            try:
                return dt_util.parse_datetime(exp)
            except (ValueError, TypeError):
                return None

        return None

    def _get_vehicle_type(self) -> str | None:
        """Determine vehicle type from visits or line ID."""
        # First try to get from first visit
        visits = self._get_visits()
        if visits:
            journey = visits[0].get("MonitoredVehicleJourney", {})
            line_ref = journey.get("LineRef") or self._line_id
            mode = journey.get("VehicleMode")  # If API provides it
            if line_ref:
                return get_vehicle_type(self._operator, line_ref, mode)

        # Fallback to configured line ID
        if self._line_id:
            return get_vehicle_type(self._operator, self._line_id)

        return None

    def _get_dynamic_icon(self) -> str:
        """Get icon based on vehicle type."""
        vehicle_type = self._get_vehicle_type()
        if vehicle_type:
            return get_vehicle_icon(vehicle_type)
        # Default fallback
        return "mdi:transit-connection-variant"


class Transit511CountSensor(Transit511BaseSensor):
    """Sensor for count of upcoming arrivals."""

    def __init__(self, coordinator: StopDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, ENTITY_TYPE_COUNT)
        self._attr_icon = "mdi:numeric"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return len(self._get_visits())


class Transit511ApiTimestampSensor(Transit511BaseSensor):
    """Sensor for API response timestamp."""

    def __init__(self, coordinator: StopDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, ENTITY_TYPE_API_TIMESTAMP)
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Return the state of the sensor."""
        timestamp = self.coordinator.data.get("response_timestamp")
        if timestamp:
            try:
                return dt_util.parse_datetime(timestamp)
            except (ValueError, TypeError):
                return None
        return None


class Transit511NextArrivalMinSensor(Transit511BaseSensor):
    """Sensor for next arrival in minutes."""

    def __init__(self, coordinator: StopDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, ENTITY_TYPE_NEXT_ARRIVAL_MIN)
        self._attr_native_unit_of_measurement = "min"

    @property
    def icon(self) -> str:
        """Return dynamic icon based on vehicle type."""
        return self._get_dynamic_icon()

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        visit = self._get_next_visit()
        arrival_time = self._get_arrival_time(visit)

        if arrival_time:
            now = dt_util.now()
            minutes = (arrival_time - now).total_seconds() / 60
            return round(minutes)

        return None


class Transit511NextArrivalTimeSensor(Transit511BaseSensor):
    """Sensor for next arrival time."""

    def __init__(self, coordinator: StopDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, ENTITY_TYPE_NEXT_ARRIVAL_TIME)
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Return the state of the sensor."""
        visit = self._get_next_visit()
        return self._get_arrival_time(visit)


class Transit511NextVehicleSensor(Transit511BaseSensor):
    """Sensor for next vehicle ID."""

    def __init__(self, coordinator: StopDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, ENTITY_TYPE_NEXT_VEHICLE)

    @property
    def icon(self) -> str:
        """Return dynamic icon based on vehicle type."""
        # Use vehicle-specific icon variant
        vehicle_type = self._get_vehicle_type()
        if vehicle_type:
            icon = get_vehicle_icon(vehicle_type)
            # Use -car variant for vehicle ID sensor
            return icon.replace("mdi:train", "mdi:train-car").replace("mdi:bus", "mdi:bus-side")
        return "mdi:card-account-details-outline"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        visit = self._get_next_visit()
        if visit:
            return visit.get("MonitoredVehicleJourney", {}).get("VehicleRef")
        return None


class Transit511NextDestinationSensor(Transit511BaseSensor):
    """Sensor for next destination."""

    def __init__(self, coordinator: StopDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, ENTITY_TYPE_NEXT_DESTINATION)
        self._attr_icon = "mdi:flag-checkered"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        visit = self._get_next_visit()
        if visit:
            return visit.get("MonitoredVehicleJourney", {}).get("DestinationName")
        return None


class Transit511NextOccupancySensor(Transit511BaseSensor):
    """Sensor for next vehicle occupancy."""

    def __init__(self, coordinator: StopDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, ENTITY_TYPE_NEXT_OCCUPANCY)
        self._attr_icon = "mdi:seat-recline-normal"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        visit = self._get_next_visit()
        if visit:
            return visit.get("MonitoredVehicleJourney", {}).get("Occupancy")
        return None


class Transit511NextThreeSensor(Transit511BaseSensor):
    """Sensor for next three arrivals in minutes."""

    def __init__(self, coordinator: StopDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, ENTITY_TYPE_NEXT_THREE)
        self._attr_icon = "mdi:format-list-numbered"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        visits = self._get_visits()[:3]
        now = dt_util.now()
        minutes = []

        for visit in visits:
            arrival_time = self._get_arrival_time(visit)
            if arrival_time:
                mins = round((arrival_time - now).total_seconds() / 60)
                minutes.append(str(mins))

        return ", ".join(minutes) if minutes else "none"


class Transit511ApiOkSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for API connectivity."""

    def __init__(self, coordinator: StopDeviceCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._operator = entry.data[CONF_OPERATOR]
        self._stop_code = entry.data[CONF_STOP_CODE]
        self._line_id = entry.data.get(CONF_LINE_ID)
        self._stop_name = entry.data.get("stop_name", self._stop_code)
        self._entry = entry

        line_part = f"_{self._line_id}" if self._line_id else ""
        self._attr_unique_id = f"{DOMAIN}_{self._operator}{line_part}_{self._stop_code}_{ENTITY_TYPE_API_OK}"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_has_entity_name = False

        # Link to device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
        )

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        # Build name: [stop_name] [directions] | API OK
        visits = self.coordinator.data.get("visits", [])

        # Get stop name and directions from API
        stop_name = self._stop_name
        directions = set()

        if visits:
            # Get stop name from first visit
            stop_name = (
                visits[0]
                .get("MonitoredVehicleJourney", {})
                .get("MonitoredCall", {})
                .get("StopPointName", self._stop_name)
            )

            # Collect all directions
            for visit in visits:
                direction = visit.get("MonitoredVehicleJourney", {}).get("DirectionRef")
                if direction:
                    directions.add(direction)

        # Build directions string
        directions_str = " ".join(sorted(directions)) if directions else ""

        # Build final name
        if directions_str:
            return f"{stop_name} {directions_str} | API OK"
        else:
            return f"{stop_name} | API OK"

    @property
    def is_on(self) -> bool:
        """Return true if API is responding."""
        return len(self.coordinator.data.get("visits", [])) > 0 or self.coordinator.last_update_success


class Transit511DirectionCountSensor(Transit511BaseSensor):
    """Sensor for count of arrivals filtered by direction."""

    def __init__(
        self,
        coordinator: StopDeviceCoordinator,
        entry: ConfigEntry,
        direction: str,
    ) -> None:
        """Initialize the sensor."""
        direction_prefix = "ib" if direction == DIRECTION_INBOUND else "ob"
        super().__init__(coordinator, entry, f"{direction_prefix}_count")
        self._direction = direction
        self._attr_icon = "mdi:numeric"

    @property
    def name(self) -> str:
        """Return the name of the sensor (override to use filtered direction)."""
        # Build name: [stop_name] [direction] | [sensor_type]
        visits = self._get_visits(self._direction)

        # Get stop name from API
        stop_name = self._stop_name
        if visits:
            stop_name = (
                visits[0]
                .get("MonitoredVehicleJourney", {})
                .get("MonitoredCall", {})
                .get("StopPointName", self._stop_name)
            )

        # Convert entity type to readable name
        sensor_type = self._entity_type.replace("_", " ").title()

        # Build final name with specific direction
        return f"{stop_name} {self._direction} | {sensor_type}"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return len(self._get_visits(self._direction))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        attrs[ATTR_DIRECTION] = self._direction
        # Add human-readable direction name
        attrs["direction_name"] = "Inbound" if self._direction == DIRECTION_INBOUND else "Outbound"
        return attrs


class Transit511DirectionNextArrivalMinSensor(Transit511BaseSensor):
    """Sensor for next arrival in minutes filtered by direction."""

    def __init__(
        self,
        coordinator: StopDeviceCoordinator,
        entry: ConfigEntry,
        direction: str,
    ) -> None:
        """Initialize the sensor."""
        direction_prefix = "ib" if direction == DIRECTION_INBOUND else "ob"
        super().__init__(coordinator, entry, f"{direction_prefix}_next_arrival_min")
        self._direction = direction
        self._attr_native_unit_of_measurement = "min"

    @property
    def name(self) -> str:
        """Return the name of the sensor (override to use filtered direction)."""
        # Build name: [stop_name] [direction] | [sensor_type]
        visits = self._get_visits(self._direction)

        # Get stop name from API
        stop_name = self._stop_name
        if visits:
            stop_name = (
                visits[0]
                .get("MonitoredVehicleJourney", {})
                .get("MonitoredCall", {})
                .get("StopPointName", self._stop_name)
            )

        # Convert entity type to readable name
        sensor_type = self._entity_type.replace("_", " ").title()

        # Build final name with specific direction
        return f"{stop_name} {self._direction} | {sensor_type}"

    @property
    def icon(self) -> str:
        """Return dynamic icon based on vehicle type."""
        return self._get_dynamic_icon()

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        visit = self._get_next_visit(self._direction)
        arrival_time = self._get_arrival_time(visit)

        if arrival_time:
            now = dt_util.now()
            minutes = (arrival_time - now).total_seconds() / 60
            return round(minutes)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        attrs[ATTR_DIRECTION] = self._direction
        # Add human-readable direction name
        attrs["direction_name"] = "Inbound" if self._direction == DIRECTION_INBOUND else "Outbound"
        return attrs


class Transit511DirectionNextArrivalTimeSensor(Transit511BaseSensor):
    """Sensor for next arrival time filtered by direction."""

    def __init__(
        self,
        coordinator: StopDeviceCoordinator,
        entry: ConfigEntry,
        direction: str,
    ) -> None:
        """Initialize the sensor."""
        direction_prefix = "ib" if direction == DIRECTION_INBOUND else "ob"
        super().__init__(coordinator, entry, f"{direction_prefix}_next_arrival_time")
        self._direction = direction
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def name(self) -> str:
        """Return the name of the sensor (override to use filtered direction)."""
        # Build name: [stop_name] [direction] | [sensor_type]
        visits = self._get_visits(self._direction)

        # Get stop name from API
        stop_name = self._stop_name
        if visits:
            stop_name = (
                visits[0]
                .get("MonitoredVehicleJourney", {})
                .get("MonitoredCall", {})
                .get("StopPointName", self._stop_name)
            )

        # Convert entity type to readable name
        sensor_type = self._entity_type.replace("_", " ").title()

        # Build final name with specific direction
        return f"{stop_name} {self._direction} | {sensor_type}"

    @property
    def native_value(self) -> datetime | None:
        """Return the state of the sensor."""
        visit = self._get_next_visit(self._direction)
        return self._get_arrival_time(visit)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        attrs[ATTR_DIRECTION] = self._direction
        # Add human-readable direction name
        attrs["direction_name"] = "Inbound" if self._direction == DIRECTION_INBOUND else "Outbound"
        return attrs


class Transit511DirectionNextVehicleSensor(Transit511BaseSensor):
    """Sensor for next vehicle ID filtered by direction."""

    def __init__(
        self,
        coordinator: StopDeviceCoordinator,
        entry: ConfigEntry,
        direction: str,
    ) -> None:
        """Initialize the sensor."""
        direction_prefix = "ib" if direction == DIRECTION_INBOUND else "ob"
        super().__init__(coordinator, entry, f"{direction_prefix}_next_vehicle")
        self._direction = direction

    @property
    def name(self) -> str:
        """Return the name of the sensor (override to use filtered direction)."""
        # Build name: [stop_name] [direction] | [sensor_type]
        visits = self._get_visits(self._direction)

        # Get stop name from API
        stop_name = self._stop_name
        if visits:
            stop_name = (
                visits[0]
                .get("MonitoredVehicleJourney", {})
                .get("MonitoredCall", {})
                .get("StopPointName", self._stop_name)
            )

        # Convert entity type to readable name
        sensor_type = self._entity_type.replace("_", " ").title()

        # Build final name with specific direction
        return f"{stop_name} {self._direction} | {sensor_type}"

    @property
    def icon(self) -> str:
        """Return dynamic icon based on vehicle type."""
        vehicle_type = self._get_vehicle_type()
        if vehicle_type:
            icon = get_vehicle_icon(vehicle_type)
            return icon.replace("mdi:train", "mdi:train-car").replace("mdi:bus", "mdi:bus-side")
        return "mdi:card-account-details-outline"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        visit = self._get_next_visit(self._direction)
        if visit:
            return visit.get("MonitoredVehicleJourney", {}).get("VehicleRef")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        attrs[ATTR_DIRECTION] = self._direction
        # Add human-readable direction name
        attrs["direction_name"] = "Inbound" if self._direction == DIRECTION_INBOUND else "Outbound"
        return attrs


class Transit511DirectionNextThreeSensor(Transit511BaseSensor):
    """Sensor for next three arrivals in minutes filtered by direction."""

    def __init__(
        self,
        coordinator: StopDeviceCoordinator,
        entry: ConfigEntry,
        direction: str,
    ) -> None:
        """Initialize the sensor."""
        direction_prefix = "ib" if direction == DIRECTION_INBOUND else "ob"
        super().__init__(coordinator, entry, f"{direction_prefix}_next_three")
        self._direction = direction
        self._attr_icon = "mdi:format-list-numbered"

    @property
    def name(self) -> str:
        """Return the name of the sensor (override to use filtered direction)."""
        # Build name: [stop_name] [direction] | [sensor_type]
        visits = self._get_visits(self._direction)

        # Get stop name from API
        stop_name = self._stop_name
        if visits:
            stop_name = (
                visits[0]
                .get("MonitoredVehicleJourney", {})
                .get("MonitoredCall", {})
                .get("StopPointName", self._stop_name)
            )

        # Convert entity type to readable name
        sensor_type = self._entity_type.replace("_", " ").title()

        # Build final name with specific direction
        return f"{stop_name} {self._direction} | {sensor_type}"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        visits = self._get_visits(self._direction)[:3]
        now = dt_util.now()
        minutes = []

        for visit in visits:
            arrival_time = self._get_arrival_time(visit)
            if arrival_time:
                mins = round((arrival_time - now).total_seconds() / 60)
                minutes.append(str(mins))

        return ", ".join(minutes) if minutes else "none"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        attrs[ATTR_DIRECTION] = self._direction
        # Add human-readable direction name
        attrs["direction_name"] = "Inbound" if self._direction == DIRECTION_INBOUND else "Outbound"
        return attrs
