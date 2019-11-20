# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag df8 - formating dataformat 8
# Copyright:    (c) 2019 TK
# Licence:      MIT
#
# data format:  https://github.com/ruuvi/ruuvi-sensor-protocols
# 
# data format         0         
# temperature         1-2       -32767 ... 32767    0.005 degrees
# humidity            3-4       0 ... 40000         0.0025% (0...163.83)
# pressure            5-6       0 ... 65535         1Pa (offset -50000)
# power info          7-8       
# movement counter    9-10      0 ... 65534
# sequence number     11-12     0 ... 65534
# reserved            13-16     reserved for future use
# crc                 17        CRC8
# mac                 18-23     48bit MAC address        
# rssi                24        -127 ... 127 last byte of the data stream
#
# TODO: NOT YET IMPLEMENTED
# -------------------------------------------------------------------------------
import logging
logger = logging.getLogger('ruuvitag')

import math

from .ruuvitag_misc import (
    twos_complement,
    rshift
)

_DF = 8
ROUND_TEMPERATURE = 3
ROUND_HUMIDITY = 4
ROUND_PRESSURE = 2
ROUND_VOLTAGE = 3
ROUND_TXPOWER = 0

# -------------------------------------------------------------------------------
class ruuvitag_df8(object):
    DATAFORMAT = 'FF990408'
    DATALEN = 24
    PASSWORD = 0x5275757669636f6d5275757669546167   # "RuuvicomRuuviTag"

# -------------------------------------------------------------------------------
    def _temperature(self, *, bytedata, minmax):
        """ Temperature in 0.005 degrees. """
        if bytedata[1:2] == 0x7FFF:
            return None

        l_min = -163.840
        l_max = 163.830
        if minmax:
            try:
                l_min = minmax['min']
                l_max = minmax['max']
            except:
                logger.debug(f'>>> minmax not defined: {minmax}')

        l_temperature = twos_complement((bytedata[1] << 8) + bytedata[2], 16) / 200
        # if l_temperature < -163.840 or l_temperature > +163.830:
        #     logger.error(f'>>> Temperature out of range: value:{l_temperature} bytedata[1]:{bytedata[1]} bytedata[2]:{bytedata[2]}')
        #     raise ValueError(f'Temperature out of range: value:{l_temperature} bytedata[1]:{bytedata[1]} bytedata[2]:{bytedata[2]}')
        if l_temperature < l_min or l_temperature > l_max:
            logger.warning(f'>>> Temperature out of limits: value:{l_temperature} min:{l_min} max:{l_max}')
            raise ValueError(f'Temperature out of limits: value:{l_temperature} min:{l_min} max:{l_max}')
        return round(l_temperature, ROUND_TEMPERATURE)

# -------------------------------------------------------------------------------
    def _humidity(self, *, bytedata, minmax):
        """ Humidity (16bit unsigned) in 0.0025% (0-163.83% range, though realistically 0-100%). """
        if bytedata[3:4] == 0xFFFF:
            return None

        l_min = 0
        l_max = 100.0
        if minmax:
            try:
                l_min = minmax['min']
                l_max = minmax['max']
            except:
                logger.debug(f'>>> minmax not defined: {minmax}')

        l_humidity = ((bytedata[3] & 0xFF) << 8 | bytedata[4] & 0xFF) / 400
        # if l_humidity < 0 or l_humidity > 100:
        #     logger.error(f'>>> Humidity out of range: value:{l_humidity} bytedata[3]:{bytedata[3]} bytedata[4]:{bytedata[4]}')
        #     raise ValueError(f'Humidity out of range: value:{l_humidity} bytedata[3]:{bytedata[3]} bytedata[4]:{bytedata[4]}')
        if l_humidity < l_min or l_humidity > l_max:
            logger.warning(f'>>> Humidity out of limits: value:{l_humidity} min:{l_min} max:{l_max}')
            raise ValueError(f'Humidity out of limits: value:{l_humidity} min:{l_min} max:{l_max}')
        return round(l_humidity, ROUND_TEMPERATURE)

# -------------------------------------------------------------------------------
    def _pressure(self, *, bytedata, minmax):
        """ Pressure (16bit unsigned) in 1 Pa units, with offset of -50 000 Pa. """
        if bytedata[5:6] == 0xFFFF:
            return None

        l_min = 500
        l_max = 1155.36
        if minmax:
            try:
                l_min = minmax['min']
                l_max = minmax['max']
            except:
                logger.debug(f'>>> minmax not defined: {minmax}')

        l_pressure = ((bytedata[5] & 0xFF) << 8 | bytedata[6] & 0xFF) + 50000
        l_pressure = round((l_pressure / 100), 2)
        # if l_pressure < 500 or l_pressure > 1155.36:
        #     logger.error(f'>>> Pressure out of range: value:{l_pressure} bytedata[5]:{bytedata[5]} bytedata[6]:{bytedata[6]}')
        #     raise ValueError(f'Pressure out of range: value:{l_pressure} bytedata[5]:{bytedata[5]} bytedata[6]:{bytedata[6]}')
        if l_pressure < l_min or l_pressure > l_max:
            logger.warning(f'>>> Pressure out of limits: value:{l_pressure} min:{l_min} max:{l_max}')
            raise ValueError(f'Pressure out of limits: value:{l_pressure} min:{l_min} max:{l_max}')
        return round(l_pressure, ROUND_PRESSURE)

