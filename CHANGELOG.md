# Changelog

All notable changes to the 511 Transit integration will be documented in this file.

## [2.0.0] - 2025-11-10

### 🚨 BREAKING CHANGES

**This is a major architectural restructuring. You must delete all existing integration entries and reconfigure.**

### Changed

- **New Service Architecture**: Integration entries are now organized by operator + monitoring type
  - Before: 1 entry per stop/vehicle (e.g., "SF Stop 12345", "SF Stop 67890")
  - After: 1 entry per operator+type (e.g., "SF Muni - Stops", "BART - Vehicles")
  - Each entry can contain multiple stops or vehicles as separate devices

- **Configuration Flow**:
  - Create a service by selecting operator and monitoring type
  - Start with empty service (no stops/vehicles)
  - Add/remove stops/vehicles via Options menu
  - Each stop/vehicle appears as its own device under the service

- **Options Menu**:
  - New menu-based options flow
  - Add Stop/Vehicle: Add new device to this service
  - Remove Stop/Vehicle: Remove device from service
  - Settings: Configure scan interval, API logging, API key, enabled entities

- **API Call Logging**:
  - Added toggle to enable/disable detailed API call logging
  - Off by default
  - Shows 🚀 API calls, 🔄 coordinator updates, ✨ new coordinator creation, ♻️ coordinator reuse
  - Configurable per service via Options → Settings

### Benefits

- **Better Organization**: All Muni stops grouped under one service, all BART stops under another
- **Easier Management**: Add/remove stops without creating new integration entries
- **Cleaner UI**: Fewer integration entries in Settings → Devices & Services
- **Shared Settings**: Scan interval and options apply to all devices in a service

### Migration Steps

1. **Document your current setup**: Note all operators, stops, and vehicles you're monitoring
2. **Delete all existing 511 Transit integration entries**
3. **Add new services**:
   - Add "SF Muni - Stops" (if you monitor Muni stops)
   - Add "SF Muni - Vehicles" (if you monitor Muni vehicles)
   - Add "BART - Stops" (if you monitor BART stops)
   - Etc.
4. **Configure each service**:
   - Click Configure (or Options)
   - Select "Add Stop" or "Add Vehicle"
   - Enter stop code/vehicle ID
   - Repeat for all your stops/vehicles
5. **Update automations/dashboards**: Entity IDs remain similar but may have changed

### Example

**Before (v1.x)**:
```
Integration Entries:
- "N Judah Train - Irving St & 5th Ave IB/OB"
- "7 Haight-Noriega Bus - Lincoln Way & 5th Ave OB"
- "BART - Embarcadero Station"
```

**After (v2.0)**:
```
Integration Entries:
- "SF Muni - Stops"
  ├── Device: "N Judah Train - Irving St & 5th Ave IB/OB"
  └── Device: "7 Haight-Noriega Bus - Lincoln Way & 5th Ave OB"
- "BART - Stops"
  └── Device: "Embarcadero Station"
```

---

## [1.5.1] - 2025-11-05

### Fixed
- 🐛 **Critical Fix**: Fixed `async_add_listener()` signature to accept optional `context` parameter
  - Resolves `TypeError: StopDeviceCoordinator.async_add_listener() takes 2 positional arguments but 3 were given`
  - All sensors now load correctly
  - Issue occurred when Home Assistant's CoordinatorEntity called async_add_listener with coordinator_context

### Technical
- Updated `StopDeviceCoordinator.async_add_listener()` signature (__init__.py:279)
- Now properly forwards context parameter to global coordinator

---

## [1.5.0] - 2025-10-27

### Added
- 🔄 **Shared API Calls**: Multiple devices monitoring the same stop now share a single API call!
  - **Huge API efficiency improvement** - dramatically reduces API usage
  - Example: 3 devices on same stop = 1 API call instead of 3
  - Automatic deduplication per (operator, stop_code)
  - Each device can still filter by different line_id

### Changed
- **Global coordinator architecture**: Created `GlobalStopCoordinator` that makes API calls
- **Device coordinators**: `StopDeviceCoordinator` subscribes to global coordinator and filters data
- Multiple config entries for the same stop automatically share the underlying API call
- No changes needed for existing installations - sharing happens automatically

### Technical
- Introduced `GlobalStopCoordinator` for shared API calls per stop (__init__.py:170-212)
- Created `StopDeviceCoordinator` for device-specific filtering (__init__.py:215-340)
- Global coordinators stored in `hass.data[DOMAIN][GLOBAL_COORDINATORS]`
- Device coordinators filter by `line_id` if specified
- Listeners automatically propagate updates from global to device coordinators
- Updated sensor.py to use `StopDeviceCoordinator` type

