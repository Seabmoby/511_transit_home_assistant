# Smart Icons Feature

## Overview

The 511 Transit integration automatically detects whether a line is a **train/rail** or **bus** service and displays the appropriate icon. No configuration needed - it just works!

## How It Works

The integration analyzes the `LineRef` (line/route identifier) from the 511 API to determine the vehicle type:

### SF Muni (Operator: SF)
- **Letters** = 🚊 Train/Rail (e.g., N, T, L, M, K, J, S, E, F)
  - N Judah → `mdi:train`
  - T Third → `mdi:train`
  - L Taraval → `mdi:train`
- **Numbers** = 🚌 Bus (e.g., 1, 7, 14, 22, 38)
  - 7 Haight → `mdi:bus`
  - 14 Mission → `mdi:bus`
  - 38 Geary → `mdi:bus`

### BART (Operator: BA)
- **All lines** = 🚊 Train
  - Red Line → `mdi:train`
  - Blue Line → `mdi:train`
  - Any BART service → `mdi:train`

### Caltrain (Operator: CM)
- **All services** = 🚊 Train
  - Local → `mdi:train`
  - Limited → `mdi:train`
  - Express → `mdi:train`

### AC Transit (Operator: AC)
- **All lines** = 🚌 Bus
  - 1 → `mdi:bus`
  - F → `mdi:bus`
  - Any AC Transit line → `mdi:bus`

### County Connection (Operator: CC)
- **All lines** = 🚌 Bus

### SamTrans (Operator: SM)
- **All lines** = 🚌 Bus

### VTA - Santa Clara Valley Transportation (Operator: SC)
- **Light Rail** = 🚊 Train
  - Blue Line → `mdi:train`
  - Green Line → `mdi:train`
  - Orange Line → `mdi:train`
  - Lines 900+ → `mdi:train`
- **Bus** = 🚌 Bus
  - Regular numbered routes → `mdi:bus`

## Which Icons Change?

### ✅ Sensors That Use Smart Icons

| Sensor | Icon Changes |
|--------|-------------|
| Next Arrival (min) | 🚊 train or 🚌 bus |
| IB/OB Next Arrival (min) | 🚊 train or 🚌 bus |
| Next Vehicle | 🚊 train-car or 🚌 bus-side |
| IB/OB Next Vehicle | 🚊 train-car or 🚌 bus-side |
| Device Tracker | 🚊 train or 🚌 bus |

### ❌ Sensors With Static Icons

| Sensor | Icon (Always) |
|--------|---------------|
| Count | mdi:numeric |
| API Timestamp | (none - timestamp) |
| Next Arrival Time | (none - timestamp) |
| Destination | mdi:flag-checkered |
| Occupancy | mdi:seat-recline-normal |
| Next Three | mdi:format-list-numbered |
| API OK | (connectivity icon) |

## Examples

### SF Muni N Judah Stop
```
LineRef: "N"
Result: vehicle_type = "train"
Icons:
  - Next Arrival (min): mdi:train 🚊
  - Next Vehicle: mdi:train-car 🚃
  - Device Tracker: mdi:train 🚊
```

### SF Muni 7 Haight Bus Stop
```
LineRef: "7"
Result: vehicle_type = "bus"
Icons:
  - Next Arrival (min): mdi:bus 🚌
  - Next Vehicle: mdi:bus-side 🚐
  - Device Tracker: mdi:bus 🚌
```

### BART Embarcadero Station
```
LineRef: "RED" (or any BART line)
Operator: "BA"
Result: vehicle_type = "train"
Icons:
  - Next Arrival (min): mdi:train 🚊
  - Next Vehicle: mdi:train-car 🚃
```

### AC Transit Line 1
```
LineRef: "1"
Operator: "AC"
Result: vehicle_type = "bus"
Icons:
  - Next Arrival (min): mdi:bus 🚌
  - Next Vehicle: mdi:bus-side 🚐
```

## Vehicle Type Attribute

All sensors and device trackers include a `vehicle_type` attribute:

```yaml
sensor.sf_n_irving_5th_ave_next_arrival_min:
  state: 5
  attributes:
    vehicle_type: train
    operator: SF
    line: N
    ...

sensor.sf_7_haight_fulton_next_arrival_min:
  state: 8
  attributes:
    vehicle_type: bus
    operator: SF
    line: 7
    ...
```

## Advanced: How Detection Works

### Priority Order
1. **API VehicleMode** - If the API provides a mode, use it
2. **Operator Rules** - Apply operator-specific logic
3. **LineRef Pattern** - Analyze the line reference
4. **Fallback** - Use generic transit icon if unknown

### Detection Function
```python
def get_vehicle_type(operator: str, line_ref: str, mode: str = None) -> str:
    """
    Returns: "train", "bus", or "unknown"
    """
```

### Code Location
All logic is in `custom_components/transit_511/const.py`:
- `get_vehicle_type()` - Determines train vs bus
- `get_vehicle_icon()` - Returns appropriate MDI icon

## Customization

The detection is automatic, but you can:

### View Vehicle Type
Check the sensor's attributes in Developer Tools:
1. Settings → Developer Tools → States
2. Find your sensor
3. Look for `vehicle_type` attribute

### Manual Override
Not currently supported - icons are automatic based on API data.

If you need custom icons, you can:
1. Create a template sensor
2. Use customize.yaml (affects all entities)
3. Use card customization in Lovelace

## API Data Used

The integration checks these fields from the 511 API:

```json
{
  "MonitoredVehicleJourney": {
    "LineRef": "N",           // ← Primary detection
    "VehicleMode": "rail",    // ← Fallback if available
    "OperatorRef": "SF"       // ← Used for operator logic
  }
}
```

## Troubleshooting

### Icons not changing?
- Check if `vehicle_type` attribute exists
- Verify `LineRef` is present in API data
- Check logs for detection errors
- Unknown operators default to generic transit icon

### Wrong icon showing?
- Check the `vehicle_type` attribute value
- Review operator detection logic in `const.py`
- Some operators may need custom rules added

### Want to add support for new operator?
1. Edit `custom_components/transit_511/const.py`
2. Add case to `get_vehicle_type()` function
3. Follow existing pattern (BA, SF, AC, etc.)
4. Test with real API data

## Benefits

✅ **Automatic** - No configuration needed
✅ **Accurate** - Based on actual API data
✅ **Dynamic** - Updates in real-time
✅ **Consistent** - Same logic across all sensors
✅ **Extensible** - Easy to add new operators

## Version History

- **v1.2.0** - Smart icons feature added
- **v1.1.x** - Static icons only
- **v1.0.0** - Initial release

## Related Documentation

- `CHANGELOG.md` - Version history
- `const.py` - Detection logic code
- `README.md` - General usage
