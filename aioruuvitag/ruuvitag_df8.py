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
    DF = _DF
    PASSWORD = 0x5275757669636f6d5275757669546167   # "RuuvicomRuuviTag"

# -------------------------------------------------------------------------------
    def _temperature(self, *, mfdata, minmax):
        """ Temperature in 0.005 degrees. """
        if mfdata[1:2] == 0x7FFF:
            return None

        l_min = -163.840
        l_max = 163.830
        if minmax:
            try:
                l_min = minmax['min']
                l_max = minmax['max']
            except:
                logger.debug(f'>>> minmax not defined: {minmax}')

        l_temperature = twos_complement((mfdata[1] << 8) + mfdata[2], 16) / 200
        # if l_temperature < -163.840 or l_temperature > +163.830:
        #     logger.error(f'>>> Temperature out of range: value:{l_temperature} mfdata[1]:{mfdata[1]} mfdata[2]:{mfdata[2]}')
        #     raise ValueError(f'Temperature out of range: value:{l_temperature} mfdata[1]:{mfdata[1]} mfdata[2]:{mfdata[2]}')
        if l_temperature < l_min or l_temperature > l_max:
            logger.warning(f'>>> Temperature out of limits: value:{l_temperature} min:{l_min} max:{l_max}')
            raise ValueError(f'Temperature out of limits: value:{l_temperature} min:{l_min} max:{l_max}')
        return round(l_temperature, ROUND_TEMPERATURE)

# -------------------------------------------------------------------------------
    def _humidity(self, *, mfdata, minmax):
        """ Humidity (16bit unsigned) in 0.0025% (0-163.83% range, though realistically 0-100%). """
        if mfdata[3:4] == 0xFFFF:
            return None

        l_min = 0
        l_max = 100.0
        if minmax:
            try:
                l_min = minmax['min']
                l_max = minmax['max']
            except:
                logger.debug(f'>>> minmax not defined: {minmax}')

        l_humidity = ((mfdata[3] & 0xFF) << 8 | mfdata[4] & 0xFF) / 400
        # if l_humidity < 0 or l_humidity > 100:
        #     logger.error(f'>>> Humidity out of range: value:{l_humidity} mfdata[3]:{mfdata[3]} mfdata[4]:{mfdata[4]}')
        #     raise ValueError(f'Humidity out of range: value:{l_humidity} mfdata[3]:{mfdata[3]} mfdata[4]:{mfdata[4]}')
        if l_humidity < l_min or l_humidity > l_max:
            logger.warning(f'>>> Humidity out of limits: value:{l_humidity} min:{l_min} max:{l_max}')
            raise ValueError(f'Humidity out of limits: value:{l_humidity} min:{l_min} max:{l_max}')
        return round(l_humidity, ROUND_TEMPERATURE)

# -------------------------------------------------------------------------------
    def _pressure(self, *, mfdata, minmax):
        """ Pressure (16bit unsigned) in 1 Pa units, with offset of -50 000 Pa. """
        if mfdata[5:6] == 0xFFFF:
            return None

        l_min = 500
        l_max = 1155.36
        if minmax:
            try:
                l_min = minmax['min']
                l_max = minmax['max']
            except:
                logger.debug(f'>>> minmax not defined: {minmax}')

        l_pressure = ((mfdata[5] & 0xFF) << 8 | mfdata[6] & 0xFF) + 50000
        l_pressure = round((l_pressure / 100), 2)
        # if l_pressure < 500 or l_pressure > 1155.36:
        #     logger.error(f'>>> Pressure out of range: value:{l_pressure} mfdata[5]:{mfdata[5]} mfdata[6]:{mfdata[6]}')
        #     raise ValueError(f'Pressure out of range: value:{l_pressure} mfdata[5]:{mfdata[5]} mfdata[6]:{mfdata[6]}')
        if l_pressure < l_min or l_pressure > l_max:
            logger.warning(f'>>> Pressure out of limits: value:{l_pressure} min:{l_min} max:{l_max}')
            raise ValueError(f'Pressure out of limits: value:{l_pressure} min:{l_min} max:{l_max}')
        return round(l_pressure, ROUND_PRESSURE)

