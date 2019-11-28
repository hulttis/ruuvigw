# coding=utf-8
#-------------------------------------------------------------------------------
# Name:        mqtt_aioclient.py
# Purpose:     generic mqtt (aiomqtt - paho) client
# Copyright:   (c) 2019 TK
# Licence:     MIT
#-------------------------------------------------------------------------------
import logging
logger = logging.getLogger('mqtt')

import ssl
import uuid
import json
import asyncio
import aiomqtt
import ciso8601
from datetime import datetime as _dt
from datetime import timezone
from datetime import timedelta
from collections import defaultdict

from mixinQueue import mixinAioQueue as _mixinQueue
import defaults as _def

# ==================================================================================

class mqtt_aioclient(_mixinQueue):
    QUEUE_GET_TIMEOUT = 0.2
    MQTT_MESSAGE_TIMEOUT = 0.2
    MQTT_CONNECT_DELAY = 1.0
    _conn_error = [
        '0: Connection successful',                                # 0
        '1: Connection refused - incorrect protocol version',      # 1
        '2: Connection refused - invalid client identifier',       # 2
        '3: Connection refused - server unavailable',              # 3
        '4: Connection refused - bad username or password',        # 4
        '5: Connection refused - not authorised'                   # 5
    ]
#-------------------------------------------------------------------------------
    def __init__(self, *,
        cfg,
        hostname,
        inqueue,
        loop,
        scheduler,
        nameservers=None
    ):
        """
            cfg - mqtt configuration
            hostname - name of the system
            inqueue - incoming queue for data
            loop - asyncio loop
            scheduler - used scheduler for scheduled tasks
            nameservers - list of used name servers
        """
        super().__init__()
        self._funcs = {
            'default':        self._execute_default,
            'execute_dict':   self._execute_dict,       # python dict
            'execute_json':   self._execute_json       # json string
        }
        self._message_callback = self._dummy_callback

        if not cfg:
           logger.error('cfg is required parameter and cannot be None')
           raise ValueError('cfg is required parameter and cannot be None')
        if not inqueue:
           logger.error('inqueue is required parameter and cannot be None')
           raise ValueError('inqueue is required parameter and cannot be None')

        self._name = cfg.get('name', _def.MQTT_NAME)
        logger.debug(f'{self._name}')
        self._cfg = cfg
        self._inqueue = inqueue

        self._stop_event = asyncio.Event()
        self._client = None
        self._topic = cfg.get('topic', _def.MQTT_TOPIC)
        self._qos = cfg.get('qos', _def.MQTT_QOS)
        self._retain = cfg.get('retain', _def.MQTT_RETAIN)
        self._client_id = f'''{cfg.get('client_id', _def.MQTT_CLIENT_ID)}-{str(uuid.uuid4())[:23]}'''

        self._loop = loop
        self._nameservers = nameservers
        self._message_task = None
        self._conn_success = False

        self._schedule(scheduler=scheduler)

        logger.debug(f'{self._name} exit')

#-------------------------------------------------------------------------------
    def _schedule(self, *, scheduler):
        logger.debug(f'{self._name} enter {type(scheduler)}')

        l_lwt = bool(self._cfg.get('lwt', _def.MQTT_LWT))
        l_lwtperiod = int(self._cfg.get('lwtperiod', _def.MQTT_LWTPERIOD))
        if l_lwt and l_lwtperiod:
            try:
                l_jobid = f'{self._name}_publish_lwt'
                scheduler.add_job(
                    self._publish_lwt,
                    'interval',
                    seconds = l_lwtperiod,
                    kwargs = {
                        'payload': self._cfg.get('lwtonline', _def.MQTT_LWTONLINE)
                    },                    
                    id = l_jobid,
                    replace_existing = True,
                    max_instances = 1,
                    coalesce = True,
                    next_run_time = _dt.now()+timedelta(seconds=l_lwtperiod)
                )
                logger.info(f'{self._name} {l_jobid} scheduled lwtperiod:{l_lwtperiod}')
            except:
                logger.exception(f'*** {self._name}')

