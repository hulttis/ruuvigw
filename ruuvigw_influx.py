# coding=utf-8
#-------------------------------------------------------------------------------
# Name:        ruuvigw_influx.py
# Purpose:     ruuvigw influx client
# Copyright:   (c) 2019 TK
# Licence:     MIT
#-------------------------------------------------------------------------------
import logging
logger = logging.getLogger('influx')

from influx_aioclient import influx_aioclient as _influx
import ruuvigw_defaults as _def

# ==================================================================================

class ruuvi_influx(_influx):
#-------------------------------------------------------------------------------
    def __init__(self, *,
        cfg,
        hostname,
        inqueue,
        # fbqueue,
        loop,
        scheduler,
        nameservers=None
    ):
        """
            cfg - influx configuration
            hostname - name of the system
            inqueue - incoming queue for data
            fbqueue - feedback queue for parent
            loop - asyncio loop
            scheduler - used scheduler for scheduled tasks
            nameservers - list of used name servers
        """
        super().__init__(
            cfg=cfg,
            inqueue=inqueue,
            # fbqueue=fbqueue,
            loop=loop,
            scheduler=scheduler,
            nameservers=nameservers
        )
        self._funcs['execute_ruuvi'] = self._execute_dict

        logger.info(f'{self._name} initialized')

#-------------------------------------------------------------------------------


