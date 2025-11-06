# How to Update the Integration in HAOS and See Changes

When you upload updated files to your Home Assistant OS installation, you need to follow specific steps to ensure the changes are loaded and visible.

## Quick Update Process

### 1. Copy Updated Files
Copy the updated `custom_components/transit_511/` folder to `/config/custom_components/` on your HAOS (replacing the old files).

### 2. Force Home Assistant to Reload the Integration

You have **three options** to ensure changes are loaded:

#### Option A: Full Home Assistant Restart (Most Reliable)
1. Go to **Settings → System → Restart**
2. Click **Restart Home Assistant**
3. Wait 1-2 minutes for full restart
4. **✓ Best for:** Major changes, new files, manifest.json updates

#### Option B: Reload the Integration (Faster)
1. Go to **Settings → Devices & Services**
2. Find your **511 Transit** integration(s)
3. Click the **three dots (⋮)** on each integration entry
4. Click **Reload**
5. Repeat for each 511 Transit config entry you have
6. **✓ Best for:** Code changes in existing files, bug fixes

#### Option C: Delete and Re-add Integration (Clean Slate)
1. Go to **Settings → Devices & Services**
2. Find your **511 Transit** integration
3. Click the **three dots (⋮)**
4. Click **Delete**
5. Click **+ Add Integration**
6. Add **511 Transit** again with your settings
7. **✓ Best for:** Testing new config flows, major structural changes

### 3. Clear Browser Cache
After updating, **always clear your browser cache**:
- **Windows/Linux:** Press `Ctrl + F5` or `Ctrl + Shift + R`
- **Mac:** Press `Cmd + Shift + R`
- **Alternative:** Open in private/incognito mode

This ensures you see the latest UI changes and translations.

## Detailed Step-by-Step Update Guide

### Complete Update Process (Recommended for v1.1.0)

Since v1.1.0 adds device support, follow these steps for a clean update:

#### Step 1: Backup Current Configuration (Optional but Recommended)
1. Note your current settings:
   - API key
   - Stop codes you're monitoring
   - Vehicle IDs you're tracking
   - Custom update intervals

#### Step 2: Upload Updated Files
1. Connect to your HAOS config directory (Samba share, VSCode, etc.)
2. Navigate to `/config/custom_components/`
3. **Delete** the old `transit_511` folder completely
4. **Copy** the new `transit_511` folder from your computer
5. Verify all files are present:
   ```
   /config/custom_components/transit_511/
   ├── __init__.py         (updated - v1.1.0)
   ├── api.py              (updated - HTTPS fix)
   ├── config_flow.py      (updated)
   ├── const.py            (updated - HTTPS)
   ├── device_tracker.py   (updated - device link)
   ├── icon.png            (new file!)
   ├── manifest.json       (updated - version 1.1.0)
   ├── sensor.py           (updated - device link)
   ├── strings.json        (updated)
   └── translations/
       └── en.json         (updated)
   ```

#### Step 3: Restart Home Assistant
1. Go to **Settings → System**
2. Click **Restart**
3. Wait for restart to complete (1-2 minutes)

#### Step 4: Verify Update
1. Go to **Settings → Devices & Services**
2. Find your **511 Transit** integrations
3. Click on one to see its details
4. **You should now see:**
   - A **Device** for each stop/vehicle (new in v1.1.0!)
   - All sensors grouped under that device
   - Device info showing manufacturer (e.g., "San Francisco Muni")
   - Device model (e.g., "Stop 18031" or "Vehicle 2080")

#### Step 5: Check Devices Page
1. Go to **Settings → Devices & Services → Devices**
2. You should see new device entries like:
   - "SF N @ Irving St & 5th Ave"
   - "SF Vehicle 2080"
3. Click on a device to see all its sensors grouped together

#### Step 6: Clear Browser Cache
- Press `Ctrl + F5` (or `Cmd + Shift + R` on Mac)
- Or open in incognito/private mode to verify

## Troubleshooting: Changes Not Appearing

### Problem: Integration still shows old version
**Solution:**
1. Check the version number:
   - Settings → Devices & Services → 511 Transit → ⋮ → Information
   - Should show "Version: 1.1.0"
2. If still showing old version:
   - Delete `/config/custom_components/transit_511/` completely
   - Restart Home Assistant
   - Copy new files
   - Restart again

### Problem: No devices appearing
**Solution:**
1. Delete the integration: Settings → Devices & Services → 511 Transit → ⋮ → Delete
2. Restart Home Assistant
3. Re-add the integration: Settings → Devices & Services → + Add Integration → 511 Transit
4. Devices will be created automatically

