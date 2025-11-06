═══════════════════════════════════════════════════════════════════════════
                    511 TRANSIT INTEGRATION - ICON STATUS
═══════════════════════════════════════════════════════════════════════════

QUICK ANSWER: Why doesn't the icon show in the integration list?
───────────────────────────────────────────────────────────────────────────

This is a LIMITATION of ALL custom Home Assistant integrations.

Only BUILT-IN integrations (included with Home Assistant core) can show
icons in the Settings → Devices & Services integration list.

Custom integrations (like this one) cannot display icons there without
being added to the Home Assistant "Brands" repository - a complex process
that requires a GitHub pull request and approval.


WHERE ICONS DO SHOW:
───────────────────────────────────────────────────────────────────────────

✅ Entity Icons
   - Next arrival sensors: mdi:train
   - Vehicle trackers: mdi:bus
   - Count sensors: mdi:numeric
   - Destination: mdi:flag-checkered
   - Occupancy: mdi:seat-recline-normal
   - And more!

✅ Device Cards
   - Device name shown clearly
   - Manufacturer (operator name)
   - Model (stop/vehicle ID)
   - Professional presentation

✅ Lovelace Dashboards
   - Use entity icons in cards
   - Create custom buttons with icons
   - Full customization available


WHERE ICONS DON'T SHOW:
───────────────────────────────────────────────────────────────────────────

❌ Integration List (Settings → Devices & Services)
   - This is where you'd see the 511 logo
   - Not possible for custom integrations
   - ALL custom integrations have this limitation
   - It's cosmetic only - doesn't affect functionality


ICON FILES INCLUDED:
───────────────────────────────────────────────────────────────────────────

We've included properly formatted icon files:
  • icon.png (500×500)
  • logo.png (500×500)
  • logo@2x.png (500×500)
  • .icons/icon.png (500×500)

These are ready to use if you want to submit to Home Assistant Brands,
or use in custom Lovelace cards.


DOES THIS MATTER?
───────────────────────────────────────────────────────────────────────────

No! The integration works perfectly without it.

✅ All functionality works
✅ Devices created properly
✅ Sensors update correctly
✅ Entity icons show everywhere
✅ Professional appearance

The missing integration list icon is purely cosmetic and normal for
custom integrations.


COMPARISON TO OTHER INTEGRATIONS:
───────────────────────────────────────────────────────────────────────────

Look at other custom integrations in your Home Assistant:
• HACS integrations
• Custom GitHub integrations
• Community integrations

Most don't have icons in the integration list either!


IF YOU REALLY WANT THE ICON:
───────────────────────────────────────────────────────────────────────────

1. Submit to Home Assistant Brands repository on GitHub
2. Create PR with icon files
3. Wait for review and approval
4. Wait for next Home Assistant release

Honestly? Not worth the effort unless you're sharing this publicly.


BOTTOM LINE:
───────────────────────────────────────────────────────────────────────────

✅ Your integration is professional and fully functional
✅ Icons show where it matters (entities, devices, dashboards)
❌ Integration list icon is a limitation ALL custom integrations face
👍 This is normal and expected

Don't worry about it! Focus on the integration working correctly,
which it does! 🚀


═══════════════════════════════════════════════════════════════════════════
For detailed information, see: ICON_SETUP.md
═══════════════════════════════════════════════════════════════════════════
