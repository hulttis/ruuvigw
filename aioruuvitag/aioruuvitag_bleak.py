# coding=utf-8
# !/usr/bin/python3
# Name:         aioruuvitag_bleak - Bluetooth Low Energy platform Agnostic Klient by Henrik Blidh
#                                   https://github.com/hbldh/bleak.git
# Copyright:    (c) 2019 TK
# Licence:      MIT
#
# sudo apt install bluez
# requires bluez 5.43
# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('ruuvitag')

import asyncio
from contextlib import suppress
from datetime import datetime as _dt
from datetime import timedelta

import platform
if platform.system() == 'Windows':
    from .scanner_windows import scanner as _scanner
elif platform.system() == 'Linux':
    from .scanner_linux import scanner as _scanner

from .ruuvitag_misc import hex_string, get_sec
from .ble_data import BLEData

# ===============================================================================
class ruuvitag_bleak(object):

#-------------------------------------------------------------------------------
    def __init__(self,*, 
        loop,
        callback,
        scheduler=None,         #       for compatibility
        device='hci0', 
        mfids=None, 
        device_reset=False,     #       for compatibility
        device_timeout=10000,   # ms    for compatibility
        **kwargs
    ):
        logger.info(f'>>> device:{device}')

        if not loop:
            raise ValueError(f'loop is None')
        self._loop = loop
        if not callback:
            raise ValueError(f'callback is None')
        self._callback = callback
        self._stopevent = asyncio.Event()

        self._scheduler = scheduler
        self._mfids = mfids
        self._device_reset = device_reset
        self._device_timeout = (device_timeout/1000)    # ms --> s

        self._device_id = 0
        if device:
            if isinstance(device, int):
                self._device_id = device
            else:
                self._device_id = int(device.replace('hci', ''))

        logger.info(f'>>> {self}')

# -------------------------------------------------------------------------------
    def __repr__(self):
        return f'ruuvitag_bleak device_id:{self._device_id} mfids:{self._mfids} device_reset:{self._device_reset} device_timeout:{self._device_timeout}'

# ------------------------------------------------------------------------------
    def __del__(self):
        # logger.debug(f'>>>')
        self.stop()

# ------------------------------------------------------------------------------
    async def _handle_data(self, *, data):
        """
        Handles received data from the Bleak scanner
        """
        if not data:
            return

        try:
            l_mdata = data.metadata['manufacturer_data']
            for l_mfid in list(l_mdata.keys()):
                if not self._mfids or l_mfid in self._mfids:
                    l_mfdata = l_mdata[l_mfid]
                    try:
                        logger.debug(f'''>>> device_id:{self._device_id} mac:{data.address} rssi:{data.rssi} mfid:{l_mfid} mflen:{len(l_mfdata)} mfdata:{hex_string(data=l_mfdata, filler='')}''')
                        await self._callback(bledata=BLEData(
                            mac = data.address,
                            rssi = data.rssi,
                            mfid = l_mfid,
                            mfdata = l_mfdata,
                            rawdata = data
                        ))
                    except:
                        logger.exception(f'>>> exception')
                        pass
        except:
            logger.exception(f'>>> exception')
            pass

# -------------------------------------------------------------------------------
    async def run(self):
        logger.info(f'>>> starting')
        l_inqueue = asyncio.Queue()
        try:
            if platform.system() == 'Windows':
                from .scanner_windows import scanner as _scanner
                logger.info(f'>>> bleak scanner:scaner_windows')
            elif platform.system() == 'Linux':
                from .scanner_linux import scanner as _scanner
                logger.info(f'>>> bleak scanner:scaner_linux')
            self._loop.create_task(_scanner(loop=self._loop, outqueue=l_inqueue, stopevent=self._stopevent))
        except:
            logger.exception(f'>>> exception')
            return False

        while not self._stopevent.is_set():
            try:
                await self._handle_data(data=await l_inqueue.get())
            except GeneratorExit:
                logger.error(f'>>> GeneratorExit')
                self._stopevent.set()
                break
            except asyncio.CancelledError:
                self._stopevent.set()
                logger.warning(f'>>> CanceledError')
                break
            except:
                logger.exception(f'>>> exception')
                pass
        # l_task.cancel()
        # with suppress(asyncio.CancelledError):
        #     self._loop.run_until_complete(l_task)

        logger.info('>>> completed')

        return True

# -------------------------------------------------------------------------------
    def stop(self):
        # logger.info(f'>>>')
        self._stopevent.set()

