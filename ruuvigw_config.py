# coding=utf-8
# -------------------------------------------------------------------------------
# Name:        config.py
# Purpose:     configuration file (json) reader
# Copyright:   (c) 2019 TK
# Licence:     MIT
# -------------------------------------------------------------------------------
import logging
logger = logging.getLogger('config')

import sys
import os.path
import platform
import json
import copy
import socket
from string import Template

import ruuvigw_defaults as _def
from urllib.parse import urlparse, urlunparse

class config_reader(object):
# -------------------------------------------------------------------------------
    def __init__(self, *,
        configfile
    ):
        super().__init__()

        self._cfg = {}

        try:
            l_cfg = self._readjson(configfile=configfile.strip())
            self._cfg = self._check_config(cfg=l_cfg)
            return
        except json.JSONDecodeError:
            raise
        except ValueError as l_e:
            raise l_e
        except Exception as l_e:
            logger.exception(f'*** invalid json file:{configfile}')
            raise l_e

# -------------------------------------------------------------------------------
    def get_cfg(self, *,
        section
    ):
        try:
            return self._cfg[section]
        except:
            return None
        return None

# ------------------------------------------------------------------------------
    def _readjson(self, *,
        configfile
    ):
        try:
            with open(configfile) as l_jsonfile:
                l_json = json.load(l_jsonfile)
            l_cfg = l_json
            return l_cfg
        except json.JSONDecodeError as l_e:
            logger.critical(f'*** JSONDecodeError msg:{l_e.msg} line:{l_e.lineno}')
            raise
        except Exception:
            logger.exception(f'*** Failed to read json file:{configfile}')
            raise

        return {}

# ------------------------------------------------------------------------------
    def _check_config(self, *, cfg):

        l_cfg = copy.deepcopy(cfg)

        try:
            l_cfg[_def.KEY_COMMON] = self._check_common(cfg=l_cfg)
            l_unique_name = []
            (l_cfg[_def.KEY_INFLUX], l_influx_enabled, l_unique_name) = self._check_influx(cfg=l_cfg, unique_name=l_unique_name)
            (l_cfg[_def.KEY_MQTT], l_mqtt_enabled, l_unique_name) = self._check_mqtt(cfg=l_cfg, unique_name=l_unique_name)
            (l_cfg[_def.KEY_KAFKA_PRODUCER], l_kafka_enabled, l_unique_name) = self._check_kafka_producer(cfg=l_cfg, unique_name=l_unique_name)
        except ValueError as l_e:
            raise l_e
        except Exception as l_e:
            print(f'*** exception: {l_e}')

        if not l_cfg[_def.KEY_INFLUX] and not l_cfg[_def.KEY_MQTT] and not l_cfg[_def.KEY_KAFKA_PRODUCER]:
            raise ValueError(f'one of [{_def.KEY_INFLUX}] and/or [{_def.KEY_MQTT}] and/or [{_def.KEY_KAFKA_PRODUCER}] configuration required')
        if not l_influx_enabled and not l_mqtt_enabled and not l_kafka_enabled:
            raise ValueError(f'one of [{_def.KEY_INFLUX}] and/or [{_def.KEY_MQTT}] and/or [{_def.KEY_KAFKA_PRODUCER}] must be enabled')

        # RUUVI
        l_ruuvi = l_cfg.get(_def.KEY_RUUVI, None)
        if not l_ruuvi:
            raise ValueError(f'[{_def.KEY_RUUVI}] configuration required')

        # RUUVITAG
        l_ruuvitag = l_cfg.get(_def.KEY_RUUVITAG, None)
        if not l_ruuvitag:
            raise ValueError(f'[{_def.KEY_RUUVITAG}] configuration required')

        return l_cfg

# ------------------------------------------------------------------------------
    def _check_common(self, *, cfg):

        # COMMON
        l_common = cfg.get(_def.KEY_COMMON, None)
        if not l_common:
            l_common = {}
        l_hostname = l_common.get('hostname', None)
        if not l_hostname:
            l_hostname = socket.getfqdn().split('.', 1)[0]
            l_common['hostname'] = l_hostname
            l_common['hostname_resolved'] = True

        # print(f'common:{l_common}')
        return l_common

