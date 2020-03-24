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
from datetime import datetime as _dt, timedelta as _td

import platform
if platform.system() == 'Windows':
    from .scanner_windows import scanner as _scanner
elif platform.system() == 'Linux':
    from .scanner_linux import scanner as _scanner

from .ruuvitag_misc import hex_string, get_sec
from .ble_data import BLEData


# ===============================================================================
class ruuvitag_bleak(object):
    SCHEDULER_MAX_INSTANCES     = 5
    HCICONFIG_CMD               = '/bin/hciconfig'

#-------------------------------------------------------------------------------
    def __init__(self,*,
        loop,
        callback,
        scheduler=None,
        device='hci0',
        mfids=None,
        device_reset=False,
        device_timeout=10.0,
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
        self._device_timeout = device_timeout

        self._device = device
        self._data_ts = 0
        self._inqueue = asyncio.Queue()
        self._scanner_stop = None
        self._scanner_task = None

        logger.info(f'>>> {self} initialized')

# -------------------------------------------------------------------------------
    def __repr__(self):
        return f'ruuvitag_bleak device:{self._device} mfids:{self._mfids} reset:{self._device_reset} timeout:{self._device_timeout}'

#-------------------------------------------------------------------------------
    def _schedule(self):
        """
        Initializes scheduler for hci device nodata checking
        """
        logger.debug(f'>>> enter {type(self._scheduler)} device_timeout:{self._device_timeout}')

        if not self._scheduler:
            return

        if self._device_timeout:
            l_jobid = f'bleak_timeout'
            try:
                self._scheduler.add_job(
                    self._do_bleak_timeout,
                    'interval',
                    seconds = 1,
                    kwargs = {
                        'jobid': l_jobid,
                        'reset': self._device_reset
                    },
                    id = l_jobid,
                    replace_existing = True,
                    max_instances = self.SCHEDULER_MAX_INSTANCES,
                    coalesce = True,
                    next_run_time = _dt.now()+_td(seconds=self._device_timeout)
                )
                logger.info(f'>>> jobid:{l_jobid} scheduled')
            except:
                logger.exception(f'>>> jobid:{l_jobid}')

#-------------------------------------------------------------------------------
    async def _do_bleak_timeout(self, *,
        jobid,
        reset=False
    ):
        """
        Supervises reception of the bleak data
        Restarts socket if no data received within device_timeout period
        """
        l_now = get_sec()
        if (l_now - self._data_ts) > self._device_timeout:
            self._data_ts = l_now
            logger.warning(f'>>> jobid:{jobid} device_timeout timer ({self._device_timeout}sec) expired')
            try:
                logger.info(f'>>> jobid:{jobid} restarting device:{self._device}')
                try:
                    self._reset()
                    self._scanner_task = self._loop.create_task(_scanner(device=self._device, loop=self._loop, outqueue=self._inqueue, stopevent=self._scanner_stop))
                except:
                    logger.exception(f'>>> exception')
                    pass
            except:
                logger.exception(f'>>> jobid:{jobid}')

# ------------------------------------------------------------------------------
    async def _reset(self):
        logger.debug(f'>>> device:{self._device}')

        self._scanner_stop.set()
        await asyncio.sleep(1.0)
        if self._device_reset:
            await self._shell_cmd(cmd=f'{self.HCICONFIG_CMD} {self._device} down')
            await asyncio.sleep(1.0)
            await self._shell_cmd(cmd=f'{self.HCICONFIG_CMD} {self._device} up')
            await asyncio.sleep(1.0)
        self._scanner_stop.clear()

# ------------------------------------------------------------------------------
    async def _shell_cmd(self, *, cmd):
        if platform.system() == 'Linux':
            logger.info(f'>>> {cmd!r}')
            l_proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)

            l_stdout, l_stderr = await l_proc.communicate()

            logger.info(f'>>> {cmd!r} exited with {l_proc.returncode}')
            if l_stdout:
                logger.debug(f'>>> stdout: {l_stdout.decode()}')
            if l_stderr:
                logger.error(f'>>> stder: {l_stderr.decode()}')

# ------------------------------------------------------------------------------
    async def _handle_data(self, *, data):
        """
        Handles received data from the Bleak scanner
        """
        if not data:
            return

        self._data_ts = get_sec()
        try:
            l_mdata = data.metadata['manufacturer_data']
            for l_mfid in list(l_mdata.keys()):
                if not self._mfids or l_mfid in self._mfids:
                    l_mfdata = l_mdata[l_mfid]
                    logger.debug(f'''>>> device:{self._device} mac:{data.address} rssi:{data.rssi} mfid:{l_mfid} mflen:{len(l_mfdata)} mfdata:{hex_string(data=l_mfdata, filler='')}''')
                    try:
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
        logger.info(f'>>> starting...')

        try:
            self._scanner_stop = asyncio.Event()
            self._scanner_task = self._loop.create_task(_scanner(device=self._device, loop=self._loop, outqueue=self._inqueue, stopevent=self._scanner_stop))
            self._schedule()
        except:
            logger.exception(f'>>> exception')
            raise

        while not self._stopevent.is_set():
            try:
                if (self._inqueue):
                    await self._handle_data(data=await self._inqueue.get())
                else:
                    await asyncio.sleep(100)
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
                break
        # l_task.cancel()
        # with suppress(asyncio.CancelledError):
        #     self._loop.run_until_complete(l_task)

        self._scanner_stop.set()
        await asyncio.sleep(0.2)
        logger.info('>>> bleak completed')
        return True

# -------------------------------------------------------------------------------
    def stop(self):
        logger.info(f'>>> bleak')
        self._stopevent.set()

