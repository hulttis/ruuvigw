# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag misc - miscellanous stuff
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
import sys
import time

def get_us():
    if sys.version_info >= (3,7):
        return int(time.perf_counter_ns()/1000)
    else:
        return int(time.perf_counter()*1000000)

def get_sec():
    return int(time.perf_counter())
