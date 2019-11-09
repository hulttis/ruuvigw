# coding=utf-8
#-------------------------------------------------------------------------------
# Name:        mqtt_aioclient.py
# Purpose:     mqtt
#
# Author:      Timo Koponen
#
# Created:     03/08/2019
# modified:    03/08/2019
# Copyright:   (c) 2017
# Licence:     <your licence>
#-------------------------------------------------------------------------------
import logging
logger = logging.getLogger(__name__)

import asyncio
from hbmqtt.client import MQTTClient, ClientException, ConnectException
from hbmqtt.mqtt.constants import QOS_0, QOS_1, QOS_2

import json
import ciso8601
from datetime import datetime as _dt
from datetime import timezone
from collections import defaultdict

from mixinQueue import mixinAioQueue as _mixinQueue
import defaults as _def

# ==================================================================================

class mqtt_aioclient(_mixinQueue):
    QUEUE_GET_TIMEOUT = 0.2
    MQTT_MESSAGE_TIMEOUT = 0.2
    MQTT_CONNECT_DELAY = 1.0
#-------------------------------------------------------------------------------
    def __init__(self, *,
        cfg,
        inqueue,
        loop,
        scheduler,
        nameservers=None
    ):
        super().__init__()
        self._funcs = {
            'default':        self._execute_default,
            'execute_dict':   self._execute_dict,       # python dict
            'execute_json':   self._execute_json       # json string
        }
        self._message_callback = self._dummy_callback

        if not cfg:
           logger.error('cfg None')
           raise ValueError('cfg cannot be None')
        if not inqueue:
           logger.error('inqueue None')
           raise ValueError('inqueue cannot be None')

        self._name = cfg.get('name', _def.MQTT_NAME)
        logger.debug(f'{self._name} enter')
        self._cfg = cfg
        self._inqueue = inqueue

        self._stop_event = asyncio.Event()
        self._client = None
        self._client_connected = False
        l_will = {}
        l_lwttopic = cfg.get('lwttopic', None)
        self._client_config = {
            'keep_alive': 10,
            'ping_delay': 1,
            'default_qos': cfg.get('qos', _def.MQTT_QOS),
            'default_retain': cfg.get('retain', _def.MQTT_RETAIN),
            'auto_reconnect': True,
            'reconnect_max_interval': 5,
            'reconnect_retries': 4,
            'check_hostname': cfg.get('check_hostname', _def.MQTT_CHECK_HOSTNAME),
            # # 'certfile': '',
            # 'keyfile': '',
        }
        if cfg.get('lwt', _def.MQTT_LWT):
            self._client_config['will'] = {
                'topic': f'''{cfg.get('lwttopic')}''',
                'retain': _def.MQTT_LWTRETAIN,
                'qos': _def.MQTT_LWTQOS,
                'message': cfg.get('lwtmessage', _def.MQTT_LWTMESSAGE).encode()
            }
        logger.debug(f'{self._name} client_config: {self._client_config}')
        self._topic = cfg.get('topic', _def.MQTT_TOPIC)
        self._qos = cfg.get('qos', _def.MQTT_QOS)
        self._retain = cfg.get('retain', _def.MQTT_RETAIN)
        self._only_newest = cfg.get('only_newest', _def.MQTT_ONLYNEWEST)

        self._loop = loop
        self._nameservers = nameservers
        self._message_task = None

        logger.debug(f'{self._name} exit')

#-------------------------------------------------------------------------------
    async def _connect(self, *, cfg):
        logger.debug(f'{self._name} cfg:{cfg}')

        try:
            l_client_id =  cfg.get('client_id', _def.MQTT_CLIENT_ID)
            self._client = MQTTClient(client_id=l_client_id, loop=self._loop, config=self._client_config)
            l_host = cfg.get('host', _def.MQTT_HOST)
            logger.debug(f'{self._name} connecting mqtt. host:{l_host} client_id:{l_client_id}')
            l_secure = ''
            if 'mqtts://' in l_host:
                l_status = await self._client.connect(l_host, cafile=cfg.get('cafile')) 
                l_secure = 'S'
            else:
                l_status = await self._client.connect(l_host)
            if l_status == 0:   # Connection Accepted
                logger.info(f'{self._name} MQTT{l_secure} connected client_id:{l_client_id}')
                logger.debug(f'{self._name} host:{l_host} topic: {self._topic} qos:{self._qos} retain:{self._retain}')
                self._client_connected = True
                await self._publish_lwt(cfg=cfg)
                return True
            else:
                logger.error(f'{self._name} MQTT{l_secure} connection failed. Status:{l_status}')
        except ConnectException:
            logger.exception(f'*** {self._name} ConnectException. host:{l_host} client_id:{l_client_id}')
            self._client = None
        except:
            logger.exception(f'*** {self._name}')
            self._client = None


        self._client_connected = False
        return False

#-------------------------------------------------------------------------------
    async def _disconnect(self):
        logger.debug(f'{self._name}')

        if self._client:
            l_client_id = self._cfg.get('client_id', _def.MQTT_CLIENT_ID)
            l_host = self._cfg.get('host', _def.MQTT_HOST)
            l_secure = ''
            if 'mqtts://' in l_host:
                l_secure = 'S'
            await self._client.disconnect()
            self._client_connected = False
            self._client = None
            logger.warning(f'{self._name} MQTT{l_secure} disconnected client_id:{l_client_id}')
            logger.debug(f'{self._name} host:{l_host}')

