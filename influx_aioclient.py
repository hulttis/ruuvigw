# coding=utf-8
#-------------------------------------------------------------------------------
# Name:        influx_aioclient.py
# Purpose:     generic influx client
# Copyright:   (c) 2019 TK
# Licence:     MIT
#-------------------------------------------------------------------------------
import logging
logger = logging.getLogger('influx')

import asyncio
import aiohttp
from aiohttp.client_exceptions import ClientConnectorCertificateError, ClientConnectorError, ServerDisconnectedError
from aioinflux import InfluxDBClient, InfluxDBWriteError
from json import JSONDecodeError

import time
import json
import queue
import ssl
from datetime import datetime as _dt
from datetime import timedelta

from mixinQueue import mixinAioQueue as _mixinQueue
import defaults as _def

# ==================================================================================

class influx_aioclient(_mixinQueue):
    QUEUE_GET_TIMEOUT = 0.2
    INFLUX_CONNECT_DELAY = 5.0
#-------------------------------------------------------------------------------
    def __init__(self, *,
        cfg,
        inqueue,
        loop,
        scheduler,
        nameservers=None
    ):
        """
            cfg - influx configuration
            inqueue - incoming queue for data
            loop - asyncio loop
            scheduler - used scheduler for scheduled tasks
            nameservers - list of used name servers
        """
        super().__init__()
        self._funcs = {
            'default':        self._execute_default,
            'execute_dict':   self._execute_dict,   # python dict
            'execute_json':   self._execute_json   # json string
        }

        if not cfg:
           logger.error('cfg is required parameter and cannot be None')
           raise ValueError('cfg is required parameter and cannot be None')
        if not inqueue:
           logger.error('inqueue is required parameter and cannot be None')
           raise ValueError('inqueue is required parameter and cannot be None')

        self._name = cfg.get('name', _def.INFLUX_NAME)
        logger.debug(f'{self._name} enter')
        self._cfg = cfg
        self._inqueue = inqueue
        l_policy = self._cfg.get('POLICY', None)
        if l_policy:
            self._policy_name = l_policy.get('name', None)
        else:
            self._policy_name = None

        self._stop_event = asyncio.Event()
        self._dbcon = None
        self._dbcon_status = False
        self._dbcon_reconnect = False

        self._loop = loop
        self._scheduler = scheduler
        self._schedule(scheduler=scheduler)
        self._nameservers = nameservers
        logger.debug(f'{self._name} exit')

# -------------------------------------------------------------------------------
    # def __del__(self):
    #     self.shutdown()
        
#-------------------------------------------------------------------------------
    # def shutdown(self):
    #     self._stop_event.set()

#-------------------------------------------------------------------------------
    def stop(self):
        self._stop_event.set()

#-------------------------------------------------------------------------------
    def _schedule(self, *, scheduler):
        logger.debug(f'{self._name} enter {type(scheduler)}')

        try:
            l_jobid = f'{self._name}_do_connect'
            scheduler.add_job(
                self._do_connect,
                'interval',
                seconds = self._cfg.get('supervision_interval', _def.INFLUX_SUPERVISION_INTERVAL),
                kwargs = {
                    'cfg': self._cfg,
                    'jobid': l_jobid
                },
                id = l_jobid,
                replace_existing = True,
                max_instances = 1,
                coalesce = True,
                next_run_time = _dt.now()+timedelta(seconds=self.INFLUX_CONNECT_DELAY)
            )
        except:
            logger.exception(f'*** {self._name}')

#-------------------------------------------------------------------------------
    async def run(self):
        logger.info(f'{self._name} start')

        # self.start_event.set()
        try:
            while not self._stop_event.is_set():
                try:
                    if self._dbcon:
                        l_item = await self.queue_get(inqueue=self._inqueue)
                        if l_item:
                            if isinstance(l_item, dict):
                                l_dict = l_item
                            else:
                                l_dict = json.loads(l_item)
                            try:
                                l_func = l_dict['func']
                                if l_func not in self._funcs:   # unknown func -> execute_default
                                    l_func = 'default'
                                    logger.error(f'{self._name} unknown func:{l_func}')
                            except: # func not received -> execute_default
                                l_func = 'default'
                                logger.error(f'{self._name} no func in received item')

                            # logger.info(f'func:{l_func}')
                            await self._funcs[l_func](item=l_item)
                    else:
                        await asyncio.sleep(self.QUEUE_GET_TIMEOUT)
                except asyncio.CancelledError:
                    logger.warning(f'{self._name} CanceledError')
                    return
                except GeneratorExit:
                    logger.warning(f'{self._name} GeneratorExit')
                    return
        except Exception:
            logger.exception(f'*** {self._name}')
        finally:
            if self._dbcon:
                logger.info(f'{self._name} closing')
                await self._dbcon.close()
                self._dbcon = None

        logger.info(f'{self._name} done')

