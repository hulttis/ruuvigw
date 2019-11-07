# coding=utf-8
#-------------------------------------------------------------------------------
# Name:        ruuvi_client.py
# Purpose:     ruuvi ble
#
# Author:      Timo Koponen
#
# Created:     09/02/2019
# modified:    09/02/2019
# Copyright:   (c) 2017
# Licence:     <your licence>
#-------------------------------------------------------------------------------
import logging
logger = logging.getLogger(__name__)

import asyncio

import time
import json
from datetime import datetime as _dt
from datetime import timedelta
from collections import defaultdict

from mixinQueue import mixinAioQueue as _mixinQueue
from mixinSchedulerEvent import mixinSchedulerEvent
from aioruuvitag.ruuvitag_calc import ruuvitag_calc as _tagcalc
import defaults as _def

#===============================================================================
class ruuvi_aioclient(_mixinQueue, mixinSchedulerEvent):
    QUEUE_PUT_TIMEOUT = 0.2
    _lastdata = defaultdict(dict)
    _cnt = defaultdict(dict)
    _func = 'execute_ruuvi'

#-------------------------------------------------------------------------------
    def __init__(self, *,
        cfg,
        hostname,
        outqueues,
        inqueue,
        loop,
        scheduler
    ):
        super().__init__()

        if not cfg:
           logger.error('cfg is None')
           raise ValueError('cfg cannot be None')

        self._name = cfg.get('name', _def.RUUVI_NAME)
        logger.debug(f'{self._name } enter')
        self._cfg = cfg
        self._max_interval = int(cfg.get('max_interval', _def.RUUVI_MAX_INTERVAL))
        self._write_lastdata_int = int(self._cfg.get('write_lastdata_int', _def.RUUVI_WRITE_LASTDATA_INT))
        self._write_lastdata_cnt = int(self._cfg.get('write_lastdata_cnt', _def.RUUVI_WRITE_LASTDATA_CNT))
        if self._write_lastdata_int:
            self._write_lastdata_int = max(self._write_lastdata_int, (self._max_interval+_def.RUUVI_WRITE_LASTDATA_DIFF))
            logger.info(f'{self._name} write_lastdata_int:{int(self._write_lastdata_int)}s')
            if self._write_lastdata_cnt:
                logger.info(f'{self._name} write_lastdata_cnt:{int(self._write_lastdata_cnt)}')
            else:
                logger.info(f'{self._name} write_lastdata_cnt unlimited')
        else:
            logger.info(f'{self._name} write lastdata disabled')

        self._meas = cfg.get('MEASUREMENTS', [])
        logger.debug(f'{self._name} measurements:{self._meas}')

        self._outqueues = outqueues
        self._inqueue = inqueue
        
        self._loop = loop
        self._stop_event = asyncio.Event(loop=loop)
        self._lastdata_lock = asyncio.Lock(loop=loop)
        self._scheduler = scheduler
        self._schedule(scheduler=scheduler)
        self._hostname = hostname
        logger.debug(f'{self._name} exit')

#-------------------------------------------------------------------------------
    def shutdown(self):
        logger.warning(f'{self._name}')
        self._stop_event.set()

#-------------------------------------------------------------------------------
    def _schedule(self, *, scheduler):
        logger.info(f'{self._name} enter {type(scheduler)}')

        if self._write_lastdata_int:
            try:
                l_jobid = f'{self._name}_lastdata'
                scheduler.add_job(
                    self._check_lastdata,
                    'interval',
                    seconds = 1,
                    id = l_jobid,
                    replace_existing = True,
                    max_instances = 1,
                    coalesce = True,
                    next_run_time = _dt.now()+timedelta(seconds=_def.RUUVI_WRITE_LASTDATA_DELAY)
                )
                logger.info(f'{self._name} {l_jobid} scheduled')
            except:
                logger.exception(f'*** {self._name}')