#-------------------------------------------------------------------------------
    async def _subscribe(self, *, topic, qos=QOS_1):
        if topic:
            logger.info(f'{self._name} topic:{topic}')
            try:
                await self._client.subscribe([(topic, qos)])
                self._message_task = self._loop.create_task(self.run_message())
            except ClientException:
                logger.error(f'{self._name} ClientException topic:{topic}')
                await self._disconnect()
            except ConnectionResetError:
                logger.error(f'{self._name} ConnectionResetError topic:{topic}')
                await self._disconnect()
            except:
                logger.exception(f'*** {self._name} MQTT subscribe failed. topic:{topic}')
                await self._disconnect()

#-------------------------------------------------------------------------------
    async def _unsubscribe(self, *, topic):
        if topic:
            logger.info(f'{self._name} topic:{topic}')
            try:
                await self._client.unsubscribe([(topic)])
            except ClientException:
                logger.error(f'{self._name} ClientException topic:{topic}')
                await self._disconnect()
            except ConnectionResetError:
                logger.error(f'{self._name} ConnectionResetError topic:{topic}')
                await self._disconnect()
            except:
                logger.exception(f'*** {self._name} MQTT unsubscribe failed. topic:{topic}')
                await self._disconnect()

#-------------------------------------------------------------------------------
    async def _publish_lwt(self, *, cfg):
        l_lwt = cfg.get('lwt', _def.MQTT_LWT)
        logger.debug(f'{self._name} lwt:{str(l_lwt)}')

        if l_lwt:
            try:
                l_topic = self._client_config['will']['topic']
                await self._publish(topic=l_topic, payload=_def.MQTT_LWTONLINE.encode(), retain=_def.MQTT_LWTRETAIN)
            except:
                pass

#-------------------------------------------------------------------------------
    async def _publish(self, *, topic, payload, retain):
        logger.debug(f'{self._name} topic: {topic} retain:{retain} payload:{payload}')

        if self._client_connected:
            try:
                await self._client.publish(topic, payload, qos=self._qos, retain=retain)
                return True
            except ClientException:
                logger.error(f'{self._name} ClientException topic:{topic}')
                await self._disconnect()
            except ConnectionResetError:
                logger.error(f'{self._name} ConnectionResetError topic:{topic}')
                await self._disconnect()
            except:
                logger.exception(f'*** {self._name} MQTT publish failed. topic:{topic} type:{type(payload)} data:{payload}')
                await self._disconnect()
        else:
            logger.debug(f'{self._name} MQTT is not connected. topic:{topic} data:{payload}')

        return False

#-------------------------------------------------------------------------------
    def shutdown(self):
        logger.warning(f'{self._name}')
        self._stop_event.set()

#-------------------------------------------------------------------------------
    async def run_message(self):
        logger.debug(f'{self._name}')

        while not self._stop_event.is_set():
            try:
                if self._client_connected:
                    l_message = await self._client.deliver_message(timeout=self.MQTT_MESSAGE_TIMEOUT)
                    if self._message_callback:
                        await self._message_callback(message=l_message)
            except ClientException:
                logger.error(f'{self._name} ClientException')
                await self._disconnect()
            except ConnectionResetError:
                logger.error(f'{self._name} ConnectionResetError')
                await self._disconnect()
            except asyncio.CancelledError:
                logger.warning(f'{self._name} CanceledError')
            except asyncio.TimeoutError:
                # logger.debug(f'{self._name} TimeoutError')
                pass
            except GeneratorExit:
                pass
            except:
                logger.exception(f'*** {self._name}')
                await self._disconnect()

#-------------------------------------------------------------------------------
    async def _dummy_callback(self, *, message):
        l_packet = message.publish_packet
        l_payload = l_packet.payload.data.decode()
        logger.debug(f'{self._name} topic:{l_packet.variable_header.topic_name} payload:{l_payload}')

#-------------------------------------------------------------------------------
    async def run(self):
        logger.info(f'{self._name} enter')

        # self.start_event.set()
        while not self._stop_event.is_set():
            try:
                if self._client_connected:
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
            except GeneratorExit:
                logger.error(f'{self._name} GeneratorExit')
            except Exception:
                logger.exception(f'*** {self._name}')

        await self._disconnect()
        logger.warning(f'{self._name} exit')

        return (True)

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
        logger.warning(f'{self._name} topic:{topic} item: {item}')
        if not item:
            logger.error(f'{self._name} topic:{topic} item: {item}')
            return

        if isinstance(item, dict):
            await self._execute_dict(topic=topic, item = item)
        else:
            await self._execute_json(topic=topic, item = item)

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
                logger.info(f'{self._name} jobid:{l_jobid} resending item:{item}')
            if isinstance(l_json, list):
                for l_item in l_json:
                    l_bytes = str(l_item).replace('\'', '\"').encode()
                    if not await self._publish(topic=topic, payload=l_bytes, retain=self._retain):
                        l_rebuffer = True
            else:
                l_bytes = str(l_json).replace('\'', '\"').encode()
                if not await self._publish(topic=topic, payload=l_bytes, retain=self._retain):
                    l_rebuffer = True
        else:
            l_rebuffer = True

        if self._inqueue and l_rebuffer:
            item['resend'] = True
            await self.queue_put(outqueue=self._inqueue, data=item)
            logger.warning(f'{self._name} jobid:{l_jobid} rebuffer')
            logger.debug(f'{self._name} jobid:{l_jobid} rebuffer data:{item}')

#==============================================================================
