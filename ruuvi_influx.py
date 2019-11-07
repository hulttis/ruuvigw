# coding=utf-8
#-------------------------------------------------------------------------------
# Name:        influx_aioclient.py
# Purpose:     influxdb
#
# Author:      Timo Koponen
#
# Created:     10/10/2017
# modified:    14/01/2019
# Copyright:   (c) 2017
# Licence:     <your licence>
#-------------------------------------------------------------------------------
import logging
logger = logging.getLogger(__name__)

from influx_aioclient import influx_aioclient as _influx
import defaults as _def

# ==================================================================================

class ruuvi_influx(_influx):
#-------------------------------------------------------------------------------
    def __init__(self, *,
        cfg,
        inqueue,
        loop,
        scheduler,
        nameservers=None
    ):
        super().__init__(
            cfg=cfg,
            inqueue=inqueue,
            loop=loop,
            scheduler=scheduler,
            nameservers=nameservers
        )
        self._funcs['execute_ruuvi'] = self._execute_dict

        logger.debug(f'{self._name} done')

#-------------------------------------------------------------------------------