### Benefits
**Before (v1.4.0)**:
- 2 stops at 60s = 120 req/hr ❌ (over 60/hr limit)
- 3 stops at 120s = 90 req/hr ❌ (over limit)

**After (v1.5.0)**:
- 2 different stops at 60s = 120 req/hr ❌ (still need to adjust)
- **2 devices, same stop** at 60s = 60 req/hr ✅ (shared call!)
- **3 devices, same stop** at 60s = 60 req/hr ✅ (shared call!)
- Mix: 2 unique stops + 3 devices on same stop = 180 req/hr from 3 calls

---

## [1.4.0] - 2025-10-27

### Changed
- 🏷️ **Improved Device, Entity, and Entry Names**: Cleaner, more readable names throughout!

  **Integration Entry Names**:
  - Automatically updated to match device names after first data fetch
  - Makes it easy to identify which line/stop each entry represents
  - Example in integrations list: "7 Haight-Noriega Bus - Lincoln Way & 5th Ave Outbound"

  **Device Names** (for stops):
  - **Format**: `[line] [line_name] [vehicle_type] - [stop_name] [direction]`
  - **Example**: "7 Haight-Noriega Bus - Lincoln Way & 5th Ave Outbound"
  - **Example**: "N Judah Train - Irving St & 5th Ave Inbound/Outbound"
  - Line names are title-cased (not all caps)
  - Direction shown at end (Inbound, Outbound, or Inbound/Outbound)
  - Automatically updated after first API fetch with live data

  **Device Names** (for vehicles):
  - **Format**: `[line] [line_name] [vehicle_type] - Vehicle [id]`
  - **Example**: "N Judah Train - Vehicle 2080"
  - Line names are title-cased

  **Entity Names** (for sensors):
  - **Format**: `[stop_name] [directions] | [sensor_type]`
  - **Example**: "Irving St & 5th Ave IB OB | Next Arrival Min"
  - **Direction-filtered**: "Irving St & 5th Ave IB | Ib Next Arrival Min"
  - Names update dynamically as API data changes

  **Entity Names** (for vehicle trackers):
  - **Simple**: "Vehicle Tracker" (device name already contains all the info)

### Technical
- Added dynamic device name and entry title updates in coordinators after first data fetch (__init__.py:186-251, 310-356)
- Config entry titles automatically updated to match device names
- Device names now include title-cased line names and direction information
- Stop device names show all available directions (Inbound/Outbound)
- Updated `Transit511BaseSensor.name` property to use stop name and directions (sensor.py:183-218)
- Updated all direction-filtered sensor names to show specific direction
- Updated `Transit511VehicleTracker.name` to simple "Vehicle Tracker" (device_tracker.py:78-83)
- Entity unique_ids remain stable (based on operator, stop_code, entity_type)
- Device and entity names now pull live data from API: stop_name, line_ref, line_name, directions, vehicle_type

### Note
**Existing Installations**: Entity IDs remain the same. Device and entity display names will update to the new format automatically after the next data fetch. No action required!

---

## [1.3.0] - 2025-10-27

### Added
- 🔑 **API Key Reuse**: Enter your API key once, then automatically reuse it for all future stops/vehicles!
  - First integration setup: Enter API key
  - Subsequent setups: API key automatically used, skip straight to stop/vehicle selection
  - Much faster to add multiple stops/vehicles
  - No need to remember or re-enter your API key

### Changed
- Config flow now checks for existing API key from other config entries
- API key entry step only shows on first integration setup
- Updated UI descriptions to indicate API key will be saved and reused

### User Experience
**Before (v1.2.x):**
- Add integration → Enter API key → Configure stop
- Add integration → Enter API key again → Configure stop
- Add integration → Enter API key again → Configure stop

**After (v1.3.0):**
- Add integration → Enter API key → Configure stop
- Add integration → Configure stop ✨ (API key reused!)
- Add integration → Configure stop ✨ (API key reused!)

---

## [1.2.1] - 2025-10-27

### Fixed
- 🐛 **Line Attribute**: Fixed "line" attribute showing as "Unknown" - now pulls actual line from API data
  - Uses `LineRef` from API response (e.g., "N", "7", "BLUE")
  - Falls back to configured line_id if API doesn't provide it
  - Also adds `line_name` attribute with full line name (e.g., "JUDAH")

### Added
- 📍 **Direction Information**: Added direction details to all sensor attributes
  - `directions` attribute shows all directions at stop (e.g., "IB, OB" or just "IB")
  - Direction-filtered sensors now include `direction_name` ("Inbound" or "Outbound")
  - Helps identify which way vehicles are heading

