# -*- coding: utf-8 -*-
"""
Wrapper class for Bluetooth LE data from collectors
"""
import re
from time import time as _time
from datetime import datetime as _dt
from datetime import timezone as _tz
from .ruuvitag_misc import hex_string

class BLEData(object):
    """A simple wrapper class representing a BLE data from collectors
    """
    # _allowed_mac = re.compile(r"""(
    #         ^([0-9A-F]{2}[-]){5}([0-9A-F]{2})$
    #         |^([0-9A-F]{2}[:]){5}([0-9A-F]{2})$
    #     )""",
    #     re.VERBOSE|re.IGNORECASE)
    _allowed_mac = re.compile(r"""(
            ^([0-9A-F]{2}[:]){5}([0-9A-F]{2})$
        )""",
        re.VERBOSE|re.IGNORECASE)

    def __init__(self, *,
        mac = None,        # device mac address
        rssi = None,       # rssi
        mfid = None,       # manufacturer id
        mfdata = None,     # manufacturer data
        rawdata = None     # raw data
    ):
        self._time = _time()
        if mac:
            if self._allowed_mac.match(mac.upper()):
                self._mac = mac.upper()
            else:
                self._mac = None
        self._rssi = rssi
        self._mfid = mfid
        self._mfdata = mfdata
        self._rawdata = rawdata

    @property
    def time(self):
        return self._time

    @property
    def mac(self):
        return self._mac

    @property
    def rssi(self):
        return self._rssi

    @property
    def mfid(self):
        return self._mfid

    @property
    def rawdata(self):
        return self._rawdata

    def mfdata(self, *, mfid=0xFFFF):
        if mfid == 0xFFFF or self._mfid == mfid:
            return self._mfdata
        return None

    def __str__(self):
        return f'''{self._time} mac:{self._mac} rssi:{self._rssi} mfid:{hex(self._mfid if self._mfid else 0xFFFF)} mfdata:{hex_string(data=self._mfdata, filler='')}'''