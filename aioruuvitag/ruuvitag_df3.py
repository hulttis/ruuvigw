# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag df3 - formating dataformat 3
# Copyright:    (c) 2019 TK
# Licence:      MIT
# data format:  https://github.com/ruuvi/ruuvi-sensor-protocols
# -------------------------------------------------------------------------------
import logging
logger = logging.getLogger('ruuvitag')

import math
from .ruuvitag_misc import (
    twos_complement,
    rshift,
    get_field_adjustment
)

_DF = 3
ROUND_TEMPERATURE = 2
ROUND_HUMIDITY = 1
ROUND_PRESSURE = 2
ROUND_VOLTAGE = 2
ROUND_TXPOWER = 0
ROUND_ACCELERATION = 3

# -------------------------------------------------------------------------------
class ruuvitag_df3(object):
    DATAFORMAT = 'FF990403'
    DATALEN = 14
    DF = _DF

# -------------------------------------------------------------------------------
    def _temperature(self, *, mfdata, minmax, tagadjustsment):
        """ Temperature in celcius: -127.99 °C to +127.99 °C in 0.01 °C increments """
        l_min = -127.99
        l_max = 127.99
        if minmax:
            try:
                l_min = minmax['min']
                l_max = minmax['max']
            except:
                logger.debug(f'>>> minmax not defined: {minmax}')

        l_temperature = (mfdata[2] & ~(1 << 7)) + (mfdata[3] / 100)
        if ((mfdata[2] >> 7) & 1):
            l_temperature *= -1
        l_temperature += get_field_adjustment('temperature', tagadjustsment)    
        
        if l_temperature < l_min or l_temperature > l_max:
            l_txt = f'''Temperature out of limits: value:{l_temperature} min:{l_min} max:{l_max} adjustment:{get_field_adjustment('humidity', tagadjustsment)}'''
            logger.warning(f'>>> {l_txt}')
            raise ValueError(l_txt)
        return round(l_temperature, ROUND_TEMPERATURE)

# -------------------------------------------------------------------------------
    def _humidity(self, *, mfdata, minmax, tagadjustsment):
        """ Humidity in %: 0.0 % to 100.0 % in 0.5 % increments """
        l_min = 0
        l_max = 100.0
        if minmax:
            try:
                l_min = minmax['min']
                l_max = minmax['max']
            except:
                logger.debug(f'>>> minmax not defined: {minmax}')

        l_humidity = round((mfdata[1] * 0.5), 1)
        l_humidity += get_field_adjustment('humidity', tagadjustsment)
        if l_humidity < l_min or l_humidity > l_max:
            l_txt = f'''Humidity out of limits: value:{l_humidity} min:{l_min} max:{l_max} adjustment:{get_field_adjustment('humidity', tagadjustsment)}'''
            logger.warning(f'>>> {l_txt}')
            raise ValueError(l_txt)
        return round(l_humidity, ROUND_HUMIDITY)

# -------------------------------------------------------------------------------
    def _pressure(self, *, mfdata, minmax, tagadjustsment):
        """ Atmospheric Pressure in hPa; 500 hPa to 1155.36 hPa in 0.01 hPa increments """
        l_min = 500
        l_max = 1155.36
        if minmax:
            try:
                l_min = minmax['min']
                l_max = minmax['max']
            except:
                logger.debug(f'>>> minmax not defined: {minmax}')

        l_pressure = (mfdata[4] << 8) + mfdata[5] + 50000
        l_pressure = round((l_pressure / 100), 3)
        l_pressure += get_field_adjustment('pressure', tagadjustsment)
        if l_pressure < l_min or l_pressure > l_max:
            l_txt = f'''Pressure out of limits: value:{l_pressure} min:{l_min} max:{l_max} adjustment:{get_field_adjustment('humidity', tagadjustsment)}'''
            logger.warning(f'>>> {l_txt}')
            raise ValueError(l_txt)
        return round(l_pressure, ROUND_PRESSURE)

# -------------------------------------------------------------------------------
    def _acceleration(self, *, mfdata):
        """ Acceleration in mG's: -32000 to 32000 (mG), however the sensor on RuuviTag supports only 16 G max (2 G in default configuration) """
        l_acc_x = round(twos_complement((mfdata[6] << 8) + mfdata[7], 16), ROUND_ACCELERATION)
        l_acc_y = round(twos_complement((mfdata[8] << 8) + mfdata[9], 16), ROUND_ACCELERATION)
        l_acc_z = round(twos_complement((mfdata[10] << 8) + mfdata[11], 16), ROUND_ACCELERATION)
        return (l_acc_x, l_acc_y, l_acc_z)

# -------------------------------------------------------------------------------
    def _battery(self, *, mfdata):
        """ Battery Voltage in mV: 0 mV to 65536 mV in 1 mV increments, practically 1800 ... 3600 mV """
        return round((mfdata[12] << 8) + mfdata[13], ROUND_VOLTAGE)

# -------------------------------------------------------------------------------
    # def _rssi(self, *, mfdata):
    #     """ rssi is last byte of the hcidump --raw output """
    #     try:
    #         l_unsigned = mfdata[14] & 0xFF
    #         return l_unsigned-256 if l_unsigned>127 else l_unsigned
    #     except:
    #         return None

# -------------------------------------------------------------------------------
    def decode(self, *, mfdata, minmax, tagadjustsment):
        try:
            if len(mfdata) >= ruuvitag_df3.DATALEN:
                l_acc_x, l_acc_y, l_acc_z = self._acceleration(mfdata=mfdata)
                return {
                    '_df': _DF,
                    'humidity': self._humidity(mfdata=mfdata, minmax=minmax.get('humidity', None), tagadjustsment=tagadjustsment),
                    'temperature': self._temperature(mfdata=mfdata, minmax=minmax.get('temperature', None), tagadjustsment=tagadjustsment),
                    'pressure': self._pressure(mfdata=mfdata, minmax=minmax.get('pressure', None), tagadjustsment=tagadjustsment),
                    'acceleration': round(math.sqrt(l_acc_x * l_acc_x + l_acc_y * l_acc_y + l_acc_z * l_acc_z), ROUND_ACCELERATION),
                    'acceleration_x': l_acc_x,
                    'acceleration_y': l_acc_y,
                    'acceleration_z': l_acc_z,
                    'battery': self._battery(mfdata=mfdata)
                }
            else:
                logger.error(f'>>> Data too short: len:{len(mfdata)} mfdata:{mfdata}')
        except ValueError:
            logger.warning(f'>>> ValueError: mfdata:{mfdata}')
        except:
            logger.exception(f'*** exception mfdata not valid: {mfdata}')

        return None