#-------------------------------------------------------------------------------
    def _on_log(self, client, userdata, level, buf):
        logger.debug(f'level:{level} buf:{buf}')

#-------------------------------------------------------------------------------
    async def _connect(self, *, cfg):
        logger.debug(f'{self._name} cfg:{cfg}')

        l_connected = asyncio.Event()
        self._conn_success = False
        def on_connect(client, userdata, flags, rc):    # callback
            l_rc_txt = mqtt_aioclient._conn_error[rc] if rc < len(mqtt_aioclient._conn_error) else ''
            if not rc:  # 0 = successful
                self._conn_success = True
                logger.debug(f'{self._name} flags:{flags} {l_rc_txt}')
            else:
                self._conn_success = False
                logger.error(f'mqtt connect failed: {l_rc_txt}')
            l_connected.set()

        try:
            l_client = aiomqtt.Client(
                loop=self._loop,
                client_id=self._client_id,
                clean_session=cfg.get('clean_session', _def.MQTT_CLEAN_SESSION)
                )
            self.on_log = self._on_log
            l_client.loop_start()
            self._set_lwt(client=l_client, payload=cfg.get('lwtonline', _def.MQTT_LWTONLINE))

            l_username = cfg.get('username', _def.MQTT_USERNAME)
            if l_username:
                l_client.username_pw_set(username=l_username, password=cfg.get('password', _def.MQTT_PASSWORD))
                logger.debug(f'{self._name} username:{l_username}')

            l_host = cfg.get('host', _def.MQTT_HOST)
            l_port = cfg.get('port', _def.MQTT_PORT)
            l_ssl = cfg.get('ssl', _def.MQTT_SSL)
            if l_ssl:
                l_port = cfg.get('port', _def.MQTT_SSLPORT)
                l_cafile = cfg.get('cafile')
                l_cert_reqs = ssl.CERT_REQUIRED if bool(cfg.get('cert_verify', _def.MQTT_CERT_VERIFY)) else ssl.CERT_NONE
                l_client.tls_set(
                    ca_certs=l_cafile,
                    cert_reqs=l_cert_reqs,
                    tls_version=ssl.PROTOCOL_TLSv1_2
                )
                l_ssl_insecure = bool(cfg.get('ssl_insecure', _def.MQTT_SSL_INSECURE))
                l_client.tls_insecure_set(l_ssl_insecure)
                logger.debug(f'{self._name} cert_reqs:{l_cert_reqs} ssl_insecure:{str(l_ssl_insecure)} cafile:{l_cafile}')
            logger.debug(f'''{self._name} host:{l_host} port:{l_port}''')
            l_client.on_connect = on_connect
            await l_client.connect(host=l_host, port=l_port, keepalive=cfg.get('keepalive', _def.MQTT_KEEPALIVE))
            await l_connected.wait()
            if self._conn_success:
                self._client = l_client
                logger.info(f'{self._name} connected host:{l_host} port:{l_port} client_id:{self._client_id}')
                await self._publish_lwt(payload=self._cfg.get('lwtonline', _def.MQTT_LWTONLINE))
                return True
            else:
                await l_client.loop_stop()
                logger.info(f'{self._name} failed to connected host:{l_host} port:{l_port}')
                return False
        except asyncio.CancelledError:
            logger.warning(f'{self._name} CancelledError')
        except:
            logger.exception(f'*** {self._name}')

        return False

#-------------------------------------------------------------------------------
    async def _disconnect(self):
        logger.debug(f'{self._name}')

        if self._client:
            l_disconnected = asyncio.Event()
            def on_disconnect(client, userdata, rc):    # callback
                logger.debug(f'{self._name}  rc:{rc}')
                l_disconnected.set()

            try:
                await self._publish_lwt(payload=self._cfg.get('lwtoffline', _def.MQTT_LWTOFFLINE))
                self._client.on_disconnect = on_disconnect
                self._client.disconnect()
                await l_disconnected.wait()
                logger.info(f'{self._name} disconnected client_id:{self._client_id}')
            except asyncio.CancelledError:
                logger.warning(f'{self._name} CancelledError')
            except:
                logger.exception(f'*** {self._name}')
            finally:
                self._client.on_disconnect = None
                await self._client.loop_stop()
                self._client = None

