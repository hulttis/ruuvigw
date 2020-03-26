# coding=utf-8
#-------------------------------------------------------------------------------
# Name:        mqtt_aiobase.py
# Purpose:     generic mqtt (aiomqtt - paho) client base
# Copyright:   (c) 2019 TK
# Licence:     MIT
#-------------------------------------------------------------------------------
import logging
logger = logging.getLogger('kafka')

import ssl
import json
import uuid
import asyncio
from aiokafka import AIOKafkaProducer as _producer
from aiokafka.errors import KafkaError, KafkaTimeoutError, ConnectionError

# ==================================================================================
class kafka_aioproducer():
    SLEEP                   = 0.5
    KAFKA_NAME              = 'kafka_aioproducer'
    KAFKA_CLIENT_ID         = f'{KAFKA_NAME}'
    KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
    KAFKA_ACKS              = 1

#-------------------------------------------------------------------------------
    def __init__(self, *,
        loop,
        **kwargs
    ):
        """
            See _parse_kwargs for user configuration parameters
        """
        self._kwargs = kwargs
        self._name = kwargs.get('name', kafka_aioproducer.KAFKA_NAME)
        logger.debug(f'''{self._name} kwargs:{kwargs}''')

        try:
            self._producercfg = self._parse_kwargs(**kwargs)
            logger.debug(f'''{self._name} producercfg:{self._producercfg}''')
        except Exception as l_e:
            logger.critical(f'*** {self._name} {l_e}')
            raise
        self._loop = loop
        self._producer = None
        self._connected = False

        logger.info(f'{self._name} initialized')

#-------------------------------------------------------------------------------
    def _parse_kwargs(self, **kwargs):
        logger.debug(f'''{self._name}''')
        if not kwargs.get('bootstrap_servers', None):
           raise ValueError("'bootstrap_servers' is required parameter")

        return {
            'bootstrap_servers': kwargs.get('bootstrap_servers', kafka_aioproducer.KAFKA_BOOTSTRAP_SERVERS),
            'client_id': f'''{kwargs.get('client_id', kafka_aioproducer.KAFKA_CLIENT_ID)}-{str(uuid.uuid4())[:10]}''',
            'acks': kwargs.get('acks', kafka_aioproducer.KAFKA_ACKS)
        }
        
#-------------------------------------------------------------------------------
    def is_connected(self):
        return self._connected

#-------------------------------------------------------------------------------
    async def connect_producer(self):
        logger.debug(f'{self._name}')

        l_success = False
        try:
            self._producer = _producer(
                loop=self._loop,
                bootstrap_servers=self._producercfg['bootstrap_servers'],
                client_id=self._producercfg['client_id'],
                acks=self._producercfg['acks']
            )
            await self._producer.start()
            self._connected = True
            logger.info(f'''{self._name} kafka connected bootstrap_servers: {self._producercfg['bootstrap_servers']}''')
            logger.info(f'''{self._name} kafka connected client_id:{self._producercfg['client_id']}''')
            l_success = True
            return True
        except ConnectionError as l_e:
            logger.critical(f'''{self._name} ConnectionError: {l_e}''')    
        except:
            logger.exception(f'''{self._name}''')
        finally:
            if not l_success:
                await self._producer.stop()
                del self._producer
                self._producer = None        

        return False

#-------------------------------------------------------------------------------
    async def disconnect_producer(self):
        logger.debug(f'{self._name}')

        if self._producer and self._connected:
            l_client_id = self._producercfg['client_id']
            try:
                await self._producer.stop()
                logger.info(f'''{self._name} disconnected client_id:{l_client_id}''')
            except asyncio.CancelledError:
                logger.warning(f'''{self._name} CancelledError''')
            except:
                logger.exception(f'''*** {self._name}''')
            finally:
                self._connected = False
                del self._producer
                self._producer = None 

#-------------------------------------------------------------------------------
    async def send(self, *, topic, value, key=None, partition=None, timestamp_ms=None):
        logger.debug(f'''{self._name} topic:{topic} key:{key} value:{value}''')
        
        if not self._producer:
            return False
        if topic:
            try:
                if isinstance(value, str):
                    value = value.encode()
                elif isinstance(value, dict):
                    value = str(json.dumps(value)).encode()
                elif not isinstance(value, bytes):
                    value = str(value).encode()
                if isinstance (key, str):
                    key = key.encode()

                l_obj = await self._producer.send_and_wait(
                    topic=topic,
                    value=value,
                    key=key,
                    partition=partition,
                    timestamp_ms=timestamp_ms
                )
                logger.debug(f'{self._name} topic:{l_obj.topic:20} key:{key.decode():20} partition:{l_obj.partition}:{l_obj.offset}')
                return True
            except asyncio.CancelledError:
                logger.warning(f'''{self._name} CancelledError''')
            except:
                logger.exception(f'''{self._name}''')

        return False

#==============================================================================
