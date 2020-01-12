# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag ble - bluetooth receiver
# Copyright:    (c) 2019 TK
# Licence:      MIT
# -------------------------------------------------------------------------------
import logging
logger = logging.getLogger('ruuvitag')

import asyncio

import time
import json
from collections import defaultdict
from datetime import datetime as _dt
from datetime import timezone

from .ruuvitag_decode import ruuvitag_decode as _tagdecode
from .ruuvitag_calc import ruuvitag_calc as _tagcalc
from .ruuvitag_misc import get_us as _get_us

from .ruuvitag_df3 import ruuvitag_df3 as _df3
from .ruuvitag_df5 import ruuvitag_df5 as _df5


import os
import sys
import platform

from .aioruuvitag_dummy import ruuvitag_dummy
from .aioruuvitag_bleak import ruuvitag_bleak
if platform.system() == 'Windows':
    from .aioruuvitag_file import ruuvitag_file
elif platform.system() == 'Linux':
    from .aioruuvitag_socket import ruuvitag_socket

DEFAULT_MINMAX = {
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
DEFAULT_MFIDS = [1177]
# ===============================================================================
class aioruuvitag_ble(object):
    """
    asyncio ruuvitag_ble_linux communication and data convert
    
    puts converted ruuvitag data to queue as json
    or
    calls async callback(json=data)
    See consumer.py and callback.py
    
     sample json data (calc_in_datas:False): {
        'mac': 'CB:D7:18:26:DA:B4', 
        'datas': {
            '_df': 5, 'humidity': 52.62, 'temperature': 29.34, 'pressure': 1005.48, 'acceleration': 1014.101, 'acceleration_x': -796, 'acceleration_y': -628, 'acceleration_z': -20, 'tx_power': 4, 'battery': 2827, 'movement_counter': 154, 'sequence_number': 25121, 'tagid': 'CB:D7:18:26:DA:B4', 'rssi': -68, 'tagname': '102livingroom', 'time': '2019-11-16T11:32:36.636133+0000'
        }, 
        'calcs': {
            'equilibriumVaporPressure': 4087.045, 'absoluteHumidity': 15.409, 'dewPoint': 18.666, 'airDensity': 0.221
        }
    }
    sample json data (calc_in_datas:True): {
        'mac': 'CB:D7:18:26:DA:B4', 
        'datas': {
            '_df': 5, 'humidity': 52.62, 'temperature': 29.34, 'pressure': 1005.48, 'acceleration': 1014.101, 'acceleration_x': -796, 'acceleration_y': -628, 'acceleration_z': -20, 'tx_power': 4, 'battery': 2827, 'movement_counter': 154, 'sequence_number': 25121, 'tagid': 'CB:D7:18:26:DA:B4', 'rssi': -68, 'tagname': '102livingroom', 'time': '2019-11-16T11:35:23.481096+0000', 'equilibriumVaporPressure': 4087.045, 'absoluteHumidity': 15.409, 'dewPoint': 18.666, 'airDensity': 0.221
        }
    }
    """
    _timefmt='%Y-%m-%dT%H:%M:%S.%f%z'
# -------------------------------------------------------------------------------
    def __init__(self, *,
        loop,
        scheduler,
        collector='socket' if platform.system() == 'Linux' else 'bleak',
        outqueue=None,
        callback=None,
        whtlist=[],
        blklist=[],
        tags={},
        sample_interval=1000,   # ms
        calc=False,
        calc_in_datas=False,
        debug=False, 
        sudo=True, 
        device_reset=False, 
        device_timeout=10000,   # ms
        whtlist_from_tags=True,
        minmax=DEFAULT_MINMAX,
        device='hci0'
    ):
        """
        loop - asyncio.loop (Required)
        scheduler - AsyncIOScheduler to schedule periodical tasks
        collector - 'socket' or 'bleak' or 'hcidump'
        outqueue - output queue (Default: None)
        callback - async callback(json=data) function to handle data in case other handling than put to the queue is needed
        whtlist - ble mac whitelist (default:[])
            ['D2:C2:5E:F0:11:D1', 'CB:D7:18:26:DA:B4']
        blklist - ble mac blacklist (default:[])
            ['D2:C2:5E:F0:11:D1', 'CB:D7:18:26:DA:B4']
        tags -  ruuvitag mac/name mapping(default:{}). Keys used as whtlist if whtlist not defined
            { 'D2:C2:5E:F0:11:D1': '102bedroom',
              'CB:D7:18:26:DA:B4': '102livingroom' }
        sample_interval - minimum sample interval (default:1000) in ms
        calc - do calculations (Default: False)
        calc_in_datas - include calcs in "datas" (Default: False) instead of "calcs", see above
        debug - "_aioruuvitag" included to the jsondata (Default: False), see above
        sudo - use sudo for shell commands (Default: False)
        device_reset - reset hcix device (not implemented for hcidump)
        device_timeout - timeout (ms) to restart device if no data received
        whtlist_from_tags - use tags as whitelist in case whtlist not given (Default: True)
        minmax - min and max values
        device - hcidevice (for socket)
        """

        # select collector
        logger.info(f'>>> collector:{collector}')
        logger.info(f'>>> platform:{sys.platform}')
        # l_minlen = min(_df3.DATALEN, _df5.DATALEN)
        self._collector = None
        if platform.system() == 'Windows':
            if collector.startswith('file'):    # need to be exclusively defined / just for testing
                try:
                    self._collector = ruuvitag_file(
                        loop=loop,
                        scheduler=scheduler,
                        callback = self._handle_bledata
                    )
                    logger.info(f'>>> collector:ruuvitag_file')
                except Exception:
                    logger.exception(f'>>> file')
            # if collector.startswith('bleak'):
            if not self._collector:
                try:
                    self._collector = ruuvitag_bleak(
                        loop=loop,
                        scheduler=scheduler,
                        device=device,
                        mfids=DEFAULT_MFIDS,
                        device_reset=device_reset,
                        device_timeout=device_timeout,
                        callback = self._handle_bledata
                    )
                    logger.info(f'>>> collector:ruuvitag_bleak')
                except Exception:
                    logger.exception(f'>>> bleak')
        elif platform.system() == 'Linux':
            if collector.startswith('socket'):
                try:
                    from socket import AF_BLUETOOTH
                    self._collector = ruuvitag_socket(
                        loop=loop,
                        callback = self._handle_bledata,
                        scheduler=scheduler,
                        device=device,
                        mfids=DEFAULT_MFIDS,
                        device_reset=device_reset,
                        device_timeout=device_timeout
                    )
                    logger.info (f'>>> collector:ruuvitag_socket')
                except Exception:
                    logger.info(f'>>> fallback to the ruuvitag_bleak')
                    logger.exception(f'>>> socket')

            if collector.startswith('bleak') or not self._collector:
                try:
                    self._collector = ruuvitag_bleak(
                        loop=loop,
                        scheduler=scheduler,
                        device=device,
                        mfids=DEFAULT_MFIDS,
                        device_reset=device_reset,
                        device_timeout=device_timeout,
                        callback = self._handle_bledata
                    )
                    logger.info(f'>>> collector:ruuvitag_bleak')
                except Exception:
                    logger.exception(f'>>> bleak')

        # self._collector = None, use dummy to show warning
        if not self._collector:
            logger.info (f'>>> collector:ruuvitag_dummy')
            self._collector = ruuvitag_dummy()
            raise ValueError(f'ruuvitag_dummy')

        self._outqueue = outqueue
        self._callback = callback
        self._whtlist = whtlist
        self._blklist = blklist
        self._tags = tags
        self._sample_interval = sample_interval
        self._calc = calc
        self._calc_in_datas = calc_in_datas
        self._debug = debug
        self._minmax = minmax

        self._cnt = defaultdict(int)
        self._lasttime = defaultdict(float)
        if not self._blklist:
            logger.info(f'>>> blacklist empty')
            self._blklist = []
        if not self._whtlist:
            logger.info(f'>>> whitelist empty')
            self._whtlist = []
        if tags and not len(self._whtlist) and whtlist_from_tags:   # if no whtlist generate it from the tags if exists
            self._whtlist = tags.keys()
            logger.info(f'>>> whitelist from tags')
        if not self._tags:
            logger.info(f'>>> tags empty')
            self._tags = {}
        
        logger.debug(f'>>> {self}')

# -------------------------------------------------------------------------------
    def __repr__(self):
        return f'aioruuvitag_ble interval:{self._sample_interval} calc:{str(self._calc)} calc_in_datas:{str(self._calc_in_datas)} whtlist:{self._whtlist} blklist:{self._blklist} tags:{self._tags} minmax:{self._minmax} callback:{self._callback} outqueue:{self._outqueue} debug:{self._debug}'

# -------------------------------------------------------------------------------
    # def __del__(self):
    #     logger.debug(f'>>> {self}')
    #     self.stop()

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
    def _checkmaclists(self, *, mac):
        """ Checks mac lists"""
        # check if blacklisted
        if mac in self._blklist:
            logger.debug(f'>>> {lmac_mac} blacklisted')
            return False
        # check if not whitelisted
        if len(self._whtlist) and mac not in self._whtlist:
            # add to blklist for faster blocking
            self._blklist.append(mac)
            logger.debug(f'>>> {mac} added to blklist (mac not in whtlist) size:{len(self._blklist)} blklist:{self._blklist}')
            return False

        return True
# -------------------------------------------------------------------------------
    async def _handle_bledata(self, *, bledata):
        """ 
        Handles received bledata from hcidump/socket. 
        Puts json formated result to the outqueue or calls callback function with it 
        """
        l_mac = bledata.mac
        l_mfdata = bledata.mfdata(mfid=0x499)
        if l_mac and l_mfdata:
            l_ruuvidata = {}
            l_outdata = {}
            # logger.debug(f'>>> {bledata}')
            # check if mac listed
            if not self._checkmaclists(mac=l_mac):
                return
            # check if it is sample time
            if not self._checkinterval(mac=l_mac, interval=self._sample_interval):
                return

            l_datas = _tagdecode.decode(mfdata=l_mfdata, minmax=self._minmax)
            if l_datas:
                try:
                    l_datas['tagname'] = self._tags[l_mac]
                except:
                    pass
                l_datas['time'] = _dt.utcfromtimestamp(bledata.time).replace(tzinfo=timezone.utc).strftime(aioruuvitag_ble._timefmt)
                if bledata.rssi:
                    l_datas['rssi'] = bledata.rssi
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
                    l_ruuvidata['recvtime'] = bledata.time
                    l_outdata['_aioruuvitag'] = l_ruuvidata

                logger.debug(f'>>> {l_mac} outdata:{l_outdata}')
                if self._callback:
                    await self._callback(jsondata=json.dumps(l_outdata))
                else:
                    await self.queue_put(outqueue=self._outqueue, data=json.dumps(l_outdata))
            else:
                logger.debug(f'>>> empty datas')

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
            except Exception:
                logger.exception(f'>>> exception')
        return False

#-------------------------------------------------------------------------------
    async def run(self):
        """ runs ble collector """
        if self._collector:
            await self._collector.run()

# -------------------------------------------------------------------------------
    def stop(self):
        """ Stops ble collector """
        if self._collector:
            # logger.info(f'>>> stopping {self._collector}')
            self._collector.stop()
