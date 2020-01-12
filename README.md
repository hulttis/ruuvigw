# RUUVI GATEWAY 4.1.1 (200111)
This software can be used to collect measurement data from Ruuvitag Bluetooth Low Energy devices https://ruuvi.com/

## MAIN FUNCTIONALITIES
- Store selectable set of ruuvitag data fields to (multiple) Influx databases
- Publish selectable set of ruuvitag data fields to (multiple) MQTT brokers
- Home assistant Auto Discovery (on restart and/or on request)
- Ruuvitag beacon renaming (mac --> tagname)
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


| `INFLUX`: [list]                              | optional                                              |
|-----------------------------------------------|-------------------------------------------------------|
| `enable`: [boolean]                           | enable/disable InfluxDB instance (default: true)      |
| `name`: [string]                              | **unique** name of the InfluxDB instance (*required*) |
| `host`: [string]                              | InfluxDB host (*required*)                            |
| `port`: [integer]                             | InfluxDB port (default: 8086)                         |
| `ssl`: [boolean]                              | use ssl (default: false)                              |
| `ssl_verify`: [boolean]                       | verify ssl certificate (default: true)                |
| `database`: [string]                          | name of the InfluxDB database (*required*)            |
| `username`: [string]                          | InfluxDB username                                     |
| `password`: [string]                          | InfluxDB password                                     |
| `POLICY`: [object]                            |                                                       |
| &nbsp;&nbsp;&nbsp;`name`: [string]            | policy name (default: _default)                       |
| &nbsp;&nbsp;&nbsp;`   duration`: [string]     | policy duration (default: 0s - forever)               |
| &nbsp;&nbsp;&nbsp;`   replication`: [integer] | policy replication (default: 1)                       |
| &nbsp;&nbsp;&nbsp;`   default`: [boolean]     | set as default policy (default: false)                |
| &nbsp;&nbsp;&nbsp;`   alter`: [boolean]       | alter if policy exists (default: false)               |


