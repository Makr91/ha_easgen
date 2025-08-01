# Emergency Alert System Generator

![GitHub release (latest by date)](https://img.shields.io/github/v/release/Makr91/ha_easgen?style=plastic)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=plastic)](https://github.com/hacs/integration)
![Project Stage](https://img.shields.io/badge/project%20stage-development-yellow.svg?style=plastic)
![GitHub all releases](https://img.shields.io/github/downloads/Makr91/ha_easgen/total?style=plastic)

![GitHub commits since latest release](https://img.shields.io/github/commits-since/Makr91/ha_easgen/latest?style=plastic)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/Makr91/ha_easgen?style=plastic)
![GitHub Release Workflow Status](https://img.shields.io/github/actions/workflow/status/Makr91/ha_easgen/release.yml?style=plastic)

## Emergency Alert System
This is a platform integration for [Emergency Alert System](https://www.fcc.gov/emergency-alert-system) for Home Assistant that generates EAS alerts with authentic tones and announcements.

The integration includes:
- **Built-in Weather Alert Monitoring**: Direct integration with weather.gov API
- **EAS Tone Generation**: Authentic EAS header/footer tones using EASGen library
- **TTS Integration**: Works with any Home Assistant TTS engine

Currently only the United States EAS system is in place. Support for other countries is welcome to be submitted via a PR.

### ⚠️ IMPORTANT LEGAL NOTICE

**This integration generates Emergency Alert System (EAS) tones. The reproduction of EAS tones is strictly regulated by the Federal Communications Commission (FCC).**

**FCC Regulations**: The FCC prohibits the unauthorized use of EAS attention signals, codes, or simulations thereof (47 CFR § 11.45). Violations can result in substantial monetary penalties ranging from tens of thousands to millions of dollars.

**Intended Use**: This integration is designed to extend official emergency alerts to devices within your home that would not otherwise receive them. It uses official alert data sources to ensure the integrity of emergency information.

**User Responsibility**: By installing and using this integration, you acknowledge that:
- You are solely responsible for compliance with all applicable laws and regulations
- You will NOT play EAS tones in public places without proper authorization
- This is intended for private, in-home use only
- You understand the potential legal consequences of misuse

**Reliability Warning**: This integration may not be reliable and should NOT be depended upon as your sole source of emergency alerts. Technical failures, network issues, or software bugs may prevent alerts from being delivered or played correctly. Always maintain multiple methods of receiving emergency information.

**NO WARRANTY**: This software is provided "AS IS" without warranty of any kind, express or implied, including but not limited to warranties of merchantability, fitness for a particular purpose, or safety. The developer makes NO guarantees that this system will function correctly during an actual emergency.

**Liability Disclaimer**: The developer of this integration assumes no liability for any unauthorized use, misuse, or legal consequences arising from the use of this software. Users assume all risks associated with generating and playing EAS tones.

**Educational Purpose**: This project is offered for educational and emergency preparedness purposes, demonstrating how emergency alert coverage can be extended to additional devices within a private residence.

### Installation

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
3. Restart Home Assistant Core
4. Add the integrations via the Integrations page

### Setup

#### Configuration
1. Go to the *Integrations* page and click **+ ADD INTEGRATION**
2. Select *Emergency Alert System Generator* in the list of integrations
3. Configure the following:
   - **State**: Enter your 2-letter state code (e.g., TX, CA, NY)
   - **Zone**: Enter your weather zone number (1-3 digits, e.g., 19, 127)
   - **County**: (Optional) Enter your county code (1-3 digits)
   - **TTS Engine**: Select your preferred TTS provider
   - **Call Sign**: Set your EAS call sign (default: KF5NTR)
   - **Organization**: Choose EAS organization type (EAS/WXR/PEP/CIV)
   - **Voice**: Set TTS voice preference
   - **Language**: Choose TTS language

#### Finding Your Zone/County Codes
You can find your weather zone and county codes at:
- [weather.gov Zone Map](https://www.weather.gov/gis/ZoneCounty)
- [NWS Zone and County Lookup](https://www.weather.gov/pimar/ZoneCounty)

#### Usage
Once configured, the integration will:
1. Monitor weather alerts for your specified location
2. Generate EAS announcements when alerts are active
3. Create TTS entities that can be used in automations

### Notes
This is an Early alpha build, please do NOT rely on this!
