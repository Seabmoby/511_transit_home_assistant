# Verifying Shared API Calls

## Check Home Assistant Logs

Look for these log messages when the integration loads:

**Creating new coordinator:**
```
Created new global coordinator for SF stop 18031
```

**Reusing existing coordinator (SHARED!):**
```
Reusing existing global coordinator for SF stop 18031
```

## How to Check:

1. Go to **Settings → System → Logs**
2. Search for: `transit_511`
3. Look for "Created new" vs "Reusing existing" messages
4. Count how many times you see each

## What You Should See:

**Example: 3 devices monitoring the same stop (18031)**
- 1x "Created new global coordinator for SF stop 18031"
- 2x "Reusing existing global coordinator for SF stop 18031"

This confirms only 1 API call is being made for all 3 devices!

## Alternative: Check Developer Tools

1. Go to **Developer Tools → States**
2. Search for: `transit_511_global`
3. Look at the coordinator names in entity IDs
4. Multiple devices with same stop_code = shared coordinator

## Watch API Call Rate

If you have multiple entries for the same stop:
- **Before v1.5.0**: Each entry = separate API call
- **After v1.5.0**: All entries for same stop = 1 shared API call

Monitor for rate limit errors in logs - you should see fewer with v1.5.0!
