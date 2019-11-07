# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag_dummy
#               continuously reads hcidump.log file
#               for testing purpose only
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
# -------------------------------------------------------------------------------
import logging
logger = logging.getLogger('aioruuvitag_ble')

import os
import asyncio
import aiofiles
from datetime import datetime as _dt
from datetime import timedelta

from .ruuvitag_misc import get_sec as _get_sec


class ruuvitag_dummy(object):
    FILENAME = f'{os.path.dirname(__file__)}/hcidump.log'
    _data_ts = 0
    _loop = None
    _scheduler = None
    _device_reset = False
    _device_timeout = 10
#-------------------------------------------------------------------------------
    def _schedule(self):
        logger.info(f'>>> enter {type(self._scheduler)} device_timeout:{self._device_timeout}')

        if self._device_timeout:
            l_jobid = f'hcidump_timeout'
            try:
                self._scheduler.add_job(
                    self._do_hcidump_timeout,
                    'interval',
                    seconds = 1,
                    kwargs = {
                        'jobid': l_jobid,
                        'sudo': self._sudo,
                        'reset': self._device_reset
                    },
                    id = l_jobid,
                    replace_existing = True,
                    max_instances = 1,
                    coalesce = True,
                    next_run_time = _dt.now()+timedelta(seconds=self._device_timeout)
                )
                logger.info(f'>>> {l_jobid} scheduled')
            except:
                logger.exception(f'*** exception')

#-------------------------------------------------------------------------------
    async def _do_hcidump_timeout(self, *, 
        jobid, 
        sudo, 
        reset):

        l_now = _get_sec()
        if (l_now - self._data_ts) > self._device_timeout:
            self._data_ts = l_now + self._device_timeout
            logger.info(f'>>> {jobid}')

# -------------------------------------------------------------------------------
    async def _get_lines(self, *, 
        loop, 
        callback
    ):
        l_rawdata = None
        while not self._get_lines_stop.is_set():
            try:
                logger.info(f'>>> reading file {self.FILENAME}...')
                async with aiofiles.open(self.FILENAME, loop=loop, mode='r') as l_fh:
                    async for l_line in l_fh:
                        self._data_ts = _get_sec()
                        if l_line.startswith('> '):
                            # handle previous data when next start character received
                            logger.debug(f'>>> rawdata:{l_rawdata}')
                            await callback(rawdata=l_rawdata)
                            await asyncio.sleep(0.1)
                            l_rawdata = l_line[2:].strip().replace(' ', '')
                        elif l_line.startswith('< '):
                            l_rawdata = None
                        elif l_rawdata:
                            l_rawdata += l_line.strip().replace(' ', '')

                        if self._get_lines_stop.is_set():
                            break

                logger.info(f'>>> file {self.FILENAME} reading done')
                await asyncio.sleep(5)
                # while True:
                #     await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                logger.warning(f'>>> CanceledError')
                raise
            except Exception:
                logger.exception(f'*** exception')

# -------------------------------------------------------------------------------
    def start(self, *, 
        loop, 
        callback
    ):
        """
        Starts to read from the file
        """
        logger.info(f'>>> starting task for file:{self.FILENAME}...')
        self._get_lines_stop = asyncio.Event(loop=loop)
        self._task = self._loop.create_task(self._get_lines(loop=loop, callback=callback))
        logger.info('>>> get_lines task created')

# -------------------------------------------------------------------------------
    def stop(self):
        logger.info(f'>>> stop to read file:{self.FILENAME}')

        self._get_lines_stop.set()
        if self._task:
            self._task.cancel()
            logger.info('>>> get_lines task canceled')

