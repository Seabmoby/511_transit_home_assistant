"""Constants for the 511 Transit integration."""
from typing import Final

DOMAIN: Final = "transit_511"

# API Configuration
API_BASE_URL: Final = "https://api.511.org/transit"
DEFAULT_SCAN_INTERVAL: Final = 60  # seconds
MIN_SCAN_INTERVAL: Final = 30
MAX_SCAN_INTERVAL: Final = 300

# Configuration Keys
CONF_API_KEY: Final = "api_key"
CONF_OPERATOR: Final = "operator"
CONF_STOP_CODE: Final = "stop_code"
CONF_VEHICLE_ID: Final = "vehicle_id"
CONF_LINE_ID: Final = "line_id"
CONF_DIRECTION: Final = "direction"
CONF_MONITORING_TYPE: Final = "monitoring_type"
CONF_ENABLED_ENTITIES: Final = "enabled_entities"
CONF_ENABLE_API_LOGGING: Final = "enable_api_logging"
CONF_STOPS: Final = "stops"  # List of stop configurations
CONF_VEHICLES: Final = "vehicles"  # List of vehicle configurations

# Monitoring Types
MONITORING_TYPE_STOP: Final = "stop"
MONITORING_TYPE_VEHICLE: Final = "vehicle"

# API Endpoints
ENDPOINT_STOP_MONITORING: Final = "StopMonitoring"
ENDPOINT_VEHICLE_MONITORING: Final = "VehicleMonitoring"
ENDPOINT_OPERATORS: Final = "operators"
ENDPOINT_LINES: Final = "lines"
ENDPOINT_STOPS: Final = "stops"
ENDPOINT_STOP_PLACES: Final = "stopplaces"
ENDPOINT_PATTERNS: Final = "patterns"
ENDPOINT_TIMETABLE: Final = "timetable"
ENDPOINT_STOP_TIMETABLE: Final = "stoptimetable"
ENDPOINT_HOLIDAYS: Final = "holidays"

# Entity Types (for stop monitoring)
ENTITY_TYPE_COUNT: Final = "count"
ENTITY_TYPE_API_TIMESTAMP: Final = "api_timestamp"
ENTITY_TYPE_NEXT_ARRIVAL_MIN: Final = "next_arrival_min"
ENTITY_TYPE_NEXT_ARRIVAL_TIME: Final = "next_arrival_time"
ENTITY_TYPE_NEXT_VEHICLE: Final = "next_vehicle"
ENTITY_TYPE_NEXT_DESTINATION: Final = "next_destination"
ENTITY_TYPE_NEXT_OCCUPANCY: Final = "next_occupancy"
ENTITY_TYPE_NEXT_THREE: Final = "next_three"
ENTITY_TYPE_API_OK: Final = "api_ok"

# Direction-filtered entity types
ENTITY_TYPE_IB_COUNT: Final = "ib_count"
ENTITY_TYPE_IB_NEXT_ARRIVAL_MIN: Final = "ib_next_arrival_min"
ENTITY_TYPE_IB_NEXT_ARRIVAL_TIME: Final = "ib_next_arrival_time"
ENTITY_TYPE_IB_NEXT_VEHICLE: Final = "ib_next_vehicle"
ENTITY_TYPE_IB_NEXT_THREE: Final = "ib_next_three"

ENTITY_TYPE_OB_COUNT: Final = "ob_count"
ENTITY_TYPE_OB_NEXT_ARRIVAL_MIN: Final = "ob_next_arrival_min"
ENTITY_TYPE_OB_NEXT_ARRIVAL_TIME: Final = "ob_next_arrival_time"
ENTITY_TYPE_OB_NEXT_VEHICLE: Final = "ob_next_vehicle"
ENTITY_TYPE_OB_NEXT_THREE: Final = "ob_next_three"

# All available entity types
ALL_ENTITY_TYPES: Final = [
    ENTITY_TYPE_COUNT,
    ENTITY_TYPE_API_TIMESTAMP,
    ENTITY_TYPE_NEXT_ARRIVAL_MIN,
    ENTITY_TYPE_NEXT_ARRIVAL_TIME,
    ENTITY_TYPE_NEXT_VEHICLE,
    ENTITY_TYPE_NEXT_DESTINATION,
    ENTITY_TYPE_NEXT_OCCUPANCY,
    ENTITY_TYPE_NEXT_THREE,
    ENTITY_TYPE_API_OK,
]

DIRECTION_FILTERED_ENTITY_TYPES: Final = [
    ENTITY_TYPE_IB_COUNT,
    ENTITY_TYPE_IB_NEXT_ARRIVAL_MIN,
    ENTITY_TYPE_IB_NEXT_ARRIVAL_TIME,
    ENTITY_TYPE_IB_NEXT_VEHICLE,
    ENTITY_TYPE_IB_NEXT_THREE,
    ENTITY_TYPE_OB_COUNT,
    ENTITY_TYPE_OB_NEXT_ARRIVAL_MIN,
    ENTITY_TYPE_OB_NEXT_ARRIVAL_TIME,
    ENTITY_TYPE_OB_NEXT_VEHICLE,
    ENTITY_TYPE_OB_NEXT_THREE,
]

# Default enabled entities
DEFAULT_ENABLED_ENTITIES: Final = [
    ENTITY_TYPE_NEXT_ARRIVAL_MIN,
    ENTITY_TYPE_NEXT_ARRIVAL_TIME,
    ENTITY_TYPE_NEXT_THREE,
    ENTITY_TYPE_API_OK,
]

