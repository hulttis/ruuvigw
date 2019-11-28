# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag_socket - bluetooth receiver
# Copyright:    (c) 2019 TK
# Licence:      MIT
#
# Thanks to: https://github.com/TheCellule/python-bleson
#
# AF_BLUETOOTH socket scanner
# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('ruuvitag')

import time
import array
import fcntl
import socket
import struct
import asyncio
from contextlib import suppress

from .ruuvitag_misc import hex_string, get_sec

# ==============================================================================
# ruuvitag_socket class
# ==============================================================================
class ruuvitag_socket(object):
    # constants
    HCI_COMMAND_PKT             = 0x01
    HCI_EVENT_PKT               = 0x04
    EVT_LE_META_EVENT           = 0x3e
    EVT_CMD_COMPLETE            = 0x0e
    EVT_CMD_STATUS              = 0x0f
    HCIDEVUP                    = 0x400448c9  # 201
    HCIDEVDOWN                  = 0x400448ca  # 202
    HCIGETDEVINFO               = -2147202861 #0x800448d3L  # _IOR(ord('H'), 211, 4)
    OGF_LE_CTL                  = 0x08
    OCF_LE_SET_SCAN_PARAMETERS  = 0x000B
    OCF_LE_SET_SCAN_ENABLE      = 0x000C
    LE_SET_SCAN_PARAMETERS_CMD  = OCF_LE_SET_SCAN_PARAMETERS | OGF_LE_CTL << 10
    LE_SET_SCAN_ENABLE_CMD      = OCF_LE_SET_SCAN_ENABLE | OGF_LE_CTL << 10
    SCAN_TYPE_ACTIVE            = 0x01
    LE_PUBLIC_ADDRESS           = 0x00
    FILTER_POLICY_NO_WHITELIST  = 0x00
# ------------------------------------------------------------------------------
    def __init__(self, *, 
        loop,
        scheduler=None,
        device=0, 
        minlen=0, 
        device_reset=False, 
        device_timeout=10000,   # ms 
        **kwargs
    ):
        logger.info(f'>>> device:{device}')

        if not loop:
            raise ValueError(f'loop is not defined')

        self._loop = loop
        self._scheduler = scheduler
        self._device_reset = device_reset
        self._device_timeout = (device_timeout/1000)    # ms --> s
        self._minlen = minlen

        self._task = None
        self._socket = None
        self._get_lines_stop = asyncio.Event()
        self._data_ts = 0
        self._device_id = 0
        if device:
            if isinstance(device, int):
                self._device_id = device
            else:
                self._device_id = int(device.replace('hci', ''))
        logger.info(f'>>> {self}')

# -------------------------------------------------------------------------------
    def __repr__(self):
        return f'ruuvitag_socket device_id:{self._device_id} minlen:{self._minlen} device_reset:{self._device_reset} device_timeout:{self._device_timeout}'

# ------------------------------------------------------------------------------
    def __del__(self):
        logger.debug(f'>>> enter')
        self.stop()

#-------------------------------------------------------------------------------
    def _schedule(self):
        """
        Initializes scheduler for hci device nodata checking
        """
        logger.debug(f'>>> enter {type(self._scheduler)} device_timeout:{self._device_timeout}')

        if not self._scheduler:
            return

        if self._device_timeout:
            l_jobid = f'socket_timeout'
            try:
                self._scheduler.add_job(
                    self._do_socket_timeout,
                    'interval',
                    seconds = 1,
                    kwargs = {
                        'jobid': l_jobid,
                        'reset': self._device_reset
                    },
                    id = l_jobid,
                    replace_existing = True,
                    max_instances = 1,
                    coalesce = True,
                    next_run_time = _dt.now()+timedelta(seconds=self._device_timeout)
                )
                logger.info(f'>>> jobid:{l_jobid} scheduled')
            except:
                logger.exception(f'*** jobid:{l_jobid}')

