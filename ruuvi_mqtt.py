# coding=utf-8
#-------------------------------------------------------------------------------
# Name:        ruuvi_mqtt.py
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
from hbmqtt.mqtt.constants import QOS_0, QOS_1, QOS_2
from collections import defaultdict

from mqtt_aioclient import mqtt_aioclient as _mqtt
import defaults as _def

# ==================================================================================

class ruuvi_mqtt(_mqtt):
    _adlock = asyncio.Lock()
#-------------------------------------------------------------------------------
    def __init__(self, *,
        cfg,
        inqueue,
        loop,
        scheduler,
        nameservers=None
    ):
        super().__init__(
            cfg=cfg,
            inqueue=inqueue,
            loop=loop,
            scheduler=scheduler,
            nameservers=nameservers
        )
        self._funcs['execute_ruuvi'] = self._execute_ruuvi
        # logger.debug(f'{self._name} funcs:{self._funcs}')

        self._addata = defaultdict(dict)
        self._adtopic = cfg.get('adtopic', _def.MQTT_ADTOPIC)
        self._adretain = cfg.get('adretain', _def.MQTT_ADRETAIN)
        self._adfields = cfg.get('ADFIELDS', _def.MQTT_ADFIELDS)
        self._anntopic = cfg.get('anntopic', _def.MQTT_ANNTOPIC)
        self._message_callback = self._handle_message

        logger.debug(f'{self._name} done')

#-------------------------------------------------------------------------------
    async def _connect(self, *, cfg):
        logger.debug(f'{self._name} cfg:{cfg}')

        if await super()._connect(cfg=cfg):
            await self._subscribe(topic=self._anntopic)
            return True
        return False

#-------------------------------------------------------------------------------
    async def _disconnect(self):
        logger.debug(f'{self._name}')

        if self._client:
            await self._unsubscribe(topic=self._anntopic)
            await super()._disconnect()

#-------------------------------------------------------------------------------
    async def _handle_message(self, *, message):
        logger.debug(f'{self._name}')

        if message:
            l_packet = message.publish_packet
            l_payload = l_packet.payload.data.decode()
            logger.debug(f'{self._name} topic:{l_packet.variable_header.topic_name} payload:{l_payload}')
            if l_payload == 'ruuvi':
                logger.info(f'{self._name} ruuvi announce received')
                self._addata.clear()

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
    async def _ruuvi_ad(self, *, item, topic):
        logger.debug(f'{self._name} type:{type(item)} item:{item}')
        l_ignore = ['time']

        if self._adtopic:
            try:
                l_tags = item['tags']
                l_name = l_tags['name']
                if not self._set_addata(key=l_tags['mac']):
                    l_dev = {
                        'ids': [l_tags['mac']],
                        'name': 'Ruuvi ' + l_name,
                        'mdl': _def.PROGRAM_NAME,
                        'sw': _def.VERSION,
                        'mf': _def.PROGRAM_COPYRIGHT
                    }
                    logger.info(f'{self._name} auto discovery:{l_name}')
                    for l_key, _ in item['fields'].items():
                        if l_key not in l_ignore:
                            l_adtopic = self._adtopic + '/' + l_name + '-' + l_key + '/config' 
                            await self._publish(topic=l_adtopic, payload=b'', retain=False)

                            l_adfields = self._adfields.get(l_key, None)
                            if l_adfields:
                                l_payload = {
                                    'dev': l_dev,
                                    'name': l_name + ' ' + l_key,
                                    'stat_t': topic,
                                    'val_tpl': l_adfields.get('val_tpl', ''),
                                    'unique_id': l_name + '-' + l_key,
                                    'qos':  QOS_1,
                                    'unit_of_meas': l_adfields.get('unit_of_meas', ''),
                                    'dev_cla': l_adfields.get('dev_cla', '')
                                }
                                await self._publish(topic=l_adtopic, payload=str(l_payload).replace('\'', '\"').encode(), retain=self._adretain)
            except:
                logger.exception(f'*** {self._name}')

#-------------------------------------------------------------------------------
    async def _execute_ruuvi(self, *, topic, item):
        logger.debug(f'{self._name} type:{type(item)}')
        if not item:
            logger.error(f'{self._name} topic:{topic} item: {item}')
            return

        l_rebuffer = False
        try:
            l_jobid = item.get('jobid', None)
            l_json = item['json']
            if isinstance(l_json, list):
                for l_item in l_json:
                    l_topic = topic + '/' + l_item['tags']['name']
                    async with ruuvi_mqtt._adlock:
                        await self._ruuvi_ad(item=l_item, topic=l_topic)
                    if self._cfg.get('debug', _def.MQTT_DEBUG):
                        l_item['fields']['hostname'] = l_item['tags']['hostname']
                    else:
                        try:
                            del l_item['fields']['time']
                        except:
                            pass
                    if not await self._publish(topic=l_topic, payload=str(l_item['fields']).replace('\'', '\"').encode(), retain=self._retain):
                        l_rebuffer = True
            else:
                l_topic = topic + '/' + l_json['tags']['name']
                if not await self._publish(topic=l_topic, payload=str(l_json).replace('\'', '\"').encode(), retain=self._retain):
                    l_rebuffer = True
        except Exception:
            logger.exception(f'*** {self._name}')
            return

        logger.debug(f'{self._name} jobid:{l_jobid} topic:{l_topic} item:{item}')
        if self._inqueue and l_rebuffer:
            item['resend'] = True
            await self.queue_put(outqueue=self._inqueue, data=item)
            logger.warning(f'{self._name} jobid:{l_jobid} rebuffer')
            logger.debug(f'{self._name} jobid:{l_jobid} rebuffer data:{item}')

