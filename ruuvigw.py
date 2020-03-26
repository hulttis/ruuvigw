# coding=utf-8
# !/usr/bin/python3
# Name:         Ruuvi InfluxDB / MQTT gateway
# Author:       Timo Koponen
# Created:      07.04.2019
# Copyright:    (c) 2019
# Licence:      MIT
# Required:     aioinflux                               // pipenv install aioinflux pandas
#               apscheduler                             // pipenv install apscheduler
#               aiohttp                                 // pipenv install aiohttp
#               aiodns                                  // pipenv install aiodns
#               aiomqtt                                 // pipenv install aiomqtt
#               aiokafka                                // pipenv install aiokafka
#               txdbus                                  // pipenv install txdbus (Linux)
#               bleak                                   // pipenv install bleak (Windows)
#               asyncio
# dev:          pylint                                  // pipenv install -d pylint
#               aiofiles                                // pipenv install aiofiles (Windows)
# -------------------------------------------------------------------------------
import os
import sys
import time
import signal
import asyncio
import argparse
import platform 
import functools
import traceback
from contextlib import suppress
from json import JSONDecodeError
from datetime import datetime as _dt, timedelta as _td
from multiprocessing import cpu_count

from apscheduler.schedulers.asyncio import AsyncIOScheduler as _scheduler
from apscheduler.events import EVENT_ALL

from mixinSchedulerEvent import mixinSchedulerEvent
from ruuvigw_dataclasses import procItem, procDict
from ruuvigw_config import config_reader as _config
from ruuvigw_aioclient import ruuvi_aioclient as _ruuvi
from ruuvigw_influx import ruuvi_influx as _influx
from ruuvigw_mqtt import ruuvi_mqtt as _mqtt
from ruuvigw_kafka import ruuvigw_kafka as _kafka
import ruuvigw_defaults as _def
from aioruuvitag.aioruuvitag_ble import aioruuvitag_ble as _tag

import logging
_LOG_CFGFILE = _def.LOG_CFGFILE
from logger_config import logger_config
logger = None 

_PROGRAM_NAME = _def.LONG_PROGRAM_NAME
_PROGRAM_PY = _def.PROGRAM_PY
_VERSION = _def.VERSION
_CFGFILE = _def.CFGFILE

# ==============================================================================
class main_class(mixinSchedulerEvent):
    SLEEP_TIME = 1.0
    _run = True
#-------------------------------------------------------------------------------
    def __init__(self, *,
        config_file = _CFGFILE,
        logconfig_file = _LOG_CFGFILE
    ):
        super().__init__()

        global logger
        logger_config(logconfig_file)
        logger = logging.getLogger('ruuvigw')

         # read config
        try:
            self._cfgh = _config(configfile=config_file)
        except JSONDecodeError:
            logger.critical('*** failed to read configuration file: {0:s} - terminating'.format(config_file))
            sys.exit()
        except ValueError as l_e:
            logger.critical(f'*** ValueError: {l_e}')
            print('')
            sys.exit()
        except Exception as l_e:
            logger.critical('*** exception:{0} traceback:{1}'.format(l_e, traceback.format_exc()))
            logger.critical('*** failed to read configuration file: {0:s} - terminating'.format(config_file))
            sys.exit()

        try:
            self._cfgh.print()
        except ValueError as l_e:
            logger.critical(f'*** ValueError: {l_e}')
            print('')
            sys.exit()
        except Exception as l_e:
            logger.critical('*** exception:{0} traceback:{1}'.format(l_e, traceback.format_exc()))
            logger.critical('*** failed to verify configuration file: {0:s} - terminating'.format(config_file))
            sys.exit()
        # sys.exit()

        # setup logger
        logger.info(f'### logger ready')
        logger.info(f'{_PROGRAM_NAME} {_VERSION}')

        # set class variables
        self._procs = procDict()  
        l_common = self._cfgh.get_cfg(section='COMMON')

        self._scheduler = _scheduler(
            max_instances = l_common.get('scheduler_instances', _def.COMMON_SCHEDULER_INSTANCES)
        )
        self._scheduler.add_listener(self._job_event, mask=EVENT_ALL)
        # self._scheduler.add_job(
        #     self._ticktak,
        #     'interval',
        #     seconds = 1,
        #     id = str('_ticktak_'),
        #     replace_existing = True,
        #     max_instances = 1,
        #     coalesce = True,
        #     next_run_time = _dt.now()+_td(seconds=5)
        # )
        self._loop = None
        self._tag = None
        # self._fbqueue = asyncio.Queue(maxsize=_def.COMMON_FBQUEUE_SIZE)

