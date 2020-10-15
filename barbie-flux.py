#!/usr/bin/python3

import datetime
import os
from influxdb import InfluxDBClient
from time import  sleep
from ibbq import ibbqThermometer, btle

from config import IBBQ_MAC, influx_host, influx_db


idb_client = InfluxDBClient(host=influx_host, port=8086, database=influx_db)


therm = ibbqThermometer(mac=IBBQ_MAC)

influx_update_window = datetime.timedelta(seconds = 30)

while True:
    try:
        therm.update()
        print(f"Battery Percentage: {therm.battery_percentage} at {therm.last_battery_time.isoformat()}")
        print(f"Values: {therm.values} at {therm.last_update_time.isoformat()}")

        update_points = []
        if datetime.datetime.now() - therm.last_battery_time < influx_update_window:
            # Update the battery value
            battery_point = { "measurement": "grill",
                             "tags": { "device": IBBQ_MAC,
                                       },
                             "time": therm.last_battery_time.isoformat(),
                             "fields": {"battery_percent": therm.battery_percentage
                                        },
                             }
            update_points.append(battery_point)

        if datetime.datetime.now() - therm.last_update_time < influx_update_window and len(therm.values) > 0:
            # Update channel values:
            field_dict = {}
            for channel, value in therm.values:
                field_dict[f"channel_{channel}"] = value


            channel_point = {"measurement": "grill",
                             "tags": {"device": IBBQ_MAC,
                                      },
                             "time": therm.last_update_time.isoformat(),
                             "fields": field_dict
                             }

            update_points.append(channel_point)

        idb_client.write_points(update_points)
        sleep(1)


        if therm.device is None:
            sleep(5)
            therm.connect(subscribe=True)

    except btle.BTLEDisconnectError:
        sleep(5)
        therm.connect()

    except btle.BTLEException:
        sleep(5)