# Direction References
DIRECTION_INBOUND: Final = "IB"
DIRECTION_OUTBOUND: Final = "OB"

# Occupancy Status
OCCUPANCY_SEATS_AVAILABLE: Final = "seatsAvailable"
OCCUPANCY_STANDING_AVAILABLE: Final = "standingAvailable"
OCCUPANCY_FULL: Final = "full"

# Error Messages
ERROR_AUTH_FAILED: Final = "auth_failed"
ERROR_CANNOT_CONNECT: Final = "cannot_connect"
ERROR_RATE_LIMIT: Final = "rate_limit"
ERROR_INVALID_OPERATOR: Final = "invalid_operator"
ERROR_INVALID_STOP: Final = "invalid_stop"
ERROR_INVALID_VEHICLE: Final = "invalid_vehicle"
ERROR_UNKNOWN: Final = "unknown"

# Attribute Keys
ATTR_OPERATOR: Final = "operator"
ATTR_OPERATOR_NAME: Final = "operator_name"
ATTR_LINE: Final = "line"
ATTR_LINE_NAME: Final = "line_name"
ATTR_STOP_CODE: Final = "stop_code"
ATTR_STOP_NAME: Final = "stop_name"
ATTR_DIRECTION: Final = "direction"
ATTR_VEHICLE_ID: Final = "vehicle_id"
ATTR_DESTINATION: Final = "destination"
ATTR_OCCUPANCY: Final = "occupancy"
ATTR_BEARING: Final = "bearing"
ATTR_LAST_UPDATED: Final = "last_updated"
ATTR_VISITS: Final = "visits"
ATTR_ORIGIN: Final = "origin"
ATTR_VEHICLE_TYPE: Final = "vehicle_type"

# Vehicle Types
VEHICLE_TYPE_BUS: Final = "bus"
VEHICLE_TYPE_TRAIN: Final = "train"
VEHICLE_TYPE_RAIL: Final = "rail"
VEHICLE_TYPE_UNKNOWN: Final = "unknown"

# Operator-specific line identification patterns
# SF Muni: Letters = Rail/Train (N, T, L, M, etc.), Numbers = Bus (1, 7, 14, etc.)
# BA (BART): Always train
# Other operators: Use mode from API when available


def get_vehicle_type(operator: str, line_ref: str | None, mode: str | None = None) -> str:
    """Determine vehicle type based on operator and line reference.

    Args:
        operator: Operator ID (e.g., "SF", "BA", "AC")
        line_ref: Line reference from API (e.g., "N", "7", "BLUE")
        mode: Transport mode from API if available

    Returns:
        Vehicle type: "train", "bus", or "unknown"
    """
    if not line_ref:
        return VEHICLE_TYPE_UNKNOWN

    # Check API mode first if available
    if mode:
        mode_lower = mode.lower()
        if "rail" in mode_lower or "train" in mode_lower or "metro" in mode_lower:
            return VEHICLE_TYPE_TRAIN
        if "bus" in mode_lower:
            return VEHICLE_TYPE_BUS

    # Operator-specific logic
    operator_upper = operator.upper()

    # BART - Always rail/train
    if operator_upper == "BA":
        return VEHICLE_TYPE_TRAIN

    # Caltrain - Always train
    if operator_upper == "CM":
        return VEHICLE_TYPE_TRAIN

    # SF Muni - Letters are rail (N, T, L, M, K, J, S), numbers are bus
    if operator_upper == "SF":
        # Check if line_ref is purely numeric
        if line_ref.isdigit():
            return VEHICLE_TYPE_BUS
        # Single letters or known rail lines
        if line_ref.upper() in ["N", "T", "L", "M", "K", "J", "S", "E", "F"]:
            return VEHICLE_TYPE_TRAIN
        # If starts with a letter, likely rail
        if line_ref and line_ref[0].isalpha():
            return VEHICLE_TYPE_TRAIN
        return VEHICLE_TYPE_BUS

    # AC Transit - Always bus
    if operator_upper == "AC":
        return VEHICLE_TYPE_BUS

    # County Connection - Always bus
    if operator_upper == "CC":
        return VEHICLE_TYPE_BUS

    # SamTrans - Always bus
    if operator_upper == "SM":
        return VEHICLE_TYPE_BUS

    # VTA (Santa Clara Valley Transportation) - Check line patterns
    if operator_upper == "SC":
        # VTA light rail lines are typically numeric (901, 902) or colors
        line_upper = line_ref.upper()
        if "BLUE" in line_upper or "GREEN" in line_upper or "ORANGE" in line_upper:
            return VEHICLE_TYPE_TRAIN
        # Lines 900+ are light rail
        if line_ref.isdigit() and int(line_ref) >= 900:
            return VEHICLE_TYPE_TRAIN
        return VEHICLE_TYPE_BUS

    # Default: unknown
    return VEHICLE_TYPE_UNKNOWN


def get_vehicle_icon(vehicle_type: str) -> str:
    """Get MDI icon for vehicle type.

    Args:
        vehicle_type: Vehicle type ("train", "bus", "unknown")

    Returns:
        MDI icon string
    """
    if vehicle_type == VEHICLE_TYPE_TRAIN:
        return "mdi:train"
    if vehicle_type == VEHICLE_TYPE_BUS:
        return "mdi:bus"
    # Default for unknown
    return "mdi:transit-connection-variant"