# ------------------------------------------------------------------------------
    def _check_influx(self, *, cfg, unique_name):
        # INFLUX
        l_influx_enabled = False
        # l_common = cfg.get('COMMON', None)
        l_influxs = cfg.get(_def.KEY_INFLUX, None)
        if l_influxs:
            for l_idx, l_influx in enumerate(l_influxs):
                l_this_enabled = False
                if l_influx.get('enable', _def.INFLUX_ENABLE):
                    l_influx_enabled = True
                    l_this_enabled = True
                l_name = l_influx.get('name', None)
                if not l_name:
                    raise ValueError(f'[{_def.KEY_INFLUX}] name required idx:{l_idx}')
                if l_name in unique_name:
                    l_txt = f'{_def.KEY_INFLUX}/{_def.KEY_MQTT}/{_def.KEY_KAFKA_PRODUCER} name need to be unique:{l_name}'
                    if l_this_enabled:
                        raise ValueError(l_txt)
                    else:
                        print(f'*** {l_txt}')
                unique_name.append(l_name)
                if not l_influx.get('host', None):
                    raise ValueError(f'[{_def.KEY_INFLUX}] host required name:{l_name}')
                if not l_influx.get('database', None):
                    raise ValueError(f'[{_def.KEY_INFLUX}] database required name:{l_name}')

                l_policy = l_influx.get('POLICY', None)
                if not l_policy:
                    l_influx['POLICY'] = _def.INFLUX_POLICY

        # print(f'influxs:{l_influxs}')
        return (l_influxs, l_influx_enabled, unique_name)

