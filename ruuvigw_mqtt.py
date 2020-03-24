# coding=utf-8
#-------------------------------------------------------------------------------
# Name:        ruuvi_mqtt.py
# Purpose:     ruuvi specific mqtt
# Copyright:   (c) 2019 TK
# Licence:     MIT
#-------------------------------------------------------------------------------
import logging
logger = logging.getLogger('mqtt')

import copy
import asyncio
from collections import defaultdict

from mqtt_aioclient import mqtt_aioclient as _mqtt
import ruuvigw_defaults as _def

# ==================================================================================

class ruuvi_mqtt(_mqtt):
    _anndelay = 1.0
#-------------------------------------------------------------------------------
    def __init__(self, *,
        cfg,
        hostname,
        inqueue,
        # fbqueue,
        loop,
        scheduler,
        nameservers=None
    ):
        """
            cfg - mqtt configuration
            hostname - name of the system
            inqueue - incoming queue for data
            fbqueue - feedback queue for parent
            loop - asyncio loop
            scheduler - used scheduler for scheduled tasks
            nameservers - list of used name servers
        """
        super().__init__(
            cfg=cfg,
            hostname=hostname,
            inqueue=inqueue,
            # fbqueue=fbqueue,
            loop=loop,
            scheduler=scheduler,
            nameservers=nameservers
        )
        self._funcs['execute_ruuvi'] = self._execute_ruuvi
        # logger.debug(f'{self._name} funcs:{self._funcs}')

        self._addata = defaultdict(dict)
        self._hostname = hostname
        # self._message_callback = self._ruuvi_message
        self._lock = asyncio.Lock()
        self._first_announce = True

        logger.info(f'{self._name} initialized')

#-------------------------------------------------------------------------------
    async def _connect(self, *, cfg):
        logger.debug(f'{self._name} cfg:{cfg}')

        if await super()._connect(cfg=cfg):
            if cfg.get('cmdtopic', _def.MQTT_CMDTOPIC):
                await self._subscribe(
                    topic=cfg.get('cmdtopic', None), 
                    qos=self._cfg.get('cmdqos', _def.MQTT_CMDQOS),
                    callback=self._ruuvi_command
                )
            return True
        return False

#-------------------------------------------------------------------------------
    async def _disconnect(self):
        logger.debug(f'{self._name}')

        if self._client:
            if self._cfg.get('cmdtopic', _def.MQTT_CMDTOPIC):
                await self._unsubscribe(topic=self._cfg.get('cmdtopic', _def.MQTT_CMDTOPIC))
            await super()._disconnect()

#-------------------------------------------------------------------------------
    def _set_addata(self, *, key):
        logger.debug(f'{self._name} addata:{self._addata}')
        try:
            l_rc = self._addata[key]
        except:
            l_rc = False
        self._addata[key] = True
        return l_rc

#-------------------------------------------------------------------------------
    async def _ruuvi_announce(self, *, item, topic):
        logger.debug(f'{self._name} type:{type(item)} item:{item}')
        l_ignore = ['time']

        if self._cfg.get('adprefix', _def.MQTT_ADPREFIX):
            try:
                l_tags = item['tags']
                l_name = l_tags['name']
                if not self._set_addata(key=l_tags['mac']):
                    l_dev = {
                        'identifiers': l_tags['mac'],
                        'name': 'Ruuvi ' + l_name,
                        'model': _def.PROGRAM_NAME,
                        'sw_version': _def.VERSION,
                        'manufacturer': _def.PROGRAM_COPYRIGHT
                    }
                    logger.info(f'{self._name} auto discovery:{l_name}')
                    # l_lwt = self._cfg.get('lwt', _def.MQTT_LWT)
                    # l_lwttopic = self._cfg.get('lwttopic', None)
                    # publish fields
                    l_adfields = self._cfg.get('ADFIELDS', _def.MQTT_ADFIELDS)
                    for l_key in item['fields'].keys():
                        if l_key not in l_ignore:
                            l_adfield = l_adfields.get(l_key, None)
                            l_component = l_adfield.get('component', 'sensor') if l_adfield else 'sensor'
                            l_adtopic = self._cfg.get('adprefix') + '/' + \
                                l_component + '/' + \
                                self._cfg.get('adnodeid', _def.MQTT_ADNODEID) + '/' + \
                                l_name + '_' + l_key + '/config' 
                            if not self._cfg.get('adretain', _def.MQTT_ADRETAIN) and self._first_announce:
                                await self._publish(
                                    topic=l_adtopic, 
                                    payload=b'',
                                    qos=self._cfg.get('adqos', _def.MQTT_ADQOS), 
                                    retain=True
                                )
                            self._first_announce = False
                            if l_adfield:
                                await asyncio.sleep(0.1)
                                l_payload = {
                                    'dev': l_dev,
                                    'unit_of_measurement': l_adfield.get('unit_of_measurement', ''),
                                    'name': l_name + ' ' + l_key,
                                    'state_topic': topic,
                                    'value_template': l_adfield.get('value_template', ''),
                                    'unique_id': l_name + '_' + l_key,
                                    'qos':  self._cfg.get('adqos', _def.MQTT_ADQOS),
                                    'device_class': l_adfield.get('device_class', ''),
                                    'icon': l_adfield.get('icon', '')
                                }
                                if self._cfg.get('lwt', _def.MQTT_LWT):
                                    l_payload['availability_topic'] = self._cfg.get('lwttopic')
                                    l_payload['payload_available'] = self._cfg.get('lwtonline', _def.MQTT_LWTONLINE)
                                    l_payload['payload_not_available'] = self._cfg.get('lwtoffline', _def.MQTT_LWTOFFLINE)

                                await self._publish(
                                    topic=l_adtopic, 
                                    payload=str(l_payload).replace('\'', '\"').encode(), 
                                    qos=self._cfg.get('adqos', _def.MQTT_ADQOS),
                                    retain=self._cfg.get('adretain', _def.MQTT_ADRETAIN)
                                )
                    return True
            except:
                logger.exception(f'*** {self._name}')
        return False

