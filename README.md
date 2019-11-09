# RUUVI GATEWAY 2.5.5 (191110)
This software can be used to collect measurement data from Ruuvitag Bluetooth Low Energy devices https://ruuvi.com/

## MAIN FUNCTIONALITIES
- Store selectable set of ruuvitag data fields to (multiple) Influx databases
- Publish selectable set of ruuvitag data fields to (multiple) MQTT brokers
- Home assistant Auto Discovery (on restart and/or on request)
- Ruuvitag beacon naming (mac --> tagname)
- Ruuvitag per measurement instance white/black lists (white list can be generated from the TAGS)
- Ruuvitag per measurement instance field renaming

## RUUVITAG FIELDS
- ruuvitag dataformats 3 and 5 are supported. see  https://github.com/ruuvi/ruuvi-sensor-protocols for more information
  
| RUUVITAG FIELD     | Unit |                               |
|:-------------------|:-----|:------------------------------|
| `_df`              |      | ruuvitag data format (3 or 5) |
| `humidity`         | %    | relative humidity             |
| `temperature`      | C    | temperature                   |
| `pressure`         | hPa  | pressure                      |
| `acceleration`     | g    | total acceleration            |
| `acceleration_x`   | g    | acceleration x-axis           |
| `acceleration_y`   | g    | acceleration y-axis           |
| `acceleration_z`   | g    | acceleration z-axis           |
| `tx_power`         | dBm  | transmit power (df:5)         |
| `battery`          | mV   | battery voltage               |
| `movement_counter` |      | movement counter (df:5)       |
| `sequence_number`  |      | sequence number (df:5)        |
| `tagid`            |      | device mac address (df:5)     |
| `rssi`             | dB   | rssi                          |

| CALCULATED FIELD           | Unit   |                            |
|:---------------------------|:-------|:---------------------------|
| `equilibriumVaporPressure` | pa     | equilibrium vapor pressure |
| `absoluteHumidity`         | g/m^3  | absolute humidity          |
| `dewPoint`                 | C      | dew point                  |
| `airDensity`               | kg/m^3 | air density                |

## CONFIGURATION
### RUUVIGW
- file: ruuvigw.json
- see `ruuvigw.json` for example configuration

| `COMMON`: [object]    | optional                                                         |
|:----------------------|:-----------------------------------------------------------------|
| `nameservers`: [list] | list of nameservers, if not given system nameserver will be used |
| `hostname`: [string]  | hostname, if not given will be detected automatically            |


| `INFLUX`: [list]                              | optional                                         |
|-----------------------------------------------|--------------------------------------------------|
| `enable`: [boolean]                           | enable/disable InfluxDB instance (default: true) |
| `name`: [string]                              | **unique** name of the InfluxDB instance         |
| `host`: [string]                              | InfluxDB host (default: localhost)               |
| `port`: [integer]                             | InfluxDB port (default: 8086)                    |
| `ssl`: [boolean]                              | use ssl (default: false)                         |
| `ssl_verify`: [boolean]                       | verify ssl certificate (default: true)           |
| `database`: [string]                          | name of the InfluxDB database                    |
| `username`: [string]                          | InfluxDB username                                |
| `password`: [string]                          | InfluxDB password                                |
| **`POLICY`**: [object]                        |                                                  |
| &nbsp;&nbsp;&nbsp;`name`: [string]            | policy name (default: _default)                  |
| &nbsp;&nbsp;&nbsp;`   duration`: [string]     | policy duration (default: 0s - forever)          |
| &nbsp;&nbsp;&nbsp;`   replication`: [integer] | policy replication (default: 1)                  |
| &nbsp;&nbsp;&nbsp;`   default`: [boolean]     | set as default policy (default: false)           |
| &nbsp;&nbsp;&nbsp;`   alter`: [boolean]       | alter if policy exists (default: false)          |



