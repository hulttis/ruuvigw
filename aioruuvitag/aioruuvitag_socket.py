# coding=utf-8
# !/usr/bin/python3
# Name:         ruuvitag_socket - bluetooth receiver
# Copyright:    (c) 2019 TK
# Licence:      MIT
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
from .ble_data import BLEData

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
        callback,
        scheduler=None,
        device='hci0', 
        mfids=None, 
        device_reset=False,
        device_timeout=10000,
        **kwargs
    ):
        logger.info(f'>>> device:{device}')

        if not loop:
            raise ValueError(f'loop is None')
        self._loop = loop
        if not callback:
            raise ValueError(f'callback is None')
        self._callback = callback
        self._stopevent = asyncio.Event()

        self._scheduler = scheduler
        self._mfids = mfids
        self._device_reset = device_reset
        self._device_timeout = (device_timeout/1000)    # ms --> s

        self._task = None
        self._socket = None
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
        return f'ruuvitag_socket device_id:{self._device_id} mfids:{self._mfids} device_reset:{self._device_reset} device_timeout:{self._device_timeout}'

# ------------------------------------------------------------------------------
    def __del__(self):
        # logger.debug(f'>>> enter')
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
                logger.exception(f'>>> jobid:{l_jobid}')

#-------------------------------------------------------------------------------
    async def _do_socket_timeout(self, *,
        jobid, 
        reset=False
    ):
        """
        Supervises reception of the socket data
        Restarts socket if no data received within device_timeout period
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
                logger.exception(f'>>> jobid:{jobid}')

# ------------------------------------------------------------------------------
    def _open(self):
        logger.debug(f'>>> device_id:{self._device_id}')

        if self._socket:
            self._close()
        
        try:
            self._socket = socket.socket(family=socket.AF_BLUETOOTH, type=socket.SOCK_RAW, proto=socket.BTPROTO_HCI)
            self._socket.setblocking(False)
            self._socket.bind((self._device_id,))
        except:
            self._socket = None
            logger.exception(f'>>> exception')

        logger.debug(f'>>> socket:{self._socket}')

# ------------------------------------------------------------------------------
    def _close(self):
        logger.debug(f'>>> device_id:{self._device_id}')

        try:
            if self._socket:
                self._socket.close()
                self._socket = None
        except:
            logger.exception(f'>>> exception')

# ------------------------------------------------------------------------------
    def _send_cmd(self, *, cmd, data):
        if self._socket:
            logger.debug(f'>>> device_id:{self._device_id} cmd:{cmd} data:{data}')
            try:
                l_arr = array.array('B', data)
                fcntl.ioctl(self._socket.fileno(), cmd, l_arr)
            except:
                logger.exception(f'>>> exception')

# ------------------------------------------------------------------------------
    def _send_cmd_value(self,*, cmd, value):
        if self._socket:
            logger.debug(f'>>> device_id:{self._device_id} cmd:{value} data:{value}')
            try:
                fcntl.ioctl(self._socket.fileno(), cmd, value)
            except:
                logger.exception(f'>>> exception')

# ------------------------------------------------------------------------------
    def _send_data(self, *, data):
        if self._socket:
            logger.debug(f'>>> device_id:{self._device_id} data:{data}')
            try:
                self._socket.send(data)
            except:
                logger.exception(f'>>> exception')

# ------------------------------------------------------------------------------
    def _set_filter(self, *, data):
        if self._socket:
            logger.debug(f'>>> device_id:{self._device_id} data:{data}')
            try:
                self._socket.setsockopt(socket.SOL_HCI, socket.HCI_FILTER, data)
            except:
                logger.exception(f'>>> exception')

# ------------------------------------------------------------------------------
    def _device_on(self):
        logger.debug(f'>>> device_id:{self._device_id}')
        self._send_cmd_value(cmd=ruuvitag_socket.HCIDEVUP, value=self._device_id)

# ------------------------------------------------------------------------------
    def _device_off(self):
        logger.debug(f'>>> device_id:{self._device_id}')
        self._send_cmd_value(cmd=ruuvitag_socket.HCIDEVDOWN, value=self._device_id)

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

# -------------------------------------------------------------------------------
    async def _get_data(self, *, data):
        """
        Gets data from the received socket data
        """
        # logger.debug(f'>>> device_id:{self._device_id} data:{hex_string(data=data)}')
        try:
            if data[0] == ruuvitag_socket.HCI_EVENT_PKT and data[1] == ruuvitag_socket.EVT_LE_META_EVENT:
                _, _, l_len = struct.unpack("<BBB", data[:3])
                return (data[3:], l_len)
        #     else:
        #         logger.debug(f'>>> Unhandled HCI event packet, subtype={data[1]} data:{hex_string(data=data)}')
        except:
            pass
        return (None, 0)

# -------------------------------------------------------------------------------
    async def _handle_data(self, *, data):        
        """
        Handles received data from the socket
        """
        # logger.debug(f'>>> device_id:{self._device_id} data:{hex_string(data=data)}')
        (l_data, l_len) = await self._get_data(data=data)
        if not l_data:
            return

        l_mfid = 0xFFFF
        try:
            l_mac = ":".join(reversed(["{:02X}".format(x) for x in l_data[4:][:6]]))
            l_rssi = l_data[l_len-1] & 0xFF
            l_rssi = l_rssi-256 if l_rssi>127 else l_rssi
            l_mfid = (l_data[16] & 0xFF) + ((l_data[17] & 0xFF) * 256)
            if not self._mfids or l_mfid in self._mfids:
                l_mfdata = l_data[18:l_len-1]
                logger.debug(f'''>>> device_id:{self._device_id} mac:{l_mac} rssi:{l_rssi} mfid:{l_mfid} mflen:{len(l_mfdata)} mfdata:{hex_string(data=l_mfdata,filler='')}''')
                try:
                    self._data_ts = get_sec()
                    await self._callback(bledata=BLEData(
                        mac = l_mac,
                        rssi = l_rssi,
                        mfid = l_mfid,
                        mfdata = l_mfdata,
                        rawdata = data
                    ))
                except:
                    logger.exception(f'>>> exception')
        except:
            # logger.exception(f'>>> exception')
            pass
        
        return None

# -------------------------------------------------------------------------------
    async def run(self):
        logger.info(f'>>> starting')

        if self._device_reset:
            logger.info(f'>>> restarting Bluetooth device_id:{self._device_id}')
            self._device_off()
            time.sleep(0.2)
            self._device_on()

        logger.info(f'>>> starting to receive from the AF_BLUETOOTH socket')
        self._open()
        self._start_scanning()

        while not self._stopevent.is_set():
            try:
                await self._handle_data(data=await self._loop.sock_recv(self._socket, 1024))
            except GeneratorExit:
                logger.error(f'>>> GeneratorExit')
                self._stopevent.set()
                break
            except asyncio.CancelledError:
                self._stopevent.set()
                logger.warning(f'>>> CanceledError')
                break
            except:
                logger.exception(f'>>> exception')
                pass
        
        self._stop_scanning()
        self._close()

        logger.info('>>> completed')

        return True

# -------------------------------------------------------------------------------
    def stop(self):
        """
        Stops AF_BLUETOOTH socket
        """
        # logger.info(f'>>> stop to receive for AF_BLUETOOTH socket')
        self._stopevent.set()

# -------------------------------------------------------------------------------
    # def task(self):
    #     """ Returns task """
    #     return self._task