#-------------------------------------------------------------------------------
    def _ticktak(self):
        pass

#-------------------------------------------------------------------------------
    def main_func(self):
        logger.info(f'started: {_dt.now()}')

        self._scheduler.start()
        self._loop = asyncio.get_event_loop()
        try:
            for l_signame in {'SIGINT', 'SIGTERM'}:
                self._loop.add_signal_handler(
                    getattr(signal, l_signame), 
                    functools.partial(self._stop, l_signame)
                )
            logger.debug('signals registered')
        except:
            logger.warning('registering signals failed')
            pass

        l_influx = self._start_influx()
        l_mqtt = self._start_mqtt()
        l_kafka = self._start_kafka()
        if not l_influx and not l_mqtt and not l_kafka:
            self._run = False
            logger.critical(f'Starting INFLUX, MQTT and KAFKA failed. Check logs and configuration !')
        self._run = self._start_ruuvi()
        self._run = self._start_ruuvitag()
        if self._run:
            try:
                self._loop.run_forever()
            except (KeyboardInterrupt, SystemExit):
                logger.warning('KeyboardInterrupt/SystemExit')
            except:
                logger.exception(f'exception')
            finally:
                logger.info(f'shutdown scheduler')
                self._scheduler.shutdown()
                logger.info(f'shutdown tasks')
                self._shutdown()

        logger.info(f'stopped:{str(_dt.now())}')

#-------------------------------------------------------------------------------
    def _stop(self, signame):
        logger.info(f'signame:{signame}')
        if self._loop:
            logger.info(f'stopping the loop')
            self._loop.stop()
        # raise KeyboardInterrupt

#-------------------------------------------------------------------------------
    def _start_influx(self):
        logger.debug('enter')

        if not self._run:
            return False

        l_status = False
        l_common = self._cfgh.get_cfg(section=_def.KEY_COMMON)
        l_influxs = self._cfgh.get_cfg(section=_def.KEY_INFLUX)
        if l_influxs:
            for l_influx in l_influxs:
                l_name = l_influx.get('name', _def.INFLUX_NAME)
                if l_influx.get('enable', _def.INFLUX_ENABLE):
                    try:
                        l_inqueue = asyncio.Queue(maxsize=l_influx.get('queue_size', _def.INFLUX_QUEUE_SIZE))
                        l_proc = _influx(
                            cfg = l_influx,
                            hostname = l_common.get('hostname', _def.COMMON_HOSTNAME),
                            inqueue = l_inqueue,
                            # fbqueue = self._fbqueue,
                            loop = self._loop,
                            scheduler = self._scheduler,
                            nameservers = l_common.get('nameservers', _def.COMMON_NAMESERVERS)
                        )
                        l_task = self._loop.create_task(l_proc.run())
                        self._procs.add(l_name, procItem(proc=l_proc, queue=l_inqueue, task=l_task))
                        logger.info(f'[{_def.KEY_INFLUX}] task:{l_name} created')
                        logger.debug(f'[{_def.KEY_INFLUX}] proc:{l_proc} task:{l_task}')
                        l_status = True
                    except Exception:
                        logger.exception(f'''[{_def.KEY_INFLUX}] failed to add task:{l_name}''')
                else:
                    logger.warning(f'''[{_def.KEY_INFLUX}]:{l_name} disabled''')
        return l_status

