# Installation Guide for Home Assistant OS (HAOS)

## Quick Installation Steps

### 1. Access Your Config Directory

Choose one of these methods to access `/config/` on your HAOS:

#### Method A: Samba Share (Easiest)
1. Install **Samba share** add-on (Settings → Add-ons → Add-on Store)
2. Start the Samba share add-on
3. From your computer:
   - **Windows:** Open File Explorer, go to `\\homeassistant.local\config`
   - **Mac:** Finder → Go → Connect to Server → `smb://homeassistant.local/config`
   - **Linux:** File Manager → `smb://homeassistant.local/config`

#### Method B: Visual Studio Code Add-on
1. Install **Studio Code Server** add-on
2. Open it and navigate to `/config/`

#### Method C: SSH/Terminal
1. Install **Terminal & SSH** or **Advanced SSH & Web Terminal** add-on
2. Access `/config/` via command line

### 2. Copy Integration Files

1. On your computer, locate this folder: `custom_components/transit_511/`
2. Copy the entire `transit_511` folder to your HAOS config:
   ```
   /config/custom_components/transit_511/
   ```

   **Note:** Create the `custom_components` folder if it doesn't exist

3. Verify all files are present:
   ```
   /config/custom_components/transit_511/
   ├── __init__.py
   ├── api.py
   ├── config_flow.py
   ├── const.py
   ├── device_tracker.py
   ├── icon.png
   ├── manifest.json
   ├── sensor.py
   ├── strings.json
   └── translations/
       └── en.json
   ```

### 3. Restart Home Assistant

1. Go to Settings → System → Restart
2. Wait for Home Assistant to fully restart (usually 1-2 minutes)

### 4. Add the Integration

1. Go to Settings → Devices & Services
2. Click "**+ Add Integration**" (bottom right)
3. Search for "**511 Transit**"
4. Follow the setup wizard:
   - Enter your 511.org API key
   - Choose Stop or Vehicle monitoring
   - Configure your first stop or vehicle

### 5. Add More Stops or Vehicles

To monitor multiple stops/vehicles:
1. Click "**+ Add Integration**" again
2. Search for "**511 Transit**"
3. Use the same (or different) API key
4. Configure another stop or vehicle

Repeat as needed for all stops and vehicles you want to monitor!

## Troubleshooting

### Integration Not Found
- Make sure all files are in `/config/custom_components/transit_511/`
- Verify you restarted Home Assistant after copying files
- Clear your browser cache (Ctrl+F5 or Cmd+Shift+R)

### "Unable to connect to the 511 API"
- Verify your API key is correct at https://511.org/open-data/token
- Check your Home Assistant has internet access
- Ensure you're not behind a firewall blocking api.511.org

### Rate Limit Issues
- Default is 60s intervals = 60 requests/hour (at limit for 1 stop)
- For multiple stops, increase intervals:
  - 2 stops → 120s intervals
  - 3 stops → 180s intervals
  - 4 stops → 240s intervals

### Entities Not Appearing
- Check Settings → Devices & Services → 511 Transit → Configure
- Make sure the stop code is correct for your operator
- Review Home Assistant logs: Settings → System → Logs

## Rate Limit Calculator

**Formula:** `(3600 ÷ interval_seconds) × number_of_stops ≤ 60`

| Stops | Interval | Requests/Hour |
|-------|----------|---------------|
| 1     | 60s      | 60 (at limit) |
| 2     | 60s      | 120 ⚠️ OVER   |
| 2     | 120s     | 60 (at limit) |
| 3     | 180s     | 60 (at limit) |
| 4     | 240s     | 60 (at limit) |
| 5     | 300s     | 60 (at limit) |

## Getting a 511.org API Key

1. Visit https://511.org/open-data/token
2. Fill out the registration form
3. You'll receive your API key via email
4. Free tier: 60 requests per hour

## Example Setup

**Scenario:** Monitor 3 Muni stops with one API key

1. **Add Integration #1:**
   - API Key: your_key_here
   - Stop Monitoring → SF → Stop 18031 (N Judah @ Irving & 5th)
   - Options: Set interval to 180s

2. **Add Integration #2:**
   - API Key: your_key_here (same key)
   - Stop Monitoring → SF → Stop 16991 (N Judah @ 9th & Irving)
   - Options: Set interval to 180s

3. **Add Integration #3:**
   - API Key: your_key_here (same key)
   - Stop Monitoring → SF → Stop 15419 (N Judah @ Carl & Cole)
   - Options: Set interval to 180s

**Result:** 3 stops × (3600÷180) = 3 × 20 = 60 requests/hour ✓

## Support

- Issues: Check the logs at Settings → System → Logs
- Questions: See README.md for detailed documentation
- Updates: Copy new files and restart Home Assistant
