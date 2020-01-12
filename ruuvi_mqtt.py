# coding=utf-8
#-------------------------------------------------------------------------------
# Name:        ruuvi_mqtt.py
# Purpose:     ruuvi specific mqtt
# Copyright:   (c) 2019 TK
# Licence:     MIT
#-------------------------------------------------------------------------------
import logging
logger = logging.getLogger('mqtt')

import asyncio
from collections import defaultdict

from mqtt_aioclient import mqtt_aioclient as _mqtt
import defaults as _def

# ==================================================================================

class ruuvi_mqtt(_mqtt):
    _adlock = asyncio.Lock()
    _anndelay = 2
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
        super().__init__(
            cfg=cfg,
            hostname=hostname,
            inqueue=inqueue,
            loop=loop,
            scheduler=scheduler,
            nameservers=nameservers
        )
        self._funcs['execute_ruuvi'] = self._execute_ruuvi
        # logger.debug(f'{self._name} funcs:{self._funcs}')

        self._announce = defaultdict(dict)
        self._adtopic = cfg.get('adtopic', None)
        self._adretain = cfg.get('adretain', _def.MQTT_ADRETAIN)
        self._adqos = cfg.get('adqos', _def.MQTT_ADQOS)
        self._adfields = cfg.get('ADFIELDS', _def.MQTT_ADFIELDS)
        self._anntopic = cfg.get('anntopic', None)
        self._annqos = cfg.get('annqos', _def.MQTT_ANNQOS)
        self._hostname = hostname
        self._message_callback = self._ruuvi_message

        logger.debug(f'{self._name} done')

#-------------------------------------------------------------------------------
    async def _connect(self, *, cfg):
        logger.debug(f'{self._name} cfg:{cfg}')

        if await super()._connect(cfg=cfg):
            if self._anntopic:
                await self._subscribe(
                    topic=self._anntopic, 
                    qos=self._annqos
                )
            return True
        return False

#-------------------------------------------------------------------------------
    async def _disconnect(self):
        logger.debug(f'{self._name}')

        if self._client:
            if self._anntopic:
                await self._unsubscribe(topic=self._anntopic)
            await super()._disconnect()

#-------------------------------------------------------------------------------
    def _set_announce(self, *, key):
        logger.debug(f'{self._name} addata:{self._announce}')
        try:
            l_rc = self._announce[key]
        except:
            l_rc = False
        self._announce[key] = True
        return l_rc

#-------------------------------------------------------------------------------
    async def _ruuvi_announce(self, *, item, topic):
        logger.debug(f'{self._name} type:{type(item)} item:{item}')
        l_ignore = ['time']

        if self._adtopic:
            try:
                l_tags = item['tags']
                l_name = l_tags['name']
                if not self._set_announce(key=l_tags['mac']):
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
                    for l_key, _ in item['fields'].items():
                        if l_key not in l_ignore:
                            l_adtopic = self._adtopic + '/' + l_name + '-' + l_key + '/config' 
                            await self._publish(
                                topic=l_adtopic, 
                                payload=b'',
                                qos=self._adqos, 
                                retain=False
                            )

                            l_adfields = self._adfields.get(l_key, None)
                            if l_adfields:
                                l_payload = {
                                    'unit_of_measurement': l_adfields.get('unit_of_measurement', ''),
                                    'name': l_name + ' ' + l_key,
                                    'state_topic': topic,
                                    'value_template': l_adfields.get('value_template', ''),
                                    'unique_id': l_name + '-' + l_key,
                                    'qos':  self._adqos,
                                    'device_class': l_adfields.get('device_class', ''),
                                    'icon': l_adfields.get('icon', ''),
                                    'dev': l_dev
                                }
                                # if l_lwt and l_lwttopic:
                                #     l_payload['avty_t'] = l_lwttopic                    # availability topic
                                await self._publish(
                                    topic=l_adtopic, 
                                    payload=str(l_payload).replace('\'', '\"').encode(), 
                                    qos=self._adqos,
                                    retain=self._adretain
                                )
                    # publish computer availability
                    # if l_lwt and l_lwttopic:
                    #     l_dev = {
                    #         'ids': [self._hostname],
                    #         'name': self._hostname,
                    #         'mdl': _def.PROGRAM_NAME,
                    #         'sw': _def.VERSION,
                    #         'mf': _def.PROGRAM_COPYRIGHT
                    #     }
                    #     l_payload = {
                    #             'dev': l_dev,
                    #             'name': self._hostname,
                    #             'stat_t': l_lwttopic,                                   # state topic
                    #             'unique_id': self._hostname,
                    #             'qos':  self._adqos,
                    #             'dev_cla': 'connectivity'
                    #     }
                    #     l_adtopic = self._adtopic + '/' + self._hostname + '/config' 
                    #     await self._publish(topic=l_adtopic, payload=str(l_payload).replace('\'', '\"').encode(), qos=self._adqos, retain=self._adretain)
            except:
                logger.exception(f'*** {self._name}')

#-------------------------------------------------------------------------------
    def _ruuvi_message(self, *, message):
        logger.debug(f'{self._name}')

        if message:
            if isinstance(message.payload, bytes):
                l_payload = message.payload.decode()
            else:
                l_payload = message.payload
            logger.debug(f'{self._name} topic:{message.topic} payload:{l_payload}')
            if l_payload == 'ruuvi':
                logger.info(f'{self._name} announce received')
                self._announce.clear()

#-------------------------------------------------------------------------------
    async def _execute_ruuvi(self, *, topic, item):
        logger.debug(f'{self._name} type:{type(item)}')
        if not item:
            logger.error(f'{self._name} topic:{topic} item: {item}')
            return

        try:
            l_jobid = item.get('jobid', None)
            l_json = item['json']
            if isinstance(l_json, list):
                for l_item in l_json:
                    l_topic = topic + '/' + l_item['tags']['name']
                    async with ruuvi_mqtt._adlock:
                        await self._ruuvi_announce(item=l_item, topic=l_topic)
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

                    if not await self._publish(topic=l_topic, payload=str(l_payload).replace('\'', '\"').encode(), retain=self._retain):
                        logger.warning(f'{self._name} jobid:{l_jobid} publish failed topic:{l_topic} payload:{l_payload}')
            else:
                l_topic = topic + '/' + l_json['tags']['name']
                async with ruuvi_mqtt._adlock:
                    await self._ruuvi_announce(item=l_item, topic=l_topic)
                l_payload = None
                if not self._cfg.get('fulljson', _def.MQTT_FULLJSON):
                    l_payload = l_json
                    try:
                        del l_payload['time']
                    except:
                        pass
                else:
                    l_payload = l_json
                if not await self._publish(topic=l_topic, payload=str(l_payload).replace('\'', '\"').encode(), retain=self._retain):
                    logger.warning(f'{self._name} jobid:{l_jobid} publish failed topic:{l_topic} payload:{l_payload}')
        except asyncio.CancelledError:
            logger.warning(f'CancelledError')
            raise
        except Exception:
            logger.exception(f'*** {self._name}')
            raise

        logger.debug(f'{self._name} jobid:{l_jobid} topic:{l_topic} item:{item}')