#-------------------------------------------------------------------------------
    def _start_mqtt(self):
        logger.debug('enter')

        if not self._run:
            return False

        l_status = False
        l_common = self._cfgh.get_cfg(section=_def.KEY_COMMON)
        l_mqtts = self._cfgh.get_cfg(section=_def.KEY_MQTT)
        if l_mqtts:
            for l_mqtt in l_mqtts:
                l_name = l_mqtt.get('name', _def.MQTT_NAME)
                if l_mqtt.get('enable', _def.MQTT_ENABLE):
                    try:
                        l_inqueue = asyncio.Queue(maxsize=l_mqtt.get('queue_size', _def.MQTT_QUEUE_SIZE))
                        l_proc = _mqtt(
                            cfg = l_mqtt,
                            hostname = l_common.get('hostname', _def.COMMON_HOSTNAME),
                            inqueue = l_inqueue,
                            # fbqueue = self._fbqueue,
                            loop = self._loop,
                            scheduler = self._scheduler,
                            nameservers = l_common.get('nameservers', _def.COMMON_NAMESERVERS)
                        )
                        l_task = self._loop.create_task(l_proc.run())
                        self._procs.add(l_name, procItem(proc=l_proc, queue=l_inqueue, task=l_task))
                        logger.info(f'[{_def.KEY_MQTT}] task:{l_name} created')
                        logger.debug(f'[{_def.KEY_MQTT}] proc:{l_proc} task:{l_task}')
                        l_status = True
                    except Exception:
                        logger.exception(f'''[{_def.KEY_MQTT}] failed to add task:{l_name}''')
                else:
                    logger.warning(f'''[{_def.KEY_MQTT}]:{l_name} disabled''')
        return l_status

#-------------------------------------------------------------------------------
    def _start_kafka(self):
        logger.debug('enter')

        if not self._run:
            return (False)

        l_status = False
        l_common = self._cfgh.get_cfg(section=_def.KEY_COMMON)
        l_kafkas = self._cfgh.get_cfg(section=_def.KEY_KAFKA_PRODUCER)
        if l_kafkas:
            for l_kafka in l_kafkas:
                l_name = l_kafka.get('name', _def.KAFKA_NAME)
                if l_kafka.get('enable', _def.KAFKA_ENABLE):
                    try:
                        l_inqueue = asyncio.Queue(maxsize=l_kafka.get('queue_size', _def.KAFKA_QUEUE_SIZE))
                        l_proc = _kafka(
                            loop = self._loop,
                            cfg = l_kafka,
                            inqueue = l_inqueue,
                            scheduler = self._scheduler,
                            nameservers = l_common.get('nameservers', _def.COMMON_NAMESERVERS)
                        )
                        l_task = self._loop.create_task(l_proc.run())
                        self._procs.add(l_name, procItem(proc=l_proc, queue=l_inqueue, task=l_task))
                        logger.info(f'[{_def.KEY_KAFKA_PRODUCER}] task:{l_name} created')
                        logger.debug(f'[{_def.KEY_KAFKA_PRODUCER}] proc:{l_proc} task:{l_task}')
                        l_status = True
                    except Exception:
                        logger.exception(f'''[{_def.KEY_KAFKA_PRODUCER}] failed to add task:{l_name}''')
                else:
                    logger.warning(f'''[{_def.KEY_KAFKA_PRODUCER}]:{l_name} disabled''')
        return l_status

#-------------------------------------------------------------------------------
    def _start_ruuvi(self):
        logger.debug('enter')

        if not self._run:
            return (False)

        l_common = self._cfgh.get_cfg(section=_def.KEY_COMMON)
        l_ruuvi = self._cfgh.get_cfg(section=_def.KEY_RUUVI)
        if l_ruuvi:
            l_outqueues = {}
            for l_measur in l_ruuvi.get('MEASUREMENTS', None):
                l_outqueue = self._find_queue(l_measur.get('OUTPUT', _def.RUUVI_OUTPUT))
                if l_outqueue:
                    l_outqueues = {**l_outqueues, **l_outqueue}
            if l_outqueues:
                logger.debug(f'outqueues:{l_outqueues}')
                try:
                    l_name = l_ruuvi.get('name', _def.RUUVI_NAME)
                    l_inqueue = asyncio.Queue(maxsize=l_ruuvi.get('queue_size', _def.RUUVI_QUEUE_SIZE))
                    l_proc = _ruuvi(
                        cfg = l_ruuvi,
                        hostname = l_common.get('hostname', _def.COMMON_HOSTNAME),
                        outqueues = l_outqueues,
                        inqueue = l_inqueue,
                        # fbqueue = self._fbqueue,
                        loop = self._loop,
                        scheduler = self._scheduler
                    )
                    l_task = self._loop.create_task(l_proc.run())
                    self._procs.add(l_name, procItem(proc=l_proc, queue=l_inqueue, task=l_task))
                    logger.info(f'[{_def.KEY_RUUVI}] task:{l_name} created')
                    logger.debug(f'[{_def.KEY_RUUVI}] proc:{l_proc} task:{l_task}')
                    return True
                except Exception:
                    logger.exception(f'{_def.KEY_RUUVI}] failed to add task:{l_name}')
            else:
                logger.error(f'''[{_def.KEY_RUUVI}] queue(s) not found:{l_ruuvi.get('OUTPUT', _def.RUUVI_OUTPUT)}''')
                logger.debug(f'''[{_def.KEY_RUUVI}] procs:{self._procs}''')
        else:
            logger.error(f'''*** [{_def.KEY_RUUVI}] configuration missing''')

        return False

