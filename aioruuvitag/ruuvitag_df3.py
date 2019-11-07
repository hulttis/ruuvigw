# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag df3 - formating dataformat 3
#
# Author:       Timo Koponen
#
# Created:      18.03.2019
# Copyright:    (c) 2019
# Licence:      Do not distribute
#
# data format:  https://github.com/ruuvi/ruuvi-sensor-protocols
# -------------------------------------------------------------------------------
import logging
logger = logging.getLogger('aioruuvitag_ble')

import math

_DF = 3
ROUND_TEMPERATURE = 2
ROUND_HUMIDITY = 1
ROUND_PRESSURE = 2
ROUND_VOLTAGE = 2
ROUND_TXPOWER = 0
ROUND_ACCELERATION = 3

# -------------------------------------------------------------------------------
def twos_complement(val, bits):
    if (val & (1 << (bits - 1))) != 0:
        val = val - (1 << bits)
    return val

# -------------------------------------------------------------------------------
class ruuvitag_df3(object):
    DATAFORMAT = 'FF990403'
    DATALEN = 14
# -------------------------------------------------------------------------------
    def _temperature(self, *, bytedata, minmax):
        """ Temperature in celcius: -127.99 °C to +127.99 °C in 0.01 °C increments """
        l_min = -127.99
        l_max = 127.99
        if minmax:
            try:
                l_min = minmax['min']
                l_max = minmax['max']
            except:
                logger.debug(f'>>> minmax not defined: {minmax}')

        l_temp = (bytedata[2] & ~(1 << 7)) + (bytedata[3] / 100)
        l_sign = (bytedata[2] >> 7) & 1
        if l_sign:
            l_temp = l_temp * -1
    
        # if l_temp < -127.99 or l_temp > 127.99:
        #     logger.error(f'>>> Temperature out of range: value:{l_temp} bytedata[2]:{bytedata[2]} bytedata[3]:{bytedata[3]}')
        #     raise ValueError(f'Temperature out of range: value:{l_temp} bytedata[2]:{bytedata[2]} bytedata[3]:{bytedata[3]}')
        if l_temp < l_min or l_temp > l_max:
            logger.warning(f'>>> Temperature out of limits: value:{l_temp} min:{l_min} max:{l_max}')
            raise ValueError(f'Temperature out of limits: value:{l_temp} min:{l_min} max:{l_max}')
        return round(l_temp, ROUND_TEMPERATURE)

# -------------------------------------------------------------------------------
    def _humidity(self, *, bytedata, minmax):
        """ Humidity in %: 0.0 % to 100.0 % in 0.5 % increments """
        l_min = 0
        l_max = 100.0
        if minmax:
            try:
                l_min = minmax['min']
                l_max = minmax['max']
            except:
                logger.debug(f'>>> minmax not defined: {minmax}')

        l_humidity = round((bytedata[1] * 0.5), 1)
        # if l_humidity < 0 or l_humidity > 100:
        #     logger.error(f'>>> Humidity out of range: value:{l_humidity} bytedata[1]:{bytedata[1]}')
        #     raise ValueError(f'Humidity out of range: value:{l_humidity} bytedata[1]:{bytedata[1]}')
        if l_humidity < l_min or l_humidity > l_max:
            logger.warning(f'>>> Humidity out of limits: value:{l_humidity} min:{l_min} max:{l_max}')
            raise ValueError(f'Humidity out of limits: value:{l_humidity} min:{l_min} max:{l_max}')
        return round(l_humidity, ROUND_HUMIDITY)

# -------------------------------------------------------------------------------
    def _pressure(self, *, bytedata, minmax):
        """ Atmospheric Pressure in hPa; 500 hPa to 1155.36 hPa in 0.01 hPa increments """
        l_min = 500
        l_max = 1155.36
        if minmax:
            try:
                l_min = minmax['min']
                l_max = minmax['max']
            except:
                logger.debug(f'>>> minmax not defined: {minmax}')

        l_pres = (bytedata[4] << 8) + bytedata[5] + 50000
        l_pres = round((l_pres / 100), 2)
        # if l_pres < 500 or l_pres > 1155.36:
        #     logger.error(f'>>> Pressure out of range: value:{l_pres} bytedata[4]:{bytedata[4]} bytedata[5]:{bytedata[5]}')
        #     raise ValueError(f'Pressure out of range: value:{l_pres}')
        if l_pres < l_min or l_pres > l_max:
            logger.warning(f'>>> Pressure out of limits: value:{l_pres} min:{l_min} max:{l_max}')
            raise ValueError(f'Pressure out of limits: value:{l_pres} min:{l_min} max:{l_max}')
        return round(l_pres, ROUND_PRESSURE)

# -------------------------------------------------------------------------------
    def _acceleration(self, *, bytedata):
        """ Acceleration in mG's: -32000 to 32000 (mG), however the sensor on RuuviTag supports only 16 G max (2 G in default configuration) """
        l_acc_x = round(twos_complement((bytedata[6] << 8) + bytedata[7], 16), ROUND_ACCELERATION)
        l_acc_y = round(twos_complement((bytedata[8] << 8) + bytedata[9], 16), ROUND_ACCELERATION)
        l_acc_z = round(twos_complement((bytedata[10] << 8) + bytedata[11], 16), ROUND_ACCELERATION)
        return (l_acc_x, l_acc_y, l_acc_z)

# -------------------------------------------------------------------------------
    def _battery(self, *, bytedata):
        """ Battery Voltage in mV: 0 mV to 65536 mV in 1 mV increments, practically 1800 ... 3600 mV """
        return round((bytedata[12] << 8) + bytedata[13], ROUND_VOLTAGE)

# -------------------------------------------------------------------------------
    def _rssi(self, *, bytedata):
        """ rssi is last byte of the hcidump --raw output """
        try:
            l_unsigned = bytedata[14] & 0xFF
            return l_unsigned-256 if l_unsigned>127 else l_unsigned
        except:
            return None

# -------------------------------------------------------------------------------
    def decode(self, *, tagdata, minmax):
        try:
            l_bytedata = bytearray.fromhex(tagdata)
            if len(l_bytedata) >= self.DATALEN:
                l_acc_x, l_acc_y, l_acc_z = self._acceleration(bytedata=l_bytedata)
                return {
                    '_df': _DF,
                    'humidity': self._humidity(bytedata=l_bytedata, minmax=minmax.get('humidity', None)),
                    'temperature': self._temperature(bytedata=l_bytedata, minmax=minmax.get('temperature', None)),
                    'pressure': self._pressure(bytedata=l_bytedata, minmax=minmax.get('pressure', None)),
                    'acceleration': round(math.sqrt(l_acc_x * l_acc_x + l_acc_y * l_acc_y + l_acc_z * l_acc_z), ROUND_ACCELERATION),
                    'acceleration_x': l_acc_x,
                    'acceleration_y': l_acc_y,
                    'acceleration_z': l_acc_z,
                    'battery': self._battery(bytedata=l_bytedata),
                    'rssi': self._rssi(bytedata=l_bytedata)
                }
            else:
                logger.error(f'>>> Data too short: len:{len(l_bytedata)} tagdata:{tagdata}')
        except ValueError:
            logger.warning(f'>>> ValueError: tagdata:{tagdata}')
        except:
            logger.exception(f'*** exception tagdata not valid: {tagdata}')

        return None

