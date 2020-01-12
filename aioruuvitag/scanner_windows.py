# -*- coding: utf-8 -*-
"""
Perform Bluetooth LE Scan.

Based on https://github.com/hbldh/bleak/blob/master/bleak/backends/dotnet/discovery.py by 
Created by hbldh <henrik.blidh@nedomkull.com>

"""
import logging
logger = logging.getLogger('ruuvitag')

import asyncio
import queue

from bleak.backends.device import BLEDevice
# Import of Bleak CLR->UWP Bridge. It is not needed here, but it enables loading of Windows.Devices
from BleakBridge import Bridge
from System import Array, Byte
from Windows.Devices.Bluetooth.Advertisement import \
    BluetoothLEAdvertisementWatcher, BluetoothLEScanningMode
from Windows.Storage.Streams import DataReader, IBuffer

QUEUE_SIZE = 100
###############################################################################
async def scanner(
    outqueue: asyncio.Queue,
    stopevent: asyncio.Event,
    **kwargs
):
    """Perform a continuous Bluetooth LE Scan using Windows.Devices.Bluetooth.Advertisement
    Args:
        outqueue:  outgoing queue
        stopevent: stop event
        loop: asyncio event loop (not used, for compatibility)
        device: bluetooth device (not used, for compatibility)

    """
    watcher = BluetoothLEAdvertisementWatcher()
    q = queue.Queue(QUEUE_SIZE)

 # -----------------------------------------------------------------------------
    def _format_bdaddr(a):
        return ":".join("{:02X}".format(x) for x in a.to_bytes(6, byteorder="big"))

# -----------------------------------------------------------------------------
    def AdvertisementWatcher_Received(sender, e):
        if sender == watcher:
            # logger.debug("Received {0}.".format(_format_event_args(e)))
            l_bdaddr = _format_bdaddr(e.BluetoothAddress)
            l_uuids = []
            for l_u in e.Advertisement.ServiceUuids:
                l_uuids.append(l_u.ToString())
            l_data = {}
            for l_m in e.Advertisement.ManufacturerData:
                l_md = IBuffer(l_m.Data)
                l_b = Array.CreateInstance(Byte, l_md.Length)
                l_reader = DataReader.FromBuffer(l_md)
                l_reader.ReadBytes(l_b)
                l_data[l_m.CompanyId] = bytes(l_b)
            local_name = e.Advertisement.LocalName
            if q:
                q.put(BLEDevice(
                    l_bdaddr,
                    local_name,
                    e,
                    uuids=l_uuids,
                    manufacturer_data=l_data,
                ))
# -----------------------------------------------------------------------------

    watcher.Received += AdvertisementWatcher_Received
    watcher.ScanningMode = BluetoothLEScanningMode.Active

    # Watcher works outside of the Python process.
    watcher.Start()
    # communication loop
    while not stopevent.is_set():
        try:
            l_data = q.get_nowait()
            if l_data and outqueue:
                await outqueue.put(l_data)
        except queue.Empty:
            try:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                logger.warning(f'>>> CancelledError')
                pass
        except:
            logger.exception()
    watcher.Stop()

    try:
        watcher.Received -= AdvertisementWatcher_Received
    except:
        logger.exception(f'>>> Could not remove event handlers')

