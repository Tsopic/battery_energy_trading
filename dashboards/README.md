# Battery Energy Trading Dashboards

This directory contains pre-built dashboard configurations for the Battery Energy Trading integration.

## 📊 Available Dashboards

### Main Dashboard (`battery_energy_trading_dashboard.yaml`)

A comprehensive dashboard showing all features and controls:

- **Nord Pool Price Chart** - Today vs Tomorrow electricity prices (requires ApexCharts Card)
- **Current Status** - Real-time operation indicators with current price
- **Operation Modes** - Enable/disable switches
- **Discharge Schedule** - Selling slots and revenue
- **Charging Schedule** - Buying slots and costs
- **Arbitrage Opportunities** - Trading opportunities
- **Configuration** - All settings in one place

## 📋 Prerequisites

The dashboard includes a Nord Pool price chart that requires the **ApexCharts Card** custom component:

1. Install **ApexCharts Card** via HACS:
   - Go to HACS → Frontend
   - Search for "ApexCharts Card"
   - Click Install
   - Restart Home Assistant

**Note:** If you don't install ApexCharts Card, the price chart won't display, but all other dashboard cards will work fine.

## 🚀 Installation

### Option 1: Manual Installation (Recommended)

1. **(Optional)** Install ApexCharts Card via HACS (see Prerequisites above)
2. In Home Assistant, go to **Settings** → **Dashboards**
3. Click **+ ADD DASHBOARD**
4. Choose **New dashboard from scratch**
5. Give it a name: "Battery Energy Trading"
6. Click the **✏️ Edit** button (top right)
7. Click **⋮** (three dots) → **Raw configuration editor**
8. Copy the entire contents of `battery_energy_trading_dashboard.yaml`
9. Paste into the editor
10. Click **SAVE**

### Option 2: Copy to Lovelace Config

If you use YAML mode for dashboards:

```yaml
# In your lovelace configuration
dashboards:
  battery-energy-trading:
    mode: yaml
    title: Battery Energy Trading
    icon: mdi:battery-charging
    filename: battery_energy_trading_dashboard.yaml
```

Then copy the YAML file to your Home Assistant config directory.

## 🎨 Customization

### Replacing Entity IDs

The dashboard uses generic entity IDs. You may need to replace:

```yaml
# Replace this pattern:
battery_energy_trading

# With your actual entry ID if different:
battery_energy_trading_xxxxx
```

### Card Types

The dashboard uses standard Home Assistant cards:
- `vertical-stack` - Groups cards vertically
- `entities` - Lists entities
- `glance` - Quick overview
- `attribute` - Shows entity attributes
- `markdown` - Text and headers

### Customizing Icons

Change any icon using [Material Design Icons](https://materialdesignicons.com/):

```yaml
icon: mdi:battery-charging  # Change to any MDI icon
```

## 📱 Mobile-Friendly

The dashboard is optimized for both desktop and mobile views:
- Vertical stacking works well on narrow screens
- Icons clearly indicate status
- Color-coded states for quick recognition

## 🎯 Features Highlighted

### Status Indicators
- 🔋 Discharging Now - Green when selling
- ⚡ Charging Now - Blue when buying
- 📤 Export Profitable - Shows when export is good
- ☀️ Solar Active - Shows when solar is generating

### Revenue Tracking
- Estimated revenue from discharge slots
- Estimated cost from charging slots
- ROI percentage for arbitrage

### Smart Controls
- Toggle features on/off
- Adjust price thresholds
- Configure battery protection
- Set solar override thresholds

## 🔧 Troubleshooting

### Entities Not Found

If you see "Entity not available":

1. Check the integration is set up correctly
2. Verify entity IDs in **Developer Tools** → **States**
3. Update entity IDs in dashboard YAML if needed

### Attributes Not Showing

Some attributes only appear when:
- Nord Pool has data (after ~13:00 CET)
- Slots are selected (based on your configuration)
- The integration has calculated schedules

### Cards Not Displaying

Ensure you have:
- Latest Home Assistant version (2024.1+)
- Integration installed and configured
- At least one sensor entity created

## 💡 Tips

### Quick Access

Add to sidebar for quick access:
1. Settings → Dashboards
2. Find "Battery Energy Trading"
3. Toggle "Show in sidebar"

### Notifications

Create automations to notify you:
```yaml
automation:
  - alias: "Notify Peak Price Selling"
    trigger:
      - platform: state
        entity_id: binary_sensor.battery_energy_trading_forced_discharge
        to: 'on'
    action:
      - service: notify.mobile_app
        data:
          title: "⚡ Selling Energy"
          message: "High price period - selling now at {{ states('sensor.nordpool') }} EUR/kWh"
```

### Conditional Cards

Show/hide sections based on switches:

```yaml
- type: conditional
  conditions:
    - entity: switch.battery_energy_trading_enable_forced_charging
      state: "on"
  card:
    # Your charging schedule card here
```

## 📚 Additional Resources

- [Home Assistant Dashboard Documentation](https://www.home-assistant.io/dashboards/)
- [Card Types](https://www.home-assistant.io/dashboards/cards/)
- [Material Design Icons](https://materialdesignicons.com/)

## 🆘 Support

Issues or questions?
- [GitHub Issues](https://github.com/Tsopic/battery_energy_trading/issues)
- [Home Assistant Community](https://community.home-assistant.io/)
