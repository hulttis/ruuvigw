# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag df5 - formating dataformat 5
# Copyright:    (c) 2019 TK
# Licence:      MIT
#
# data format:  https://github.com/ruuvi/ruuvi-sensor-protocols
# rawdata 043E2B02010301B4DA2618D7CB1F0201061BFF99040516EC5238C574FCE4FD8CFFEC99769A6221CBD71826DAB4BC
#                                                   --------------------------------------------------
# 05            data format         0
# 16EC          temperature         1
# 5238          humidity            3
# C574          pressure            5
# FCE4          acceleration x      7
# FD8C          acceleration y      9
# FFEC          acceleration z      11
# 9976          power info          13
# 9A            movement counter    15
# 6221          sequence number     16
# CBD71826DAB4  mac                 18
# -------------------------------------------------------------------------------
import logging
logger = logging.getLogger('ruuvitag')

import math
from .ruuvitag_misc import (
    twos_complement,
    rshift,
    get_field_adjustment
)

_DF = 5
ROUND_TEMPERATURE = 3
ROUND_HUMIDITY = 4
ROUND_PRESSURE = 2
ROUND_VOLTAGE = 3
ROUND_TXPOWER = 0
ROUND_ACCELERATION = 3

# -------------------------------------------------------------------------------
class ruuvitag_df5(object):
    DATAFORMAT = 'FF990405'
    DATALEN = 24
    DF = _DF

# -------------------------------------------------------------------------------
    def _temperature(self, *, mfdata, minmax, tagadjustsment):
        """ Temperature in celcius: -163.840 °C to +163.830 °C in 0.005 °C increments """
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
        l_temperature += get_field_adjustment('temperature', tagadjustsment)
        if l_temperature < l_min or l_temperature > l_max:
            l_txt = f'''Temperature out of limits: value:{l_temperature} min:{l_min} max:{l_max} adjustment:{get_field_adjustment('humidity', tagadjustsment)}'''
            logger.warning(f'>>> {l_txt}')
            raise ValueError(l_txt)
        return round(l_temperature, ROUND_TEMPERATURE)

# -------------------------------------------------------------------------------
    def _humidity(self, *, mfdata, minmax, tagadjustsment):
        """ Humidity in %: 0.0 % to 100 % in 0.0025 % increments. """
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
        l_humidity += get_field_adjustment('humidity', tagadjustsment)
        if l_humidity < l_min or l_humidity > l_max:
            l_txt = f'''Humidity out of limits: value:{l_humidity} min:{l_min} max:{l_max} adjustment:{get_field_adjustment('humidity', tagadjustsment)}'''
            logger.warning(f'>>> {l_txt}')
            raise ValueError(l_txt)
        return round(l_humidity, ROUND_TEMPERATURE)

# -------------------------------------------------------------------------------
    def _pressure(self, *, mfdata, minmax, tagadjustsment):
        """ Atmospheric Pressure in hPa; 500 hPa to 1155.36 hPa in 0.01 hPa increments """
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
        if (mfdata[7:8] == 0x7FFF or
                mfdata[9:10] == 0x7FFF or
                mfdata[11:12] == 0x7FFF):
            return (None, None, None)

        l_acc_x = round(twos_complement((mfdata[7] << 8) + mfdata[8], 16), ROUND_ACCELERATION)
        l_acc_y = round(twos_complement((mfdata[9] << 8) + mfdata[10], 16), ROUND_ACCELERATION)
        l_acc_z = round(twos_complement((mfdata[11] << 8) + mfdata[12], 16), ROUND_ACCELERATION)
        return (l_acc_x, l_acc_y, l_acc_z)

# -------------------------------------------------------------------------------
    def _powerinfo(self, *, mfdata):
        """
        Power info (11+5bit unsigned), first 11bits unsigned is the battery voltage above 1.6V, 
        in millivolts (1.6V to 3.647V range). last 5 bits unsigned is the TX power above -40dBm, 
        in 2dBm steps. (-40dBm to +24dBm range)        
        """
        l_power_info = (mfdata[13] & 0xFF) << 8 | (mfdata[14] & 0xFF)
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
        """ Movement counter (8bit unsigned), incremented by motion detection interrupts from LIS2DH12 """
        return mfdata[15] & 0xFF

# -------------------------------------------------------------------------------
    def _sequencenumber(self, *, mfdata):
        """ Measurement sequence number (16bit unsigned), each time a measurement is taken, 
        this is incremented by one, used for measurement de-duplication (depending on the transmit interval, 
        multiple packets with the same measurements can be sent, and there may be measurements that never were sent)
        """
        return (mfdata[16] & 0xFF) << 8 | mfdata[17] & 0xFF

# -------------------------------------------------------------------------------
    def _tagid(self, *, mfdata):
        """ 48bit MAC address """
        return ':'.join('{:02X}'.format(x) for x in mfdata[18:24])

# -------------------------------------------------------------------------------
    # def _rssi(self, *, mfdata):
    #     """ rssi is last byte of the hcidump --raw output """
    #     try:
    #         l_unsigned = mfdata[24] & 0xFF
    #         return l_unsigned-256 if l_unsigned>127 else l_unsigned
    #     except:
    #         return None

# -------------------------------------------------------------------------------
    def decode(self, *, mfdata, minmax, tagadjustsment):
        try:
            if len(mfdata) >= ruuvitag_df5.DATALEN:
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