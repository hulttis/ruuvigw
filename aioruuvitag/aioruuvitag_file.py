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
#
# -------------------------------------------------------------------------------
import logging
logger = logging.getLogger('ruuvitag')

import os
import time
import asyncio
import aiofiles
from datetime import datetime as _dt
from datetime import timedelta

from .ruuvitag_misc import get_sec as _get_sec


class ruuvitag_file(object):
    FILENAME = f'{os.path.dirname(__file__)}/hcidump.log'
#-------------------------------------------------------------------------------
    def __init__(self,*, loop, minlen=0, **kwargs):
        logger.info(f'>>> ruuvitag_file')

        if not loop:
            raise ValueError(f'loop is not defined')
        self._loop = loop
        self._minlen = minlen

        self._task = None
        self._get_lines_stop = None

        logger.info(f'>>> {self}')

# -------------------------------------------------------------------------------
    def __repr__(self):
        return f'ruuvitag_file minlen:{self._minlen}'

# ------------------------------------------------------------------------------
    def __del__(self):
        logger.info(f'>>> cleaning the rest')
        self.stop()

# -------------------------------------------------------------------------------
    async def _get_lines(self, *, 
        loop, 
        callback
    ):
        l_rawdata = None
        while not self._get_lines_stop.is_set():
            try:
                logger.info(f'>>> reading file {ruuvitag_file.FILENAME}...')
                async with aiofiles.open(ruuvitag_file.FILENAME, loop=loop, mode='r') as l_fh:
                    async for l_line in l_fh:
                        if l_line.startswith('> '):
                            # handle previous data when next start character received
                            logger.debug(f'>>> rawdata:{l_rawdata}')
                            if l_rawdata and len(l_rawdata) >= self._minlen:  # check enough data received 
                                await callback(rawdata=l_rawdata)
                            await asyncio.sleep(0.1)
                            l_rawdata = l_line[2:].strip().replace(' ', '')
                        elif l_line.startswith('< '):
                            l_rawdata = None
                        elif l_rawdata:
                            l_rawdata += l_line.strip().replace(' ', '')

                        if self._get_lines_stop.is_set():
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
    def start(self, *, 
        callback
    ):
        """
        Starts to read from the file
        """
        if not self._loop:
            logger.critical(f'>>> loop not defined')
            return False
        if not callback:
            logger.critical(f'>>> callback not defined')
            return False

        logger.info(f'>>> starting task for file:{ruuvitag_file.FILENAME}...')
        self._get_lines_stop = asyncio.Event()
        self._task = self._loop.create_task(self._get_lines(loop=self._loop, callback=callback))
        logger.info('>>> get_lines task created')

        return True

# -------------------------------------------------------------------------------
    def stop(self):
        if self._task:
            logger.info(f'>>> stop to read file:{ruuvitag_file.FILENAME}')
            self._get_lines_stop.set()
            self._task.cancel()
            time.sleep(0.2)
            logger.info('>>> get_lines task canceled')
            self._task = None

# -------------------------------------------------------------------------------
    def task(self):
        """ Returns task """
        return self._task