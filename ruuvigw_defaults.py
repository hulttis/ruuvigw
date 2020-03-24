# coding=utf-8
#-------------------------------------------------------------------------------
# Name:        defaults.py
# Purpose:     default values
# Copyright:   (c) 2019 TK
# Licence:     MIT
#-------------------------------------------------------------------------------
from multiprocessing import cpu_count
import platform
import sys

PROGRAM_NAME = 'Ruuvi Gateway'
LONG_PROGRAM_NAME = 'Ruuvi InfluxDB/MQTT Gateway'
PROGRAM_PY = 'ruuvigw.py'
VERSION = '4.3.3 (200324)'
PROGRAM_COPYRIGHT = '(c) TK 2020'

CFGFILE = 'ruuvigw.json'
if platform.system() == 'Windows':
    LOG_CFGFILE = 'ruuvigw_logging_win.json'
else:
    LOG_CFGFILE = 'ruuvigw_logging.json'
print (f'### DEFAULT LOG CONFIG FILE:{LOG_CFGFILE}')

KEY_COMMON = 'COMMON'
KEY_INFLUX = 'INFLUX'
KEY_MQTT = 'MQTT'
KEY_KAFKA_PRODUCER = 'KAFKA PRODUCER'
KEY_RUUVITAG = 'RUUVITAG'
KEY_RUUVI = 'RUUVI'

SEPARATOR_LENGTH = 70
# COMMON
COMMON_SCHEDULER_INSTANCES = 50
COMMON_FBQUEUE_SIZE = 10
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
INFLUX_REBUFFER = False

# MQTT
MQTT_ENABLE = True
MQTT_NAME = ''
MQTT_FULLJSON = False
MQTT_TOPIC = 'test'
MQTT_QOS = 1
MQTT_RETAIN = False
MQTT_CLEAN_SESSION = False
MQTT_HOST = 'localhost'
MQTT_PORT = 1883
MQTT_SSLPORT = 8883
MQTT_SSL = False
MQTT_SSL_INSECURE = False
MQTT_CERT_VERIFY = True
MQTT_KEEPALIVE = 15.0
MQTT_CLIENT_ID = 'mqtt'
MQTT_CMDTOPIC = None
MQTT_CMDQOS = MQTT_QOS
MQTT_CMD_ANNOUNCE = 'announce'
MQTT_ADPREFIX = None
MQTT_ADNODEID = "ruuvi"
MQTT_ADQOS = MQTT_QOS
MQTT_ADRETAIN = MQTT_RETAIN
MQTT_LWT= False
MQTT_LWTTOPIC = '$topic/$client_id/lwt'
MQTT_LWTOFFLINE = 'offline'
MQTT_LWTONLINE = 'online'
MQTT_LWTRETAIN = MQTT_RETAIN
MQTT_LWTQOS = MQTT_QOS
MQTT_LWTPERIOD = 60.0
MQTT_USERNAME = ''
MQTT_PASSWORD = ''
MQTT_SUPERVISION_INTERVAL = 10.0
MQTT_QUEUE_SIZE = 100
MQTT_REBUFFER = False
MQTT_ONLYNEWEST = True
MQTT_ADFIELDS = {
    "temperature": {
        "component": "sensor",
        "unit_of_measurement": "C",
        "device_class": "temperature",
        "value_template": "{{ float(value_json.temperature) | round(1) }}",
        "icon": "mdi:thermometer"
    },
    "humidity": {
        "component": "sensor",
        "unit_of_measurement": "%",
        "device_class": "humidity",
        "value_template": "{{ float(value_json.humidity) | round(1) }}",
        "icon": "mdi:water-percent"
    },
    "pressure": {
        "component": "sensor",
        "unit_of_measurement": "hPa",
        "device_class": "pressure",
        "value_template": "{{ float(value_json.pressure) | round(1) }}",
        "icon": "mdi:gauge"
    },
    "batteryVoltage": {
        "component": "sensor",
        "unit_of_measurement": "V",
        "device_class": "battery",
        "value_template": "{{ (float(value_json.batteryVoltage) / 1000) | round(3) }}",
        "icon": "mdi:battery"
    }
}
MQTT_HB = False
MQTT_HBAD = True
MQTT_HBTOPIC = '$topic/$client_id/hb'
MQTT_HBQOS = MQTT_QOS
MQTT_HBRETAIN = MQTT_RETAIN

# KAFKA
KAFKA_ENABLE = True
KAFKA_NAME = 'kafka'
KAFKA_QUEUE_SIZE = 100
KAFKA_KEY = None
KAFKA_ACKS = 1
KAFKA_PUBTOPIC = ['$topic']
KAFKA_BOOTSTRAP_SERVERS = None

# RUUVI
RUUVI_NAME = 'ruuvi'
RUUVI_CALCS = False 
RUUVI_TIMEFMT = '%Y-%m-%dT%H:%M:%S.%f%z'
RUUVI_MAX_INTERVAL = 60.0
RUUVI_WRITE_LASTDATA_INT = 0
RUUVI_WRITE_LASTDATA_DIFF = 10.0
RUUVI_WRITE_LASTDATA_DELAY = 10.0
RUUVI_WRITE_LASTDATA_CNT = 40
RUUVI_QUEUE_SIZE = 100
RUUVI_DEBUG = False
RUUVI_PRECISION = 2
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
RUUVI_OUTPUT = []

# RUUVITAG
RUUVITAG_NAME = 'ruuvitag'
RUUVITAG_RUUVINAME = 'ruuvi'
RUUVITAG_COLLECTOR = 'socket'
RUUVITAG_DEVICE = 'hci0'
RUUVITAG_TIMEFMT = RUUVI_TIMEFMT
RUUVITAG_SAMPLE_INTERVAL = 1.0
RUUVITAG_CALC = False
RUUVITAG_CALC_IN_DATAS = False
RUUVITAG_DEBUG = False
RUUVITAG_DEVICE_TIMEOUT = 10.0
# RUUVITAG_SUDO = False
RUUVITAG_DEVICE_RESET = False
RUUVITAG_WHTLIST_FROM_TAGS = True
# RUUVITAG_MINMAX = {
#     "temperature": {
#         "min": -50.0,
#         "max": 100.0
#     },
#     "humidity": {
#         "min": 0,
#         "max": 100
#     },
#     "pressure": {
#         "min": 900,
#         "max": 1100
#     }
# }
RUUVITAG_MINMAX = {}