#-------------------------------------------------------------------------------
    async def _do_connect(self, *, cfg, jobid):
        logger.debug(f'{self._name} {jobid}')

        if not cfg:
            raise ValueError('Influx configuration missing')

        if not self._dbcon:
            logger.debug(f'{self._name} {jobid} reconnect:{self._dbcon_reconnect}')
            self._dbcon = await self._connect(cfg=cfg)
            if not self._dbcon:
                logger.error(f'{self._name} {jobid} connection failed')
            else:
                logger.info(f'{self._name} {jobid} connected')
        else:
            if not await self._poll_influx(cfg=cfg):
                logger.warning(f'{self._name} {jobid} connection lost')
                if self._dbcon:
                    await self._dbcon.close()
                self._dbcon = None
                self._dbcon_reconnect = True

#-------------------------------------------------------------------------------
    async def _connect(self, *, cfg):
        logger.debug(f'{self._name} cfg:{cfg}')
        l_starttime = time.time()

        if not cfg:
            raise ValueError('INFLUX configuration missing')

        try:
            (l_status, l_con) = await self._connectdb(cfg=cfg)
        except Exception:
            logger.exception(f'*** {self._name} connectdb failed')
            return None

        if not l_status:
            logger.error(f'{self._name} connectdb failed')
            return None

        # logger.info('{0} load balancer:{1}'.format(self._name, str(cfg.get('load_balancer', _def.INFLUX_LOAD_BALANCER))))
        # if not cfg.get('load_balancer', _def.INFLUX_LOAD_BALANCER) and not self._dbcon_reconnect:
        if not self._dbcon_reconnect:
            try:
                l_status = await self._createdb(con=l_con, cfg=cfg)
            except Exception:
                logger.exception(f'*** {self._name} createdb failed')
                return None
            if not l_status:
                return None

            try:
                l_status = await self._createpolicy(con=l_con, cfg=cfg)
            except Exception:
                logger.exception(f'*** {self._name} createpolicy failed')
                return None
            if not l_status:
                return None

        logger.info('{0} connected in {1:f}s'.format(self._name, (time.time()-l_starttime)))
        return l_con

#-------------------------------------------------------------------------------
    async def _poll_influx(self, *, cfg):
        logger.debug(f'{self._name}')

        l_close = False
        try:
            if self._dbcon:
                l_ping = await self._dbcon.ping()
                logger.debug(f'{self._name} ping:{l_ping}')
                return True
        except ServerDisconnectedError:
            logger.critical(f'{self._name} ServerDisconnectedError')
            l_close = True
        except ClientConnectorError:
            logger.critical(f'{self._name} ClientConnectorError')
            l_close = True
        except ConnectionRefusedError:
            logger.error(f'{self._name} ConnectionRefusedError')
            l_close = True
        except asyncio.TimeoutError:
            logger.critical(f'{self._name} TimeoutError')
            l_close = True
        except asyncio.CancelledError:
            logger.warning(f'{self._name} CanceledError')
            l_close = True
        except:
            logger.exception(f'*** {self._name} ')
            l_close = True
        finally:
            if l_close:
                if self._dbcon:
                    await self._dbcon.close()
                    self._dbcon = None

        return False

#-------------------------------------------------------------------------------
    async def _query(self, *, con=None, query):
        l_con = con
        if not l_con:
            l_con = self._dbcon
        if not l_con:
            return None

        try:
            return await l_con.query(query)
        except JSONDecodeError as l_e:
            logger.error(f'{self._name} JSONDecodeError query:{query} msg:{l_e.msg}')
        except ServerDisconnectedError:
            logger.critical(f'{self._name} ServerDisconnectedError query:{query}')
        except ClientConnectorError:
            logger.critical(f'{self._name} ClientConnectorError query:{query}')
        except asyncio.TimeoutError:
            logger.critical(f'{self._name} TimeoutError query:{query}')
        except asyncio.CancelledError:
            logger.warning(f'{self._name} CancelledError query:{query}')
        except ConnectionRefusedError:
            logger.error(f'{self._name} ConnectionRefusedError query:{query}')
        except Exception:
            logger.exception(f'*** {self._name} {query}')

        return None

