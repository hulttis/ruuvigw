# coding=utf-8
#-------------------------------------------------------------------------------
# Name:        ruuvigw_kafka.py
# Purpose:     ruuvigw kafka client
# Copyright:   (c) 2020 TK
# Licence:     MIT
#-------------------------------------------------------------------------------
import logging
logger = logging.getLogger('kafka')

import copy
import json
import time
import asyncio
from string import Template

from mixinQueue import mixinAioQueue as _mixinQueue
from kafka_aioproducer import kafka_aioproducer as _producer
import ruuvigw_defaults as _def

# ==================================================================================

class ruuvigw_kafka(_producer, _mixinQueue):
    QUEUE_GET_TIMEOUT       = 0.2

#-------------------------------------------------------------------------------
    def __init__(self, *,
        loop,
        cfg,
        inqueue,
        hostname='localhost',
        scheduler=None,
        **kwargs
    ):
        """
            loop - asyncio loop
            cfg - mqtt configuration
            inqueue - incoming queue for data
            hostname - name of the system
            scheduler - used scheduler for scheduled tasks
            **kwargs - any other arguments
        """
        super().__init__(
            loop=loop,
            **cfg
        )

        if not cfg:
           logger.error('cfg is required parameter and cannot be None')
           raise ValueError('cfg is required parameter and cannot be None')
        if not inqueue:
           logger.error('inqueue is required parameter and cannot be None')
           raise ValueError('inqueue is required parameter and cannot be None')

        self._name = cfg.get('name', _def.KAFKA_NAME)
        logger.debug(f'{self._name}')

        self._cfg = cfg
        self._hostname = hostname
        self._inqueue = inqueue
        self._scheduler = scheduler

        self._stop_event = asyncio.Event()
        self._client = None

        self._starttime = time.time()
        self._schedule(scheduler=scheduler)

        logger.info(f'{self._name} initialized')

#-------------------------------------------------------------------------------
    def _schedule(self, *, scheduler):
        logger.debug(f'{self._name} enter {type(scheduler)}')

#-------------------------------------------------------------------------------
    def stop(self):
        logger.info(f'{self._name}')
        self._stop_event.set()

#-------------------------------------------------------------------------------
    def _get_topic(self, *, topic, item):
        l_t = Template(topic)
        l_topic = l_t.substitute(
            topic=item['topic']
        )
        return l_topic.replace('/','.')

#-------------------------------------------------------------------------------
    async def run(self):
        logger.info(f'{self._name} started')

        await super()._connect_producer()
        l_exception = False
        try:
            while not self._stop_event.is_set():
                l_item = await self.queue_get(inqueue=self._inqueue)
                if l_item:
                    l_item = l_item if isinstance(l_item, dict) else json.loads(l_item)
                    for l_topic in self._cfg.get('PUBTOPIC', _def.KAFKA_PUBTOPIC):
                        await self._execute_ruuvi(
                            topic=l_topic,
                            key=self._cfg.get('key', _def.KAFKA_KEY),
                            item=l_item
                        )
        except asyncio.CancelledError:
            logger.warning(f'{self._name} CanceledError')
        except GeneratorExit:
            logger.warning(f'{self._name} GeneratorExit')
        except:
            logger.exception(f'*** {self._name}')
            l_exception = True
        finally:
            if l_exception:
                logger.critical(f'''*** {self._name} failed''')
            else:
                logger.info(f'''{self._name} completed''')
            await super()._disconnect_producer()

#-------------------------------------------------------------------------------
    def _get_topic(self, *, topic, item):
        if topic:
            return Template(topic).substitute(
                tagname=item['tags']['name'],
                tagmac=item['tags']['mac'].replace(':','')
            )
        return None

#-------------------------------------------------------------------------------
    def _get_key(self, *, key, item):
        if key:
            return Template(key).substitute(
                tagname=item['tags']['name'],
                tagmac=item['tags']['mac'].replace(':','')
            )
        return None

#-------------------------------------------------------------------------------
    async def _execute_ruuvi(self, *, topic, key, item):
            if not item:
                logger.error(f'{self._name} item: {item}')
                return
            item = copy.deepcopy(item)
            logger.debug(f'{self._name} topic:{topic} type:{type(item)} item:{item}')

            try:
                l_json = item['json']
                if isinstance(l_json, list):
                    for l_item in l_json:
                        l_topic = self._get_topic(topic=topic, item=l_item)
                        if not await self._send(
                            topic=l_topic, 
                            value=str(l_item).replace('\'', '\"'),
                            key=self._get_key(key=key, item=l_item)
                        ):
                            logger.warning(f'{self._name} publish failed topic:{l_topic} payload:{l_item}')
                else:
                    l_topic = self._get_topic(topic=topic, item=l_item)
                    if not await self._send(
                        topic=l_topic, 
                        value=str(l_item).replace('\'', '\"'),
                        key=self._get_key(key=key, item=l_item)
                    ):
                        logger.warning(f'{self._name} publish failed topic:{topic} payload:{l_json}')
            except asyncio.CancelledError:
                logger.warning(f'CancelledError')
                raise
            except Exception:
                logger.exception(f'*** {self._name}')
                raise


#==============================================================================