#-------------------------------------------------------------------------------
    def _ruuvi_command(self, client, userdata, message):
        logger.debug(f'{self._name} client:{client} userdata:{userdata} message:{message}')

        if message:
            if isinstance(message.payload, bytes):
                l_payload = message.payload.decode()
            else:
                l_payload = message.payload
            logger.debug(f'{self._name} topic:{message.topic} payload:{l_payload}')
            if message.topic == self._cfg.get('cmdtopic', _def.MQTT_CMDTOPIC):
                if l_payload == _def.MQTT_CMD_ANNOUNCE:
                    logger.info(f'{self._name} topic:{message.topic} payload:{l_payload} received')
                    self._addata.clear()
                    self._do_announce = True    # do base class announce

#-------------------------------------------------------------------------------
    async def _execute_ruuvi(self, *, topic, item):
        async with self._lock:
            if not item:
                logger.error(f'{self._name} topic:{topic} item: {item}')
                return
            item = copy.deepcopy(item)
            logger.debug(f'{self._name} type:{type(item)}')

            l_heartbeat = False
            try:
                l_jobid = item.get('jobid', None)
                l_json = item['json']
                if isinstance(l_json, list):
                    for l_item in l_json:
                        l_topic = topic + '/' + l_item['tags']['name']
                        if await self._ruuvi_announce(item=l_item, topic=l_topic):
                            await asyncio.sleep(self._anndelay)
                        l_payload = None
                        if not self._cfg.get('fulljson', _def.MQTT_FULLJSON):
                            l_payload = l_item['fields']
                            try:
                                del l_payload['time']
                            except:
                                pass
                        else:
                            l_payload = l_item

                        if not await self._publish(
                            topic=l_topic, 
                            payload=str(l_payload).replace('\'', '\"').encode(),
                            qos=self._cfg.get('qos', _def.MQTT_QOS),
                            retain=self._cfg.get('retain', _def.MQTT_RETAIN)
                        ):
                            logger.warning(f'{self._name} jobid:{l_jobid} publish failed topic:{l_topic} payload:{l_payload}')
                        else:
                            l_heartbeat = True
                else:
                    l_topic = topic + '/' + l_json['tags']['name']
                    if await self._ruuvi_announce(item=l_item, topic=l_topic):
                        await asyncio.sleep(self._anndelay)
                    l_payload = None
                    if not self._cfg.get('fulljson', _def.MQTT_FULLJSON):
                        l_payload = l_json
                        try:
                            del l_payload['time']
                        except:
                            pass
                    else:
                        l_payload = l_json
                    if not await self._publish(
                        topic=l_topic, 
                        payload=str(l_payload).replace('\'', '\"').encode(),
                        qos=self._cfg.get('qos', _def.MQTT_QOS),
                        retain=self._cfg.get('retain', _def.MQTT_RETAIN)
                    ):
                        logger.warning(f'{self._name} jobid:{l_jobid} publish failed topic:{topic} payload:{l_payload}')
                    else:
                        l_heartbeat = True
            except asyncio.CancelledError:
                logger.warning(f'CancelledError')
                raise
            except Exception:
                logger.exception(f'*** {self._name}')
                raise

            if l_heartbeat:
                await self._publish_hb()

            logger.debug(f'{self._name} jobid:{l_jobid} topic:{topic} item:{item}')