| `MQTT`: [list]                            | optional                                                                      |
|:------------------------------------------|:------------------------------------------------------------------------------|
| `enable`: [boolean]                       | enable/disable MQTT instance (default: true)                                  |
| `name`: [string]                          | **unique** name of the MQTT instance (*required*)                             |
| `client_id`: [string]                     | **unique** client-id (default: `hostname-x`)                                  |
| `uri`                                     | mqtt url (uri or host/port/username/password/ssl are needed                   |
| `host`: [string]                          | mqtt host (*required*)                                                        |
| `port`: [integer]                         | mqtt port (default: 1883 (for ssl 8883))                                      |
| `ssl`: [boolean]                          | secure mqtt (default: False)                                                  |
| `ssl_insecure`: [boolean]                 | allow ssl without verifying hostname in the certificate (default: False)      |
| `clean_session`: [boolean]                | clean session (default: False)                                                |
| `fulljson`: [boolean]                     | send full json object received from the ruuvi client (default: False)         |
|                                           | useful for storing ruuvitag data to the influx via Node-RED                   |
| `cert_verify`: [boolean]                  | verify ssl certificates (default: True)                                       |
| `cafile`: [string]                        | certificate file (full path)                                                  |
| `topic`: [string]                         | mqtt publish topic                                                            |
| `qos`: [integer]                          | quality of service (default: 1)                                               |
| `retain`: [boolean]                       | mqtt publish retain (default: false)                                          |
| `adtopic`: [string]                       | home assistant autodiscovery topic (default: None - no autodiscovery)         |
| `adretain`: [boolean]                     | home assistant autodiscovery retain (default: false)                          |
| `anntopic`: [string]                      | home assistant auto discovery announce topic (default: None - not subscribed) |
| `lwt`: [boolean]                          | enable LWT (Last Will Testament (default: False)                              |
| &nbsp;&nbsp;&nbsp;`lwttopic`: [string]    | LWT topic (default: `topic`/`client_id`/`lwt`)                                |
| &nbsp;&nbsp;&nbsp;`lwtqos`: [integer]     | LWT quality of service (default: 1)                                           |
| &nbsp;&nbsp;&nbsp;`lwtretain`: [boolean]  | LWT retain (default: False                                                    |
| &nbsp;&nbsp;&nbsp;`lwtperiod`: [integer]  | LWT update period in seconds (default: 60)                                    |
| &nbsp;&nbsp;&nbsp;`lwtonline`: [string]   | LWT online text (default: online)                                             |
| &nbsp;&nbsp;&nbsp;`lwtoffline`: [string ] | LWT offline text (default: offline)                                           |
| `ADFIELDS`: [object]                      | home assistant auto discovery fields (see *ruuvigw.json*)                     |

| `RUUVITAG`: [object]           | *required*                                                                                     |
|:-------------------------------|:-----------------------------------------------------------------------------------------------|
| `name`: [string]               | name of the ruuvitag instance (default: ***ruuvitag***)                                        |
| `ruuviname`: [string]          | name of the ruuvi instance ruuvitag will be connected (default: ***ruuvi***)                   |
| `collector`: [string]          | ruuvigw collector `socket`or `bleak` (default: `socket`)                                       |
|                                | `socket` will fallback to the `bleak`. Windows: `bleak` if forced                              |
| `sample_interval`: [integer]   | sample interval in ms (default: 1000ms)                                                        |
| `device_timeout`: [integer]    | hcidump timeout in ms (default: 10000ms)                                                       |
| `sudo`: [boolean]              | use sudo for hcidump command (default: False). needed if not run as root. set false for docker |
| `whtlist_from_tags`: [boolean] | generate whitelist from the TAGS                                                               |
| `TAGS`: [object]               | ruuvitags (see *ruuvigw.json*)                                                                 |
| `WHTLIST`: [list]              |                                                                                                |
| `BLKLIST`: [list]              |                                                                                                |
*NOTE: Two ruuvigw's with `bleak` collector doesn't work at the same time at the same computer*

| `RUUVI`: [object]         | *required*                                                                                         |
|:--------------------------|:---------------------------------------------------------------------------------------------------|
| `name`: [string]          | name of the ruuvi instance (default: ***ruuvi***)                                                  |
|                           | note: used also as InfluxDB measurement name. Need to match with RUUVITAG.ruuviname                |
| `max_interval`: [integer] | max data interval interval (default:60s)                                                           |
| `MEASUREMENTS`: [object]  | Ruuvi measurements                                                                                 |
| `name`: [string]          | measurement name                                                                                   |
| `calcs`: [boolean]        | calculate equilibriumVaporPressure, absoluteHumidity, dewPoint, airDensity fields (default: false) |
| `OUTPUT`: [list]          | list of InfluxDB/MQTT output(s) (*required*)                                                       |
| `FIELDS`: [object]        | ruuvitag to InfluxDB and MQTT field name mapping (see ruuvitag fields) (see: *ruuvigw.json*)       |

### HOME ASSISTANT MQTT AUTO DISCOVERY
- ruuvigw sends auto discovery to the `adtopic` by default to the following fields: temperature, humidity, pressure and batteryVoltage
- ruuvigw subscribes mqtt topic defined in `anntopic` and expects mqtt payload to be `ruuvi`. auto discovery is sent to all found sensors during next update

### LOGGER
- see  `ruuvigw_logging.json` for example configuration 

## INSTALLATION
### REQUIREMENTS
- Linux (tested in Ubuntu server 18.04.03 and 2019-09-26-raspbian-buster-lite).
- at least python 3.7 (recommended 3.8)
- at least pip3.7 (recommended 3.8)
- virtualenv (`pip3.8 install --user virtualenv`) - if not installed
- git (`sudo apt -y install git`)
- python with AF_BLUETOOTH socket support (`python -c "from socket import AF_BLUETOOTH"`)
- bluez 5.43 or above (`sudo apt -y install bluez`) if python doesn't support AF_BLUETOOTH socket or if you want to use bleak
NOTE: Instructions are for Python 3.8

### COMPILE PYTHON 3.8.0 FROM SOURCE - FOR AF_BLUETOOTH SOCKET SUPPORT
- `cd ~/`
- `sudo apt -y install build-essential tk-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev libffi-dev libbluetooth-dev`
- `wget https://www.python.org/ftp/python/3.8.0/Python-3.8.0.tar.xz`
- `tar xf Python-3.8.0.tar.xz`
- `cd Python-3.8.0/`
- `./configure`
- `make -j 4`
- `sudo make altinstall`
- `python3.8 -V && pip3.8 -V`

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
- create virtual environment (`cd /app/ruuvigw && python3.8 -m venv env`)
- activate virtual environment (`source env/bin/activate`)
- check python and pip (`which python && which pip && python -V && pip -V`)
- install requirements (`pip install -r requirements.txt`)
- deactivate virtual environment (`deactivate`)
- copy /app/ruuvigw/ruuvigw.service to /lib/systemd/system directory (`cp /app/ruuvigw/ruuvigw.service /lib/systemd/system/.`)
- reload daemons (`systemctl daemon-reload`)
- enable ruuvigw (`systemctl enable ruuvigw`)
- start ruuvigw (`systemctl start ruuvigw`)
- check ruuvigw status (`systemctl status ruuvigw`)
- check ruuvigw logs (`journalctl -u ruuvigw -b --no-pager`)

#### UPGRADE
- `sudo -i`
- stop ruuvigw (`systemctl stop ruuvigw`)
- `cd /app`
- copy config to safe location (`cp -v ./ruuvigw/ruuvigw.json . && cp -v ./ruuvigw/ruuvigw_logging.json .`)
- remove ruuvigw (`rm -fr ./ruuvigw`)
- clone git repository (`git clone --no-checkout https://github.com/hulttis/ruuvigw.git`)
- copy old config back to ruuvigw (`cp -v *.json ruuvigw/.`)
- create virtual environment (`cd /app/ruuvigw && python3.8 -m venv env`)
- activate virtual environment (`source env/bin/activate`)
- install requirements (`pip install -r requirements.txt`)
- deactivate virtual environment (`deactivate`)
- empty logs (`rm -v /var/log/ruuvigw/*.log`)
- start ruuvigw (`systemctl start ruuvigw`)
- check ruuvigw status (`systemctl status ruuvigw`)
- empty journal if needed (`journalctl --vacuum-time=1s`) - will clear all journals
- check ruuvigw logs (`journalctl -u ruuvigw -b --no-pager`)
  
*or if you dare you can use do_upgrade_ruuvigw.sh script on your own risk*
 
## COMMAND LINE PARAMETERS
### ruuvigw.py [-h] [-c config] [-l logconfig]
| optional argument | long format | parameter                 |
|:------------------|:------------|:--------------------------|
| -h                | --help      |                           |
| -c                | --config    | configuration file        |
| -l                | --logconfig | logger configuration file |

## SELECTION OF THE BLE SCANNING METHOD
- socket, if Python supports AF_BLUETOOTH socket type
- hcidump/hcitool, if found from the `/usr/bin/` directory
- if none of the above is found, ruuvigw will not start
  
# LICENCE
MIT License is used for this software.