#-------------------------------------------------------------------------------
    async def run(self):
        logger.info(f'{self._name} enter hostname:{self._hostname}')

        l_json = None
        if self._inqueue:
            while not self._stop_event.is_set():
                try:
                    l_json = await self.queue_get(inqueue=self._inqueue)
                    await self._handle_data(indata=l_json)
                except asyncio.CancelledError:
                    logger.warning(f'{self._name} CanceledError')
                except GeneratorExit:
                    logger.error(f'GeneratorExit')
                except Exception:
                    logger.exception(f'*** {self._name}')
                    continue
        else:
            logger.critical(f'{self._name} FAILED TO START. NO QUEUE')

        for l_mea in self._cnt:
            for l_mac in self._cnt[l_mea]:
                logger.info(f'{self._name} {l_mea} {l_mac} cnt:{self._cnt[l_mea][l_mac]}')

        logger.warning(f'{self._name} exit')
        return True

#-------------------------------------------------------------------------------
    def _update_cnt(self, *, measurname, mac):
        try:
            l_cnt = self._cnt[measurname][mac]
        except:
            l_cnt = 0
        self._cnt[measurname][mac] = (l_cnt + 1)
        return l_cnt

#-------------------------------------------------------------------------------
    # xcnt ... how many lastdata updates
    # ycnt ... how many denied updates because of maxdelta 
    async def _update_lastdata(self, *, measur, mac, xtime, datas, reason, xcnt=0, ycnt=0):
        async with self._lastdata_lock:
            l_measurname = measur.get('name', _def.RUUVI_NAME)
            self._lastdata[l_measurname][mac] = (xtime, datas, measur, reason, xcnt, ycnt)
            # logger.debug(f'{self._name} {l_measurname} {mac} lastdata:{self._lastdata}')

#-------------------------------------------------------------------------------
    async def _remove_lastdata(self, *, measur, mac):
        async with self._lastdata_lock:
            l_measurname = measur.get('name', _def.RUUVI_NAME)
            try:
                del self._lastdata[l_measurname][mac]
            except:
                pass

#-------------------------------------------------------------------------------
    async def _get_lastdata(self, *, measur, mac):
        async with self._lastdata_lock:
            l_measurname = measur.get('name', _def.RUUVI_NAME)
            try:
                return self._lastdata[l_measurname][mac]
            except:
                pass
        return (None, None, None, None, None, None)

#-------------------------------------------------------------------------------
    async def _get_lastdata_items(self):
        async with self._lastdata_lock:
            return self._lastdata.items()

#-------------------------------------------------------------------------------
    async def _check_lastdata(self):
        """
        scheduled task
        """
        l_now = time.time()
        logger.debug(f'{self._name}')

        if self._write_lastdata_int:
            try:
                for l_measurname, l_tmp_measurdata in await self._get_lastdata_items():
                    # logger.debug(f'{self._name} measur:{l_measurname} data:{l_measurdata}')
                    l_measurdata = {**l_tmp_measurdata}
                    for l_mac, l_macdata in l_measurdata.items():
                        # logger.debug(f'{self._name} mac:{l_mac} data:{l_macdata}')
                        (l_lasttime, l_datas, l_measur, _, l_xcnt, _) = l_macdata
                        l_tagname = l_datas['tagname']
                        if abs(l_now-l_lasttime) > self._write_lastdata_int:
                            if not self._write_lastdata_cnt or l_xcnt < self._write_lastdata_cnt:
                                # if write_lastdata_cnt forver or l_xcnt < write_lastdata_cnt 
                                if 'time' in l_datas: # delete time from datas - will be set to utcnow byt _get_json
                                    del l_datas['time'] 
                                l_fdata = json.dumps({
                                    'func': self._func,
                                    'jobid': f'{l_measurname}_lastdata',
                                    'json': await self._get_json(measur=l_measur, mac=l_mac, datas=l_datas, reason='lastdata:'+str(l_xcnt), lasttime=l_lasttime)
                                })
                                await self._update_lastdata(measur=l_measur, mac=l_mac, xtime=(l_lasttime + self._write_lastdata_int), datas=l_datas, reason='lastdata', xcnt=(l_xcnt+1)) # ycnt=0
                                await self._queue_output(measur=l_measur, datas=l_fdata)
                                logger.info(f'{self._name} {l_measurname} {l_mac} {l_tagname} cnt:{l_xcnt}')
                                logger.debug(f'{self._name} {l_measurname} {l_mac} {l_tagname} data:{l_fdata}')
                            elif self._write_lastdata_cnt and l_xcnt >= self._write_lastdata_cnt:
                                await self._remove_lastdata(measur=l_measur, mac=l_mac) 
                                logger.info(f'{self._name} {l_measurname} {l_mac} {l_tagname} write_lastdata_cnt:{self._write_lastdata_cnt} reached')
            except Exception:
                logger.exception(f'*** {self._name}')
            
