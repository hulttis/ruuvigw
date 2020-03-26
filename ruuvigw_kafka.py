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
    CONNECT_ATTEMPT_DELAY   = 10
    SEND_FAILED_LIMIT       = 10

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

        if not await super().connect_producer():
            logger.critical(f'{self._name} connect failed')
        l_exception = False
        l_connect_attempt_sec = 0
        l_connect_attempt_cnt = 0
        l_send_failed_cnt = 0
        try:
            while not self._stop_event.is_set():
                l_item = await self.queue_get(inqueue=self._inqueue)
                if super().is_connected():
                    if l_item:
                        l_item = l_item if isinstance(l_item, dict) else json.loads(l_item)
                        for l_topic in self._cfg.get('PUBTOPIC', _def.KAFKA_PUBTOPIC):
                            if await self._execute_ruuvi(
                                topic=l_topic,
                                key=self._cfg.get('key', _def.KAFKA_KEY),
                                item=l_item
                            ):
                                l_send_failed_cnt = 0
                            else:
                                l_send_failed_cnt += 1
                                if l_send_failed_cnt > ruuvigw_kafka.SEND_FAILED_LIMIT:
                                    await super().disconnect_producer()
                else:
                    l_time = int(time.time())
                    l_diff = int(abs(l_time - l_connect_attempt_sec))
                    if l_diff > ruuvigw_kafka.CONNECT_ATTEMPT_DELAY:
                        logger.info(f'{self._name} reconnect attempt:{l_connect_attempt_cnt} diff:{int(l_diff)}')
                        if await super().connect_producer():
                            l_connect_attempt_cnt = 0
                            logger.info(f'{self._name} reconnected:{l_connect_attempt_cnt}')
                        else:
                            logger.critical(f'{self._name} reconnect:{l_connect_attempt_cnt} failed')
                            l_connect_attempt_cnt += 1
                            l_connect_attempt_sec = int(time.time())
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
            await super().disconnect_producer()

#-------------------------------------------------------------------------------
    def _substitute(self, *, template, values):
        if template:
            try:
                return Template(template).substitute(
                    tagname=values['tags']['name'],
                    tagmac=values['tags']['mac'].replace(':',''),
                    tagdataFormat=values['tags']['dataFormat']
                )
            except:
                pass
        return None

#-------------------------------------------------------------------------------
    async def _execute_ruuvi(self, *, topic, key, item):
        if not item:
            logger.error(f'{self._name} item: {item}')
            return False

        item = copy.deepcopy(item)
        logger.debug(f'{self._name} topic:{topic} type:{type(item)} item:{item}')

        try:
            l_json = item['json']
            if not isinstance(l_json, list):
                l_json = [l_json]
            for l_item in l_json:
                l_topic = self._substitute(template=topic, values=l_item)
                if await self.send(
                    topic=l_topic, 
                    value=str(l_item).replace('\'', '\"'),
                    key=self._substitute(template=key, values=l_item)
                ):
                    return True
                logger.warning(f'{self._name} publish failed topic:{l_topic} payload:{l_item}')
        except asyncio.CancelledError:
            logger.warning(f'CancelledError')
        except Exception:
            logger.exception(f'*** {self._name}')

        return False

#==============================================================================
