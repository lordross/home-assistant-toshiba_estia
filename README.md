
# Toshiba - Estia Heat pump Home Assistant integration

Toshiba Estia Heat pump integration into home-assistant.io

This project is a fork from the following repository from [h4de5](https://github.com/h4de5/home-assistant-toshiba_ac/releases) that has the Toshiba AC Home Assistant functionality.
Also the required package dependency toshiba_ac package is forked in [Toshiba-Estia-control](https://github.com/lordross/Toshiba-Estia-control)

My intention is to eventually merge both forked repositories back once the package is stable enough.

## Requirements

You need a supported (or compatible) Toshiba Estia device with either a built-in Wifi module or an adapter. See [list of compatible devices](#compatible-devices)

## Installation

### Manual installation

- Download [latest release](https://github.com/lordross/home-assistant-toshiba_estia/releases)
- Create a folder: `custom_components` in your home-assistant config directory
- Extract content (the folder `toshiba_estia`) of the release zip into the newly created directory
- Reboot Home Assistant
- Follow common integration manual

### Common manual to activate the integration

- The integration should be available as `Toshiba Estia` in the `Add integration dialog`
- You need to enter your Toshiba AC account credentials (same as within the app)
- There is no bounding/registering of new AC units possible with this code - please continue to use the app for this

## Compatible devices

If your device is compatible with the [official Toshiba AC mobile app](https://play.google.com/store/apps/details?id=jp.co.toshiba_carrier.ac_control) or [Toshiba Home AC Control](https://play.google.com/store/apps/details?id=com.toshibatctc.SmartAC) it has good chances to be supported by this integration. Furthermore it has been tested with the following hardware: [List of Supported Devices](https://github.com/h4de5/home-assistant-toshiba_ac/issues/45) - feel free to update that list! 

Please Note: Toshiba distributes their AC devices with a different app in the US: [Toshiba AC NA](https://play.google.com/store/apps/details?id=com.midea.toshiba&hl=de_AT) (North America). This fork of [the midea_ac_lan extension](https://github.com/mill1000/midea-ac-py) my be able to control a NA-edition AC unit. It doesn't require an account, which is nice.


## More links and resources

- Feature Request in the [home-assistant community](https://community.home-assistant.io/t/toshiba-home-ac-control/137698)
- my first draft to communicate with the rest service using an [Toshiba API client in PHP](https://gist.github.com/h4de5/7f97db0f4efc265e48904d4a84dab4fb)
- extended example to retrieve state of the AC unit and update the timeprogram using an [Toshiba API client in python](https://github.com/h4de5/home-assistant-toshiba_ac/tree/keep-http-api/custom_components/toshiba_ac/toshiba_ac_api)
- finally using AMQP interface to send state changes directly in [updated python package](https://github.com/KaSroka/Toshiba-AC-control)
