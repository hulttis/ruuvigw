# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag_decode - decoding ruuvitag data
# Copyright:    (c) 2019 TK
# Licence:      MIT
#
# Dataformat: https://github.com/ruuvi/ruuvi-sensor-protocols
# -------------------------------------------------------------------------------
import logging
logger = logging.getLogger('ruuvitag')

from .ruuvitag_df3 import ruuvitag_df3 as _df3
from .ruuvitag_df5 import ruuvitag_df5 as _df5
from .ruuvitag_df8 import ruuvitag_df8 as _df8

# -------------------------------------------------------------------------------
class ruuvitag_decode():
    DATAFORMAT_3 = _df3.DATAFORMAT
    DATAFORMAT_5 = _df5.DATAFORMAT
    DATAFORMAT_8 = _df8.DATAFORMAT
# -------------------------------------------------------------------------------
    @staticmethod
    def decode(*, rawdata, minmax):
        """ 
        Decodes received rawdata with the correct decoder based on the dataformat 
        Returns json
        """
        try:
            (l_decoder, l_tagdata) = ruuvitag_decode._tagdata(rawdata=rawdata)
            if l_decoder:
                return l_decoder.decode(tagdata=l_tagdata, minmax=minmax)
            else:
                return None
        except ValueError:
            logger.error(f'>>> ValueError: rawdata:{rawdata}')
        except:
            logger.exception(f'*** exception')
        return None

    @staticmethod
    def _tagdata(*, rawdata):
        """ 
        Checks received data/dataformat from rawdata
        Returns decoder class and tagdata
        """
        if not rawdata:
            return (None, None)

        try:
            if ruuvitag_decode.DATAFORMAT_3 in rawdata:
                l_start = rawdata.index(ruuvitag_decode.DATAFORMAT_3) + len(ruuvitag_decode.DATAFORMAT_3)-2
                return (_df3(), rawdata[l_start:])

            if ruuvitag_decode.DATAFORMAT_5 in rawdata:
                l_start = rawdata.index(ruuvitag_decode.DATAFORMAT_5) + len(ruuvitag_decode.DATAFORMAT_5)-2
                return (_df5(), rawdata[l_start:])
        except ValueError:
            logger.error(f'>>> ValueError: rawdata:{rawdata}')
        except:
            logger.exception(f'*** exception')

        return (None, None)
