# How to Verify Shared API Calls Are Working

## Quick Check: Restart and Look at Logs

After restarting Home Assistant with v1.5.1:

1. **Open Home Assistant Logs**: Settings → System → Logs
2. **Filter for**: `transit_511`
3. **Look for these messages during startup**:

```
INFO (MainThread) [custom_components.transit_511] Created new global coordinator for SF stop 18031
INFO (MainThread) [custom_components.transit_511] Reusing existing global coordinator for SF stop 18031
```

**What it means:**
- First device for a stop: "Created new" ✨
- Second+ device for same stop: "Reusing existing" 🔄 (SHARED!)

## Example Scenarios

### Scenario 1: Multiple Devices, Same Stop
You have 3 config entries:
- Device 1: Stop 18031 (all lines)
- Device 2: Stop 18031 (line N only) 
- Device 3: Stop 18031 (line 7 only)

**Expected logs:**
```
Created new global coordinator for SF stop 18031
Reusing existing global coordinator for SF stop 18031
Reusing existing global coordinator for SF stop 18031
```

**Result**: ✅ 1 API call shared by 3 devices!

### Scenario 2: Different Stops
You have 2 config entries:
- Device 1: Stop 18031
- Device 2: Stop 15296

**Expected logs:**
```
Created new global coordinator for SF stop 18031
Created new global coordinator for SF stop 15296
```

**Result**: ✅ 2 API calls (can't be shared, different stops)

### Scenario 3: Mixed Scenario
You have 4 config entries:
- Device 1: Stop 18031 (line N)
- Device 2: Stop 18031 (line 7)
- Device 3: Stop 15296
- Device 4: Stop 15296 (line 14)

**Expected logs:**
```
Created new global coordinator for SF stop 18031
Reusing existing global coordinator for SF stop 18031
Created new global coordinator for SF stop 15296
Reusing existing global coordinator for SF stop 15296
```

**Result**: ✅ 2 API calls for 4 devices (50% reduction!)

## Check Current Global Coordinators

**Method 1: Search Logs**
Look for lines with "transit_511_global" in recent logs

**Method 2: Check Entity Names**
The global coordinators are named:
`transit_511_global_{OPERATOR}_{STOP_CODE}`

So if you see errors for:
- `transit_511_global_SF_15297`
- `transit_511_global_SF_15296`

That means you have 2 unique stops being monitored (2 API calls total).

## Verify API Efficiency

**Before v1.5.0:**
- Monitoring same stop 3 times = 3 API calls = 180 req/hr at 60s interval ❌

**After v1.5.0:**
- Monitoring same stop 3 times = 1 API call = 60 req/hr at 60s interval ✅

**How to confirm:**
1. Check how many devices you have per stop
2. Count "Reusing existing" messages
3. More "Reusing" = more sharing = fewer API calls!

## Pro Tip: Rate Limit Tracking

If you were hitting rate limits before (60 req/hr):
- Watch for "Rate limit exceeded" errors
- With sharing enabled, you should see these less frequently
- Each "Reusing" message = one less API call!