#-------------------------------------------------------------------------------
    async def _subscribe(self, *, topic, qos=1):
        logger.debug(f'{self._name} topic:{topic} qos:{qos}')

        if self._client:
            l_subscribed = asyncio.Event()
            def on_subscribe(client, userdata, mid, granted_qos):    # callback
                logger.debug(f'{self._name} mid:{mid} granted_qos:{granted_qos}')
                l_subscribed.set()

            try:
                self._client.on_subscribe = on_subscribe
                self._client.subscribe(topic=topic, qos=qos)
                await l_subscribed.wait()
                logger.info(f'{self._name} subscribed topic:{topic}')
                self._client.on_message = self._on_message
            except asyncio.CancelledError:
                logger.warning(f'{self._name} CancelledError')
            except:
                logger.exception(f'{self._name}')
            finally:
                self._client.on_subscribe = None

#-------------------------------------------------------------------------------
    async def _unsubscribe(self, *, topic):
        logger.debug(f'{self._name} topic:{topic}')

        if self._client:
            l_unsubscribed = asyncio.Event()
            def on_unsubscribe(client, userdata, mid):    # callback
                logger.debug(f'{self._name} mid:{mid}')
                l_unsubscribed.set()

            try:
                self._client.on_unsubscribe = on_unsubscribe
                self._client.unsubscribe(topic=topic)
                await l_unsubscribed.wait()
                logger.info(f'{self._name} unsubscribed topic:{topic}')
            except asyncio.CancelledError:
                logger.warning(f'{self._name} CancelledError')
            except:
                logger.exception(f'{self._name}')
            finally:
                self._client.on_unsubscribe = None

#-------------------------------------------------------------------------------
    def _set_lwt(self, *, client, payload):
        if client:
            l_lwt = self._cfg.get('lwt', _def.MQTT_LWT)
            l_topic = self._cfg.get('lwttopic', None)
            if l_lwt and l_topic:
                logger.debug(f'{self._name} topic:{l_topic} payload:{payload}')
                client.will_set(
                    topic=self._cfg.get('lwttopic'), 
                    payload=payload, 
                    qos=self._cfg.get('lwtqos', _def.MQTT_LWTQOS),
                    retain=self._cfg.get('lwtretain', _def.MQTT_LWTRETAIN)
                )

#-------------------------------------------------------------------------------
    async def _publish_lwt(self, *, payload):
        if self._client:
            l_lwt = self._cfg.get('lwt', _def.MQTT_LWT)
            l_topic = self._cfg.get('lwttopic')
            logger.debug(f'{self._name} lwt:{str(l_lwt)}')
            if l_lwt:
                await self._publish(
                    topic=l_topic, 
                    payload=payload, 
                    qos=self._cfg.get('lwtqos', _def.MQTT_LWTQOS), 
                    retain=self._cfg.get('lwtretain', _def.MQTT_LWTRETAIN)
                )
                logger.debug(f'{self._name} lwt topic:{l_topic} payload:{payload}')

#-------------------------------------------------------------------------------
    async def _publish(self, *, topic, payload, qos=1, retain=False):
        logger.debug(f'{self._name} topic: {topic} qos:{qos} retain:{retain} type:{type(payload)} payload:{payload}')

        if self._client:
            try:
                if isinstance(payload, str):
                    payload = payload.encode()
                elif not isinstance(payload, bytes):
                    payload = str(payload).encode()

                l_publish = self._client.publish(
                    topic=topic, 
                    payload=payload, 
                    qos=qos, 
                    retain=retain
                )
                await l_publish.wait_for_publish()
                logger.debug(f'{self._name} published')
                return True
            except asyncio.CancelledError:
                logger.warning(f'{self._name} CancelledError')
            except:
                logger.exception(f'{self._name}')

        return False

#-------------------------------------------------------------------------------
    def _on_message(self, client, userdata, message):
        logger.debug(f'{self._name} topic:{message.topic} payload:{message.payload}')

        if self._message_callback:
             self._message_callback(message=message)