# ------------------------------------------------------------------------------
    def _check_mqtt(self, *, cfg, unique_name):
        # MQTT
        l_mqtt_enabled = False
        l_common = cfg.get(_def.KEY_COMMON, None)
        l_mqtts = cfg.get(_def.KEY_MQTT, None)
        if l_mqtts:
            for l_idx, l_mqtt in enumerate(l_mqtts):
                l_this_enabled = False
                if l_mqtt.get('enable', _def.INFLUX_ENABLE):
                    l_mqtt_enabled = True
                    l_this_enabled = True
                l_name = l_mqtt.get('name', None)
                if not l_name:
                    l_txt = f'[{_def.KEY_MQTT}] name required idx:{l_idx}'
                    if l_this_enabled:
                        raise ValueError(l_txt)
                    else:
                        print(f'*** {l_txt}')
                if l_name in unique_name:
                    l_txt = f'{_def.KEY_INFLUX}/{_def.KEY_MQTT}/{_def.KEY_KAFKA_PRODUCER} name need to be unique:{l_name}'
                    if l_this_enabled:
                        raise ValueError(l_txt)
                    else:
                        print(f'*** {l_txt}')
                unique_name.append(l_name)
                l_client_id = l_mqtt.get('client_id', None)
                if not l_client_id:
                    l_client_id = f'''{l_common['hostname']}-{l_idx}'''
                    l_mqtt['client_id'] = l_client_id
                    l_mqtt['client_id_generated'] = True
                l_uri = l_mqtt.get('uri', None)

                l_host = None
                l_port = None
                l_ssl = False
                l_username = None
                l_password = None
                if l_uri:
                    l_uri_attr = urlparse(l_uri)
                    l_scheme = l_uri_attr.scheme
                    if l_scheme not in ('mqtts', 'mqtt'):
                        l_txt = f'unknown uri scheme {l_uri_attr.scheme} name:{l_name}'
                        if l_this_enabled:
                            raise ValueError(l_txt)
                        else:
                            print(f'*** {l_txt}')
                    l_host = l_uri_attr.hostname
                    l_port = l_uri_attr.port if l_uri_attr else l_mqtt.get('port', _def.MQTT_PORT)
                    l_ssl = l_mqtt.get('ssl', _def.MQTT_SSL)
                    if l_uri_attr.scheme == 'mqtts':
                        l_port = l_uri_attr.port if l_uri_attr else l_mqtt.get('port', _def.MQTT_SSLPORT)
                        l_ssl = True
                    if l_ssl:
                        l_scheme = 'mqtts'
                    else:
                        l_scheme = 'mqtt'
                    l_username = l_uri_attr.username if l_uri_attr.username else l_mqtt.get('username', _def.MQTT_USERNAME)
                    l_password = l_uri_attr.password if l_uri_attr.password else l_mqtt.get('password', _def.MQTT_PASSWORD)
                else:
                    l_host = l_mqtt.get('host', None)
                    l_port = l_mqtt.get('port', _def.MQTT_PORT)
                    l_ssl = l_mqtt.get('ssl', _def.MQTT_SSL)
                    if l_ssl:
                        l_port = l_mqtt.get('port', _def.MQTT_SSLPORT)
                    l_username = l_mqtt.get('username', _def.MQTT_USERNAME)
                    l_password = l_mqtt.get('password', _def.MQTT_PASSWORD)
                if not l_host:
                    l_txt = f'MQTT host (or complete uri) required name:{l_name}'
                    if l_this_enabled:
                        raise ValueError(l_txt)
                    else:
                        print(f'*** {l_txt}')
                l_mqtt['host'] = l_host
                l_mqtt['port'] = l_port
                l_mqtt['ssl'] = l_ssl
                l_mqtt['username'] = l_username
                l_mqtt['password'] = l_password

                if l_ssl:
                    l_cafile = l_mqtt.get('cafile', None)
                    if not l_cafile:
                        l_txt = f'MQTTS used, cafile required name:{l_name}'
                        if l_this_enabled:
                            raise ValueError(l_txt)
                        else:
                            print(f'*** {l_txt}')
                    if not os.path.exists(l_cafile):
                        l_txt = f'''MQTTS used, cafile doesn't exist name:{l_name} cafile:{l_cafile}'''
                        if l_this_enabled:
                            raise ValueError(l_txt)
                        else:
                            print(f'*** {l_txt}')
                l_topic = l_mqtt.get('topic', None)
                if not l_topic:
                    l_txt = f'[{_def.KEY_MQTT}] topic required name:{l_name}'
                    if l_this_enabled:
                        raise ValueError(l_txt)
                    else:
                        print(f'*** {l_txt}')

                l_lwttopic = l_mqtt.get('lwttopic', _def.MQTT_LWTTOPIC)
                l_t = Template(l_lwttopic)
                l_mqtt['lwttopic'] = l_t.substitute(
                    hostname=l_common['hostname'],
                    topic=l_topic,
                    client_id=l_client_id)

                l_cmdtopic = l_mqtt.get('cmdtopic', _def.MQTT_CMDTOPIC)
                if l_cmdtopic:
                    l_t = Template(l_cmdtopic)
                    l_mqtt['cmdtopic'] = l_t.substitute(
                        hostname=l_common['hostname'],
                        topic=l_topic,
                        client_id=l_client_id)

                l_hbtopic = l_mqtt.get('hbtopic', _def.MQTT_HBTOPIC)
                if l_hbtopic:
                    l_t = Template(l_hbtopic)
                    l_mqtt['hbtopic'] = l_t.substitute(
                        hostname=l_common['hostname'],
                        topic=l_topic,
                        client_id=l_client_id)

        # print(f'mqtts:{l_mqtts}')
        return (l_mqtts, l_mqtt_enabled, unique_name)