### Changed
- All sensors now pull line information from live API data instead of config
- Better attribute organization and human-readable values

---

## [1.2.0] - 2025-10-27

### Added
- 🎨 **Smart Icons**: Icons now automatically change based on vehicle type!
  - **SF Muni**: Letters (N, T, L, etc.) → 🚊 `mdi:train`, Numbers (7, 14, etc.) → 🚌 `mdi:bus`
  - **BART (BA)**: Always 🚊 `mdi:train`
  - **AC Transit, County Connection, SamTrans**: Always 🚌 `mdi:bus`
  - **Caltrain (CM)**: Always 🚊 `mdi:train`
  - **VTA (SC)**: Light rail lines → 🚊 `mdi:train`, Bus lines → 🚌 `mdi:bus`
- 📊 **Vehicle Type Attribute**: All sensors and trackers now include `vehicle_type` attribute
- 🔍 **Automatic Detection**: Uses LineRef from API data to determine train vs bus

### Changed
- Dynamic icons for all arrival sensors (next arrival, IB/OB arrivals)
- Dynamic icons for vehicle ID sensors (shows train-car or bus-side)
- Device tracker icons update based on actual vehicle type
- Icons update in real-time as vehicle data changes

### Technical
- Added `get_vehicle_type()` helper function in `const.py`
- Added `get_vehicle_icon()` helper function in `const.py`
- Operator-specific logic for all major Bay Area transit agencies
- Fallback to API VehicleMode when available

---

## [1.1.1] - 2025-10-27

### Changed
- 📝 **Documentation**: Improved documentation for custom integrations

### Technical
- Removed unused `icon` field from manifest.json (not supported for custom integrations)

---

## [1.1.0] - 2025-10-27

### Added
- ✨ **Device Support**: Each stop and vehicle now creates a Device in Home Assistant
  - All sensors grouped under their parent device
  - Device shows manufacturer (operator name) and model (stop/vehicle ID)
  - Better organization in the Devices page
- 📝 **Comprehensive Documentation**:
  - `UPDATING_IN_HAOS.md` - Detailed guide for updating integration
  - `INSTALLATION_HAOS.md` - Step-by-step installation for HAOS users
  - Enhanced README with device information

### Fixed
- 🐛 **HTTPS URL**: Changed API base URL from HTTP to HTTPS (fixes connection errors)
- 🐛 **API Validation**: Improved API key validation using StopMonitoring endpoint
- 🔧 **JSON Parsing**: Enhanced error handling for API responses

### Changed
- 📦 Updated all entities to link to their parent devices
- 🏗️ Coordinators now track device_id for entity association
- 📚 Improved inline documentation and comments

### Technical Details
- Added `device_registry` support in `__init__.py`
- All sensors and device_trackers now include `DeviceInfo`
- Device identifiers: `{domain}_{operator}_{stop/vehicle_id}`
- Suggested area: "Transit"

---

## [1.0.0] - 2025-10-27

### Initial Release
- Stop Monitoring for arrival/departure predictions
- Vehicle Monitoring for GPS tracking
- Multiple sensor types:
  - Count, timestamps, arrival times
  - Vehicle IDs, destinations, occupancy
  - Direction-filtered sensors (IB/OB)
  - API connectivity status
- Device tracker for vehicle locations
- Configurable update intervals (30-300s)
- Support for multiple stops and vehicles
- Config flow with operator selection
- Rate limit handling (60 req/hour)
- Options flow for customization

### Supported APIs
- StopMonitoring (SIRI)
- VehicleMonitoring (SIRI)
- Operators, Lines, Stops (NeTEx)
- Stop Places, Patterns, Timetables (NeTEx)

---

## Version Numbering

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR** version: Incompatible API changes or breaking changes
- **MINOR** version: New features, backward compatible
- **PATCH** version: Bug fixes, backward compatible

## Upgrade Notes

### From 1.0.0 to 1.1.0

**No breaking changes!** Existing installations will continue to work.

**To get device support:**
1. Update files in `/config/custom_components/transit_511/`
2. Restart Home Assistant
3. **Option A:** Keep existing sensors (devices created on restart)
4. **Option B:** Delete and re-add integration for clean device setup

**New features automatically available:**
- ✅ Devices visible in Settings → Devices & Services → Devices
- ✅ All sensors grouped under devices
- ✅ HTTPS API connection (more reliable)

**See:** `UPDATING_IN_HAOS.md` for detailed update instructions