### Problem: Old sensors still exist without device link
**Solution:**
- The sensors need to be recreated to link to devices
- Delete the integration and re-add it (your config will be lost)
- **OR** wait for the next Home Assistant restart - devices will be created

### Problem: Browser shows old UI
**Solution:**
- Hard refresh: `Ctrl + F5` or `Cmd + Shift + R`
- Clear browser cache completely
- Open in private/incognito window
- Try a different browser

### Problem: "Integration not found" after update
**Solution:**
1. Check file permissions: All files should be readable
2. Verify file structure is correct (see Step 2 above)
3. Check Home Assistant logs:
   - Settings → System → Logs
   - Search for "transit_511"
4. Common issues:
   - Missing `__init__.py` file
   - Incorrect folder name (must be exactly `transit_511`)
   - Files copied to wrong location

### Problem: Integration loads but errors immediately
**Solution:**
1. Check logs: Settings → System → Logs
2. Common causes:
   - Syntax error in updated files
   - Missing import in Python files
3. If logs show import errors, verify all files were copied correctly

## Version-Specific Update Notes

### Updating from v1.0.0 to v1.1.0

**New Features:**
- ✨ Devices created for each stop and vehicle
- ✨ All sensors linked to their parent device
- ✨ Integration icon (511.png)
- 🐛 Fixed HTTPS API URL issue
- 🐛 Better API validation

**Breaking Changes:**
- None! Existing sensors will continue to work

**Recommended Actions:**
1. Delete and re-add integration to see device grouping
2. Or wait - devices will be created on next restart

### Updating Future Versions

For future updates, the process is the same:
1. Upload new files
2. Restart Home Assistant (or reload integration)
3. Clear browser cache
4. Check changelog for breaking changes

## Verifying the Update Was Successful

### Checklist:
- [ ] Version shows "1.1.1" in integration info
- [ ] Devices page shows device for each stop/vehicle
- [ ] Sensors are grouped under devices
- [ ] Entity icons showing (mdi:train, mdi:bus, etc.)
- [ ] API connection working (check API OK sensor)
- [ ] Data updating (check timestamps)

**Note:** Integration list icon won't show - this is normal for custom integrations. See `ICON_SETUP.md` for details.

### Quick Test:
1. Go to **Settings → Devices & Services → Devices**
2. Search for "transit" or your operator name (e.g., "SF")
3. You should see device cards with:
   - Device name (e.g., "SF N @ Irving St & 5th Ave")
   - Manufacturer (e.g., "San Francisco Muni")
   - Model (e.g., "Stop 18031")
   - List of sensors below

## Best Practices for Future Updates

### Before Updating:
1. ✅ Note your current configuration
2. ✅ Take screenshots of dashboards using the integration
3. ✅ Check if update has breaking changes

### During Update:
1. ✅ Delete old folder completely before copying new one
2. ✅ Verify all files copied successfully
3. ✅ Restart Home Assistant (don't just reload)

### After Update:
1. ✅ Clear browser cache
2. ✅ Check logs for errors
3. ✅ Verify all sensors still working
4. ✅ Test one stop/vehicle before adding more

## Still Having Issues?

### Check Home Assistant Logs
1. Settings → System → Logs
2. Search for "transit_511" or "511"
3. Look for ERROR or WARNING messages
4. Common errors:
   - `ModuleNotFoundError`: Missing file or wrong structure
   - `ImportError`: Syntax error in Python files
   - `AttributeError`: Version mismatch or incomplete update

### File Permission Issues
If running HAOS on certain systems:
```bash
# From SSH/Terminal add-on:
cd /config/custom_components/transit_511
ls -la
# All files should be readable (permissions like -rw-r--r--)
```

### Complete Fresh Install
If all else fails:
1. Delete integration from UI
2. Delete `/config/custom_components/transit_511/` folder
3. Restart Home Assistant
4. Copy fresh files from this repository
5. Restart Home Assistant again
6. Re-add integration

## Summary: Quick Reference

| Situation | Action | Time |
|-----------|--------|------|
| Updated Python files | Restart HA | 2 min |
| Updated manifest.json | Restart HA | 2 min |
| Updated translations | Reload integration + clear cache | 30 sec |
| Major version change | Delete & re-add integration | 2 min |
| Changes not showing | Clear browser cache | 5 sec |
| Testing new config | Delete & re-add | 2 min |

**Remember:** Always restart Home Assistant after updating files, and always clear your browser cache!
