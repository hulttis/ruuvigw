# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag_hcidump - bluetooth receiver
# Copyright:    (c) 2019 TK
# Licence:      MIT
#
# sudo apt install bluez-hcidump
#
# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('ruuvitag')

import asyncio
from contextlib import suppress
from datetime import datetime as _dt
from datetime import timedelta

from .ruuvitag_misc import get_sec

# ===============================================================================
class ruuvitag_hcidump(object):
    HCIDUMP_CMD = 'hcidump --raw'
    HCITOOL_CMD = 'hcitool lescan --duplicates'

#-------------------------------------------------------------------------------
    def __init__(self,*, 
        loop, 
        scheduler=None, 
        minlen=0, 
        device_reset=False, 
        device_timeout=10000,   # ms 
        sudo=False, 
        **kwargs
    ):
        if not loop:
            raise ValueError(f'loop is not defined')

        self._loop = loop
        self._scheduler = scheduler
        self._device_reset = device_reset
        self._device_timeout = (device_timeout/1000)    # ms --> s
        self._sudo = sudo
        self._minlen = minlen

        self._task = None
        self._hcidump = None
        self._hcitool = None
        self._get_lines_stop = asyncio.Event()
        self._data_ts = 0

        logger.info(f'>>> {self}')

# -------------------------------------------------------------------------------
    def __repr__(self):
        return f'ruuvitag_hcidump minlen:{self._minlen} device_reset:{self._device_reset} device_timeout:{self._device_timeout}'

# ------------------------------------------------------------------------------
    def __del__(self):
        logger.debug(f'>>> enter')
        self.stop()

#-------------------------------------------------------------------------------
    def _schedule(self):
        """
        Initializes scheduler for hcidump nodata checking
        """
        logger.debug(f'>>> enter {type(self._scheduler)} device_timeout:{self._device_timeout}')

        if not self._scheduler:
            return

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
                logger.info(f'>>> jobid:{l_jobid} scheduled')
            except:
                logger.exception(f'*** jobid:{l_jobid}')

#-------------------------------------------------------------------------------
    async def _do_hcidump_timeout(self, *,
        jobid, 
        sudo=True, 
        reset=False
    ):
        """
        Supervises reception of the hcidump data
        Restarts async cmd process if no data received within timeout period - device_timeout
        """
        l_now = get_sec()
        if (l_now - self._data_ts) > self._device_timeout:
            logger.warning(f'>>> jobid:{jobid} device_timeout timer ({self._device_timeout}ms) expired')
            try:
                logger.info(f'>>> jobid:{jobid} restarting hcidump:{self._hcidump} hcitool:{self._hcitool}')
                await self._kill_cmd(pid=self._hcidump, name='hcidump')
                await self._kill_cmd(pid=self._hcitool, name='hcitool')
            except ProcessLookupError:
                logger.error(f'>>> jobid:{jobid} ProcessLookupError')
            except:
                logger.exception(f'*** jobid:{jobid}')
            finally:
                self._hcitool = await self._start_cmd(cmd=ruuvitag_hcidump.HCITOOL_CMD,sudo=sudo, reset=reset)
                self._hcidump = await self._start_cmd(cmd=ruuvitag_hcidump.HCIDUMP_CMD, sudo=sudo, reset=reset)
                self._data_ts = 0
                logger.info(f'>>> jobid:{jobid} hcidump:{self._hcidump} hcitool:{self._hcitool} running')

# -------------------------------------------------------------------------------
    async def _start_cmd(self, *, 
        cmd,
        sudo=True, 
        reset=False
    ):
        """
        Starts async cmd process
        """
        try:
            if sudo:
                return await asyncio.create_subprocess_shell(cmd=f'sudo -n {cmd}', stdout=asyncio.subprocess.PIPE)
            else:
                return await asyncio.create_subprocess_shell(cmd=f'{cmd}', stdout=asyncio.subprocess.PIPE)
        except:
            logger.exception(f'*** exception cmd:{cmd} sudo:{str(sudo)}')

