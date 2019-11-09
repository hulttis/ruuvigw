# coding=utf-8
# -------------------------------------------------------------------------------
# Name:        config.py
# Purpose:     configuration file (json) reader
#
# Author:      Timo Koponen
#
# Created:     09/02/2019
# Copyright:   (c) t 2017
# Licence:     <your licence>
#
# implement _print_config() if _print_default() output is not enought
# -------------------------------------------------------------------------------
import logging
logger = logging.getLogger(__name__)

import os.path
import uuid
import json
import socket
import defaults as _def

class config_reader(object):
# -------------------------------------------------------------------------------
    def __init__(self, *, 
        configfile
    ):
        super().__init__()

        self._cfg = {}

        try:
            self._cfg = self._readjson(configfile=configfile.strip())
            return
        except json.JSONDecodeError:
            raise
        except (Exception):
            logger.exception(f'*** invalid json file:{configfile}')
            raise
        logger.error(f'*** invalid configuration file: {configfile}')

# -------------------------------------------------------------------------------
    def get_cfg(self, *, 
        section
    ):
        try:
            return self._cfg[section]
        except:
            return None

# ------------------------------------------------------------------------------
    def _readjson(self, *, 
        configfile
    ):
        try:
            with open(configfile) as l_jsonfile:
                l_json = json.load(l_jsonfile)
            l_cfg = l_json
            return (l_cfg)
        except json.JSONDecodeError as l_e:
            logger.critical(f'*** JSONDecodeError msg:{l_e.msg} line:{l_e.lineno}')
            raise
        except Exception:
            logger.exception(f'*** Failed to read json file:{configfile}')
            raise

        return ({})

# ------------------------------------------------------------------------------
    def print(self):

        try:
            self._print_config()
        except AttributeError:
            logger.exception(f'*** exception')
            self._print_default()
        except ValueError: 
            raise
        except Exception:
            logger.exception(f'*** exception')

# ------------------------------------------------------------------------------
    def _print_default(self):

        # dict
        for l_key, l_value in self._cfg.items():
            print('')
            self._print_item(key=l_key, value=l_value)

# ------------------------------------------------------------------------------
    def _print_item(self, *,
        key,
        value,
        indent=0
    ):
        l_txt = ''
        if isinstance(value, dict):
            if len(key):
                l_txt = ' '*indent + f'{key}'
                print(l_txt)
                print(' '*indent + '-'*(len(l_txt)-indent))
            for l_key, l_value in value.items():
                self._print_item(key=l_key, value=l_value, indent=indent+3)
        elif isinstance(value, list):
            for l_idx, l_item in enumerate(value):
                l_txt = ' '*indent + f'{key}[{l_idx}]'
                print(l_txt)
                print(' '*indent + '-'*(len(l_txt)-indent))
                self._print_item(key='', value=l_item, indent=indent)
                print('')
        else:
            if len(key):
                print(' '*indent + f'{key}: {value}')
            else:
                print(' '*indent + f'{value}')

