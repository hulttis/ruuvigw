# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag calc - calculations
#
# Author:       Timo Koponen
#
# Created:      18.03.2019
# Copyright:    (c) 2019
# Licence:      Do not distribute
#
# required:
#
# -------------------------------------------------------------------------------
import logging
logger = logging.getLogger('aioruuvitag_ble')

import math

# -------------------------------------------------------------------------------
class ruuvitag_calc():
# -------------------------------------------------------------------------------
    @staticmethod
    def set_value(*, out, field, value):
        if value:
            out[field] = value
# -------------------------------------------------------------------------------
    @staticmethod
    def calc(*, datas, out):
        ruuvitag_calc.set_value(out=out, field='equilibriumVaporPressure', value=ruuvitag_calc.equilibriumVaporPressure(datas=datas))
        ruuvitag_calc.set_value(out=out, field='absoluteHumidity', value=ruuvitag_calc.absoluteHumidity(datas=datas))
        ruuvitag_calc.set_value(out=out, field='dewPoint', value=ruuvitag_calc.dewPoint(datas=datas))
        ruuvitag_calc.set_value(out=out, field='airDensity', value=ruuvitag_calc.airDensity(datas=datas))

# -------------------------------------------------------------------------------
    @staticmethod
    def equilibriumVaporPressure(*, datas):
        try:
            l_temp = float(datas['temperature'])
            return round((611.2 * math.exp(17.67 * l_temp / (243.5 + l_temp))), 3)
        except:
            return None
        return None

# -------------------------------------------------------------------------------
    @staticmethod
    def absoluteHumidity(*, datas):
        try:
            l_temp = float(datas['temperature'])
            l_humi = float(datas['humidity'])
            return round((ruuvitag_calc.equilibriumVaporPressure(datas=datas) * l_humi * 0.021674 / (273.15 + l_temp)), 3)
        except:
            return None
        return None

# -------------------------------------------------------------------------------
    @staticmethod
    def dewPoint(*, datas):
        try:
            l_humi = float(datas['humidity'])
            l_v = math.log(l_humi / 100 * ruuvitag_calc.equilibriumVaporPressure(datas=datas) / 611.2)
            return round(((-243.5 * l_v) / (l_v - 17.67)), 3)
        except:
            return None
        return None

# -------------------------------------------------------------------------------
    @staticmethod
    def airDensity(*, datas):
        """
        kg/m3
        """
        try:
            l_temp = float(datas['temperature'])
            l_humi = float(datas['humidity'])
            l_pres = float(datas['pressure'])
            return round((1.2929 * 273.15 / (l_temp + 273.15) * (l_pres - 0.3783 * l_humi / 100 * ruuvitag_calc.equilibriumVaporPressure(datas=datas)) / 101300)*100, 3)
        except:
            return None
        return None

