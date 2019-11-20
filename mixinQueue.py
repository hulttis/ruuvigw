# coding=utf-8
# !/usr/bin/python3
# Name:         mixinQueue
# Copyright:    (c) 2019 TK
# Licence:      MIT
# -------------------------------------------------------------------------------
import logging
logger = logging.getLogger('mixin')

import queue
import asyncio

# ===============================================================================
class mixinQueue(object):
    QUEUE_PUT_TIMEOUT = 0.2
    QUEUE_GET_TIMEOUT = 0.2
# -------------------------------------------------------------------------------
    def queue_put(self, *,
        outqueue,
        data
    ):
        if outqueue and data:
            try:
                outqueue.put(data, True, self.QUEUE_PUT_TIMEOUT)
                return True
            except queue.Full:
                logger.warning(f'queue full')
                pass
            except Exception:
                logger.exception(f'*** exception')
                pass
        return False

# -------------------------------------------------------------------------------
    def queue_get(self, *,
        inqueue
    ):
        if inqueue:
            try:
                l_data = inqueue.get(True, self.QUEUE_GET_TIMEOUT)
                return l_data
            except (queue.Empty, EOFError):
                pass
            except Exception:
                logger.exception(f'*** exception')
                pass
        return None

# ===============================================================================
class mixinAioQueue(object):
# -------------------------------------------------------------------------------
    async def queue_put(self, *,
        outqueue,
        data
    ):
        if outqueue and data:
            try:
                await outqueue.put(data)
                return True
            except asyncio.QueueFull:
                logger.warning(f'queue full')
                # remove oldest entry
                await outqueue.get()
                await self.queue_put(outqueue=outqueue, data=data)
            except GeneratorExit:
                logger.error(f'GeneratorExit')
                raise
            except Exception:
                logger.exception(f'*** exception')
        return False

# -------------------------------------------------------------------------------
    async def queue_get(self, *,
        inqueue
    ):
        if inqueue:
            try:
                return await inqueue.get()
            # except asyncio.QueueEmpty:
            #     logger.warning(f'queue empty')
            except GeneratorExit:
                logger.error(f'GeneratorExit')
                raise
            except asyncio.CancelledError:
                logger.warning(f'CancelledError')
                raise
            except:
                logger.exception(f'*** exception')
        return None        