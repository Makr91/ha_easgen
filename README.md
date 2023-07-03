# Home Assitant integrations
Additional integrations for [Home Assistant](https://www.home-assistant.io/)

## Emergency Alert System
This is a platform integration for [Emergency Alert System](https://www.fcc.gov/emergency-alert-system)

### Installation
Please look at the [WeatherAlerts installation & configuration instructions](https://github.com/custom-components/weatheralerts) to set up Weather Alerts first.

#### HACS
1. Install [HACS](https://hacs.xyz)
1. Go to any of the sections (integrations, frontend, automation).
1. Click on the 3 dots in the top right corner.
1. Select "Custom repositories"
1. Add the URL to the repository: https://github.com/Makr91/ha_easgen
1. Select the correct category.
1. Click the "ADD" button.
1. Go to Home Assistant settings -> Integrations and add Emergency Alert System
1. Restart HA

#### Manual
1. Clone this repository
2. Copy `custom_components/ha_easgen` to your Home Assistant insance on `<config dir>/custom_components/`

### Setup

#### GUI
1. Go to the *Integrations* page and click **+ ADD INTEGRATION**
2. Select *Emergency Alert System* in the list of integrations
3. Click Submit.


#### Manual Configuration
1. add a media player to your home assistant configuration (`<config dir>/configuration.yaml`):

```yaml

```
2. Restart your Home assistant to make changes take effect.

### Configuration

```yaml

```


### Notes
This is an Early alpha build, please do NOT rely on this!

### Tests

