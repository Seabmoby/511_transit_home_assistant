# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for 511.org Transit API that provides real-time transit information for Bay Area transit agencies including SF Muni, BART, AC Transit, and others. The integration uses the 511.org API to create sensors and device trackers for stop predictions and vehicle locations.

## Development Setup

### Testing the Integration
```bash
# Run tests (when implemented)
pytest tests/

# Run tests with coverage
pytest --cov=custom_components.muni tests/

# Run a single test file
pytest tests/test_sensor.py
```

### Linting and Code Quality
```bash
# Run pre-commit hooks (if configured)
pre-commit run --all-files

# Format code with black (if configured)
black custom_components/muni

# Type checking with mypy (if configured)
mypy custom_components/muni
```

### Testing in Home Assistant
Place the integration in Home Assistant's `custom_components` directory:
```bash
# Development installation
ln -s $(pwd)/custom_components/muni /path/to/homeassistant/custom_components/muni
```

Then restart Home Assistant to load the integration.

## Architecture

### Home Assistant Integration Structure
```
custom_components/transit_511/
├── __init__.py              # Integration setup, coordinator
├── manifest.json            # Integration metadata
├── config_flow.py           # Configuration UI flow
├── const.py                 # Constants, API endpoints, config keys
├── api.py                   # 511 API client
├── sensor.py                # Sensor entities for stop monitoring
├── device_tracker.py        # Device tracker for vehicle monitoring
├── strings.json             # UI translations
└── translations/
    └── en.json              # English translations
```

### Data Flow
1. **Configuration** - User enters API key once, then configures monitoring targets:
   - Stop monitoring: agency + stop code → creates arrival/departure sensors
   - Vehicle monitoring: agency + vehicle ID → creates device tracker
   - User toggles which entity types to create
2. **Coordinator** - Separate DataUpdateCoordinators for each monitored target
3. **Entities** - Dynamic entity creation based on user selections
4. **API Client** - Handles all 511.org API endpoints

### Key Components

#### API Client (`api.py`)
Implements methods for all 511.org API endpoints:
- `StopMonitoring` - Get arrival/departure predictions for a stop
- `VehicleMonitoring` - Get current vehicle location and status
- `operators` - List available transit operators
- `lines` - Get routes for an operator
- `stops` - Get stops for an operator/line
- `stopplaces` - Get detailed stop information
- `patterns` - Get trip patterns for a route
- `timetable` - Get scheduled timetables
- `stoptimetable` - Get scheduled departures at a stop
- `holidays` - Get service exceptions

#### Data Coordinator
- One coordinator per monitored entity (stop or vehicle)
- Update interval: 30-180 seconds (configurable, default 60s)
- Rate limit handling: 60 requests/hour per API key
- Caches API responses to minimize calls

#### Device Registry
- Each stop or vehicle creates a Device in Home Assistant
- All sensors/entities linked to their parent device
- Device identifiers: `{DOMAIN}_{operator}_{stop_code}` or `{DOMAIN}_{operator}_vehicle_{vehicle_id}`
- Device info includes:
  - Name: From config entry title
  - Manufacturer: Operator name (e.g., "San Francisco Muni")
  - Model: "Stop {stop_code}" or "Vehicle {vehicle_id}"
  - Suggested area: "Transit"

#### Sensor Platform (`sensor.py`)
Creates sensors for stop monitoring data:
- Count of upcoming arrivals
- Next arrival time (timestamp)
- Next arrival minutes (integer with unit)
- Vehicle ID
- Destination name
- Occupancy status
- Next three arrivals (comma-separated minutes)
- Direction-filtered variants (IB/OB)
- API timestamp
- API connectivity status (binary_sensor)

#### Device Tracker Platform (`device_tracker.py`)
Creates device trackers for vehicles:
- GPS location from VehicleLocation (latitude/longitude)
- Bearing/heading
- Occupancy
- Line/route name
- Origin/destination
- Next stop

### Config Flow Details

#### Step 1: API Key
- Single API key entry
- Validation by calling `/transit/operators`
- Stored encrypted in config entry

#### Step 2: Monitoring Type
User selects:
- Stop Monitoring (arrivals/departures)
- Vehicle Monitoring (GPS tracking)
- Or both

#### Step 3a: Stop Monitoring Configuration
- Select operator (dropdown from API)
- Select line (optional, dropdown from API)
- Enter stop code or select from list
- Toggle entity types:
  - [x] Count of arrivals
  - [x] Next arrival time
  - [x] Next arrival minutes
  - [x] Vehicle ID
  - [x] Destination
  - [x] Occupancy
  - [x] Next three arrivals
  - [x] Direction-filtered sensors
  - [x] API status