#-------------------------------------------------------------------------------
    async def _check_delta(self, *, measur, mac, datas, field, delta):
        l_measurname = measur.get('name', _def.RUUVI_NAME)
        l_tagname = datas['tagname']

        try:
            l_newvalue = datas.get(field, None)
            (_, l_olddata, _, _, _, _) = await self._get_lastdata(measur=measur, mac=mac)
            if l_olddata:
                l_oldvalue = l_olddata.get(field, None)
                if l_newvalue and l_oldvalue:
                    if abs(l_newvalue - l_oldvalue) < delta:
                        return False
                    else:
                        logger.info(f'{self._name} {l_measurname} {mac} {l_tagname:20s} {field:17s} old:{l_oldvalue:.2f} new:{l_newvalue:.2f} diff:{abs(l_newvalue-l_oldvalue):.2f} delta:{delta:.2f}')
        except:
            logger.exception(f'*** {self._name}')

        return True

#-------------------------------------------------------------------------------
    async def _check_maxdelta(self, *, measur, mac, datas, field, maxdelta):
        l_measurname = measur.get('name', _def.RUUVI_NAME)
        l_tagname = datas['tagname']

        l_maxchange = maxdelta.get('maxchange', None)
        l_maxcount = maxdelta.get('maxcount', None)
        if not l_maxchange or not l_maxcount:
            return True
            
        try:
            l_newvalue = datas.get(field, None)
            (_, l_olddata, _, _, _, l_ycnt) = await self._get_lastdata(measur=measur, mac=mac)
            l_oldvalue = l_olddata.get(field, None)
            if l_newvalue and l_oldvalue:
                if abs(l_newvalue-l_oldvalue) > l_maxchange:
                    # value is changed more than maxchange
                    logger.debug(f'{self._name} {l_measurname} {mac} {l_tagname:20s} {field:17s} old:{l_oldvalue:.2f} new:{l_newvalue:.2f} diff:{abs(l_newvalue-l_oldvalue):.2f} maxchange:{l_maxchange:.2f} maxcount:{l_maxcount} ycnt:{l_ycnt}')
                    # Value has been > maxchange less than count times
                    if (l_ycnt < l_maxcount):
                        return False
        except:
            logger.exception(f'*** {self._name}')

        return True

#-------------------------------------------------------------------------------
    async def _is_diff(self, *, measur, mac, datas):
        l_now = time.time()
        l_measurname = measur.get('name', _def.RUUVI_NAME)
        l_tagname = datas['tagname']

        try:
            (l_lasttime, _, _, _, l_xcnt, l_ycnt) = await self._get_lastdata(measur=measur, mac=mac)
            if not l_lasttime:
                await self._update_lastdata(measur=measur, mac=mac, xtime=l_now, datas=datas, reason='first') # xcnt=0 ycnt=0
                return (True, 'first', 0)

            # check if max_interval has been passed
            if abs(l_now - l_lasttime) > self._max_interval:
                logger.debug(f'{self._name} {l_measurname} {mac} {l_tagname} max interval {self._max_interval}s passed')
                l_xtime = l_lasttime + self._max_interval
                if (l_xtime + self._max_interval) < l_now:
                    l_xtime = l_now
                    logger.debug(f'{self._name} {l_measurname} {mac} {l_tagname} lasttime adjusted now:{l_now}')
                await self._update_lastdata(measur=measur, mac=mac, xtime=l_xtime, datas=datas, reason='max_interval') # xcnt=0 ycnt=0
                return (True, 'max_interval', l_lasttime)

            # check maxdelta (maximum allowed value change)
            for l_field, l_maxdelta in measur.get('MAXDELTA', _def.RUUVI_MAXDELTA).items():
                if not await self._check_maxdelta(measur=measur, mac=mac, datas=datas, field=l_field, maxdelta=l_maxdelta):
                    await self._update_lastdata(measur=measur, mac=mac, xtime=l_now, datas=datas, reason='max_delta '+l_field, xcnt=l_xcnt, ycnt=(l_ycnt+1))
                    return (False, None, 0)

            # check delta (minimum change to trigger database update)
            for l_field, l_delta in measur.get('DELTA', _def.RUUVI_DELTA).items():
                if not await self._check_delta(measur=measur, mac=mac, datas=datas, field=l_field, delta=l_delta):
                    return (False, None, 0)

            await self._update_lastdata(measur=measur, mac=mac, xtime=l_now, datas=datas, reason=l_field) # xcnt=0 ycnt=0
            return (True, l_field, l_lasttime)
                
        except:
            logger.exception(f'*** {self._name}')

        return (False, None, 0)

