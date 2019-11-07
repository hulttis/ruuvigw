# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag_linux - bluetooth receiver
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
# sudo apt install bluez
# sudo apt install bluez-hcidump
#
# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('aioruuvitag_ble')

import asyncio
from contextlib import suppress
from datetime import datetime as _dt
from datetime import timedelta

from .ruuvitag_misc import get_sec as _get_sec

# ===============================================================================
class ruuvitag_linux(object):
    HCIDUMP_CMD = 'hcidump --raw'
    HCITOOL_CMD = 'hcitool lescan --duplicates'
    _hcidump = None
    _hcitool = None
    _data_ts = 0
    _loop = None
    _scheduler = None
    _sudo = True
    _device_reset = False
    _device_timeout = 10

#-------------------------------------------------------------------------------
    def _schedule(self):
        """
        Initializes scheduler for hcidump nodata checking
        """
        logger.debug(f'>>> enter {type(self._scheduler)} device_timeout:{self._device_timeout}')

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
                logger.exception(f'*** jobid:{l_jobid} exception')

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
        l_now = _get_sec()
        if (l_now - self._data_ts) > self._device_timeout:
            logger.warning(f'>>> jobid:{jobid} device_timeout timer ({self._device_timeout}ms) expired')
            try:
                logger.info(f'>>> jobid:{jobid} restarting hcidump:{self._hcidump} hcitool:{self._hcitool}')
                await self._kill_cmd(pid=self._hcidump, name='hcidump')
                await self._kill_cmd(pid=self._hcitool, name='hcitool')
            except ProcessLookupError:
                logger.error(f'>>> jobid:{jobid} ProcessLookupError')
            except:
                logger.exception(f'*** jobid:{jobid} exception')
            finally:
                self._hcitool = await self._start_cmd(cmd=self.HCITOOL_CMD,sudo=sudo, reset=reset)
                self._hcidump = await self._start_cmd(cmd=self.HCIDUMP_CMD, sudo=sudo, reset=reset)
                self._data_ts = l_now + self._device_timeout
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
    async def _kill_cmd(self, *, 
        pid,
        name=''
    ):
        """
        Kills cmd process
        """
        def _killkill():
            try:
                pid.kill()
                pid.wait()
            except ProcessLookupError:
                logger.error(f'>>> pid:{pid} name:{name} ProcessLookupError')
            finally:
                logger.info(f'>>> pid:{pid} name:{name} killed')

        if pid:
            await self._loop.run_in_executor(None, _killkill)

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
            self._hcitool = await self._start_cmd(cmd=self.HCITOOL_CMD, sudo=self._sudo, reset=self._device_reset)
            self._hcidump = await self._start_cmd(cmd=self.HCIDUMP_CMD, sudo=self._sudo, reset=self._device_reset)
            if self._hcidump:
                logger.info(f'>>> hcidump:{self._hcidump} hcitool:{self._hcitool} running')
                while  not self._get_lines_stop.is_set():
                    try:
                        l_stdout = await asyncio.wait_for(self._hcidump.stdout.readline(), loop=loop, timeout=self._device_timeout)
                        if l_stdout:
                            self._data_ts = _get_sec()
                            # logger.debug(f'>>> stdout:{l_stdout}')
                            l_line = l_stdout.decode()
                            if l_line.startswith('> '):
                                # handle previous data when next start character received
                                logger.debug(f'>>> pid:{self._hcidump.pid} rawdata:{l_rawdata}')
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

# -------------------------------------------------------------------------------
    def start(self, *, 
        loop, 
        callback
    ):
        """
        Starts to receive from the hcidump
        """
        logger.info(f'>>> starting to receive from the hcidump')
        self._get_lines_stop = asyncio.Event(loop=loop)
        self._task = loop.create_task(self._get_lines(loop=loop, callback=callback))
        logger.info('>>> get_lines task created')

# -------------------------------------------------------------------------------
    def stop(self):
        """
        Stops hcidump
        """
        logger.info(f'>>> stop to receive from hcidump')
        self._get_lines_stop.set()
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                self._loop.run_until_complete(asyncio.wait_for(self._task, timeout=2.0))
            logger.info('>>> get_lines task canceled')

        self._loop.run_until_complete(self._kill_cmd(pid=self._hcitool, name='hcitool'))
        self._loop.run_until_complete(self._kill_cmd(pid=self._hcidump, name='hcidump'))