#-------------------------------------------------------------------------------
    # def shutdown(self):
    #     self._stop_event.set()

#-------------------------------------------------------------------------------
    def stop(self):
        self._stop_event.set()

#-------------------------------------------------------------------------------
    def _dummy_callback(self, *, message):
        l_payload = message.payload.decode()
        logger.debug(f'{self._name} topic:{message.topic} payload:{l_payload}')

#-------------------------------------------------------------------------------
    async def run(self):
        logger.info(f'{self._name} start')

        # self.start_event.set()
        try:
            while not self._stop_event.is_set():
                try:
                    if self._client:
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

                            logger.debug(f'{self._name} func:{l_func} {self._funcs[l_func]}')
                            await self._funcs[l_func](topic=self._topic, item=l_item)
                    else:
                        if not self._client:
                            await self._connect(cfg=self._cfg)
                        else:
                            await asyncio.sleep(self.QUEUE_GET_TIMEOUT)
                except asyncio.CancelledError:
                    logger.warning(f'{self._name} CanceledError')
                    return
                except GeneratorExit:
                    logger.warning(f'{self._name} GeneratorExit')
                    return
        except:
            logger.exception(f'*** {self._name}')
        finally:
            await self._disconnect()
            logger.info(f'{self._name} done')

#-------------------------------------------------------------------------------
    async def _get_newest(self, *, item):
        logger.debug(f'{self._name} type:{type(item)} {item}')

        l_newest_item = None
        l_newest_ts = _dt(1970,1,1,tzinfo=timezone.utc)
        if isinstance(item, list):
            for l_item in item:
                l_time = l_item.get('time', None)
                if l_time:
                    l_ts = ciso8601.parse_datetime(l_time).replace(tzinfo=timezone.utc)
                    if l_ts > l_newest_ts:
                        l_newest_item = l_item
                        l_newest_ts = l_ts
        else:
            l_newest_item = item

        logger.debug(f'{self._name} item: {l_newest_item}')
        return l_newest_item

#-------------------------------------------------------------------------------
    async def _execute_default(self, *, topic, item):
        logger.error(f'{self._name} topic:{topic} item: {item}')
        # if not item:
        #     logger.error(f'{self._name} topic:{topic}')
        #     return

        # if isinstance(item, dict):
        #     await self._execute_dict(topic=topic, item = item)
        # else:
        #     await self._execute_json(topic=topic, item = item)

#-------------------------------------------------------------------------------
    async def _execute_json(self, *, topic, item):
        logger.debug(f'{self._name} type:{type(item)}')
        if not item:
            logger.error(f'{self._name} topic:{topic} item: {item}')
            return

        l_dict = json.loads(item)
        await self._execute_dict(topic=topic, item=l_dict)

#-------------------------------------------------------------------------------
    async def _execute_dict(self, *, topic, item):
        logger.debug(f'{self._name} type:{type(item)}')
        if not item:
            logger.error(f'{self._name} topic:{topic} item: {item}')
            return

        l_rebuffer = False
        l_json = item.get('json', None)
        l_jobid = item.get('jobid', None)
        if self._client and l_json:
            if item.get('resend', None):
                logger.debug(f'{self._name} jobid:{l_jobid} resending item:{item}')
            if isinstance(l_json, list):
                for l_item in l_json:
                    l_bytes = str(l_item).replace('\'', '\"').encode()
                    if not await self._publish(topic=topic, payload=l_bytes, qos=self._qos, retain=self._retain):
                        l_rebuffer = True
            else:
                l_bytes = str(l_json).replace('\'', '\"').encode()
                if not await self._publish(topic=topic, payload=l_bytes, qos=self._qos, retain=self._retain):
                    l_rebuffer = True
        else:
            l_rebuffer = True

        if self._inqueue and l_rebuffer:
            item['resend'] = True
            await self.queue_put(outqueue=self._inqueue, data=item)
            logger.debug(f'{self._name} jobid:{l_jobid} rebuffer data:{item}')

#==============================================================================
