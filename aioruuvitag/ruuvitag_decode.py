# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag_decode - decoding ruuvitag data
# Copyright:    (c) 2019 TK
# Licence:      MIT
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
    DF_3 = _df3.DF
    DF_5 = _df5.DF
    DF_8 = _df8.DF
# -------------------------------------------------------------------------------
    @staticmethod
    def decode(*, mfdata, minmax):
        """ 
        Decodes received rawdata with the correct decoder based on the dataformat 
        Returns json
        """
        try:
            l_decoder = ruuvitag_decode._decoder(mfdata=mfdata)
            if l_decoder:
                return l_decoder.decode(mfdata=mfdata, minmax=minmax)
            else:
                return None
        except ValueError:
            logger.error(f'>>> ValueError: mdata:{mfdata}')
        except:
            logger.exception(f'*** exception')
        return None

    # @staticmethod
    # def _tagdata(*, rawdata):
    #     """ 
    #     Checks received data/dataformat from rawdata
    #     Returns decoder class and tagdata
    #     """
    #     if not rawdata:
    #         return (None, None)

    #     try:
    #         if _df3.DATAFORMAT in rawdata:
    #             l_start = rawdata.index(_df3.DATAFORMAT) + len(_df3.DATAFORMAT)-2
    #             return (_df3(), rawdata[l_start:])

    #         if _df5.DATAFORMAT in rawdata:
    #             l_start = rawdata.index(_df5.DATAFORMAT) + len(_df5.DATAFORMAT)-2
    #             return (_df5(), rawdata[l_start:])

    #         if _df8.DATAFORMAT in rawdata:
    #             l_start = rawdata.index(_df8.DATAFORMAT) + len(_df8.DATAFORMAT)-2
    #             return (_df8(), rawdata[l_start:])

    #     except ValueError:
    #         logger.error(f'>>> ValueError: rawdata:{rawdata}')
    #     except:
    #         logger.exception(f'*** exception')

    #     return (None, None)

    @staticmethod
    def _decoder(*, mfdata):
        """ 
        Returns decoder class
        """
        if not mfdata:
            return None
        try:
            l_df = mfdata[0]
            if l_df == _df3.DF:
                return _df3()
            if l_df == _df5.DF:
                return _df5()
            if l_df == _df8.DF:
                return None
                # return _df8()
        except:
            pass
        return None
    