#-------------------------------------------------------------------------------
    def _start_ruuvitag(self):
        logger.debug('enter')

        if not self._run:
            return False
        l_ruuvitag = self._cfgh.get_cfg(section=_def.KEY_RUUVITAG)
        if l_ruuvitag:
            l_outqueue = self._find_queue(l_ruuvitag.get('ruuviname', _def.RUUVITAG_RUUVINAME))
            try:
                l_name = l_ruuvitag.get('name', _def.RUUVITAG_NAME)
                l_proc = _tag(
                    loop = self._loop,
                    scheduler = self._scheduler,
                    collector = l_ruuvitag.get('collector', _def.RUUVITAG_COLLECTOR),
                    outqueue = l_outqueue,
                    # fbqueue = self._fbqueue,
                    whtlist = l_ruuvitag.get('WHTLIST', None),
                    blklist = l_ruuvitag.get('BLKLIST', None),
                    adjustment = l_ruuvitag.get('ADJUSTMENT', None),
                    tags = l_ruuvitag.get('TAGS', None),
                    sample_interval = l_ruuvitag.get('sample_interval', _def.RUUVITAG_SAMPLE_INTERVAL),
                    calc = l_ruuvitag.get('calc', _def.RUUVITAG_CALC),
                    calc_in_datas = l_ruuvitag.get('calc_in_datas', _def.RUUVITAG_CALC_IN_DATAS),
                    debug = l_ruuvitag.get('debug', _def.RUUVITAG_DEBUG),
                    device_timeout = l_ruuvitag.get('device_timeout', _def.RUUVITAG_DEVICE_TIMEOUT),
                    device_reset = l_ruuvitag.get('device_reset', _def.RUUVITAG_DEVICE_RESET),
                    whtlist_from_tags = l_ruuvitag.get('whtlist_from_tags', _def.RUUVITAG_WHTLIST_FROM_TAGS),
                    minmax = l_ruuvitag.get('MINMAX', _def.RUUVITAG_MINMAX),
                    device = l_ruuvitag.get('device', _def.RUUVITAG_DEVICE)
                )
                # start ruuvitag task
                l_task = self._loop.create_task(l_proc.run())
                self._procs.add(l_name, procItem(proc=l_proc, queue=None, task=l_task))
                logger.info(f'[{_def.KEY_RUUVITAG}] task:{l_name} created')
                logger.debug(f'[{_def.KEY_RUUVITAG}] proc:{l_proc} task:{l_task}')
                return True
            except ValueError:
                logger.critical(f'*** [{_def.KEY_RUUVITAG}] start failed ValueError')
            except:
                logger.exception(f'*** [{_def.KEY_RUUVITAG}] start failed')
        else:
            logger.error(f'*** [{_def.KEY_RUUVITAG}] configuration missing')
            
        return False

#-------------------------------------------------------------------------------
    def _shutdown(self):
        logger.debug(f'procs:{self._procs}')

        if self._procs:
            l_procs = self._procs.procs
            for l_key in l_procs.keys():
                l_proc = l_procs[l_key]
                l_task = l_proc.task
                if l_task and not l_task.cancelled():
                    if l_proc.proc and hasattr(l_proc.proc, 'stop'):
                        logger.info(f'stop task:{l_key}')
                        l_proc.proc.stop()
                    logger.info(f'cancel task:{l_key}')
                    l_task.cancel()
                    with suppress(asyncio.CancelledError):
                        self._loop.run_until_complete(l_task)                    