#-------------------------------------------------------------------------------
    def _field_value(self, *, measur, field, datas):
        try:
            l_precision = measur['ROUND'][field] 
            # print(f'precision found: {field} {l_precision}')
        except:
            # print(f'precision not found: {field}')
            l_precision = _def.RUUVI_PRECISION
        try:
            return round(datas[field], l_precision)
        except:
            return None

#-------------------------------------------------------------------------------
    async def _get_fields(self, *, measur, mac, datas):
        # logger.debug(f'{self._name}')
        if not datas:
            return None

        l_measurname = measur.get('name', _def.RUUVI_NAME)
        l_tagname = datas['tagname']

        logger.debug(f'{self._name} {l_measurname} {mac} {l_tagname}')

        l_fields = {}
        l_meafields = measur.get('FIELDS', None)
        if l_meafields:
            for l_field in l_meafields:
                l_value = self._field_value(measur=measur, field=l_field, datas=datas)
                if l_value:
                    l_fields[l_meafields[l_field]] = l_value
        else:
            for l_field in datas:
                if datas[l_field]:
                    l_fields[l_field] = datas[l_field]

        if len(l_fields):
            l_fields['time'] = datas['time'] if ('time' in datas) else _dt.utcnow().strftime(_def.RUUVI_TIMEFMT)
        else:
            logger.warning(f'{self._name} {l_measurname} {mac} {l_tagname} fields empty')

        logger.debug(f'{self._name} {l_measurname} {mac} {l_tagname} fields:{l_fields}')
        return (l_fields)

#-------------------------------------------------------------------------------
    async def _get_debugs(self, *, measur, mac, reason, datas, tagdatas=None, lasttime=0):
        # logger.debug(f'{self._name}')

        try:
            l_measurname = measur.get('name', _def.RUUVI_NAME)
            l_tagname = datas['tagname']
            l_now = time.time()
            logger.debug(f'{self._name} {l_measurname} {mac} {l_tagname} {lasttime} {l_now}')
            l_debugs = {}
            if measur.get('debug', _def.RUUVI_DEBUG):
                l_debugs['debugReason']                     = reason
                l_debugs['debugCount']                      = int(self._update_cnt(measurname=l_measurname, mac=mac))
                l_debugs['debugInterval']                   = int((l_now-lasttime)*1000000) if ((lasttime<l_now) and lasttime) else 0 # us
                # l_debugs['debugHost']                       = self._cfg.get('hostname', _def.RUUVI_HOSTNAME)
                if tagdatas:
                    l_debugs['debugTagCount']               = int(tagdatas['count'])
                    l_debugs['debugTagInterval']            = int(tagdatas['interval'])      # us
                    l_debugs['debugTagElapsed']             = int(tagdatas['elapsed'])       # us
                    l_debugs['debugTagRecvTime']            = int(tagdatas['recvtime'])      # us

            logger.debug(f'{self._name} {l_measurname} {mac} {l_tagname} debugs:{l_debugs}')
            return l_debugs
        except:
            logger.exception(f'*** {self._name}')
        return {}

