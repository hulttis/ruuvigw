# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag ble - bluetooth receiver
#
# Author:       Timo Koponen
#
# Created:      18.03.2019
# Copyright:    (c) 2019
# Licence:      Do not distribute
#
# visudo
# %sudo   ALL=(ALL:ALL) NOPASSWD: ALL
#
# hcidump
# sudo apt install bluez-hcidump
#
# -------------------------------------------------------------------------------
import logging
logger = logging.getLogger('aioruuvitag_ble')

import asyncio

import time
import json
from collections import defaultdict
from datetime import datetime as _dt
from datetime import timezone

from .ruuvitag_decode import ruuvitag_decode as _tagdecode
from .ruuvitag_calc import ruuvitag_calc as _tagcalc
from .ruuvitag_misc import get_us as _get_us

import os
import sys
if not sys.platform.startswith('linux') or os.environ.get('CI') == 'True': 
    from .aioruuvitag_dummy import ruuvitag_dummy as _aioruuvitag_base
    print (f'### using aioruuvitag_dummy')
else:
    # try:
    #     from socket import AF_BLUETOOTH
    #     from .aioruuvitag_bleson import ruuvitag_bleson as _aioruuvitag_base
    #     print (f'### using aioruuvitag_bleson')
    # except ImportError:    
    from .aioruuvitag_linux import ruuvitag_linux as _aioruuvitag_base
    print (f'### using aioruuvitag_linux')

# ===============================================================================
class aioruuvitag_ble(_aioruuvitag_base):
    """
    asyncio ruuvitag_ble_linux communication and data convert
    
    puts converted ruuvitag data to queue as json
    or
    calls async callback(json=data)
    See consumer.py and callback.py
    
    json data format: {
        "mac": "CB:D7:18:26:DA:B4", 
        "datas": {"_df": 5, "humidity": 51.4, "temperature": 27.24, "pressure": 1004.3, "acceleration": 1031.201, "acceleration_x": 176, "acceleration_y": -12, "acceleration_z": 1016, 
            "tx_power": 4, "battery": 2797, "movement_counter": 101, "sequence_number": 48044, "tagmac": "CB:D7:18:26:DA:B4", "tagname": "102livingroom", "time": "2019-03-22T02:41:28.278461"}, 
        "calcs": {"equilibriumVaporPressure": 3616.486748894707, "absoluteHumidity": 13.412310386800344, "dewPoint": 16.357681811014125, "airDensity": 0.003494334841241077}, 
        "_aioruuvitag": {"blklist": ["00:9E:C8:B1:94:47", "08:DF:1F:C5:FA:12", "42:66:DF:14:19:2C"], "tagcnt": 33, "tagint": 2030, "recvtime": 1553222488.2784607, 
            "elapsed": 153.54156494140625}
    }
    """
    _cnt = defaultdict(int)
    _lasttime = defaultdict(float)
    _minmax = {
        "temperature": {
            "min": -127.99,
            "max": 127.99
        },
        "humidity": {
            "min": 0,
            "max": 100
        },
        "pressure": {
            "min": 500,
            "max": 1155.36
        }
    }
    _timefmt='%Y-%m-%dT%H:%M:%S.%f%z'
