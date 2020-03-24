# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag_file
#               continuously reads hcidump.log file
#               for testing purpose only
# Copyright:    (c) 2019 TK
# Licence:      MIT
#
# visudo
# %sudo   ALL=(ALL:ALL) NOPASSWD: ALL
# -------------------------------------------------------------------------------
import logging
logger = logging.getLogger('ruuvitag')

import os
import asyncio
import aiofiles
from contextlib import suppress

from .ble_data import BLEData

class ruuvitag_file(object):
    FILENAME = f'{os.path.dirname(__file__)}/hcidump.log'
#-------------------------------------------------------------------------------
    def __init__(self,*, loop, callback, **kwargs):
        logger.info(f'>>> ruuvitag_file')

        if not loop:
            raise ValueError(f'loop is None')
        self._loop = loop
        if not callback:
            raise ValueError(f'callback is None')
        self._callback = callback
        self._stopevent = asyncio.Event()

        logger.info(f'>>> {self} initialized')

# -------------------------------------------------------------------------------
    def __repr__(self):
        return f'ruuvitag_file'

# -------------------------------------------------------------------------------
    def _parse(self, *,
        rawdata
    ):
        if rawdata:
            l_bytedata = bytearray.fromhex(rawdata)
            l_len = len(l_bytedata)
            
            l_mac = None
            l_rssi = None
            l_mfid = None
            l_mfdata = None
            try:
                l_rawmac = rawdata[14:][:12]
                l_mac = ':'.join(reversed([l_rawmac[i:i + 2] for i in range(0, len(l_rawmac), 2)]))
                if len(l_mac) != 17:    # check mac length
                    l_mac = None

                l_rssi = l_bytedata[l_len-1] & 0xFF
                l_rssi = l_rssi-256 if l_rssi>127 else l_rssi

                l_mfid = (l_bytedata[19] & 0xFF) + ((l_bytedata[20] & 0xFF) * 256)
                l_mfdata = l_bytedata[21:l_len-1]
                return BLEData(
                    mac = l_mac,
                    rssi = l_rssi,
                    mfid = l_mfid,
                    mfdata = l_mfdata,
                    rawdata = l_bytedata
                )
            except:
                pass

        return None

# -------------------------------------------------------------------------------
    async def _get_lines(self, *, 
        loop, 
        callback
    ):
        while not self._stopevent.is_set():
            l_rawdata = None
            try:
                logger.info(f'>>> reading file {ruuvitag_file.FILENAME}...')
                async with aiofiles.open(ruuvitag_file.FILENAME, loop=loop, mode='r') as l_fh:
                    async for l_line in l_fh:
                        # logger.debug(f'line: {l_line}')
                        if l_line.startswith('> '):
                            # handle previous data when next start character received
                            if l_rawdata:
                                l_bledata = self._parse(rawdata=l_rawdata)
                                if l_bledata:
                                    await callback(bledata=l_bledata)
                                await asyncio.sleep(0.1)
                            l_rawdata = l_line[2:].strip().replace(' ', '')
                        elif l_line.startswith('< '):
                            l_rawdata = None
                        elif l_rawdata:
                            l_rawdata += l_line.strip().replace(' ', '')

                        if self._stopevent.is_set():
                            break

                logger.info(f'>>> file {ruuvitag_file.FILENAME} reading done')
                await asyncio.sleep(5)
                # while True:
                #     await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                logger.warning(f'>>> CanceledError')
                return
            except Exception:
                logger.exception(f'*** exception')

# -------------------------------------------------------------------------------
    async def run(self):
        logger.info(f'>>> starting...')
        l_task = self._loop.create_task(self._get_lines(loop=self._loop, callback=self._callback))
        while not self._stopevent.is_set():
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                logger.warning(f'>>> CanceledError')
                return
            except:
                pass
        l_task.cancel()
        with suppress(asyncio.CancelledError):
            self._loop.run_until_complete(l_task)

        logger.info('>>> completed')

        return True

# -------------------------------------------------------------------------------
    def stop(self):
        # logger.info(f'>>>')
        self._stopevent.set()