#### Step 3b: Vehicle Monitoring Configuration
- Select operator
- Enter vehicle ID or select active vehicles
- Creates device_tracker entity

#### Multiple Configurations
- User can add integration multiple times to monitor many stops/vehicles
- Each stop/vehicle gets its own config entry and coordinator
- Each config entry can share the same API key
- Options flow allows editing configuration per entry
- Unique IDs prevent duplicate entries for same stop/vehicle

#### Supporting Both Stop and Vehicle Monitoring
- Users add the integration once per stop or vehicle
- To monitor both: Add integration → configure stop → Add integration again → configure vehicle
- Each entry is independent with its own update interval and entity configuration

## Home Assistant Integration Guidelines

### Entity Naming
- Unique ID format: `{domain}_{operator}_{stop_code}_{entity_type}` or `{domain}_{operator}_{vehicle_id}`
- Entity IDs: `sensor.transit_511_{operator}_{stop}_{type}`
- Device name: `{operator} {line} @ {stop_name}` or `{operator} Vehicle {vehicle_id}`

### State Updates
- DataUpdateCoordinator per monitored target (one per config entry)
- Default interval: 60 seconds (configurable 30-300s)
- API rate limit: 60 requests/hour per API key
  - Multiple config entries share API key limit
  - Formula: (3600 / interval) × num_entries ≤ 60
  - Example: 3 stops at 180s intervals = 60 req/hr
- Failed updates: exponential backoff

### Configuration Storage
- API key: Stored in `config_entry.data["api_key"]` (encrypted)
- Monitoring config: Stored in `config_entry.data`
- Entity toggles: Stored in `config_entry.options`
- Update interval: Stored in `config_entry.options["scan_interval"]`

### Error Handling
- API unavailable: Set entities to unavailable
- Rate limit exceeded: Log warning, increase interval temporarily
- Invalid response: Log error with response details
- Missing fields: Use defaults (handle null VehicleRef, Occupancy, etc.)

## 511.org API Details

### Base URL
`https://api.511.org/transit/` (HTTPS required)

### Authentication
All endpoints require `api_key` parameter

### Rate Limits
- 60 requests per hour per API key
- Plan accordingly: 1 stop at 60s interval = 60 req/hr (at limit)

### Response Format
- Default: XML
- Add `format=JSON` parameter for JSON
- Responses may include UTF-8 BOM (`\ufeff`) - strip it

### StopMonitoring Response Structure
```json
{
  "ServiceDelivery": {
    "ResponseTimestamp": "2025-10-27T20:07:17Z",
    "StopMonitoringDelivery": {
      "ResponseTimestamp": "2025-10-27T20:07:17Z",
      "MonitoredStopVisit": [
        {
          "RecordedAtTime": "2025-10-27T20:07:03Z",
          "MonitoringRef": "18031",
          "MonitoredVehicleJourney": {
            "LineRef": "N",
            "DirectionRef": "IB",
            "PublishedLineName": "JUDAH",
            "OperatorRef": "SF",
            "DestinationName": "King St & 4th St",
            "VehicleLocation": {
              "Longitude": "-122.487015",
              "Latitude": "37.7612267"
            },
            "Bearing": "75.0000000000",
            "Occupancy": "seatsAvailable",
            "VehicleRef": "2080",
            "MonitoredCall": {
              "StopPointRef": "18031",
              "StopPointName": "Irving St & 5th Ave",
              "AimedArrivalTime": "2025-10-27T20:14:06Z",
              "ExpectedArrivalTime": "2025-10-27T20:14:10Z"
            }
          }
        }
      ]
    }
  }
}
```

### Important Fields
- `ExpectedArrivalTime` - Use this first (real-time prediction)
- `AimedArrivalTime` - Fallback if ExpectedArrivalTime is null
- `DirectionRef` - "IB" (inbound) or "OB" (outbound)
- `VehicleRef` - May be null for scheduled-only predictions
- `Occupancy` - May be null; values: "seatsAvailable", "standingAvailable", "full"
- `RecordedAtTime` - May be "1970-01-01T00:00:00Z" for schedule-only data

### VehicleMonitoring Response
Similar structure but focused on vehicle rather than stop:
- Current GPS location
- Next stop predictions
- Route information
- Vehicle status