# -------------------------------------------------------------------------------
    def __init__(self, *,
        loop,
        scheduler,
        outqueue=None,
        callback=None,
        whtlist=[],
        blklist=[],
        tags={},
        sample_interval=1000,
        calc=False,
        calc_in_datas=False,
        debug=False, 
        sudo=True, 
        device_reset=False, 
        device_timeout=10000, 
        whtlist_from_tags=False,
        minmax={}
    ):
        """
        loop - asyncio.loop (Required)
        scheduler - AsyncIOScheduler to schedule periodical tasks
        outqueue - output queue (Default: None)
        callback - async callback(json=data) function to handle data in case other handling that put to the queue is needed
        timefmt - timestamp format (default:'%Y-%m-%dT%H:%M:%S.%f')
        whtlist - ble mac whitelist (default:[])
            ['D2:C2:5E:F0:11:D1', 'CB:D7:18:26:DA:B4']
        blklist - ble mac blacklist (default:[])
            ['D2:C2:5E:F0:11:D1', 'CB:D7:18:26:DA:B4']
        tags -  ruuvitag mac/name mapping(default:{}). Keys used as whtlist if whtlist not defined
            { 'D2:C2:5E:F0:11:D1': '102bedroom',
              'CB:D7:18:26:DA:B4': '102livingroom' }
        sample_interval - minimum sample interval (default:1000) in ms
        calc - execute calculations (Default: False)
        calc_in_datas - include calcs in "datas" (Default: False) instead of "calcs", see above
        debug - "_aioruuvitag" included to the jsondata (Default: False), see above
        sudo - use sudo for shell commands
        device_reset - reset hcix device (not implemented yet)
        device_timeout - timeout (ms) to restart device if no data received
        whtlist_from_tags - use tags as whitelist in case whtlist not given
        minmax - min and max values
        """
        self._loop = loop
        self._sample_interval = sample_interval
        self._task = None
        self._blklist = blklist
        if not self._blklist:
            logger.info(f'>>> blacklist empty')
            self._blklist = []
        self._whtlist = whtlist
        if not self._whtlist:
            logger.info(f'>>> whitelist empty')
            self._whtlist = []
        if tags and not len(self._whtlist) and whtlist_from_tags:   # if no whtlist generate it from the tags if exists
            self._whtlist = tags.keys()
            logger.info(f'>>> whitelist from tags')
        self._tags = tags
        if not self._tags:
            logger.info(f'>>> tags empty')
            self._tags = {}
        self._outqueue = outqueue
        self._callback = callback
        self._calc = calc
        self._calc_in_datas = calc_in_datas
        self._debug = debug
        self._scheduler = scheduler
        self._sudo = sudo
        self._device_reset  = device_reset
        self._device_timeout = (device_timeout/1000)    # ms --> s
        if minmax:
            self._minmax = minmax

# -------------------------------------------------------------------------------
    def __str__(self):
        return f'debug:{self._debug} sudo:{self._sudo} device_reset:{self._device_reset} interval:{self._sample_interval} _device_timeout:{self._device_timeout} calc:{str(self._calc)} calc_in_datas:{str(self._calc_in_datas)} whtlist:{self._whtlist} blklist:{self._blklist} tags:{self._tags} minmax:{self._minmax} callback:{self._callback} outqueue:{self._outqueue}'

#-------------------------------------------------------------------------------
    # def _schedule(self, *, scheduler, hcidump_reinit=0.0):
    #     # logger.info(f'>>> enter {type(scheduler)} hcidump_reinit:{hcidump_reinit}')
    #     super()._schedule(scheduler=scheduler, hcidump_reinit=hcidump_reinit)

# -------------------------------------------------------------------------------
    def start(self):
        """ Starts ble communication """
        logger.info(f'>>> starting...')

        super()._schedule()
        super().start(loop=self._loop, callback=self._handle_rawdata)

        # logger.info(f'>>> {self}')
        return self._outqueue

# -------------------------------------------------------------------------------
    def stop(self):
        """ Stops ble communication """
        logger.info(f'>>> stopping...')
        super().stop()

# -------------------------------------------------------------------------------
    def task(self):
        """ Returns task """
        return self._task

# -------------------------------------------------------------------------------
    def _update_cnt(self, *, mac):
        """ Updates measurement counter per mac """
        try:
            l_cnt = self._cnt[mac]
        except:
            l_cnt = 0
        self._cnt[mac] = (l_cnt + 1)
        return l_cnt

# -------------------------------------------------------------------------------
    def _update_us(self, *, mac):
        """ Updates last us per mac """
        try:
            l_us = self._lasttime[mac]
        except:
            l_us = 0
        l_now = _get_us()
        self._lasttime[mac] = l_now
        return int(l_now-l_us) if ((l_us<l_now) and l_us) else 0