# ------------------------------------------------------------------------------
    def _check_kafka_producer(self, *, cfg, unique_name):
        # KAFKA
        l_kafka_enabled = False
        l_common = cfg.get(_def.KEY_COMMON, None)
        l_kafkas = cfg.get(_def.KEY_KAFKA_PRODUCER, None)
        if l_kafkas:
            for l_idx, l_kafka in enumerate(l_kafkas):
                l_this_enabled = False
                if l_kafka.get('enable', _def.KAFKA_ENABLE):
                    l_kafka_enabled = True
                    l_this_enabled = True
                l_name = l_kafka.get('name', None)
                if not l_name:
                    l_txt = f'kafka name required idx:{l_idx}'
                    if l_this_enabled:
                        raise ValueError(l_txt)
                    else:
                        print(f'*** {l_txt}')
                if l_name in unique_name:
                    l_txt = f'{_def.KEY_INFLUX}/{_def.KEY_MQTT}/{_def.KEY_KAFKA_PRODUCER} name need to be unique:{l_name}'
                    if l_this_enabled:
                        raise ValueError(l_txt)
                    else:
                        print(f'*** {l_txt}')
                unique_name.append(l_name)

                l_client_id = l_kafka.get('client_id', None)
                if not l_client_id:
                    l_client_id = f'''{l_common['hostname']}-{l_idx}'''
                    l_kafka['client_id'] = l_client_id
                    l_kafka['client_id_generated'] = True

                l_servers = l_kafka.get('bootstrap_servers', None)
                if not l_servers:
                    l_txt = f'{l_name} bootstrap_servers required'
                    if l_this_enabled:
                        raise ValueError(l_txt)
                    else:
                        print(f'*** {l_txt}')
                if not isinstance(l_servers, list):
                    l_kafka['bootstrap_servers'] = [l_servers] 

                # l_key = l_kafka.get('key', _def.KAFKA_KEY)
                # if l_key:
                #     if isinstance(l_key, str):
                #         l_kafka['key'] = l_key.encode()

                l_topics = l_kafka.get('PUBTOPIC', _def.KAFKA_PUBTOPIC)
                if not l_topics:
                    l_txt = f'[{_def.KEY_KAFKA_PRODUCER}][PUBTOPIC] required name:{l_name}'
                    if l_this_enabled:
                        raise ValueError(l_txt)
                    else:
                        print(f'*** {l_txt}')
                if not isinstance(l_topics, list):
                    l_kafka['PUBTOPIC'] = [l_topics] 

        # print(f'kafkas:{l_kafkas}')
        return (l_kafkas, l_kafka_enabled, unique_name)

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
        for l_key in self._cfg.keys():
            print('')
            self._print_item(key=l_key, value=self._cfg[l_key])

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
            for l_key in value.keys():
                self._print_item(key=l_key, value=value[l_key], indent=indent+3)
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

        l_common = self.get_cfg(section=_def.KEY_COMMON)
        if l_common:
            print ('')
            print (f'{_def.KEY_COMMON}')
            print ('-'*_def.SEPARATOR_LENGTH)
            l_hostname = l_common.get('hostname', None)
            l_resolved = '(resolved)' if l_common.get('hostname_resolved', False) else ''
            print (f'hostname:               {l_hostname} {l_resolved}')
            l_nameservers = l_common.get('nameservers', None)
            if l_nameservers:
                for l_idx, l_nameserver in enumerate(l_nameservers):
                    print (f'nameserver[{l_idx}]:          {l_nameserver}')
            else:
                print (f'nameserver:             using system dns server')
            print ('')

        l_influxs = self.get_cfg(section=_def.KEY_INFLUX)
        if l_influxs:
            for l_influx in l_influxs:
                print (f'''{_def.KEY_INFLUX}: {l_influx.get('name')}''')
                print ('-'*_def.SEPARATOR_LENGTH)
                l_enable = l_influx.get('enable', _def.INFLUX_ENABLE)
                print (f'   enable:              {str(l_enable)}')
                if l_enable:
                    l_policy = l_influx.get('POLICY', _def.INFLUX_POLICY)
                    l_host = l_influx.get('host')
                    l_host += ':' + str(l_influx.get('port', _def.INFLUX_PORT))
                    print (f'   host:                {l_host}')
                    l_ssl = l_influx.get('ssl', _def.INFLUX_SSL)
                    print (f'   ssl:                 {str(l_ssl)}')
                    if l_ssl:
                        print ('      ssl_verify:       {0:s}'.format(str(l_influx.get('ssl_verify', _def.INFLUX_SSL_VERIFY))))
                    print ('   database:            {0:s}'.format(l_influx.get('database', _def.INFLUX_DATABASE)))
                    print ('   username:            {0:s}'.format(l_influx.get('username', _def.INFLUX_USERNAME)))
                    print ('   timeout:             {0:.1f}s'.format(l_influx.get('timeout', _def.INFLUX_TIMEOUT)))
                    print ('   retries:             {0:d}'.format(l_influx.get('retries', _def.INFLUX_RETRIES)))
                    print ('   POLICY:              {0:s}'.format(l_policy.get('name', _def.INFLUX_POLICY_NAME)))
                    print ('      duration:         {0:s}'.format(l_policy.get('duration', _def.INFLUX_POLICY_DURATION)))
                    print ('      replication:      {0:d}'.format(l_policy.get('replication', _def.INFLUX_POLICY_REPLICATION)))
                    print ('      default:          {0:s}'.format(str(l_policy.get('default', _def.INFLUX_POLICY_DEFAULT))))
                    print ('      alter:            {0:s}'.format(str(l_policy.get('alter', _def.INFLUX_POLICY_ALTER))))
                print ('')


        l_mqtts = self.get_cfg(section=_def.KEY_MQTT)
        if l_mqtts:
            for l_mqtt in l_mqtts:
                l_name = l_mqtt.get('name')
                print (f'''{_def.KEY_MQTT}: {l_mqtt.get('name')}''')
                print ('-'*_def.SEPARATOR_LENGTH)
                l_enable = l_mqtt.get('enable', _def.MQTT_ENABLE)
                print (f'   enable:              {str(l_enable)}')
                if l_enable:
                    l_client_id = l_mqtt.get('client_id')
                    l_generated = '(generated)' if l_mqtt.get('client_id_generated', False) else ''
                    print (f'   client id:           {l_client_id} {l_generated}')
                    l_uri = l_mqtt.get('uri', None)
                    l_uri_params = [
                        False,      # 0 host
                        False,      # 1 port
                        False,      # 2 username
                        False,      # 3 password
                        False       # 4 ssl
                    ]
                    if l_uri:   # mqtts://username:password@host:port
                        print (f'   uri:                 {l_uri}')
                        l_uri_attr = urlparse(l_uri)
                        if l_uri_attr.hostname:
                            l_uri_params[0] = True
                        if l_uri_attr.port:
                            l_uri_params[1] = True
                        if l_uri_attr.username:
                            l_uri_params[2] = True
                        if l_uri_attr.password:
                            l_uri_params[3] = True
                        if l_uri_attr.scheme in ('mqtts', 'mqtt'):
                            l_uri_params[4] = True
                    print ('   host:                {0:s} {1:s}'.format(l_mqtt.get('host'), '(from uri)' if l_uri_params[0] else ''))
                    print ('   port:                {0:d} {1:s}'.format(l_mqtt.get('port'), '(from uri)' if l_uri_params[1] else ''))
                    l_ssl = l_mqtt.get('ssl')
                    print ('   ssl:                 {0:s} {1:s}'.format(str(l_ssl), '(from uri)' if l_uri_params[4] else ''))
                    if l_ssl:
                        print ('      ssl_insecure:     {0:s}'.format(str(l_mqtt.get('ssl_insecure', _def.MQTT_SSL_INSECURE))))
                        print ('      cert_verify:      {0:s}'.format(str(l_mqtt.get('cert_verify', _def.MQTT_CERT_VERIFY))))
                        print (f'''      cafile:           {str(l_mqtt.get('cafile', None))}''')
                    print ('   username:            {0:s} {1:s}'.format(l_mqtt.get('username', _def.MQTT_USERNAME), '(from uri)' if l_uri_params[2] else ''))
                    print ('   fulljson:            {0:s}'.format(str(l_mqtt.get('fulljson', _def.MQTT_FULLJSON))))
                    print ('   clean_session:       {0:s}'.format(str(l_mqtt.get('clean_session', _def.MQTT_CLEAN_SESSION))))
                    l_topic = l_mqtt.get('topic', None)
                    print ('   topic:               {0:s}'.format(str(l_topic)))
                    print ('   qos:                 {0:d}'.format(l_mqtt.get('qos', _def.MQTT_QOS)))
                    print ('   retain:              {0:s}'.format(str(l_mqtt.get('retain', _def.MQTT_RETAIN))))
                    l_adprefix = l_mqtt.get('adprefix', _def.MQTT_ADPREFIX)
                    if l_adprefix:
                        print (f'   adprefix:            {l_adprefix}')
                        print ('   adnodeid:            {0:s}'.format(str(l_mqtt.get('adnodeid', _def.MQTT_ADNODEID))))
                        print ('   adqos:               {0:s}'.format(str(l_mqtt.get('adqos', _def.MQTT_ADQOS))))
                        print ('   adretain:            {0:s}'.format(str(l_mqtt.get('adretain', _def.MQTT_ADRETAIN))))
                    l_cmdtopic = l_mqtt.get('cmdtopic', None)
                    if l_cmdtopic:
                        print (f'''   cmdtopic:            {l_cmdtopic}''')
                        print (f'''      cmdqos:           {l_mqtt.get('cmdqos', _def.MQTT_CMDQOS)}''')
                        print (f'''      cmd announce:     {_def.MQTT_CMD_ANNOUNCE}''')
                    l_lwt = l_mqtt.get('lwt', _def.MQTT_LWT)
                    l_lwttopic = l_mqtt.get('lwttopic', None)
                    print ('   lwt:                 {0:s}'.format(str(l_lwt)))
                    if l_lwt and l_lwttopic:
                        print (f'''      lwttopic:         {l_lwttopic}''')
                        print (f'''      lwtqos:           {l_mqtt.get('lwtqos', _def.MQTT_LWTQOS)}''')
                        print (f'''      lwtretain:        {l_mqtt.get('lwtretain', _def.MQTT_LWTRETAIN)}''')
                        print (f'''      lwtperiod:        {l_mqtt.get('lwtperiod', _def.MQTT_LWTPERIOD)}''')
                        print (f'''      lwtonline:        {l_mqtt.get('lwtonline', _def.MQTT_LWTONLINE)}''')
                        print (f'''      lwtoffline:       {l_mqtt.get('lwtoffline', _def.MQTT_LWTOFFLINE)}''')
                    l_hb = l_mqtt.get('hb', _def.MQTT_HB)
                    l_hbtopic = l_mqtt.get('hbtopic', None)
                    print ('   hb:                  {0:s}'.format(str(l_hb)))
                    if l_hb and l_hbtopic:
                        print (f'''      hbtopic:          {l_hbtopic}''')
                        print (f'''      hbqos:            {l_mqtt.get('hbqos', _def.MQTT_HBQOS)}''')
                        print (f'''      hbretain:         {l_mqtt.get('hbretain', _def.MQTT_HBRETAIN)}''')
                        print (f'''      hbad:             {l_mqtt.get('hbad', _def.MQTT_HBAD)}''')
                print ('')

        l_kafkas = self.get_cfg(section=_def.KEY_KAFKA_PRODUCER)
        if l_kafkas:
            for l_kafka in l_kafkas:
                print (f'''{_def.KEY_KAFKA_PRODUCER}: {l_kafka.get('name')}''')
                print ('-'*_def.SEPARATOR_LENGTH)
                l_enable = l_kafka.get('enable', _def.KAFKA_ENABLE)
                print (f'   enable:              {str(l_enable)}')
                if l_enable:
                    l_client_id = l_kafka.get('client_id')
                    l_generated = '(generated)' if l_kafka.get('client_id_generated', False) else ''
                    print (f'   client id:           {l_client_id} {l_generated}')
                    print (f'''   key:                 {str(l_kafka.get('key', _def.KAFKA_KEY))}''')
                    print (f'''   acks:                {str(l_kafka.get('acks', _def.KAFKA_ACKS))}''')
                    print (f'''   bootstrap servers:   {l_kafka.get('bootstrap_servers', _def.KAFKA_BOOTSTRAP_SERVERS)}''')
                    l_topics = l_kafka.get('PUBTOPIC', _def.KAFKA_PUBTOPIC)
                    print(f'   PUBTOPIC:            {l_topics}')
                print ('')

        l_ruuvitag = self.get_cfg(section='RUUVITAG')
        if l_ruuvitag:
            print ('RUUVITAG: {0}'.format(l_ruuvitag.get('name', _def.RUUVITAG_NAME)))
            print ('-'*_def.SEPARATOR_LENGTH)
            print ('ruuvi name:             {0:s}'.format(l_ruuvitag.get('ruuviname', _def.RUUVITAG_RUUVINAME)))
            if platform.system() == 'Linux':
                print ('device:                 {0:s}'.format(l_ruuvitag.get('device', _def.RUUVITAG_DEVICE)))
            print ('collector:              {0:s}'.format(l_ruuvitag.get('collector', _def.RUUVITAG_COLLECTOR)))
            # print ('time format:            {0:s}'.format(l_ruuvitag.get('timefmt', _def.RUUVITAG_TIMEFMT)))
            print ('sample interval:        {0:.1f} sec'.format(l_ruuvitag.get('sample_interval', _def.RUUVITAG_SAMPLE_INTERVAL)))
            print ('device timeout:         {0:.1f} sec'.format(l_ruuvitag.get('device_timeout', _def.RUUVITAG_DEVICE_TIMEOUT)))
            print ('restart ble device:     {0:s}'.format(str(l_ruuvitag.get('device_reset', _def.RUUVITAG_DEVICE_RESET))))
            l_calc = l_ruuvitag.get('calc', _def.RUUVITAG_CALC)
            print ('do calculations:        {0:s}'.format(str(l_calc)))
            if l_calc:
                print ('   calc in datas:       {0:s}'.format(str(l_ruuvitag.get('calc_in_datas', _def.RUUVITAG_CALC_IN_DATAS))))
            # print ('use sudo:               {0:s}'.format(str(l_ruuvitag.get('sudo', _def.RUUVITAG_SUDO))))
            print ('whtlist from tags:      {0:s}'.format(str(l_ruuvitag.get('whtlist_from_tags', _def.RUUVITAG_WHTLIST_FROM_TAGS))))
            # self._print_queue(cfg=l_ruuvitag, indent='')
            print ('')

            l_tags = l_ruuvitag.get('TAGS')
            if l_tags:
                print ('TAG MAC                 TAG NAME')
                print ('-'*(_def.SEPARATOR_LENGTH))
                for l_key in l_tags:
                    print('{0:20s}    {1}'.format(l_key, l_tags[l_key]))
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
            l_adjs = l_ruuvitag.get('ADJUSTMENT', None)
            if l_adjs:
                print(f'MEASUREMENT FIELD VALUE ADJUSTMENT')
                print(f'TAG MAC                 FIELD                         ADJUSTMENT')
                print ('-'*(_def.SEPARATOR_LENGTH))
                for l_tag, l_fields in l_adjs.items():
                    for l_field, l_adj in l_fields.items():
                        if l_adj > 0:
                            print('{0:23s} {1:29s} + {2}'.format(l_tag, l_field, l_adj))
                        elif l_adj < 0:
                            print('{0:23s} {1:29s} - {2}'.format(l_tag, l_field, abs(l_adj)))
                        else:
                            print('{0:23s} {1:29s}   {2}'.format(l_tag, l_field, l_adj))
                        l_tag = ''
                        
                print('')
            # l_minmax = l_ruuvitag.get('MINMAX', _def.RUUVITAG_MINMAX)
            # if l_minmax:
            #     print ('MINMAX                 MIN      MAX')
            #     print ('-'*(_def.SEPARATOR_LENGTH))
            #     for l_key in l_minmax:
            #         print ('{0:17s} {1:8.1f} {2:8.1f}'.format(l_key, l_minmax[l_key]['min'], l_minmax[l_key]['max']))
            #     print ('')
        else:
            raise ValueError(f'[RUUVITAG] configuration required')

        l_ruuvi = self.get_cfg(section='RUUVI')
        if l_ruuvi:
            print ('RUUVI: {0}'.format(l_ruuvi.get('name', _def.RUUVI_NAME)))
            print ('-'*_def.SEPARATOR_LENGTH)
            print ('max interval:           {0:.1f}'.format(l_ruuvi.get('max_interval', _def.RUUVI_MAX_INTERVAL)))
            # print ('write lastdata int:  {0:d} s'.format(l_ruuvi.get('write_lastdata_int', _def.RUUVI_WRITE_LASTDATA_INT)))
            # print ('write lastdata cnt:  {0:d}'.format(l_ruuvi.get('write_lastdata_cnt', _def.RUUVI_WRITE_LASTDATA_CNT)))

            # self._print_queue(cfg=l_ruuvi, indent='')
            print ('')

            for l_meas in l_ruuvi.get('MEASUREMENTS'):
                print ('MEASUREMENT: {0}'.format(l_meas.get('name', _def.RUUVI_NAME)))
                print ('-'*_def.SEPARATOR_LENGTH)
                print ('   calcs                {0:s}'.format(str(l_meas.get('calcs', _def.RUUVI_CALCS))))
                # print ('   debugs            {0:s}'.format(str(l_meas.get('debug', _def.RUUVI_DEBUG))))
                print ()
                l_outputs = l_meas.get('OUTPUT', _def.RUUVI_OUTPUT)
                if l_outputs:
                    print ('   OUTPUT               TYPE                          STATUS')
                    print ('   '+'-'*(_def.SEPARATOR_LENGTH-3))
                    for l_item in l_outputs:
                        (l_status, l_type) = self._check_output(name=l_item)
                        print ('   {0:20s} {1:29s} {2}'.format(l_item, l_type, l_status))
                    print ('')

                l_round = l_meas.get('ROUND', _def.RUUVI_ROUND)
                l_fields = l_meas.get('FIELDS', None)
                if l_fields:
                    print ('   RUUVITAG FIELD NAME  INFLUXDB FIELD NAME           DECIMALS')
                    print ('   '+'-'*(_def.SEPARATOR_LENGTH-3))
                    for l_key in l_fields:
                        print('   {0:20s} {1:30s}'.format(l_key, l_fields[l_key]), end='')
                        l_precision = l_round.get(l_key, _def.RUUVI_PRECISION)
                        if l_precision:
                            print(f'{l_precision}')
                        else:
                            print('')
                    print ('')

                # l_delta = l_meas.get('DELTA', _def.RUUVI_DELTA)
                # if l_delta:
                #     print ('   FIELD NAME                DELTA')
                #     print ('   '+'-'*(_def.SEPARATOR_LENGTH-3))
                #     for l_key in l_delta:
                #         print('   {0:25s} {1}'.format(l_key, l_delta[l_key]))
                #     print ('')

                # l_maxdelta = l_meas.get('MAXDELTA', _def.RUUVI_MAXDELTA)
                # if l_maxdelta:
                #     print ('   FIELD NAME                MAXCHANGE  MAXCOUNT')
                #     print ('   '+'-'*(_def.SEPARATOR_LENGTH-3))
                #     for l_key in l_maxdelta:
                #         print('   {0:25s} {1:<10.1f} {2}'.format(l_key, l_maxdelta[l_key]['maxchange'], l_maxdelta[l_key]['maxcount']))
                #     print ('')
        else:
            raise ValueError(f'[RUUVI] configuration required')