#-------------------------------------------------------------------------------
    async def _do_socket_timeout(self, *,
        jobid, 
        reset=False
    ):
        """
        Supervises reception of the hci data
        Restarts hci device if no data received within timeout period - device_timeout
        """
        l_now = get_sec()
        if (l_now - self._data_ts) > self._device_timeout:
            logger.warning(f'>>> jobid:{jobid} device_timeout timer ({self._device_timeout}ms) expired')
            try:
                logger.info(f'>>> jobid:{jobid} restarting device:{self._device_id}')
                self._close()
                if reset:
                    self._device_off()
                    asyncio.sleep(0.2)
                    self._device_on()
                self._open()
            except:
                logger.exception(f'*** jobid:{jobid}')

# ------------------------------------------------------------------------------
    def _open(self):
        logger.debug(f'>>> device_id:{self._device_id}')

        if self._socket:
            self._close()

        self._socket = socket.socket(family=socket.AF_BLUETOOTH, type=socket.SOCK_RAW, proto=socket.BTPROTO_HCI)
        self._socket.setblocking(False)
        self._socket.bind((self._device_id,))
        logger.debug(f'>>> socket:{self._socket}')

# ------------------------------------------------------------------------------
    def _close(self):
        logger.debug(f'>>> device_id:{self._device_id}')

        if self._socket:
            self._socket.close()
            self._socket = None

# -------------------------------------------------
    def _device_on(self):
        logger.debug(f'>>> device_id:{self._device_id}')
        self._send_cmd_value(cmd=ruuvitag_socket.HCIDEVUP, value=self._device_id)

# -------------------------------------------------
    def _device_off(self):
        logger.debug(f'>>> device_id:{self._device_id}')
        self._send_cmd_value(cmd=ruuvitag_socket.HCIDEVDOWN, value=self._device_id)

# ------------------------------------------------------------------------------
    def _send_cmd(self, *, cmd, data):
        if self._socket:
            logger.debug(f'>>> device_id:{self._device_id} cmd:{cmd} data:{data}')
            l_arr = array.array('B', data)
            fcntl.ioctl(self._socket.fileno(), cmd, l_arr)

# ------------------------------------------------------------------------------
    def _send_cmd_value(self,*, cmd, value):
        if self._socket:
            logger.debug(f'>>> device_id:{self._device_id} cmd:{value} data:{value}')
            fcntl.ioctl(self._socket.fileno(), cmd, value)

# ------------------------------------------------------------------------------
    def _send_data(self, *, data):
        if self._socket:
            logger.debug(f'>>> device_id:{self._device_id} data:{data}')
            self._socket.send(data)

# ------------------------------------------------------------------------------
    def _set_filter(self, *, data):
        if self._socket:
            logger.debug(f'>>> device_id:{self._device_id} data:{data}')
            self._socket.setsockopt(socket.SOL_HCI, socket.HCI_FILTER, data)

# ------------------------------------------------------------------------------
    def _set_scan_filter(self):
        logger.debug(f'>>> device_id:{self._device_id}')

        l_typeMask   = 1 << ruuvitag_socket.HCI_EVENT_PKT
        l_eventMask1 = (1 << ruuvitag_socket.EVT_CMD_COMPLETE) | (1 << ruuvitag_socket.EVT_CMD_STATUS)
        l_eventMask2 = 1 << (ruuvitag_socket.EVT_LE_META_EVENT - 32)
        l_opcode     = 0

        l_filter = struct.pack("<LLLH", l_typeMask, l_eventMask1, l_eventMask2, l_opcode)
        self._set_filter(data=l_filter)

# ------------------------------------------------------------------------------
    def _set_scan_parameters(self):
        logger.debug(f'>>> device_id:{self._device_id}')

        l_len = 7
        l_type = ruuvitag_socket.SCAN_TYPE_ACTIVE
        l_internal = 0x0010   #  ms * 1.6
        l_window = 0x0010     #  ms * 1.6
        l_own_addr  = ruuvitag_socket.LE_PUBLIC_ADDRESS
        l_filter = ruuvitag_socket.FILTER_POLICY_NO_WHITELIST
        l_cmd = struct.pack("<BHBBHHBB", ruuvitag_socket.HCI_COMMAND_PKT, ruuvitag_socket.LE_SET_SCAN_PARAMETERS_CMD,
                            l_len, l_type, l_internal, l_window, l_own_addr, l_filter )
        self._send_data(data=l_cmd)

