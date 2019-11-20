# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag_dummy
#               just dummy - do nothing
# Copyright:    (c) 2019 TK
# Licence:      MIT
# -------------------------------------------------------------------------------
import logging
logger = logging.getLogger('ruuvitag')

class ruuvitag_dummy(object):
#-------------------------------------------------------------------------------
    def __init__(self):
        print(f'>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
        print(f'>>> Check that AF_BLUETOOTH socket is supported by Python                        <<<')
        print(f'>>> Check existence of hcidump and hcitool                                       <<<')
        print(f'>>> one of them is required to run ruuvigw                                       <<<')
        print(f'>>> check RUUVITAG.collector setting                                             <<<')
        print(f'>>>                                                                              <<<')
        print(f'>>> hcitool can be installed by: sudo apt -y install bluez bluez-hcitool         <<<')
        print(f'>>> for AF_BLUETOOTH socket support you might need to compile own python version <<<')
        print(f'>>> recommended to use Python 3.8.0 (3.7.4 should work as well)                  <<<')
        print(f'>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')

#-------------------------------------------------------------------------------
    def start(self, *, 
        callback
    ):
        if not callback:
            logger.critical(f'>>> callback not defined')
            return False

        return False

# -------------------------------------------------------------------------------
    def stop(self):
        pass

