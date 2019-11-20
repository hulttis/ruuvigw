import sys
try:
    from socket import AF_BLUETOOTH
    print(f'### AF_BLUETOOTH')
except:
    print(f'*** AF_BLUETOOTH socket not supported by python')
    sys.exit()

import logging
logger = logging.getLogger(__name__)

import asyncio
from contextlib import suppress

from .aioruuvitag_socket import ruuvitag_socket as _ruuvi
from .ruuvitag_misc import hex_string

# -------------------------------------------------------------------------------
# -------------------------------------------------------------------------------
async def _rawdata(*, rawdata):
    print(f'rawdata: {hex_string(data=rawdata)}')

# -------------------------------------------------------------------------------
if __name__ == '__main__':

    l_loop = asyncio.get_event_loop()
    l_ruuvi = _ruuvi(
        device='hci0',
        minlen= 0
    )
    l_ruuvi._loop = l_loop
    l_ruuvi.start(callback=_rawdata)

    try:
        l_loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info('KeyboardInterrupt/SystemExit')
    finally:
        l_ruuvi.stop()
        with suppress(asyncio.CancelledError):
            l_loop.run_until_complete(l_ruuvi._task)
        l_loop.stop()
        l_loop.close()