| `MQTT`: [list]                                               | optional                                                                      |
|:-------------------------------------------------------------|:------------------------------------------------------------------------------|
| `enable`: [boolean]                                          | enable/disable MQTT instance (default: true)                                  |
| `name`: [string]                                             | **unique** name of the MQTT instance                                          |
| `client_id`: [string]                                        | **unique** client-id (default: `hostname-uuid4`)                              |
| `host`: [string]                                             | mqtt host (default: mqtt://localhost:1883)                                    |
| `topic`: [string]                                            | mqtt publish topic                                                            |
| `retain`: [boolean]                                          | mqtt publish retain (default: false)                                          |
| `adtopic`: [string]                                          | home assistant autodiscovery topic (default: None - no autodiscovery)         |
| `adretain`: [boolean]                                        | home assistant autodiscovery retain (default: false)                          |
| `anntopic`: [string]                                         | home assistant auto discovery announce topic (default: None - not subscribed) |
| `lwt`: [boolean]                                             | enable LWT (Last Will Testament (default: False)                              |
| `lwttopic`: [string]                                         | LWT topic (default: `topic/hostname/lwt`)                                     |
| `qos`: [integer]                                             | quality of service (default: 1)                                               |
| `cafile`: [string]                                           | certificate file                                                              |
| `check_hostname`: [boolean]                                  | check the peer cert’s hostname                                                |
| `ADFIELDS`: [object]                                         | home assistant auto discovery fields (default: see defaults.py)               |
| &nbsp;&nbsp;&nbsp;`<field name>`: [object]                   | name of the auto discovery field                                              |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`unit_of_meas`: [string] | unit of measurement                                                           |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`dev_cla`: [string]      | device class                                                                  |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`val_tpl`: [string]      | value template                                                                |
| `RUUVI`: [object]                             | required                                                                                                          |
|:----------------------------------------------|:------------------------------------------------------------------------------------------------------------------|
| `name`: [string]                              | name of the ruuvi instance (default: ***ruuvi_default***) note: used also as InfluxDB measurement name            |
| `max_interval`: [integer]                     | max data interval interval (default:60s)                                                                          |
| `MEASUREMENTS`: [object]                      | Ruuvi measurements                                                                                                |
| `name`: [string]                              | measurement name                                                                                                  |
| `calcs`: [boolean]                            | calculate equilibriumVaporPressure, absoluteHumidity, dewPoint, airDensity fields (default: false)                |
| `OUTPUT`: [list]                              | list of InfluxDB/MQTT output(s) (default: "influx_default", "mqtt_default")                                       |
| `<output>`: [string]                          | name of the output InfluxDB and/or MQTT instance                                                                  |
| `FIELDS`: [object]                            | ruuvitag to InfluxDB and MQTT field name mapping (see ruuvitag fields)                                            |
| &nbsp;&nbsp;&nbsp`<ruuvitag field>`: [string] | ruuvigw field name used for InfluxDB / MQTT                                                                       |

| `RUUVITAG`: [object]                                       | required                                                                             |
|:-----------------------------------------------------------|:-------------------------------------------------------------------------------------|
| `name`: [string]                                           | name of the ruuvitag instance (default: ruuvitag_default)                            |
| `ruuviname`: [string]                                      | name of the ruuvi instance ruuvitag will be connected (default: ***ruuvi_default***) |
| `sample_interval`: [integer]                               | sample interval in ms (default: 1000ms)                                              |
| `device_timeout`: [integer]                                | hcidump timeout in ms (default: 10000ms)                                             |
| `sudo`: [boolean]                                          | use sudo for hcidump command (default: False). needed if not run as root. set false for docker             |
| `whtlist_from_tags`: [boolean]                             | generate whitelist from the TAGS                                                     |
| `TAGS`: [object]                                           | ruuvitags (see *ruuvigw.json*)                                                 |
| &nbsp;&nbsp;&nbsp;`<mac>`: [string]                        | ruuvitag mac address                                                                 |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`<tag name>`: [string] | ruuvitag name                                                                        |
| `WHTLIST`: [list]                                          |                                                                                      |
| &nbsp;&nbsp;&nbsp;`<mac>`: [string]                        | white listed mac                                                                     |
| `BLKLIST`: [list]                                          |                                                                                      |
| &nbsp;&nbsp;&nbsp;`<mac>`: [string]                        | black listed mac                                                                     |

### HOME ASSISTANT MQTT AUTO DISCOVERY
- ruuvigw subscribes mqtt topic defined in `anntopic` and expects mqtt payload to be `ruuvi`

### LOGGER
- see  `ruuvigw_logging.json` for example configuration 

## INSTALLATION
### REQUIREMENTS
- Linux (tested in Ubuntu server 18.04.03 and 2019-09-26-raspbian-buster-lite). **NOT WORKING IN WINDOWS**
- python 3.7.x  (tested with 3.7.4)
- pip3.7
- virtualenv (`pip3.7 install --user virtualenv`)
- git (`sudo apt -y install git`)
- bluez and bluez-hcitool (`sudo apt -y install bluez bluez-hcitool`)

### PYTHON 3.7.4 AND PIP (FROM SOURCE) - IF NEEDED
- `cd ~/`
- `sudo apt -y install build-essential tk-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev libffi-dev libbluetooth-dev`
- `wget https://www.python.org/ftp/python/3.7.4/Python-3.7.4.tar.xz`
- `tar xf Python-3.7.4.tar.xz`
- `cd Python-3.7.4/`
- `./configure`
- `make -j 4`
- `sudo make altinstall`
- `python3.7 -V && pip3.7 -V`

### DOCKER
- figure out yourself
- see `https://github.com/hulttis/ruuvigw-docker` for Dockerfile sample
  
### DOCKER-COMPOSE
- see `https://github.com/hulttis/ruuvigw-docker` for installation instructions

### LINUX SERVICE
- `sudo -i`
- create /app directory (`mkdir -p /app && cd /app`)
- create /var/log/ruuvigw directory (`mkdir -p /var/log/ruuvigw`) for logs
- clone git repository to /app directory (`git clone https://github.com/hulttis/ruuvigw.git`)
- edit /app/ruuvigw/ruuvigw.json file (`nano /app/ruuvigw/ruuvigw.json`)
- create virtual environment (`cd /app/ruuvigw && python3.7 -m venv env`)
- activate virtual environment (`source env/bin/activate`)
- check python and pip (`which python && which pip && python -V && pip -V`)
- install requirements (`pip install -r requirements.txt`)
- deactivate virtual environment (`deactivate`)
- copy /app/ruuvigw/ruuvigw.service to /lib/systemd/system directory (`cp /app/ruuvigw/ruuvigw.service /lib/systemd/system/.`)
- reload daemons (`systemctl daemon-reload`)
- enable ruuvigw (`systemctl enable ruuvigw`)
- start ruuvigw (`systemctl start ruuvigw`)
- check ruuvigw status (`systemctl status ruuvigw`)
- checl ruuvigw logs (`journalctl -u ruuvigw -b --no-pager`)
  
## COMMAND LINE PARAMETERS
### ruuvigw.py [-h] [-c config] [-l logconfig]
| optional argument | long format | parameter                 |
|:------------------|:------------|:--------------------------|
| -h                | --help      |                           |
| -c                | --config    | configuration file        |
| -l                | --logconfig | logger configuration file |

# LICENCE
MIT License is used for this software.