#-------------------------------------------------------------------------------
    async def _connectdb(self, *, cfg):
        # logger.debug(f'{self._name} cfg:{cfg}')
        logger.debug(f'{self._name}')

        l_close = False
        try:
            l_resolver = aiohttp.resolver.AsyncResolver(
                loop = self._loop,
                nameservers=self._nameservers
            ) if self._nameservers else None
            l_sslctx = None
            if cfg.get('ssl', _def.INFLUX_SSL) and not cfg.get('ssl_verify', _def.INFLUX_SSL_VERIFY):
                l_sslctx = ssl.create_default_context()
                l_sslctx.check_hostname = False
                l_sslctx.verify_mode = ssl.CERT_NONE
            l_connector = aiohttp.TCPConnector(
                limit=1000,
                limit_per_host=0,
                use_dns_cache=True,
                ttl_dns_cache=180,
                resolver=l_resolver,
                ssl=l_sslctx
            )
            l_timeout = cfg.get('timeout', _def.INFLUX_TIMEOUT)
            l_con = InfluxDBClient(
                host=cfg.get('host', _def.INFLUX_HOST),
                port=cfg.get('port', _def.INFLUX_PORT),
                ssl=cfg.get('ssl', _def.INFLUX_SSL),
                # verify_ssl=cfg.get('ssl_verify', _def.INFLUX_SSL_VERIFY),
                username=cfg.get('username', _def.INFLUX_USERNAME),
                password=cfg.get('password', _def.INFLUX_PASSWORD),
                database=cfg.get('database', _def.INFLUX_DATABASE),
                timeout=aiohttp.ClientTimeout(connect=l_timeout, total=(l_timeout*2)),
                # retries=cfg.get('retries', _def.INFLUX_RETRIES),
                # loop = self._loop,
                connector=l_connector
            )
            l_ping = await l_con.ping()
            logger.debug(f'{self._name} ping:{l_ping}')

            return (True, l_con)
        except ServerDisconnectedError:
            logger.critical(f'{self._name} ServerDisconnectedError')
            l_close = True
        except ClientConnectorError:
            logger.critical(f'{self._name} ClientConnectorError')
            l_close = True
        except ConnectionRefusedError:
            logger.error(f'{self._name} ConnectionRefusedError')
            l_close = True
        except asyncio.TimeoutError:
            logger.critical(f'{self._name} TimeoutError')
            l_close = True
        except asyncio.CancelledError:
            logger.warning(f'{self._name} CancelledError')
            l_close = True
        except Exception:
            logger.error('{0} failed to connect influx@{1}:{2} ssl:{3}'.format(self._name, cfg.get('host', _def.INFLUX_HOST), cfg.get('port', _def.INFLUX_PORT), str(cfg.get('ssl', _def.INFLUX_SSL))))
            logger.exception(f'*** {self._name}')
            l_close = True
        finally:
            if l_close:
                logger.debug(f'{self._name} closing')
                await l_con.close()

        return (False, None)

#-------------------------------------------------------------------------------
    async def _createdb(self, *, con, cfg):
        l_db = cfg.get('database', _def.INFLUX_DATABASE)
        logger.debug(f'{self._name} database:{l_db}')

        l_resp = await self._query(con=con, query=f'SHOW DATABASES')
        if not l_resp:
            return False

        l_dblist = []
        for l_value in l_resp['results'][0]['series'][0]['values']:
            l_dblist.append(l_value[0])
        logger.debug(f'{self._name} dblist:{l_dblist}')

        if l_db in l_dblist:
            logger.info(f'{self._name} database:{l_db} exists')
            return True

        l_resp = await self._query(con=con, query=f'CREATE DATABASE {l_db}')
        if not l_resp:
            logger.error(f'{self._name} failed to create database:{l_db}')
            return False

        logger.info(f'{self._name} database:{l_db} created')
        return True

