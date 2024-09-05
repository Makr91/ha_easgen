# Emergency Alert System Generator

![GitHub release (latest by date)](https://img.shields.io/github/v/release/Makr91/ha_easgen?style=plastic)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=plastic)](https://github.com/hacs/integration)
![Project Stage](https://img.shields.io/badge/project%20stage-development-yellow.svg?style=plastic)
![GitHub all releases](https://img.shields.io/github/downloads/Makr91/ha_easgen/total?style=plastic)

![GitHub commits since latest release](https://img.shields.io/github/commits-since/Makr91/ha_easgen/latest?style=plastic)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/Makr91/ha_easgen?style=plastic)
![GitHub Release Workflow Status](https://img.shields.io/github/actions/workflow/status/Makr91/ha_easgen/release.yml?style=plastic)

## Emergency Alert System
This is a platform integration for [Emergency Alert System](https://www.fcc.gov/emergency-alert-system) for Home Assistant to Generate a the EAS Alerts for Satellites.

### Installation

#### Pre-Requisites
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

### Notes
This is an Early alpha build, please do NOT rely on this!

### Tests

