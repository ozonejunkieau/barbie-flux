"""
worker for inkbird ibbq and other equivalent cooking/BBQ thermometers.
Thermometer sends every ~2sec the current temperature.

HT to: https://github.com/zewelor/bt-mqtt-gateway/blob/2a7e7abe3c401badf0225babefd5c4bc58e6d525/workers/ibbq.py
"""
import struct

from loguru import logger as _LOGGER
from bluepy import btle
import datetime


REQUIREMENTS = ["bluepy"]


class ibbqThermometer:
    SettingResult = "fff1"
    AccountAndVerify = "fff2"
    RealTimeData = "fff4"
    SettingData = "fff5"
    Notify = b"\x01\x00"
    realTimeDataEnable = bytearray([0x0B, 0x01, 0x00, 0x00, 0x00, 0x00])
    batteryLevel = bytearray([0x08, 0x24, 0x00, 0x00, 0x00, 0x00])
    KEY = bytearray(
        [
            0x21,
            0x07,
            0x06,
            0x05,
            0x04,
            0x03,
            0x02,
            0x01,
            0xB8,
            0x22,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ]
    )

    def getBattery(self):
        self.Setting_uuid.write(self.batteryLevel)

    def connect(self, subscribe = True):
        try:
            self.device = btle.Peripheral(self.mac)
            _LOGGER.debug(f"{self.mac} connected ")
        except btle.BTLEDisconnectError as e:
            _LOGGER.exception(f"failed connect {e}")

        if subscribe:
            self.subscribe()

    def disconnect(self):
        try:
            self.device.disconnect()
        except btle.BTLEInternalError as e:
            _LOGGER.exception(e)

        self.device = None

    def __init__(self, mac, battery_check_period_seconds = 60):
        self.last_update_time = datetime.datetime.min

        self.battery_percentage = 0
        self.last_battery_time = datetime.datetime.min
        self.battery_check_delta = datetime.timedelta(seconds=battery_check_period_seconds)

        self.mac = mac
        self.values = list()

        self.device = None
        self.connect(subscribe=False)


        if not self.device:
            return

        self.subscribe()

    @property
    def connected(self):
        return bool(self.device)

    def subscribe(self):

        class MyDelegate(btle.DefaultDelegate):
            def __init__(self, caller):
                btle.DefaultDelegate.__init__(self)
                self.caller = caller
                _LOGGER.debug(f"delegate init")

            def handleNotification(self, cHandle, data):
                _LOGGER.debug(f"called handler {cHandle}: {data}")

                handler_time = datetime.datetime.now()

                batMin = 0.95
                batMax = 1.5
                result = list()
                #    safe = data
                if cHandle == 0x25:
                    if data[0] == 0x24:
                        currentV = struct.unpack("<H", data[1:3])
                        maxV = struct.unpack("<H", data[3:5])
                        self.caller.battery_percentage = 100.0 * ((batMax * currentV[0] / maxV[0] - batMin) / (batMax - batMin))

                        _LOGGER.debug(f"Battery V: {currentV} of Max V: {maxV}. ({self.caller.battery_percentage}%)")

                        self.caller.last_battery_time = handler_time

                elif cHandle == 0x30:
                    while len(data) > 0:
                        v, data = data[0:2], data[2:]
                        result.append(struct.unpack("<H", v)[0] / 10.0)
                    self.caller.values = [(i + 1, j) for i, j in enumerate(result) if j < 500]

                    self.caller.last_update_time = handler_time



        if self.device is None:
            return
        try:
            services = self.device.getServices()
            for service in services:
                if "fff0" not in str(service.uuid):
                    continue
                for schar in service.getCharacteristics():
                    if self.AccountAndVerify in str(schar.uuid):
                        self.account_uuid = schar
                    if self.RealTimeData in str(schar.uuid):
                        self.RT_uuid = schar
                    if self.SettingData in str(schar.uuid):
                        self.Setting_uuid = schar
                    if self.SettingResult in str(schar.uuid):
                        self.SettingResult_uuid = schar

            self.account_uuid.write(self.KEY)
            _LOGGER.info(f"Authenticated {self.mac}")
            self.RT_uuid.getDescriptors()
            self.device.writeCharacteristic(self.RT_uuid.getHandle() + 1, self.Notify)
            self.device.writeCharacteristic(
                self.SettingResult_uuid.getHandle() + 1, self.Notify
            )
            self.getBattery()
            self.Setting_uuid.write(self.realTimeDataEnable)
            self.device.withDelegate(MyDelegate(self))
            _LOGGER.info(f"Subscribed {self.mac}")
            self.offline_count = 0
        except btle.BTLEException as e:
            _LOGGER.exception(f"failed {self.mac} {e}")
            self.device = None
            _LOGGER.info("unsubscribe")
        return self.device

    def update(self):

        if not self.connected:
            return list()
        self.values = list()

        try:
            if datetime.datetime.now() > self.last_battery_time + self.battery_check_delta:
                self.getBattery()

            while self.device.waitForNotifications(1):
                pass

            offline_time = datetime.datetime.now() - self.last_update_time
            if offline_time > datetime.timedelta(seconds=10):
                _LOGGER.debug(f"{self.mac} is silent since {self.last_update_time.isoformat()}")

            if offline_time > datetime.timedelta(seconds=30):
                self.disconnect()
                self.debug(f"{self.mac} reconnect required")

        except btle.BTLEDisconnectError as e:
            _LOGGER.exception(e)
            self.device = None
        finally:
            return (self.battery_percentage, self.values)

