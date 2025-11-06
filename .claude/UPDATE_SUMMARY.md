# 511 Transit Integration v1.1.0 - Update Summary

## What's New in This Version

### 🎉 Major Feature: Device Organization

Each stop or vehicle you monitor now creates a **proper Device** in Home Assistant!

**Before (v1.0.0):**
- Sensors floating in entity list
- Hard to find related sensors
- No grouping

**After (v1.1.0):**
- Each stop = 1 Device with all its sensors
- Each vehicle = 1 Device with tracker
- Easy to find in Devices page
- Professional organization

**Example:**
```
Device: "SF N @ Irving St & 5th Ave"
├── Manufacturer: San Francisco Muni
├── Model: Stop 18031
└── Entities:
    ├── sensor.sf_n_irving_5th_ave_next_arrival_min
    ├── sensor.sf_n_irving_5th_ave_next_arrival_time
    ├── sensor.sf_n_irving_5th_ave_next_three
    ├── binary_sensor.sf_n_irving_5th_ave_api_ok
    └── [all other enabled sensors...]
```

### 🔧 Critical Bug Fixes

1. **HTTPS API Fix** - Changed API URL from HTTP to HTTPS
   - **Impact:** Fixes "Unable to connect" errors during setup
   - **Your issue:** ✅ SOLVED

2. **Better API Validation** - Uses StopMonitoring instead of operators endpoint
   - **Impact:** More reliable API key validation
   - **Result:** Setup works on first try

### 🎨 Visual Improvements

- **Icon Files Included:** 511.org logo files provided (icon.png, logo.png)
  - *Note:* Custom integrations cannot show icons in the integration list without Home Assistant Brands submission
  - *Entity icons work:* All sensors use appropriate MDI icons (mdi:train, mdi:bus, etc.)
- **Device Cards:** Clean device presentation in Devices page

## Files Changed

| File | Change | Why |
|------|--------|-----|
| `__init__.py` | Added device registry support | Create devices for stops/vehicles |
| `sensor.py` | Added DeviceInfo to all sensors | Link sensors to devices |
| `device_tracker.py` | Added DeviceInfo | Link trackers to devices |
| `const.py` | HTTP → HTTPS | Fix API connection |
| `api.py` | Better validation & logging | Improved reliability |
| `manifest.json` | Version 1.1.0 + icon | Version bump & icon |
| `icon.png` | NEW FILE | 511 logo |

## How to Update in HAOS

### Quick Steps:
1. **Copy Files:** Replace `/config/custom_components/transit_511/` with new version
2. **Restart:** Settings → System → Restart Home Assistant
3. **Clear Cache:** Press Ctrl+F5 in browser
4. **Verify:** Check Settings → Devices & Services → Devices

### Detailed Guide:
See **`UPDATING_IN_HAOS.md`** for complete step-by-step instructions

## What Happens to Existing Configuration?

### ✅ Your Data is Safe
- All existing sensors continue working
- No need to reconfigure
- API key is preserved
- Update intervals unchanged

### 🔄 What Changes
- Devices are created automatically on restart
- Sensors get linked to devices
- Better organization in UI

### 🎯 Recommended Action
**Option 1 - Keep Everything (Easiest):**
1. Update files
2. Restart HA
3. Devices appear automatically

**Option 2 - Fresh Start (Cleanest):**
1. Note your settings (API key, stops, vehicles)
2. Delete integration(s)
3. Update files
4. Restart HA
5. Re-add integration(s)
6. Devices created from scratch

## Verification Checklist

After updating, verify:

- [ ] Version shows "1.1.0" in Settings → Devices & Services → 511 Transit
- [ ] Icon shows 511 logo
- [ ] Go to Settings → Devices & Services → **Devices** tab
- [ ] See device(s) for your stop(s)/vehicle(s)
- [ ] Click on a device - see all sensors listed
- [ ] Sensors still updating (check timestamps)
- [ ] API OK sensor is "on"

## Before You Update

### Backup Your Settings
Write down:
- API key: `___________________________`
- Stops monitoring:
  - Operator: `___` Stop: `_____` Line: `___`
  - Operator: `___` Stop: `_____` Line: `___`
- Vehicles monitoring:
  - Operator: `___` Vehicle: `_____`
- Update intervals (if customized): `___` seconds

### Check Current Version
1. Go to Settings → Devices & Services
2. Find "511 Transit"
3. Click three dots (⋮) → Information
4. Note current version

## After Update - What to Expect

### In Devices & Services Page:
- Integration shows 511 icon
- Same number of config entries as before
- Each entry shows device count

### In Devices Tab:
- New devices appear (one per stop/vehicle)
- Device names match your stop/vehicle names
- Click device to see all sensors

### In Entity List:
- All sensors still present
- Each sensor now shows "Via device: [device name]"
- No sensors lost

## Troubleshooting

### "Changes not visible"
→ Clear browser cache: Ctrl+F5

### "No devices appearing"
→ Delete integration and re-add

### "Integration not found"
→ Check file structure, restart HA

### "Sensors lost device link"
→ Delete integration and re-add

**Full troubleshooting guide:** See `UPDATING_IN_HAOS.md`

## Additional Resources

- **Installation Guide:** `INSTALLATION_HAOS.md`
- **Update Guide:** `UPDATING_IN_HAOS.md`
- **User Manual:** `README.md`
- **Architecture:** `CLAUDE.md`
- **Changes:** `CHANGELOG.md`

## Questions?

Check the documentation files above, or review Home Assistant logs:
- Settings → System → Logs
- Search for "transit_511"

---

## Summary: Why Update?

✅ **Fixes your connection issue** (HTTPS)
✅ **Better organization** (devices)
✅ **Visual improvements** (icon)
✅ **More reliable** (better validation)
✅ **No breaking changes** (safe upgrade)

**Recommended:** Update now for better experience!
