"""Device tracker platform for 511 Transit integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import Transit511VehicleCoordinator
from .const import (
    ATTR_BEARING,
    ATTR_DESTINATION,
    ATTR_LAST_UPDATED,
    ATTR_LINE,
    ATTR_LINE_NAME,
    ATTR_OCCUPANCY,
    ATTR_OPERATOR,
    ATTR_OPERATOR_NAME,
    ATTR_ORIGIN,
    ATTR_VEHICLE_ID,
    ATTR_VEHICLE_TYPE,
    CONF_MONITORING_TYPE,
    CONF_OPERATOR,
    CONF_VEHICLE_ID,
    DOMAIN,
    MONITORING_TYPE_VEHICLE,
    get_vehicle_icon,
    get_vehicle_type,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up 511 Transit device trackers from a config entry."""
    # Only set up device tracker for vehicle monitoring
    if entry.data.get(CONF_MONITORING_TYPE) != MONITORING_TYPE_VEHICLE:
        return

    coordinator: Transit511VehicleCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([Transit511VehicleTracker(coordinator, entry)])


class Transit511VehicleTracker(CoordinatorEntity, TrackerEntity):
    """Representation of a 511 Transit vehicle device tracker."""

    def __init__(
        self,
        coordinator: Transit511VehicleCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)

        self._operator = entry.data[CONF_OPERATOR]
        self._vehicle_id = entry.data[CONF_VEHICLE_ID]
        self._operator_name = entry.data.get("operator_name", self._operator)

        # Set entity attributes
        self._attr_unique_id = f"{DOMAIN}_{self._operator}_vehicle_{self._vehicle_id}"
        self._attr_has_entity_name = False

        # Link to device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
        )

    @property
    def name(self) -> str:
        """Return the name of the device tracker."""
        # For vehicle trackers, just use "Vehicle Tracker" as the entity name
        # The device name already contains the line and vehicle info
        return "Vehicle Tracker"

    @property
    def icon(self) -> str:
        """Return dynamic icon based on vehicle type."""
        activity = self._get_vehicle_activity()
        if activity:
            journey = activity.get("MonitoredVehicleJourney", {})
            line_ref = journey.get("LineRef")
            mode = journey.get("VehicleMode")
            if line_ref:
                vehicle_type = get_vehicle_type(self._operator, line_ref, mode)
                return get_vehicle_icon(vehicle_type)
        return "mdi:transit-connection-variant"

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        activity = self._get_vehicle_activity()
        if activity:
            location = (
                activity.get("MonitoredVehicleJourney", {})
                .get("VehicleLocation", {})
            )
            lat = location.get("Latitude")
            if lat:
                try:
                    return float(lat)
                except (ValueError, TypeError):
                    return None
        return None

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        activity = self._get_vehicle_activity()
        if activity:
            location = (
                activity.get("MonitoredVehicleJourney", {})
                .get("VehicleLocation", {})
            )
            lon = location.get("Longitude")
            if lon:
                try:
                    return float(lon)
                except (ValueError, TypeError):
                    return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        activity = self._get_vehicle_activity()
        if not activity:
            return {
                ATTR_OPERATOR: self._operator,
                ATTR_OPERATOR_NAME: self._operator_name,
                ATTR_VEHICLE_ID: self._vehicle_id,
            }

        journey = activity.get("MonitoredVehicleJourney", {})

        attributes = {
            ATTR_OPERATOR: self._operator,
            ATTR_OPERATOR_NAME: self._operator_name,
            ATTR_VEHICLE_ID: self._vehicle_id,
            ATTR_LINE: journey.get("LineRef"),
            ATTR_LINE_NAME: journey.get("PublishedLineName"),
            ATTR_DESTINATION: journey.get("DestinationName"),
            ATTR_ORIGIN: journey.get("OriginName"),
            ATTR_OCCUPANCY: journey.get("Occupancy"),
            ATTR_LAST_UPDATED: self.coordinator.data.get("response_timestamp"),
        }

        # Add bearing if available
        bearing = journey.get("Bearing")
        if bearing:
            try:
                attributes[ATTR_BEARING] = float(bearing)
            except (ValueError, TypeError):
                pass

        # Add vehicle type
        line_ref = journey.get("LineRef")
        mode = journey.get("VehicleMode")
        if line_ref:
            vehicle_type = get_vehicle_type(self._operator, line_ref, mode)
            attributes[ATTR_VEHICLE_TYPE] = vehicle_type

        # Add next stop information if available
        monitored_call = journey.get("MonitoredCall")
        if monitored_call:
            attributes["next_stop_name"] = monitored_call.get("StopPointName")
            attributes["next_stop_id"] = monitored_call.get("StopPointRef")
            attributes["aimed_arrival_time"] = monitored_call.get("AimedArrivalTime")
            attributes["expected_arrival_time"] = monitored_call.get("ExpectedArrivalTime")

        return attributes

    def _get_vehicle_activity(self) -> dict[str, Any] | None:
        """Get the vehicle activity for this vehicle."""
        activities = self.coordinator.data.get("activities", [])

        # Find the activity for this specific vehicle
        for activity in activities:
            journey = activity.get("MonitoredVehicleJourney", {})
            if journey.get("VehicleRef") == self._vehicle_id:
                return activity

        # If we requested a specific vehicle and got data, return the first activity
        # (the API should only return data for the requested vehicle)
        if activities and self._vehicle_id:
            return activities[0]

        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False

        # Entity is available if we have location data
        activity = self._get_vehicle_activity()
        if activity:
            location = (
                activity.get("MonitoredVehicleJourney", {})
                .get("VehicleLocation", {})
            )
            return bool(location.get("Latitude") and location.get("Longitude"))

        return False