# ------------------------------------------------------------------------------
    def _check_output(self, *, name):
        l_outputs = [
            _def.KEY_INFLUX,
            _def.KEY_MQTT,
            _def.KEY_KAFKA_PRODUCER
        ]
        for l_output in l_outputs:
            l_o = self._find_output(cfgs=self.get_cfg(section=l_output), name=name)
            if l_o:
                return ('enabled' if bool(l_o.get('enable', _def.INFLUX_ENABLE)) else 'disabled', l_output.lower())
        return ('(n/a)', '(n/a)')

# ------------------------------------------------------------------------------
    def _find_output(self, *, cfgs, name):
        if cfgs:
            for l_cfg in cfgs:
                if l_cfg.get('name', None) == name:
                    return l_cfg
        return None

# ------------------------------------------------------------------------------
    # def _print_queue(self, *, cfg, indent='   '):
    #     l_q = cfg.get('QUEUE', _def.QUEUE_DEFAULT)
    #     print ('{0:s}QUEUE'.format(indent))
    #     print ('{0:s}   max size:         {1:d}'.format(indent, l_q.get('max_size')))
    #     print ('{0:s}   remove oldest:    {1:s}'.format(indent, str(l_q.get('remove_oldest_if_full'))))
    #     print ('{0:s}   rebuffering:      {1:s}'.format(indent, str(l_q.get('rebuffer'))))