# -------------------------------------------------------------------------------
    def _checkinterval(self, *, mac, interval):
        """ Checks minimum update interval per mac """
        try:
            l_epoc = self._lasttime[mac]
        except:
            l_epoc = 0
        l_now = time.time()*1000
        if (l_now-l_epoc) > interval:
            return True

        return False

# -------------------------------------------------------------------------------
    async def _handle_rawdata(self, *, rawdata):
        """ 
        Handles received rawdata from hcidump. 
        Puts json formated result to the outqueue or calls callback function with it 
        """
        l_ruuvidata = {}
        l_outdata = {}
        if rawdata:
            l_us = _get_us()
            l_ts = time.time()
            # l_utc = _dt.utcfromtimestamp(l_ts).replace(tzinfo=timezone.utc).strftime(self._timefmt)
            # print(f'ts:{l_ts} utc:{l_utc}')

            # l_datalen = rawdata[2]
            l_rawmac = rawdata[14:][:12]
            l_mac = ':'.join(reversed([l_rawmac[i:i + 2] for i in range(0, len(l_rawmac), 2)]))
            if len(l_mac) == 17: # check valid mac
                # blacklist
                if l_mac in self._blklist:
                    # print(f'{l_mac} in blklist')
                    return
                # whitelist
                if len(self._whtlist) and l_mac not in self._whtlist:
                    # add to blklist for faster blocking
                    self._blklist.append(l_mac)
                    logger.debug(f'>>> {l_mac} added to blklist (mac not in whtlist) size:{len(self._blklist)} blklist:{self._blklist}')
                    return
                # sample interval
                if not self._checkinterval(mac=l_mac, interval=self._sample_interval):
                    # print(f'{l_mac} too fast')
                    return

                l_datas = _tagdecode.decode(rawdata=rawdata[26:], minmax=self._minmax)
                if l_datas:
                    try:
                        l_datas['tagname'] = self._tags[l_mac]
                    except:
                        pass
                    l_datas['time'] = _dt.utcfromtimestamp(l_ts).replace(tzinfo=timezone.utc).strftime(self._timefmt)
                    l_outdata = {'mac': l_mac, 'datas':l_datas}
                    if self._calc:
                        if self._calc_in_datas:
                            _tagcalc.calc(datas=l_datas, out=l_outdata['datas'])
                        else:
                            l_outdata['calcs'] = {}
                            _tagcalc.calc(datas=l_datas, out=l_outdata['calcs'])
                    if self._debug:
                        l_ruuvidata.clear()
                        l_ruuvidata['blklist'] = self._blklist
                        l_ruuvidata['count'] = self._update_cnt(mac=l_mac)
                        l_ruuvidata['interval'] = self._update_us(mac=l_mac)
                        l_ruuvidata['recvtime'] = int(l_ts)
                        l_ruuvidata['elapsed'] = (_get_us()-l_us)
                        l_outdata['_aioruuvitag'] = l_ruuvidata

                    logger.debug(f'>>> {l_mac} outdata:{l_outdata}')
                    if self._callback:
                        await self._callback(jsondata=json.dumps(l_outdata))
                    else:
                        await self.queue_put(outqueue=self._outqueue, data=json.dumps(l_outdata))
                else:
                    # add to blacklist only if whitelist not defined
                    if l_mac not in self._whtlist:
                        logger.debug(f'>>> {l_mac} added to blklist size:{len(self._blklist)} blklist:{self._blklist} rawdata:{rawdata[26:]}')
                        self._blklist.append(l_mac)
            else:
                logger.warning(f'>>> illegal mac:{l_mac} len:{len(l_mac)}')

# -------------------------------------------------------------------------------
    async def queue_put(self, *,
        outqueue,
        data
    ):
        """ Puts data to the outqueue """
        if outqueue and data:
            try:
                await outqueue.put(data)
                return True
            except asyncio.QueueFull:
                logger.warning(f'>>> queue full')
                # remove oldest from the queue
                await outqueue.get()
                await self.queue_put(outqueue=outqueue, data=data)
                pass
            except Exception:
                logger.exception(f'*** exception')
                pass
        return False
