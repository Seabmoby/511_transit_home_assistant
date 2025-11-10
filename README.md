# 511 Transit - Home Assistant Integration

A custom Home Assistant integration for the 511.org Transit API that provides real-time transit information for Bay Area transit agencies including SF Muni, BART, AC Transit, and more.

## Features

- **API Key Reuse** 🔑 *(v1.3.0)*: Enter your API key once, then automatically reuse it for all future stops/vehicles - no more re-entering credentials!
- **Smart Icons** 🎨: Icons automatically change based on vehicle type (SF Muni: Letters → 🚊 train, Numbers → 🚌 bus, BART/Caltrain → 🚊 train, AC Transit/SamTrans → 🚌 bus)
- **Device Organization**: Each stop or vehicle creates a dedicated Device with all sensors grouped together
- **Stop Monitoring**: Track arrival and departure times at transit stops
- **Vehicle Tracking**: GPS tracking of individual transit vehicles via device_tracker
- **Flexible Entity Creation**: Choose which sensors to create for each stop
- **Direction Filtering**: Separate sensors for inbound/outbound directions
- **Multiple Stops/Vehicles**: Add as many stops or vehicles as needed
- **Configurable Update Intervals**: Balance freshness vs. API rate limits

## Supported Transit Agencies

Any agency available through the 511.org API, including:
- San Francisco Muni (SF)
- BART (BA)
- AC Transit (AC)
- Caltrain (CM)
- County Connection (CC)
- And many more Bay Area transit agencies

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right and select "Custom repositories"
4. Add this repository URL and select "Integration" as the category
5. Click "Install"
6. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/transit_511` folder to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

### Getting an API Key

1. Visit https://511.org/open-data/token
2. Register for a free API key
3. Note: Free tier has a limit of 60 requests per hour

### Setting Up the Integration

**First Time Setup:**
1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "511 Transit"
4. **Enter your 511.org API key** (you'll only need to do this once!)
5. Choose monitoring type:
   - **Stop Monitoring**: For arrival/departure predictions at a stop
   - **Vehicle Monitoring**: For GPS tracking of a specific vehicle
6. Configure your stop or vehicle details

**Adding Additional Stops/Vehicles:**
1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "511 Transit"
4. Your API key is **automatically reused** - you'll skip straight to monitoring type selection!
5. Configure your next stop or vehicle

The integration remembers your API key from the first setup, making it quick and easy to add multiple stops and vehicles without re-entering credentials.

#### Stop Monitoring Setup

1. Select the transit operator (e.g., SF for Muni)
2. Enter the stop code (e.g., 18031 for Irving & 5th Ave)
3. Optionally specify a line/route ID to filter
4. The integration will create various sensors for that stop

#### Vehicle Monitoring Setup

1. Select the transit operator
2. Enter the vehicle ID you want to track
3. A device_tracker entity will be created with GPS location

### Adding Multiple Stops or Vehicles

**Each stop/vehicle gets its own Device** in Home Assistant with:
- All related sensors grouped under the device
- Device info showing operator/agency name
- Easy organization in the Devices page
- Independent update intervals and configuration

**Example workflow (v1.3.0+):**
- **First integration**: Enter API key → Stop monitoring → N Judah @ Irving & 5th → **Creates device: "SF N @ Irving St & 5th Ave"**
- **Second integration**: API key reused automatically → Stop monitoring → N Judah @ 9th & Irving → **Creates device: "SF N @ 9th Ave & Irving St"**
- **Third integration**: API key reused automatically → Vehicle monitoring → Track vehicle 2080 → **Creates device: "SF Vehicle 2080"**
- **Fourth integration**: API key reused automatically → Stop monitoring → BART @ Embarcadero → **Creates device: "BA @ Embarcadero Station"**

**Note:** After your first setup, you'll never need to enter your API key again - it's automatically reused for all subsequent stops and vehicles!

### Monitoring Both Stops and Vehicles

You can monitor as many stops and vehicles as you want:
1. Each requires a separate integration entry (just click "Add Integration" again)
2. Your API key is automatically shared across all entries (v1.3.0+)
3. Be mindful of the 60 requests/hour rate limit (see below)

### Finding Stop Codes

- **SF Muni**: Stop codes are visible on stop signs and in the 511.org trip planner
- **511.org API**: Use the `/transit/stops` endpoint with your operator ID
- **Example**: For SF Muni stop "Irving St & 5th Ave", the stop code is `18031`

## Available Sensors (Stop Monitoring)

The integration can create the following sensors for each stop:

### Basic Sensors
- **Count**: Number of upcoming arrivals
- **API Timestamp**: Last API update time
- **Next Arrival (minutes)**: Minutes until next arrival
- **Next Arrival Time**: Timestamp of next arrival
- **Next Vehicle**: Vehicle ID of next arrival
- **Next Destination**: Destination of next vehicle
- **Next Occupancy**: Crowding level (seatsAvailable, standingAvailable, full)
- **Next Three**: Comma-separated minutes for next 3 arrivals (e.g., "6, 14, 22")
- **API OK**: Binary sensor for API connectivity

### Direction-Filtered Sensors
For each direction (IB = Inbound, OB = Outbound):
- **IB/OB Count**: Count filtered by direction
- **IB/OB Next Arrival (minutes)**: Next arrival for that direction
- **IB/OB Next Arrival Time**: Timestamp for that direction
- **IB/OB Next Vehicle**: Vehicle ID for that direction
- **IB/OB Next Three**: Next 3 arrivals for that direction

## Device Tracker (Vehicle Monitoring)

When monitoring a vehicle, the integration creates a device_tracker entity with:
- GPS coordinates (latitude/longitude)
- Bearing/heading
- Line/route information
- Origin and destination
- Occupancy status
- Next stop information

## Configuration Options

After setup, you can configure:
- **Update Interval**: How often to fetch data (30-300 seconds)
  - Default: 60 seconds
  - Note: 60 req/hour limit = max 1 request per minute per API key
- **Enabled Entities**: Which sensors to create for stop monitoring

## Rate Limits

The 511.org API has a rate limit of **60 requests per hour** per API key.

### Tips to Stay Under Limit
- Default interval: 60 seconds = 60 requests/hour per stop (at the limit)
- **Multiple stops/vehicles:** Each config entry makes its own requests
  - 2 stops at 60s = 120 req/hr (OVER LIMIT)
  - 2 stops at 120s = 60 req/hr (at limit)
  - 3 stops at 180s = 60 req/hr (at limit)
  - 4 stops at 240s = 60 req/hr (at limit)
- **Formula:** `(3600 / interval_seconds) × number_of_stops ≤ 60`
- **Recommended:** If monitoring multiple stops, increase intervals accordingly
- **Example:** 3 stops → use 180s (3 minute) intervals

### Rate Limit Strategies
1. **Single API key, multiple stops:** Adjust intervals based on number of stops
2. **Multiple API keys:** Get additional API keys to monitor more stops at shorter intervals
3. **Priority stops:** Use shorter intervals (60s) for important stops, longer intervals (300s) for others

## Example Use Cases

### Dashboard Card for Next Arrivals
```yaml
type: entities
title: N Judah @ Irving & 5th
entities:
  - entity: sensor.sf_n_irving_5th_ave_next_arrival_min
    name: Next Train
  - entity: sensor.sf_n_irving_5th_ave_next_three
    name: Next 3 Trains
  - entity: sensor.sf_n_irving_5th_ave_next_destination
    name: Destination
  - entity: sensor.sf_n_irving_5th_ave_next_occupancy
    name: Crowding
