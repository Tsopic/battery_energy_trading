# HACS Validation Setup

## Repository Topics (Required)

You need to add these topics to your GitHub repository:

1. Go to: https://github.com/Tsopic/battery_energy_trading
2. Click on the ⚙️ (Settings icon) next to "About"
3. Add these topics:
   - `home-assistant`
   - `hacs`
   - `battery`
   - `energy-trading`
   - `nord-pool`
   - `custom-component`
   - `home-assistant-integration`

## Brands Repository (Optional for Custom Repos)

The "brands" error can be ignored for custom HACS repositories. This is only required for default HACS repositories.

If you want to add it later:
1. Fork: https://github.com/home-assistant/brands
2. Add your integration logo
3. Create PR to brands repository

## Current Validation Status

✅ **Passing:**
- Issues validation
- Archived validation
- Integration manifest (valid JSON)
- HACS.json format

⚠️ **Needs Manual Fix (on GitHub):**
- Repository topics - Add via GitHub UI

❌ **Can be Ignored (for custom repos):**
- Brands repository - Only needed for default HACS

## After Adding Topics

1. Add the topics via GitHub UI
2. Wait a few minutes for GitHub to update
3. Re-run HACS validation
4. All required checks should pass

## Alternative: Add via GitHub CLI

```bash
gh repo edit Tsopic/battery_energy_trading \
  --add-topic home-assistant \
  --add-topic hacs \
  --add-topic battery \
  --add-topic energy-trading \
  --add-topic nord-pool \
  --add-topic custom-component \
  --add-topic home-assistant-integration
```