# ------------------------------------------------------------------------------
    def _find_queue(self, p_key):
        if not p_key:
            return (None)

        if isinstance(p_key, list):
            l_queues = {}
            for l_key in p_key:
                l_proc = self._procs.get(l_key)
                if l_proc:
                    l_queues[l_key] = l_proc.queue
                # else:
                #     logger.error(f'queue:{l_key} not found')
            if len(l_queues):
                return (l_queues)
        else:
            l_proc = self._procs.get(p_key)
            if l_proc:
                return l_proc.queue
        return (None)

# ------------------------------------------------------------------------------
# import sys
# import os

# def restart_program():
#     """Restarts the current program.
#     Note: this function does not return. Any cleanup action (like
#     saving data) must be done before calling this function."""
#     python = sys.executable
#     os.execl(python, python, * sys.argv)

# if __name__ == "__main__":
#     answer = raw_input("Do you want to restart this program ? ")
#     if answer.lower().strip() in "y yes".split():
#         restart_program()

# ==============================================================================
class check_class():
#-------------------------------------------------------------------------------
    def __init__(self, *,
        config_file = _CFGFILE,
    ):
         # read config
        self._cfgh = None
        try:
            self._cfgh = _config(configfile=config_file)
        except JSONDecodeError:
            print(f'*** failed to read configuration file: {config_file} - terminating')
        except ValueError as l_e:
            print(f'*** ValueError: {l_e}')
            print(f'*** failed to read configuration file: {config_file} - terminating')
        except Exception as l_e:
            print(f'*** exception:{l_e} traceback:{traceback.format_exc()}')
            print(f'*** failed to read configuration file: {config_file} - terminating')

        try:
            if self._cfgh:
                self._cfgh.print()
        except ValueError as l_e:
            print(f'*** ValueError: {l_e}')
            print(f'*** failed to read configuration file: {config_file} - terminating')
        except Exception as l_e:
            print(f'*** exception:{l_e} traceback:{traceback.format_exc()}')
            print(f'*** failed to print configuration file: {config_file} - terminating')

        print('')

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    l_parser = argparse.ArgumentParser(prog=_PROGRAM_PY, description=f'{_PROGRAM_NAME} {_VERSION}')
    l_parser.add_argument('-c', '--config',  help='<config> ..... configuration file', default=_CFGFILE, required=False,
        type=str, dest='cfgfile', metavar='<config>')
    l_parser.add_argument('-l', '--logconfig',  help='<logconfig> ..... logger configuration file', default=_LOG_CFGFILE, required=False,
        type=str, dest='logcfgfile', metavar='<logconfig>')
    l_parser.add_argument('--test',    help='<test> ....... test mode', action='store_true', dest='testmode')
    l_parser.add_argument('--check',   help='<check> ...... check configuration', action='store_true', dest='checkconfig')
    l_args = l_parser.parse_args()

    print('')
    print ('--- {0:s} STARTED {1:s} ---'.format(_PROGRAM_NAME.upper(), str(_dt.now())))
    print('')
    print(f'version:                {_VERSION}')
    print(f'platform:               {sys.platform}')
    print(f'python:                 {platform.python_version()}')
    print(f'cpu count:              {cpu_count()}')
    print(f'parent pid:             {os.getpid()}')

    print('')
    print('COMMANDLINE ARGUMENTS')
    print('-'*21)
    print(f'configuration file:     {l_args.cfgfile.strip()}')
    print(f'logger config:          {l_args.logcfgfile.strip()}')
    if l_args.testmode:
        print(f'test mode:              {l_args.testmode}')
    if l_args.checkconfig:
        print(f'check config:           {l_args.checkconfig}')

    try:
        if l_args.checkconfig:
            l_main = check_class(
                config_file = l_args.cfgfile.strip()
            )
        else:
            l_main = main_class(
                config_file = l_args.cfgfile.strip(),
                logconfig_file = l_args.logcfgfile.strip()
            )
            if l_args.testmode:
                import profile
                profile.run('l_main.main_func()', sort=1)
            else:
                sys.exit(l_main.main_func())
    except (Exception) as l_e:
        logger.exception('***')

# ==============================================================================