# ------------------------------------------------------------------------------
    def _enable_scan(self, *, enabled=False, filter_duplicates=False):
        logger.debug(f'>>> device_id:{self._device_id} enabled:{str(enabled)} filter_duplicates:{filter_duplicates}')

        l_len = 2
        enable = 0x01 if enabled else 0x00
        dups   = 0x01 if filter_duplicates else 0x00
        l_cmd = struct.pack("<BHBBB", ruuvitag_socket.HCI_COMMAND_PKT, ruuvitag_socket.LE_SET_SCAN_ENABLE_CMD,
                            l_len, enable, dups)
        self._send_data(data=l_cmd)

# ------------------------------------------------------------------------------
    def _start_scanning(self):
        logger.debug(f'>>> device_id:{self._device_id}')

        self._enable_scan(enabled=False)
        self._set_scan_filter()
        self._set_scan_parameters()
        self._enable_scan(enabled=True, filter_duplicates=False)

# ------------------------------------------------------------------------------
    def _stop_scanning(self):
        logger.debug(f'>>> device_id:{self._device_id}')

        self._enable_scan(enabled=False)

# ------------------------------------------------------------------------------
    async def _get_data(self, *, socdata):
        logger.debug(f'>>> device_id:{self._device_id} socdata:{hex_string(data=socdata)}')

        if socdata:
            if socdata[0] == ruuvitag_socket.HCI_EVENT_PKT:
                if socdata[1] == ruuvitag_socket.EVT_LE_META_EVENT:
                    _, _, l_len = struct.unpack("<BBB", socdata[:3])
                    if l_len >= self._minlen:  # check enough data received
                        return hex_string(data=socdata, filler='')
                else:
                    logger.debug(f'>>> Unhandled HCI event packet, subtype={socdata[1]} socdata:{hex_string(data=socdata)}')
            else:
                logger.debug(f'>>> Unhandled HCI packet, type={socdata[0]} socdata:{hex_string(data=socdata)}')
        return None

# ------------------------------------------------------------------------------
    async def _get_lines(self, *,
        loop,
        callback
    ):
        """
        Receives data from socket
        """
        logger.debug(f'>>> device_id:{self._device_id}')

        self._data_ts = 0
        try:
            while not self._get_lines_stop.is_set():
                try:
                    l_socdata = await loop.sock_recv(self._socket, 1024)
                    self._data_ts = get_sec()
                    l_rawdata = await self._get_data(socdata=l_socdata)
                    if l_rawdata:
                        await callback(rawdata=l_rawdata)
                    # await asyncio.sleep(0.01)
                except asyncio.TimeoutError:
                    logger.error(f'>>> TimeoutError. restarting AF_BLUETOOTH socket')
                    self._close()
                    await asyncio.sleep(0.2)
                    self._open()
                    pass
                except asyncio.CancelledError:
                    logger.warning(f'>>> CanceledError')
                    return
        except Exception:
            logger.exception(f'*** exception')
        finally:
            self._close()


# -------------------------------------------------------------------------------
    def start(self, *,
        callback=None
    ):
        """
        Starts to receive from AF_BLUETOOTH socket
        """
        if not self._loop:
            print(f'self._loop is not defined')
            return False
        if not callback:
            print(f'>>> callback is not defined')
            return False

        if self._device_reset:
            logger.info(f'>>> restarting Bluetooth device_id:{self._device_id}')
            self._device_off()
            time.sleep(0.2)
            self._device_on()

        logger.info(f'>>> starting to receive from the AF_BLUETOOTH socket')
        self._open()
        self._start_scanning()
        self._task = self._loop.create_task(self._get_lines(loop=self._loop, callback=callback))
        logger.info('>>> get_lines task created')

        return True

# -------------------------------------------------------------------------------
    def stop(self):
        """
        Stops AF_BLUETOOTH socket
        """
        logger.info(f'>>> stop to receive from AF_BLUETOOTH socket')
        self._get_lines_stop.set()
        self._stop_scanning()
        self._close()

# -------------------------------------------------------------------------------
    def task(self):
        """ Returns task """
        return self._task
