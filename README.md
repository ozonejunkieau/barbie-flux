# barbie-flux

A script to allow the inkbird iBBQ units to log data to influxDB from a Raspberry Pi. Great for smoking, roasting and trivial oven based data science.

__This is based on the work already done here: https://github.com/zewelor/bt-mqtt-gateway/blob/2a7e7abe3c401badf0225babefd5c4bc58e6d525/LICENSE. I just simplified it for the purpose of logging to influxDB.__

## Usage
* Install on a Raspberry Pi (3B+ for Bluetooth) via `git clone`.
* Create a virtual environment if desired.
* Install the requirements.txt file with `python3 -m pip install -r requirements.txt`.
* Copy the example configuration file and complete with appropriate values. `cp example-config.py config.py; nano config.py`. Enter the MAC address of your thermometer, the influx host and the influx database name.
* Install as a systemd service if desired, a service file will be included at a later date.
* Either start and enable the service, or run via `./barbie-flux.py`.

## Database Structure
The created fields in influx are somewhat self explanatory: `battery_percent`, `channel_1`, `channel_2`,  `channel_3` and `channel_4`.

## Notes
This is hacky and kind of untested. It's run for a few weeks robustly when run as a systemd service. It will start logging if the thermometer is turned on and stop logging if the thermometer is turned off. It's not production code!

## Known Issues
The results are a bit weird whilst it's charging. I suspect there is a bit flag to indicate this in the unpacked battery charge information. If you work it out, please let me know!