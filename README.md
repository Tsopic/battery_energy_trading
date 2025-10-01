# Battery Energy Trading for Home Assistant

[![GitHub Release](https://img.shields.io/github/v/release/Tsopic/battery_energy_trading)](https://github.com/Tsopic/battery_energy_trading/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/hacs/integration)

A comprehensive Home Assistant integration for intelligent battery management and energy trading optimization. Automatically buy energy when prices are low, sell when prices are high, and maximize solar energy utilization.

## 🎯 Features

### Smart Energy Trading
- **Arbitrage Detection** - Automatically identifies profitable buy-low, sell-high opportunities
- **Dynamic Pricing** - Integrates with Nord Pool (or any price sensor) for real-time price tracking
- **15-Minute Slot Support** - Works with modern 15-minute energy markets
- **Profit Optimization** - Calculates optimal charging and discharging schedules

### Intelligent Battery Management
- **Optional Force Charging** - Toggle automatic charging during cheap hours (disabled by default for solar-only setups)
- **Smart Discharging** - Sells excess solar/battery during highest-price 15-min slots (enabled by default)
- **Battery Protection** - Respects minimum battery levels
- **Solar Override** - Allows discharge even at low battery when solar is generating

### Solar-First Operation
- **Designed for Solar Users** - Default settings prioritize selling excess solar, not grid charging
- **Peak Price Selling** - Automatically exports during high-price periods
- **Flexible Modes** - Toggle charging/discharging independently via switches

### Safety & Control
- **Minimum Battery Levels** - Prevents over-discharge
- **Price Thresholds** - Won't sell at a loss
- **Export Management** - Smart grid export based on profitability
- **Automation-Friendly Switches** - Full control via Home Assistant automations

## 📊 What Problems Does This Solve?

1. **Energy Cost Optimization** - Reduce electricity bills by buying at cheapest times
2. **Revenue Generation** - Earn money by selling energy at peak prices
3. **Battery Longevity** - Smart charging/discharging patterns extend battery life
4. **Solar Maximization** - Optimizes solar energy usage and storage
5. **Grid Independence** - Reduces reliance on grid during expensive periods

## 🚀 Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on `Integrations`
3. Click the three dots in the top right corner
4. Select `Custom repositories`
5. Add this repository URL: `https://github.com/Tsopic/battery_energy_trading`
6. Select category: `Integration`
7. Click `Add`
8. Click `+ Explore & Download Repositories`
9. Search for `Battery Energy Trading`
10. Click `Download`
11. Restart Home Assistant

### Manual Installation

1. Download the [latest release](https://github.com/Tsopic/battery_energy_trading/releases)
2. Extract and copy `custom_components/battery_energy_trading` to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## ⚙️ Configuration

### Setup via UI

1. Go to `Settings` → `Devices & Services`
2. Click `+ Add Integration`
3. Search for `Battery Energy Trading`
4. Configure the required entities:
   - **Nord Pool Entity** - Your electricity price sensor (e.g., `sensor.nordpool_kwh_ee_eur_3_10_022`)
   - **Battery Level Entity** - Battery charge percentage (e.g., `sensor.battery_level`)
   - **Battery Capacity Entity** - Battery capacity in kWh (e.g., `sensor.battery_capacity`)
   - **Solar Power Entity** (optional) - Current solar production (e.g., `sensor.power_production_now`)

### Configuration Parameters

After setup, configure the following parameters via the dashboard:

| Parameter | Description | Default | Range |
|-----------|-------------|---------|-------|
| Forced Discharge Hours | Number of highest-price hours to sell | 2 | 0-8 hours |
| Minimum Export Price | Minimum price to allow export | 0.0125 EUR | -0.3 to 0.1 EUR |
| Minimum Forced Sell Price | Minimum price for forced discharge | 0.3 EUR | 0 to 0.5 EUR |
| Maximum Force Charge Price | Maximum price for forced charging | 0.0 EUR | -0.5 to 0.2 EUR |
| Force Charging Hours | Number of cheapest hours to charge | 1 | 0-24 hours |
| Force Charge Target | Target battery % for force charging | 70% | 0-100% |
| Minimum Battery Level | Minimum battery % for discharge | 25% | 10-50% |
| Minimum Solar Threshold | Solar power to override battery limits | 500 W | 0-5000 W |

## 📱 Dashboard

The integration provides the following entities for your dashboard:

### Switches (Primary Controls)
- **Enable Forced Charging** - Toggle automatic grid charging (default: OFF)
- **Enable Forced Discharge** - Toggle peak-time selling (default: ON)
- **Enable Export Management** - Toggle smart export control (default: ON)

### Sensors (with 15-min slot details)
- **Discharge Time Slots** - Selected 15-min slots with energy amounts and prices
  - Shows: `17:00-17:15 (1.2kWh @€0.452), 18:00-18:15 (1.2kWh @€0.428)`
  - Attributes: `slot_count`, `total_energy_kwh`, `estimated_revenue_eur`, detailed `slots` array
- **Charging Time Slots** - Cheapest 15-min slots for charging (if enabled)
  - Shows energy amounts, prices, and estimated costs
- **Arbitrage Opportunities** - Profitable charge/discharge windows with profit calculations

### Binary Sensors (Automation Triggers)
- **Forced Discharge Active** - Currently selling at peak prices
- **Cheapest Hours Active** - Currently in cheap charging period (only if charging enabled)
- **Low Price Mode** - Price below export threshold
- **Export Profitable** - Exporting would be profitable
- **Battery Below 15%** - Low battery warning
- **Solar Power Available** - Sufficient solar production (>500W)

### Configuration (Number Inputs)
- **Forced Discharge Hours** - How many slots to sell (0-8, default: 2)
- **Minimum Export Price** - Minimum to allow export (default: €0.0125)
- **Minimum Forced Sell Price** - Minimum for discharge (default: €0.30)
- **Maximum Force Charge Price** - Maximum for charging (default: €0.00)
- **Force Charging Hours** - How many slots to charge (0-24, default: 1)
- **Force Charge Target** - Target battery % (0-100%, default: 70%)
- **Minimum Battery Level** - Min % for discharge (10-50%, default: 25%)
- **Minimum Solar Threshold** - Solar power override (0-5000W, default: 500W)

## 🔧 Integration with Existing Systems

This integration is designed to work with:

- **Nord Pool Integration** - Or any electricity price sensor
- **Battery Systems** - SolarEdge, Huawei, Tesla, etc.
- **Solar Inverters** - Any system providing power production data
- **Home Assistant Automations** - Full automation support

### Example Automations

**Solar-Only Mode (Default):**
Sell excess solar at peak prices, never charge from grid:

```yaml
# Forced Charging is OFF by default
# Forced Discharge is ON by default
# Just let the integration manage discharge automatically
```

**Enable Grid Charging During Cheap Hours:**

```yaml
automation:
  - alias: "Enable Charging in Winter"
    trigger:
      - platform: template
        value_template: "{{ now().month in [11, 12, 1, 2] }}"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.battery_energy_trading_enable_forced_charging
```

**Disable Discharge on Cloudy Days:**

```yaml
automation:
  - alias: "Disable Discharge When Cloudy"
    trigger:
      - platform: numeric_state
        entity_id: sensor.solar_forecast_today
        below: 10  # kWh
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.battery_energy_trading_enable_forced_discharge
```

**Notification When Selling:**

```yaml
automation:
  - alias: "Notify High Price Period"
    trigger:
      - platform: state
        entity_id: binary_sensor.battery_energy_trading_forced_discharge
        to: 'on'
    action:
      - service: notify.mobile_app
        data:
          title: "Energy Trading"
          message: "High price period - selling energy now!"
```

## 🎨 Example Dashboard Card

```yaml
type: entities
title: Battery Energy Trading
entities:
  - entity: sensor.battery_energy_trading_arbitrage_opportunities
  - entity: binary_sensor.battery_energy_trading_forced_discharge
  - entity: binary_sensor.battery_energy_trading_export_profitable
  - entity: number.battery_energy_trading_min_forced_sell_price
  - entity: number.battery_energy_trading_forced_discharge_hours
```

## 📈 How It Works

### Arbitrage Strategy
1. **Price Analysis** - Monitors Nord Pool prices throughout the day
2. **Opportunity Detection** - Identifies price spreads > 100 points (configurable)
3. **Optimal Scheduling** - Calculates best 2-hour charging and 1-hour discharge windows
4. **Execution** - Automatically triggers charge/discharge based on schedule

### Battery Protection
- Never discharges below configured minimum level (default 25%)
- Solar override allows discharge when solar > 500W (configurable)
- Emergency charge triggers below 15% battery

### Export Management
- Blocks export when price < minimum threshold
- Automatically enables export during profitable periods
- Prevents selling at a loss

## 🛠️ Development Status

**Version 0.1.0** - Initial Release

### Current Features
- ✅ Configuration flow
- ✅ Nord Pool integration
- ✅ Battery monitoring
- ✅ Solar power integration
- ✅ Arbitrage detection
- ✅ Binary sensors for automation triggers
- ✅ Number inputs for configuration

### Roadmap
- 🔄 Complete sensor implementations
- 🔄 Advanced arbitrage algorithms
- 🔄 Historical analytics
- 🔄 Cost/revenue tracking
- 🔄 Multi-day forecasting
- 🔄 Machine learning price predictions
- 🔄 Custom dashboard cards

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Credits

Originally inspired by battery management and energy trading automation patterns.

## 💬 Support

- **Issues**: [GitHub Issues](https://github.com/Tsopic/battery_energy_trading/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Tsopic/battery_energy_trading/discussions)
- **Home Assistant Community**: [Community Forum](https://community.home-assistant.io/)

## ☕ Support Development

If you find this integration useful, consider:

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/martinkaskj)