#-------------------------------------------------------------------------------
    async def _get_calcs(self, *, measur, mac, datas):
        # logger.debug(f'{self._name}')

        try:
            l_measurname = measur.get('name', _def.RUUVI_NAME)
            l_tagname = datas['tagname']
            # logger.debug(f'{self._name} {l_measurname} {mac} {l_tagname}')
            l_calcs = {}
            if measur.get('calcs', _def.RUUVI_CALCS):
                _tagcalc.calc(datas=datas, out=l_calcs)

            logger.debug(f'{self._name} {l_measurname} {mac} {l_tagname} calcs:{l_calcs}')
            return l_calcs
        except:
            logger.exception(f'*** {self._name}')

        return {}
#-------------------------------------------------------------------------------
    async def _get_json(self, *, measur, mac, datas, reason, tagdatas=None, lasttime=0):
        # logger.debug(f'{self._name}')
        if not datas:
            return None

        l_measurname = measur.get('name', _def.RUUVI_NAME)
        l_tagname = datas['tagname']

        # logger.debug(f'{self._name} {l_measurname} {mac} {l_tagname}')

        l_fields = await self._get_fields(measur=measur, mac=mac, datas=datas)
        if not l_fields:
            logger.debug(f'{self._name} {l_measurname} {mac} {l_tagname} fields empty')
            return None

        l_debugs = await self._get_debugs(measur=measur, mac=mac, reason=reason, datas=datas, tagdatas=tagdatas, lasttime=lasttime)
        if l_debugs:
            l_fields = {**l_fields, **l_debugs}
        l_calcs = await self._get_calcs(measur=measur, mac=mac, datas=datas)
        if l_calcs:
            l_fields = {**l_fields, **l_calcs}

        l_json = [
            {
                "measurement": measur.get('name', _def.RUUVI_NAME),
                "tags": {
                    "mac": mac,
                    "name": l_tagname,
                    "dataFormat": str(self._field_value(measur=measur, field='_df', datas=datas)),
                    "hostname": self._hostname
                },
                "fields": l_fields
            }
        ]

        logger.debug(f'{self._name} {l_measurname} {mac} {l_tagname} json:{l_json}')
        return l_json

#-------------------------------------------------------------------------------
    async def _handle_data(self, *, indata):
        logger.debug(f'{self._name} {type(indata)} indata:{indata}')
        if not indata or not len(indata):
            return

        try:
            l_dict = json.loads(indata)
            l_mac = l_dict['mac']
            l_datas = l_dict['datas']
            l_tagdatas = l_dict.get('_aioruuvitag', None)
            l_tagname = l_datas['tagname']
            for l_measur in self._meas:
                l_measurname = l_measur.get('name', _def.RUUVI_NAME)
                logger.debug(f'{self._name} {l_measurname} {l_mac} {l_tagname} datas:{l_datas}')
                (l_status, l_reason, l_lasttime) = await self._is_diff(measur=l_measur, mac=l_mac, datas=l_datas)
                if l_status:
                    l_fdata = {
                        'func': self._func,
                        'jobid': l_measurname,
                        'json': await self._get_json(measur=l_measur, mac=l_mac, datas=l_datas, reason=l_reason, tagdatas=l_tagdatas, lasttime=l_lasttime)
                    }
                    await self._queue_output(measur=l_measur, datas=l_fdata)
                    logger.debug(f'{self._name} {l_measurname} {l_mac} {l_tagname} fdata:{l_fdata}')
                # else:
                #     logger.debug(f'{self._name} {l_measurname} {l_mac} {l_tagname} data ignored')
        except:
            logger.exception(f'*** {self._name}')

#-------------------------------------------------------------------------------
    async def _queue_output(self, *, measur, datas):
        try:
            if self._outqueues:
                if isinstance(self._outqueues, dict):
                    for l_out in measur.get('OUTPUT', []):
                        l_outqueue = self._outqueues.get(l_out, None)
                        if l_outqueue:
                            # print(f'out:{l_out} {l_outqueue}')
                            if not await self.queue_put(outqueue=l_outqueue, data=datas):
                                return False
                    return True
                else:
                    return await self.queue_put(outqueue=self._outqueues, data=datas)
        except:
            logger.exception(f'*** {self._name}')

        return False