# -------------------------------------------------------------------------------
    def _powerinfo(self, *, mfdata):
        """
        Power info (11+5bit unsigned), first 11 bits is the battery voltage above 1.6V, 
        in millivolts (1.6V to 3.646V range). Last 5 bits unsigned are the TX power above -40dBm, 
        in 2dBm steps. (-40dBm to +20dBm range).        
        """
        l_power_info = (mfdata[7] & 0xFF) << 8 | (mfdata[8] & 0xFF)
        l_battery_voltage = rshift(l_power_info, 5) + 1600
        l_tx_power = (l_power_info & 0b11111) * 2 - 40

        if rshift(l_power_info, 5) == 0b11111111111:
            l_battery_voltage = None
        if (l_power_info & 0b11111) == 0b11111:
            l_tx_power = None

        return (round(l_battery_voltage, ROUND_VOLTAGE), round(l_tx_power, ROUND_TXPOWER))

# -------------------------------------------------------------------------------
    def _battery(self, *, mfdata):
        """ Battery Voltage in mV: 1600 mV to 3647 mV in 1 mV increments, practically 1800 ... 3600 mV """
        return self._powerinfo(mfdata=mfdata)[0]

# -------------------------------------------------------------------------------
    def _txpower(self, *, mfdata):
        """ Ruuvitag transmitting power: -40 dBm to +22 dBm in 2 dBm increments """
        return self._powerinfo(mfdata=mfdata)[1]

# -------------------------------------------------------------------------------
    def _movementcounter(self, *, mfdata):
        """ Movement counter (16 bit unsigned), incremented by motion detection interrupts from accelerometer """
        return (mfdata[9] & 0xFF) << 8 | mfdata[10] & 0xFF

# -------------------------------------------------------------------------------
    def _sequencenumber(self, *, mfdata):
        """ Measurement sequence number (16bit unsigned), each time a measurement is taken, 
        this is incremented by one, used for measurement de-duplication (depending on the transmit interval, 
        multiple packets with the same measurements can be sent, and there may be measurements that never were sent)
        """
        return (mfdata[11] & 0xFF) << 8 | mfdata[12] & 0xFF

# -------------------------------------------------------------------------------
    def _crc(self, *, mfdata):
        """ CRC8, used to check for correct decryption """
        return mfdata[17] & 0xFF

# -------------------------------------------------------------------------------
    def _tagid(self, *, mfdata):
        """ 48bit MAC address """
        return ':'.join('{:02X}'.format(x) for x in mfdata[18:24])

# -------------------------------------------------------------------------------
    def _rssi(self, *, mfdata):
        """ rssi is last byte of the hcidump --raw output """
        try:
            l_unsigned = mfdata[24] & 0xFF
            return l_unsigned-256 if l_unsigned>127 else l_unsigned
        except:
            return None

# -------------------------------------------------------------------------------
    def decode(self, *, mfdata, minmax):
        try:
            if len(mfdata) >= ruuvitag_df8.DATALEN:
                return {
                    '_df': _DF,
                    'humidity': self._humidity(mfdata=mfdata, minmax=minmax.get('humidity', None)),
                    'temperature': self._temperature(mfdata=mfdata, minmax=minmax.get('temperature', None)),
                    'pressure': self._pressure(mfdata=mfdata, minmax=minmax.get('pressure', None)),
                    'tx_power': self._txpower(mfdata=mfdata),
                    'battery': self._battery(mfdata=mfdata),
                    'movement_counter': self._movementcounter(mfdata=mfdata),
                    'sequence_number': self._sequencenumber(mfdata=mfdata),
                    'tagid': self._tagid(mfdata=mfdata)
                }
            else:
                logger.error(f'>>> Data too short: len:{len(mfdata)} mfdata:{mfdata}')
        except ValueError:
            logger.warning(f'>>> ValueError: mfdata:{mfdata}')
        except:
            logger.exception(f'*** exception mfdata not valid: {mfdata}')
        
        return None