#-------------------------------------------------------------------------------
    async def _createpolicy(self, *, con, cfg):
        logger.debug(f'{self._name}')

        l_policy = cfg.get('POLICY', _def.INFLUX_POLICY)
        if not l_policy:
            logger.error(f'{self._name} POLICY not defined')
            return (False)

        con.db = cfg.get('database', _def.INFLUX_DATABASE)
        l_resp = await self._query(con=con, query=f'SHOW RETENTION POLICIES')
        if not l_resp:
            return False

        l_policyname = l_policy.get('name', _def.INFLUX_POLICY_NAME)
        l_rplist = []
        for _, l_value in enumerate(l_resp['results'][0]['series'][0]['values']):
            l_rplist.append(l_value[0])
        logger.debug(f'{self._name} rplist:{l_rplist}')

        if l_policyname not in l_rplist:  # create
            l_q = 'CREATE RETENTION POLICY {0} ON {1} DURATION {2} REPLICATION {3}'.format(
                l_policyname,
                cfg.get('database', _def.INFLUX_DATABASE),
                l_policy.get('duration', _def.INFLUX_POLICY_DURATION),
                l_policy.get('replication', _def.INFLUX_POLICY_REPLICATION)
            )
            if l_policy.get('default', _def.INFLUX_POLICY_DEFAULT):
                l_q += ' DEFAULT'
            l_resp = await self._query(con=con, query=l_q)
            if not l_resp:
                logger.error(f'{self._name} failed to create policy:{l_policyname}')
                return False
            logger.info(f'{self._name} retention policy:{l_policyname} created')
        elif l_policy.get('alter', _def.INFLUX_POLICY_ALTER):   # alter existing policy
            l_q = 'ALTER RETENTION POLICY {0} ON {1} DURATION {2} REPLICATION {3}'.format(
                l_policyname,
                cfg.get('database', _def.INFLUX_DATABASE),
                l_policy.get('duration', _def.INFLUX_POLICY_DURATION),
                l_policy.get('replication', _def.INFLUX_POLICY_REPLICATION)
            )
            if l_policy.get('default', _def.INFLUX_POLICY_DEFAULT):
                l_q += ' DEFAULT'
            l_resp = await self._query(con=con, query=l_q)
            if not l_resp:
                logger.error(f'{self._name} failed to alter policy:{l_policyname}')
                return False
            logger.info(f'{self._name} retention policy:{l_policyname} altered')
        else:
            logger.info(f'{self._name} retention policy:{l_policyname} exists')

        return True

#-------------------------------------------------------------------------------
    async def _execute_default(self, *, item):
        logger.error(f'{self._name} item: {item}')

#-------------------------------------------------------------------------------
    async def _execute_json(self, *, item):
        logger.debug(f'{self._name} type:{type(item)}')
        l_dict = json.loads(item)
        # l_dict['func'] = 'execute_dict'
        await self._execute_dict(item=l_dict)

#-------------------------------------------------------------------------------
    async def _execute_dict(self, *, item):
        logger.debug(f'{self._name} type:{type(item)}')

        l_reconnect = False
        l_rebuffer = False
        try:
            l_json = item.get('json', None)
            l_jobid = item.get('jobid', None)
            if self._dbcon and l_json:
                if item.get('resend', None):
                    logger.debug(f'{self._name} jobid:{l_jobid} resending item:{item}')
                # await self._dbcon.write(data=l_json, precision='s', rp=self._policy_name)
                await self._dbcon.write(data=l_json, rp=self._policy_name)
                logger.debug(f'{self._name} jobid:{l_jobid}')
                return True
            else:
                l_rebuffer = True
        except InfluxDBWriteError as l_e:
            logger.error(f'{self._name} jobid:{l_jobid} InfluxDBWriteError ({l_e.status} {l_e.reason}): {l_e.headers.get("X-Influxdb-Error", "")} item:{item}')
            l_reconnect = True
        except ConnectionRefusedError:
            logger.error(f'{self._name} jobid:{l_jobid} ConnectionRefusedError item:{item}')
            l_reconnect = True
        except ServerDisconnectedError:
            logger.error(f'{self._name} jobid:{l_jobid} ServerDisconnectedError item:{item}')
            l_reconnect = True
        except ClientConnectorError:
            logger.error(f'{self._name} jobid:{l_jobid} ClientConnectorError item:{item}')
            l_reconnect = True
        except asyncio.TimeoutError:
            logger.error(f'{self._name} jobid:{l_jobid} TimeoutError item:{item}')
            l_reconnect = True
        except asyncio.CancelledError:
            logger.error(f'{self._name} CancelledError item:{item}')
        except:
            logger.exception(f'*** {self._name}')
        finally:
            if l_reconnect: # reconnect needed
                if self._dbcon:
                    logger.warning(f'{self._name} jobid:{l_jobid} disconnect')
                    await self._dbcon.close()
                    self._dbcon = None
                self._dbcon_reconnect = True
                # rebuffer unsent data by sending it back to the queue
            if l_rebuffer or l_reconnect:
                if self._inqueue:
                    item['resend'] = True
                    await self.queue_put(outqueue=self._inqueue, data=item)
                    logger.debug(f'{self._name} jobid:{l_jobid} rebuffer data:{item}')

        return False

#==============================================================================