```

### Automation: Notify When Train Approaching
```yaml
automation:
  - alias: "Train Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.sf_n_irving_5th_ave_ib_next_arrival_min
        below: 5
    action:
      - service: notify.mobile_app
        data:
          message: "N Judah arriving in {{ states('sensor.sf_n_irving_5th_ave_ib_next_arrival_min') }} minutes!"
```

### Map Card with Vehicle Tracker
```yaml
type: map
entities:
  - entity: device_tracker.sf_vehicle_2080
default_zoom: 13
```

## Troubleshooting

### "Authentication failed" Error
- Verify your API key is correct
- Check that your API key is active at https://511.org/open-data/token

### "Rate limit exceeded" Error
- You're making more than 60 requests per hour
- Increase your update interval
- Reduce the number of monitored stops/vehicles

### No Data / Sensors Show "Unknown"
- Verify the stop code is correct for your operator
- Check that the stop has active service
- Some stops may not have real-time data available

### Sensors Not Updating
- Check the "API OK" binary sensor - should be "on"
- Review Home Assistant logs for errors
- Verify internet connectivity

## API Documentation

Full 511.org API documentation: https://511.org/open-data/transit

## Support

For issues, feature requests, or questions:
- Open an issue on GitHub
- Check the Home Assistant community forums

## License

MIT License - see LICENSE file for details
