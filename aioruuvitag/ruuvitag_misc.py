# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag misc - miscellanous ruuvitag
# Copyright:    (c) 2019 TK
# Licence:      MIT
# -------------------------------------------------------------------------------
import sys
import time

# ------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------------
def get_us():
    if sys.version_info >= (3,7):
        return int(time.perf_counter_ns()/1000)
    else:
        return int(time.perf_counter()*1000000)

# ------------------------------------------------------------------------------
def get_ms():
    return get_us()/1000

# ------------------------------------------------------------------------------
def get_sec():
    return int(time.perf_counter())
    
# ------------------------------------------------------------------------------
def hex_string(*, data, filler=' '):
    if not data:
        return None
    return ''.join('{:02X}{}'.format(x, filler) for x in data)

# -------------------------------------------------------------------------------
def rshift(val, n):
    return (val % 0x100000000) >> n

# -------------------------------------------------------------------------------
def twos_complement(val, bits):
    if (val & (1 << (bits - 1))) != 0:
        val = val - (1 << bits)
    return val

# -------------------------------------------------------------------------------
def get_field_adjustment(field, tagadjustsment):
    if not tagadjustsment:
        return 0
    try:
        return tagadjustsment[field]
    except:
        return 0
    return 0        