# -------------------------------------------------------------------------------
    # async def _kill_cmd(self, *, 
    #     pid,
    #     name=''
    # ):
    #     """
    #     Kills cmd process
    #     """
    #     def _killkill():
    #         try:
    #             pid.kill()
    #             pid.wait()
    #         except ProcessLookupError:
    #             logger.error(f'>>> pid:{pid} name:{name} ProcessLookupError')
    #         finally:
    #             logger.info(f'>>> pid:{pid} name:{name} killed')

    #     if pid:
    #         await self._loop.run_in_executor(None, _killkill)

    async def _kill_cmd(self, *, 
        pid,
        name=''
    ):
        """
        Kills cmd process
        """
        if pid:
            logger.info(f'pid:{pid}')
            try:
                await pid.kill()
                await pid.wait()
            except ProcessLookupError:
                logger.error(f'>>> pid:{pid} name:{name} ProcessLookupError')
            finally:
                logger.info(f'>>> pid:{pid} name:{name} killed')

# -------------------------------------------------------------------------------
    async def _get_lines(self, *, 
        loop, 
        callback
    ):
        """
        Receives data from hcidump async cmd process
        Restarts hcidump cmd process if it timesout - device_timeout
        """
        try:
            l_rawdata = None

            self._data_ts = 0
            self._hcitool = await self._start_cmd(cmd=ruuvitag_hcidump.HCITOOL_CMD, sudo=self._sudo, reset=self._device_reset)
            self._hcidump = await self._start_cmd(cmd=ruuvitag_hcidump.HCIDUMP_CMD, sudo=self._sudo, reset=self._device_reset)
            if self._hcidump:
                logger.info(f'>>> hcidump:{self._hcidump} hcitool:{self._hcitool} running')
                while not self._get_lines_stop.is_set():
                    try:
                        l_stdout = await asyncio.wait_for(self._hcidump.stdout.readline(), loop=loop, timeout=self._device_timeout)
                        if l_stdout:
                            self._data_ts = get_sec()
                            # logger.debug(f'>>> stdout:{l_stdout}')
                            l_line = l_stdout.decode()
                            if l_line.startswith('> '):
                                # handle previous data when next start character received
                                logger.debug(f'>>> pid:{self._hcidump.pid} rawdata:{l_rawdata}')
                                if l_rawdata and len(l_rawdata) >= self._minlen:
                                    await callback(rawdata=l_rawdata)
                                # append received line to data
                                l_rawdata = l_line[2:].strip().replace(' ', '')
                            elif l_line.startswith('< '):
                                l_rawdata = None
                            elif l_rawdata:
                                # append received line to data
                                l_rawdata += l_line.strip().replace(' ', '')
                            else:
                                # dissmiss the received data
                                pass
                    except asyncio.TimeoutError:
                        logger.error(f'>>> TimeoutError restarting hcidump:{self._hcidump} hcitool:{self._hcitool}')
                        await self._kill_cmd(pid=self._hcidump, name='hcidump')
                        await self._kill_cmd(pid=self._hcitool, name='hcitool')
                        self._hcitool = await self._start_cmd(cmd=self.HCITOOL_CMD, sudo=self._sudo, reset=self._device_reset)
                        self._hcidump = await self._start_cmd(cmd=self.HCIDUMP_CMD, sudo=self._sudo, reset=self._device_reset)
                        self._data_ts = 0
                        logger.info(f'>>> TimeoutError hcidump:{self._hcidump} hcitool:{self._hcitool} running')
                        pass
                    except asyncio.CancelledError:
                        logger.warning(f'>>> CanceledError')
                        return
                    except Exception:
                        logger.exception(f'*** exception')
                        return
        except Exception:
            logger.exception(f'*** exception')
            return
        finally:
            await self._kill_cmd(pid=self._hcidump, name='hcidump')
            await self._kill_cmd(pid=self._hcitool, name='hcitool')

# -------------------------------------------------------------------------------
    def start(self, *, 
        callback=None
    ):
        """
        Starts to receive from the hcidump
        """
        if not self._loop:
            print(f'self._loop is not defined')
            return False
        if not callback:
            print(f'>>> callback is not defined')
            return False

        logger.info(f'>>> starting to receive from the hcidump')
        self._task = self._loop.create_task(self._get_lines(loop=self._loop, callback=callback))
        logger.info('>>> get_lines task created')

        return True

# -------------------------------------------------------------------------------
    def stop(self):
        """
        Stops hcidump
        """
        if self._task:
            logger.info(f'>>> stop to receive from hcidump')
            self._get_lines_stop.set()
            self._task = None

# -------------------------------------------------------------------------------
    def task(self):
        """ Returns task """
        return self._task