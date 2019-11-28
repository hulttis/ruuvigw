# coding=utf-8
#-------------------------------------------------------------------------------
# Name:        defaults.py
# Purpose:     default values
# Copyright:   (c) 2019 TK
# Licence:     MIT
#-------------------------------------------------------------------------------
from multiprocessing import cpu_count
import os
import sys

PROGRAM_NAME = 'Ruuvi Gateway'
LONG_PROGRAM_NAME = 'Ruuvi InfluxDB/MQTT Gateway'
PROGRAM_PY = 'ruuvigw.py'
VERSION = '3.1.5 (191128)'
PROGRAM_COPYRIGHT = '(c) TK 2019'

CFGFILE = 'ruuvigw.json'
if not sys.platform.startswith('linux') or os.environ.get('CI') == 'True': 
    LOG_CFGFILE = 'ruuvigw_logging_win.json'
else:
    LOG_CFGFILE = 'ruuvigw_logging.json'
print (f'### DEFAULT LOG CONFIG FILE:{LOG_CFGFILE}')


SEPARATOR_LENGTH = 70
# COMMON
COMMON_SCHEDULER_INSTANCES = 10
COMMON_NAMESERVERS = []
COMMON_HOSTNAME = '' 
# INFLUX
INFLUX_ENABLE = True
INFLUX_NAME = 'influx_default'
INFLUX_SUPERVISION_INTERVAL = 20
INFLUX_HOST = ''
INFLUX_PORT = 8086
INFLUX_SSL = False 
INFLUX_SSL_VERIFY = True 
INFLUX_USERNAME = ''
INFLUX_PASSWORD = ''
INFLUX_DATABASE = '' 
INFLUX_TIMEOUT = 2.0 
INFLUX_RETRIES = 2
INFLUX_POLICY_NAME = '_default'
INFLUX_POLICY_DURATION = '365d'
INFLUX_POLICY_REPLICATION = 1
INFLUX_POLICY_DEFAULT = False
INFLUX_POLICY_ALTER = False
INFLUX_POLICY = {
    "name": INFLUX_POLICY_NAME,
    "duration": INFLUX_POLICY_DURATION,
    "replication": INFLUX_POLICY_REPLICATION,
    "default": INFLUX_POLICY_DEFAULT,
    "alter": INFLUX_POLICY_ALTER
    }
INFLUX_QUEUE_SIZE = 100

# MQTT
MQTT_ENABLE = True
MQTT_FULLJSON = False
MQTT_TOPIC = 'test'
# MQTT_ADTOPIC = None
# MQTT_ANNTOPIC = None
MQTT_NAME = ''
MQTT_HOST = 'localhost'
MQTT_PORT = 1883
MQTT_SSLPORT = 8883
MQTT_SSL = False
MQTT_SSL_INSECURE = False
MQTT_CERT_VERIFY = True
MQTT_KEEPALIVE = 15
MQTT_CLIENT_ID = 'mqtt'
# MQTT_CAFILE = ''
# MQTT_CAPATH = ''
# MQTT_CADATA = ''
MQTT_LWT= False
MQTT_LWTTOPIC = 'lwt'
MQTT_LWTOFFLINE = 'offline'
MQTT_LWTONLINE = 'online'
MQTT_LWTRETAIN = False
MQTT_LWTQOS = 1
MQTT_LWTPERIOD = 60
MQTT_USERNAME = ''
MQTT_PASSWORD = ''
MQTT_QOS = 1
MQTT_RETAIN = False
MQTT_CLEAN_SESSION = False
MQTT_ADQOS = 1
MQTT_ADRETAIN = False
MQTT_ANNQOS = 1
MQTT_SUPERVISION_INTERVAL = 10
MQTT_QUEUE_SIZE = 100
MQTT_ONLYNEWEST = True
MQTT_ADFIELDS = {
    "temperature": {
        "unit_of_meas": "C",
        "dev_cla": "temperature",
        "val_tpl": "{{ value_json.temperature | float | round(1) }}"
    },
    "humidity": {
        "unit_of_meas": "%",
        "dev_cla": "humidity",
        "val_tpl": "{{ value_json.humidity | float | round(1) }}"
    },
    "pressure": {
        "unit_of_meas": "hPa",
        "dev_cla": "pressure",
        "val_tpl": "{{ value_json.pressure | float | round(1) }}"
    },
    "batteryVoltage": {
        "unit_of_meas": "V",
        "dev_cla": "battery",
        "val_tpl": "{{ value_json.batteryVoltage | float / 1000 | round(3) }}"
    }
}

# RUUVI
RUUVI_NAME = 'ruuvi'
RUUVI_CALCS = False 
RUUVI_TIMEFMT = '%Y-%m-%dT%H:%M:%S.%f%z'
RUUVI_MAX_INTERVAL = 60
RUUVI_WRITE_LASTDATA_INT = 0
RUUVI_WRITE_LASTDATA_DIFF = 10
RUUVI_WRITE_LASTDATA_DELAY = 10
RUUVI_WRITE_LASTDATA_CNT = 40
RUUVI_QUEUE_SIZE = 100
RUUVI_DEBUG = False
RUUVI_PRECISION = 3
RUUVI_ROUND = {
    "temperature": 1,
    "humidity": 1,
    "pressure": 1,
    "acceleration": 2
}
RUUVI_DELTA = {
    "temperature": 0.1,
    "humidity": 1,
    "pressure": 0.1,
    "acceleration": 20
}
RUUVI_MAXDELTA = {
    "temperature": {
    "maxchange": 5.0,
    "maxcount": 10
    },
    "humidity": {
    "maxchange": 5.0,
    "maxcount": 10
    },
    "pressure": {
    "maxchange": 1.0,
    "maxcount": 10
    },
    "acceleration": {
    "maxchange": 50,
    "maxcount": 10
    }
}
RUUVI_OUTPUT = [
]

# RUUVITAG
RUUVITAG_NAME = 'ruuvitag'
RUUVITAG_RUUVINAME = 'ruuvi'
RUUVITAG_COLLECTOR = 'socket'
RUUVITAG_DEVICE = 'hci0'
RUUVITAG_TIMEFMT = RUUVI_TIMEFMT
RUUVITAG_SAMPLE_INTERVAL = 1000
RUUVITAG_CALC = False
RUUVITAG_CALC_IN_DATAS = False
RUUVITAG_DEBUG = False
RUUVITAG_DEVICE_TIMEOUT = 10000
RUUVITAG_SUDO = False
RUUVITAG_DEVICE_RESET = False
RUUVITAG_WHTLIST_FROM_TAGS = True
RUUVITAG_MINMAX = {
    "temperature": {
        "min": -50.0,
        "max": 50.0
    },
    "humidity": {
        "min": 0,
        "max": 100
    },
    "pressure": {
        "min": 900,
        "max": 1100
    }
}