# ------------------------------------------------------------------------------
    def _print_config(self):

        l_common = self.get_cfg(section='COMMON')
        if not l_common:
            print(f'[COMMON] default')
            self._cfg['COMMON'] = {}
            self._cfg['COMMON']['scheduler_max_instances'] = _def.COMMON_SCHEDULER_MAXINSTANCES
            self._cfg['COMMON']['nameservers'] = []
            l_common = self.get_cfg(section='COMMON')

        print ('')
        print ('COMMON')
        print ('-'*_def.SEPARATOR_LENGTH)
        l_hostname = l_common.get('hostname', _def.COMMON_HOSTNAME)
        if not l_hostname:
            l_hostname = socket.getfqdn().split('.', 1)[0]
            self._cfg['COMMON']['hostname'] = l_hostname
        print (f'hostname:            {l_hostname}')
        l_nameservers = l_common.get('nameservers', None)
        if l_nameservers:
            for l_idx, l_nameserver in enumerate(l_nameservers):
                print ('nameserver[{0:d}]:       {1:s}'.format(l_idx, l_nameserver))
        else:
             print ('nameserver:          using system dns server')
        print ('')

        l_unique = []
        l_influx_enabled = False
        l_influxs = self.get_cfg(section='INFLUX')
        if l_influxs:
            for l_influx in l_influxs:
                l_name = l_influx.get('name', None)
                if not l_name:
                    raise ValueError('influx name need to be defined')
                print (f'INFLUX: {l_name}')
                print ('-'*_def.SEPARATOR_LENGTH)
                if l_name in l_unique:
                    raise ValueError(f'influx/mqtt name need to be unique. check configuration for {l_name}')
                l_unique.append(l_name)
                l_enable = l_influx.get('enable', _def.INFLUX_ENABLE)
                print ('   enable:              {0:s}'.format(str(l_enable)))
                if l_enable:
                    l_influx_enabled = True
                    l_policy = l_influx.get('POLICY', _def.INFLUX_POLICY)
                    l_host = l_influx.get('host', None)
                    if not l_host:
                        raise ValueError(f'host is required. check configuration for {l_name}')
                    l_host += ':' + str(l_influx.get('port', _def.INFLUX_PORT))
                    print ('   host:                {0:s}'.format(l_host))
                    print ('   ssl:                 {0:s}'.format(str(l_influx.get('ssl', _def.INFLUX_SSL))))
                    print ('   ssl_verify:          {0:s}'.format(str(l_influx.get('ssl_verify', _def.INFLUX_SSL_VERIFY))))
                    print ('   database:            {0:s}'.format(l_influx.get('database', _def.INFLUX_DATABASE)))
                    print ('   username:            {0:s}'.format(l_influx.get('username', _def.INFLUX_USERNAME)))
                    print ('   POLICY:              {0:s}'.format(l_policy.get('name', None)))
                    print ('      default:          {0:s}'.format(str(l_policy.get('default', ''))))
                    print ('      alter:            {0:s}'.format(str(l_policy.get('alter', ''))))
                    print ('      duration:         {0:s}'.format(l_policy.get('duration', '')))
                    print ('      replication:      {0:d}'.format(l_policy.get('replication', '')))
                    print ('   workers:             {0:d}'.format(l_influx.get('workers', _def.INFLUX_WORKERS)))
                    # print ('   queue size:          {0:d}'.format(l_influx.get('queue_size', _def.INFLUX_QUEUE_SIZE)))
                    # print ('   super interval:      {0:.1f} s'.format(l_influx.get('supervision_interval', _def.INFLUX_SUPERVISION_INTERVAL)))
                    print ('   timeout:             {0:.1f}s'.format(l_influx.get('timeout', _def.INFLUX_TIMEOUT)))
                    print ('   retries:             {0:d}'.format(l_influx.get('retries', _def.INFLUX_RETRIES)))
                print ('')

        l_unique_clientid = []
        l_mqtt_enabled = False
        l_mqtts = self.get_cfg(section='MQTT')
        if l_mqtts:
            l_mqtt_cnt = 0
            for l_mqtt in l_mqtts:
                l_name = l_mqtt.get('name', None)
                if not l_name:
                    raise ValueError('mqtt name need to be defined')
                print (f'MQTT: {l_name}')
                print ('-'*_def.SEPARATOR_LENGTH)
                if l_name in l_unique:
                    raise ValueError(f'influx/mqtt name need to be unique')
                l_unique.append(l_name)
                l_enable = l_mqtt.get('enable', _def.MQTT_ENABLE)
                print ('   enable:              {0:s}'.format(str(l_enable)))
                if l_enable:
                    l_mqtt_enabled = True
                    l_client_id = l_mqtt.get('client_id', None)
                    if not l_client_id:
                        l_client_id = f'''{l_common['hostname']}-{str(uuid.uuid4())}'''
                        l_mqtt['client_id'] = l_client_id
                    print (f'   client id:           {l_client_id}')
                    if l_client_id in l_unique_clientid:
                        raise ValueError(f'client_id need to be unique. check configuration for {l_name}')
                    l_unique_clientid.append(l_client_id)
                    l_host = l_mqtt.get('host', None)
                    if not l_host:
                        raise ValueError(f'host is required. check configuration for {l_name}')
                    print ('   host:                {0:s}'.format(l_host))
                    l_topic = l_mqtt.get('topic', _def.MQTT_TOPIC)
                    if not l_topic:
                        raise ValueError(f'topic is required. check configuration for {l_name}')
                    print ('   topic:               {0:s}'.format(l_topic))
                    print ('   retain:              {0:s}'.format(str(l_mqtt.get('retain', _def.MQTT_RETAIN))))
                    l_adtopic = l_mqtt.get('adtopic', _def.MQTT_ADTOPIC)
                    if l_adtopic:
                        print (f'   adtopic:             {l_adtopic}')
                        print ('   adretain:            {0:s}'.format(str(l_mqtt.get('adretain', _def.MQTT_ADRETAIN))))
                    l_anntopic = l_mqtt.get('lwttopic', _def.MQTT_ANNTOPIC)
                    if l_anntopic:
                        print (f'   anntopic             {l_anntopic}')
                    print ('   lwt:                 {0:s}'.format(str(l_mqtt.get('lwt', _def.MQTT_LWT))))
                    l_lwttopic = l_mqtt.get('lwttopic', _def.MQTT_LWTTOPIC)
                    if not l_lwttopic:
                        l_lwttopic = f'{l_topic}/{l_hostname}/lwt'
                        l_mqtt['lwttopic'] = l_lwttopic
                    if l_mqtt.get('lwt', _def.MQTT_LWT):
                        print (f'   lwttopic             {l_lwttopic}')
                    if 'mqtts://' in l_host:
                        print ('   check_hostname:      {0:s}'.format(str(l_mqtt.get('check_hostname', _def.MQTT_CHECK_HOSTNAME))))
                        l_cafile = l_mqtt.get('cafile', _def.MQTT_CAFILE)
                        if l_cafile:
                            print (f'   cafile:              {l_cafile}')
                            if not os.path.exists(l_cafile):
                                raise ValueError(f'''mqtts used but cafile doesn't exist. check configuration for {l_name}''')
                        else:
                            raise ValueError(f'''mqtts used but cafile is NOT defined. check configuration for {l_name}''')
                    # if l_mqtt.get('capath', _def.MQTT_CAPATH):
                    #     print ('   capath:              {0:s}'.format(l_mqtt.get('capath', _def.MQTT_CAPATH)))
                    # if l_mqtt.get('cadata', _def.MQTT_CADATA):
                    #     print ('   cadata:              {0:s}'.format(l_mqtt.get('cadata', _def.MQTT_CADATA)))
                    print ('   QOS:                 {0:d}'.format(l_mqtt.get('qos', _def.MQTT_QOS)))
                    print ('   timeout:             {0:.1f} s'.format(l_mqtt.get('timeout', _def.MQTT_TIMEOUT)))
                    print ('   retries:             {0:d}'.format(l_mqtt.get('retries', _def.MQTT_RETRIES)))
                    # print ('   queue size:          {0:d}'.format(l_mqtt.get('queue_size', _def.MQTT_QUEUE_SIZE)))
                    # LWT
                    # self._print_queue(cfg=l_mqtt)
                    l_mqtt_cnt += 1
                print ('')

        if not l_influxs and not l_mqtts:
            raise ValueError(f'[INFLUX] and [MQTT] configuration missing (one of them needed)')
        if not l_influx_enabled and not l_mqtt_enabled:
            raise ValueError(f'[INFLUX] and [MQTT] all disabled (one of them needed)')

        l_ruuvitag = self.get_cfg(section='RUUVITAG')
        if l_ruuvitag:
            print ('RUUVITAG: {0}'.format(l_ruuvitag.get('name', _def.RUUVITAG_NAME)))
            print ('-'*_def.SEPARATOR_LENGTH)
            print ('ruuvi name:          {0:s}'.format(l_ruuvitag.get('ruuviname', _def.RUUVITAG_RUUVINAME)))
            # print ('time format:         {0:s}'.format(l_ruuvitag.get('timefmt', _def.RUUVITAG_TIMEFMT)))
            print ('sample interval:     {0:d} ms'.format(l_ruuvitag.get('sample_interval', _def.RUUVITAG_SAMPLE_INTERVAL)))
            print ('device timeout:      {0:d} ms'.format(l_ruuvitag.get('device_timeout', _def.RUUVITAG_DEVICE_TIMEOUT)))
            print ('do calculations:     {0:s}'.format(str(l_ruuvitag.get('calc', _def.RUUVITAG_CALC))))
            # print ('calc in datas:       {0:s}'.format(str(l_ruuvitag.get('calc_in_datas', _def.RUUVITAG_CALC_IN_DATAS))))
            print ('use sudo:            {0:s}'.format(str(l_ruuvitag.get('sudo', _def.RUUVITAG_SUDO))))
            # print ('restart ble device:  {0:s}'.format(str(l_ruuvitag.get('device_reset', _def.RUUVITAG_DEVICE_RESET))))
            print ('whtlist from tags:   {0:s}'.format(str(l_ruuvitag.get('whtlist_from_tags', _def.RUUVITAG_WHTLIST_FROM_TAGS))))
            # self._print_queue(cfg=l_ruuvitag, indent='')
            print ('')

            l_tags = l_ruuvitag.get('TAGS')
            if l_tags:
                print ('TAG MAC              TAG NAME')
                print ('-'*(_def.SEPARATOR_LENGTH))
                for l_key in l_tags:
                    print('{0:20s} {1}'.format(l_key, l_tags[l_key]))
                print ('')

            l_from_tags = ''
            l_macs = l_ruuvitag.get('WHTLIST', None)
            if not l_macs:
                if l_tags:
                    l_macs = l_tags.keys()
                    l_from_tags = ' (FROM TAGS)'
            if l_macs:
                print ('WHTLIST MAC{0}'.format(l_from_tags))
                print ('-'*(_def.SEPARATOR_LENGTH))
                for l_item in l_macs:
                    print ('{0}'.format(l_item))
                print ('')
            l_macs = l_ruuvitag.get('BLKLIST', None)
            if l_macs:
                print ('BLKLIST MAC')
                print ('-'*(_def.SEPARATOR_LENGTH))
                for l_item in l_macs:
                    print ('{0}'.format(l_item))
                print ('')
            # l_minmax = l_ruuvitag.get('MINMAX', _def.RUUVITAG_MINMAX)
            # if l_minmax:
            #     print ('MINMAX                 MIN      MAX')
            #     print ('-'*(_def.SEPARATOR_LENGTH))
            #     for l_key in l_minmax:
            #         print ('{0:17s} {1:8.1f} {2:8.1f}'.format(l_key, l_minmax[l_key]['min'], l_minmax[l_key]['max']))
            #     print ('')
        else:
            raise ValueError(f'[RUUVITAG] configuration missing')

        l_ruuvi = self.get_cfg(section='RUUVI')
        if l_ruuvi:
            print ('RUUVI: {0}'.format(l_ruuvi.get('name', _def.RUUVI_NAME)))
            print ('-'*_def.SEPARATOR_LENGTH)
            # print ('time format:         {0:s}'.format(l_ruuvi.get('timefmt', _def.RUUVI_TIMEFMT)))
            print ('max interval:        {0:d} s'.format(l_ruuvi.get('max_interval', _def.RUUVI_MAX_INTERVAL)))
            # print ('write lastdata int:  {0:d} s'.format(l_ruuvi.get('write_lastdata_int', _def.RUUVI_WRITE_LASTDATA_INT)))
            # print ('write lastdata cnt:  {0:d}'.format(l_ruuvi.get('write_lastdata_cnt', _def.RUUVI_WRITE_LASTDATA_CNT)))
            
            # self._print_queue(cfg=l_ruuvi, indent='')
            print ('')
            
            for l_meas in l_ruuvi.get('MEASUREMENTS'):
                print ('MEASUREMENT: {0}'.format(l_meas.get('name', _def.RUUVI_NAME)))
                print ('-'*_def.SEPARATOR_LENGTH)
                print ('   include calcs     {0:s}'.format(str(l_meas.get('calcs', _def.RUUVI_CALCS))))
                print ('   include debugs    {0:s}'.format(str(l_meas.get('debug', _def.RUUVI_DEBUG))))
                print ()
                l_outputs = l_meas.get('OUTPUT', _def.RUUVI_OUTPUT)
                if l_outputs:
                    print ('   OUTPUT                    TYPE       STATUS')
                    print ('   '+'-'*(_def.SEPARATOR_LENGTH-3))
                    for l_item in l_outputs:
                        l_status = '(n/a)'
                        l_type = '(n/a)'
                        l_i = self._find_influx(name=l_item)
                        if not l_i:
                            l_i = self._find_mqtt(name=l_item)
                            if l_i:
                                l_type = 'mqtt'
                                if l_i.get('enable', _def.INFLUX_ENABLE):
                                    l_status = 'enabled'
                                else:
                                    l_status = 'disabled'
                        else:
                            l_type = 'influx'
                            if l_i.get('enable', _def.INFLUX_ENABLE):
                                l_status = 'enabled'
                            else:
                                l_status = 'disabled'
                        print ('   {0:25s} {1:10s} {2}'.format(l_item, l_type, l_status))
                    print ('')            

                l_round = l_meas.get('ROUND', _def.RUUVI_ROUND)
                l_fields = l_meas.get('FIELDS', None)
                if l_fields:
                    print ('   RUUVITAG FIELD NAME       INFLUXDB FIELD NAME           PRECISION')
                    print ('   '+'-'*(_def.SEPARATOR_LENGTH-3))
                    for l_key in l_fields:
                        print('   {0:25s} {1:30s}'.format(l_key, l_fields[l_key]), end='')
                        l_precision = l_round.get(l_key, _def.RUUVI_PRECISION)
                        if l_precision:
                            print(f'{l_precision}')
                        else:
                            print('')
                    print ('')

                l_delta = l_meas.get('DELTA', _def.RUUVI_DELTA)
                if l_delta:
                    print ('   FIELD NAME                DELTA')
                    print ('   '+'-'*(_def.SEPARATOR_LENGTH-3))
                    for l_key in l_delta:
                        print('   {0:25s} {1}'.format(l_key, l_delta[l_key]))
                    print ('')

                l_maxdelta = l_meas.get('MAXDELTA', _def.RUUVI_MAXDELTA)
                if l_maxdelta:
                    print ('   FIELD NAME                MAXCHANGE  MAXCOUNT')
                    print ('   '+'-'*(_def.SEPARATOR_LENGTH-3))
                    for l_key in l_maxdelta:
                        print('   {0:25s} {1:<10.1f} {2}'.format(l_key, l_maxdelta[l_key]['maxchange'], l_maxdelta[l_key]['maxcount']))
                    print ('')
        else:
            raise ValueError(f'[RUUVI] configuration missing')

# ------------------------------------------------------------------------------
    def _find_influx(self, *, name):
        l_influxs = self.get_cfg(section='INFLUX')
        if l_influxs:
            for l_influx in l_influxs:
                if l_influx.get('name', None) == name:
                    return l_influx
        return None

# ------------------------------------------------------------------------------
    def _find_mqtt(self, *, name):
        l_mqtts = self.get_cfg(section='MQTT')
        if l_mqtts:
            for l_mqtt in l_mqtts:
                if l_mqtt.get('name', None) == name:
                    return l_mqtt
        return None

# ------------------------------------------------------------------------------
    # def _print_queue(self, *, cfg, indent='   '):
    #     l_q = cfg.get('QUEUE', _def.QUEUE_DEFAULT)
    #     print ('{0:s}QUEUE'.format(indent))
    #     print ('{0:s}   max size:         {1:d}'.format(indent, l_q.get('max_size')))
    #     print ('{0:s}   remove oldest:    {1:s}'.format(indent, str(l_q.get('remove_oldest_if_full'))))
    #     print ('{0:s}   rebuffering:      {1:s}'.format(indent, str(l_q.get('rebuffer'))))

