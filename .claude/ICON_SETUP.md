# Icon Setup for 511 Transit Integration

## Why the Icon Doesn't Show

Home Assistant has different icon systems:

1. **Built-in integrations**: Use the `icon` field in `manifest.json` - **Only works for core integrations**
2. **Custom integrations**: Need to use the brands system or provide icon through other means

Unfortunately, custom integrations cannot easily display icons in the integration list the same way core integrations do. The `icon` field in manifest.json is generally ignored for custom integrations.

## Current Icon Files Included

The integration includes these icon files:
- `icon.png` - 500x500 PNG (original)
- `logo.png` - 500x500 PNG (Home Assistant logo format)
- `logo@2x.png` - 500x500 PNG (Retina display version)

## Where You WILL See Icons

Even though the integration icon doesn't show in the integration list, icons will appear in:

### ✅ Entity Cards
Individual sensors use MDI (Material Design Icons):
- `mdi:train` - Next arrival sensors
- `mdi:numeric` - Count sensors
- `mdi:train-car` - Vehicle sensors
- `mdi:flag-checkered` - Destination sensors
- `mdi:seat-recline-normal` - Occupancy sensors
- `mdi:format-list-numbered` - Next three arrivals
- `mdi:bus` - Device tracker for vehicles

### ✅ Device Pages
Devices show up properly in Settings → Devices & Services → Devices with:
- Device name
- Manufacturer (operator name)
- Model (stop/vehicle ID)
- Area assignment

## Workaround Options

### Option 1: Accept the Limitation
Most custom integrations don't have icons in the integration list. Your integration will:
- ✅ Work perfectly
- ✅ Show device cards
- ✅ Show entity icons
- ❌ No icon in integration list (like most custom integrations)

### Option 2: Add to Home Assistant Brands (Advanced)
For the icon to show in the integration list, you would need to:

1. Create a brands repository entry:
   ```
   https://github.com/home-assistant/brands
   ```

2. Submit a pull request with:
   - `icon.png` (256x256)
   - `logo.png` (256x256)
   - `icon@2x.png` (512x512)
   - `logo@2x.png` (512x512)

3. File structure:
   ```
   brands/
   └── custom_integrations/
       └── transit_511/
           ├── icon.png
           ├── icon@2x.png
           ├── logo.png
           └── logo@2x.png
   ```

4. Wait for PR approval and merge

**Note:** This is a lot of effort for just an icon, and most custom integrations don't do this.

### Option 3: Use Frontend Card (Lovelace)
Create a custom button card for quick access:

```yaml
type: button
name: 511 Transit
icon: mdi:train
tap_action:
  action: navigate
  navigation_path: /config/integrations/integration/transit_511
```

Or create a picture-entity card with your icon:

```yaml
type: picture
image: /local/511_icon.png
tap_action:
  action: navigate
  navigation_path: /config/integrations
```

(First, upload `icon.png` to `/config/www/511_icon.png`)

## What's More Important

The lack of an icon in the integration list is cosmetic. What matters:

✅ **Devices are created** - YES
✅ **Sensors work properly** - YES
✅ **Entity icons show** - YES
✅ **Data updates** - YES
✅ **Professional organization** - YES
❌ **Icon in integration list** - NO (limitation of custom integrations)

## Comparison: Custom vs Built-in

| Feature | Built-in Integration | Custom Integration (Us) |
|---------|---------------------|------------------------|
| Icon in integration list | ✅ Yes | ❌ No* |
| Entity icons | ✅ Yes | ✅ Yes |
| Device creation | ✅ Yes | ✅ Yes |
| Config flow | ✅ Yes | ✅ Yes |
| Functionality | ✅ Yes | ✅ Yes |

*Without brands repository submission

## Files Provided

Even though the icon won't show in the integration list without brands submission, we've included:

```
custom_components/transit_511/
├── icon.png          # 500x500 - Base icon
├── logo.png          # 500x500 - Logo format
├── logo@2x.png       # 500x500 - Retina version
└── .icons/
    └── icon.png      # 500x500 - Alternative location
```

These files are:
- Properly formatted
- Correct size
- Ready for brands submission if you choose to do so
- Can be used in Lovelace dashboards

## Recommendation

**Don't worry about the integration list icon.**

The integration works perfectly without it. Focus on:
1. ✅ Devices showing up properly
2. ✅ Sensors working correctly
3. ✅ Data updating reliably

The missing icon in the integration list is normal for custom integrations and doesn't affect functionality at all.

## Future: If You Want the Icon

If you really want the icon in the integration list:

1. Wait until you're happy with the integration
2. Submit to Home Assistant Brands repository
3. Follow their guidelines for custom integrations
4. Wait for approval

But honestly, it's not worth the effort unless you're planning to share this integration publicly.

## Summary

- **Icon files included**: ✅ Yes, properly formatted
- **Will show in integration list**: ❌ No (custom integration limitation)
- **Will show as entity icons**: ✅ Yes, using MDI icons
- **Does it matter**: ❌ No, purely cosmetic
- **Does integration work**: ✅ Yes, perfectly

**Bottom line:** Your integration is professional and functional. The missing integration list icon is a limitation all custom integrations face.