# -------------------------------------------------------------------------------
    def _powerinfo(self, *, bytedata):
        """
        Power info (11+5bit unsigned), first 11 bits is the battery voltage above 1.6V, 
        in millivolts (1.6V to 3.646V range). Last 5 bits unsigned are the TX power above -40dBm, 
        in 2dBm steps. (-40dBm to +20dBm range).        
        """
        l_power_info = (bytedata[7] & 0xFF) << 8 | (bytedata[8] & 0xFF)
        l_battery_voltage = rshift(l_power_info, 5) + 1600
        l_tx_power = (l_power_info & 0b11111) * 2 - 40

        if rshift(l_power_info, 5) == 0b11111111111:
            l_battery_voltage = None
        if (l_power_info & 0b11111) == 0b11111:
            l_tx_power = None

        return (round(l_battery_voltage, ROUND_VOLTAGE), round(l_tx_power, ROUND_TXPOWER))

# -------------------------------------------------------------------------------
    def _battery(self, *, bytedata):
        """ Battery Voltage in mV: 1600 mV to 3647 mV in 1 mV increments, practically 1800 ... 3600 mV """
        return self._powerinfo(bytedata=bytedata)[0]

# -------------------------------------------------------------------------------
    def _txpower(self, *, bytedata):
        """ Ruuvitag transmitting power: -40 dBm to +22 dBm in 2 dBm increments """
        return self._powerinfo(bytedata=bytedata)[1]

# -------------------------------------------------------------------------------
    def _movementcounter(self, *, bytedata):
        """ Movement counter (16 bit unsigned), incremented by motion detection interrupts from accelerometer """
        return (bytedata[9] & 0xFF) << 8 | bytedata[10] & 0xFF

# -------------------------------------------------------------------------------
    def _sequencenumber(self, *, bytedata):
        """ Measurement sequence number (16bit unsigned), each time a measurement is taken, 
        this is incremented by one, used for measurement de-duplication (depending on the transmit interval, 
        multiple packets with the same measurements can be sent, and there may be measurements that never were sent)
        """
        return (bytedata[11] & 0xFF) << 8 | bytedata[12] & 0xFF

# -------------------------------------------------------------------------------
    def _crc(self, *, bytedata):
        """ CRC8, used to check for correct decryption """
        return bytedata[17] & 0xFF

# -------------------------------------------------------------------------------
    def _tagid(self, *, bytedata):
        """ 48bit MAC address """
        return ':'.join('{:02X}'.format(x) for x in bytedata[18:24])

# -------------------------------------------------------------------------------
    def _rssi(self, *, bytedata):
        """ rssi is last byte of the hcidump --raw output """
        try:
            l_unsigned = bytedata[24] & 0xFF
            return l_unsigned-256 if l_unsigned>127 else l_unsigned
        except:
            return None

# -------------------------------------------------------------------------------
    def decode(self, *, tagdata, minmax):
        try:
            l_bytedata = bytearray.fromhex(tagdata)
            if len(l_bytedata) >= ruuvitag_df8.DATALEN:
                return {
                    '_df': _DF,
                    'humidity': self._humidity(bytedata=l_bytedata, minmax=minmax.get('humidity', None)),
                    'temperature': self._temperature(bytedata=l_bytedata, minmax=minmax.get('temperature', None)),
                    'pressure': self._pressure(bytedata=l_bytedata, minmax=minmax.get('pressure', None)),
                    'tx_power': self._txpower(bytedata=l_bytedata),
                    'battery': self._battery(bytedata=l_bytedata),
                    'movement_counter': self._movementcounter(bytedata=l_bytedata),
                    'sequence_number': self._sequencenumber(bytedata=l_bytedata),
                    'tagid': self._tagid(bytedata=l_bytedata),
                    'rssi': self._rssi(bytedata=l_bytedata)
                }
            else:
                logger.error(f'>>> Data too short: len:{len(l_bytedata)} tagdata:{tagdata}')
        except ValueError:
            logger.warning(f'>>> ValueError: tagdata:{tagdata}')
        except:
            logger.exception(f'*** exception tagdata not valid: {tagdata}')
        
        return None