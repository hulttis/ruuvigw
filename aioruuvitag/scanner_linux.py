# -*- coding: utf-8 -*-
"""
Perform Bluetooth LE Scan.

Based on https://github.com/hbldh/bleak/blob/master/bleak/backends/bluezdbus/discovery.py
Created by hbldh <henrik.blidh@nedomkull.com>

"""
import logging
logger = logging.getLogger('bleak_scanner')

import asyncio
import queue

from .scanner_bledevice import BLEDevice
# import scanner_bluezdbus_defs as defs
from .scanner_bluezdbus_utils import validate_mac_address

# txdbus.client MUST be imported AFTER bleak.backends.bluezdbus.reactor!
from txdbus import client
from txdbus.error import RemoteError
from twisted.internet.asyncioreactor import AsyncioSelectorReactor
from twisted.internet.error import ReactorNotRunning

# DBus Interfaces
OBJECT_MANAGER_INTERFACE = "org.freedesktop.DBus.ObjectManager"
# PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"

# Bluez specific DBUS
BLUEZ_SERVICE = "org.bluez"
# ADAPTER_INTERFACE = "org.bluez.Adapter1"
DEVICE_INTERFACE = "org.bluez.Device1"
# BATTERY_INTERFACE = "org.bluez.Battery1"

# GATT interfaces
# GATT_MANAGER_INTERFACE = "org.bluez.GattManager1"
# GATT_PROFILE_INTERFACE = "org.bluez.GattProfile1"
# GATT_SERVICE_INTERFACE = "org.bluez.GattService1"
# GATT_CHARACTERISTIC_INTERFACE = "org.bluez.GattCharacteristic1"
# GATT_DESCRIPTOR_INTERFACE = "org.bluez.GattDescriptor1"

QUEUE_SIZE = 100
###############################################################################

# -----------------------------------------------------------------------------
def _filter_on_device(objs):
    for path, interfaces in objs.items():
        device = interfaces.get("org.bluez.Device1")
        if device is None:
            continue

        yield path, device

# -----------------------------------------------------------------------------
def _filter_on_adapter(objs, pattern="hci0"):
    # logger.debug(f'>>> objs:{objs} pattern:{pattern}')

    for path, interfaces in objs.items():
        adapter = interfaces.get("org.bluez.Adapter1")
        if adapter is None:
            continue

        if not pattern or pattern == adapter["Address"] or path.endswith(pattern):
            return path, interfaces

    raise Exception("Bluetooth adapter not found")

# -----------------------------------------------------------------------------
def _device_info(path, props):
    # logger.debug(f'>>> path:{path} props:{props}')

    try:
        name = props.get("Name", props.get("Alias", path.split("/")[-1]))
        address = props.get("Address", None)
        if address is None:
            try:
                address = path[-17:].replace("_", ":")
                if not validate_mac_address(address):
                    address = None
            except Exception:
                address = None
        rssi = props.get("RSSI", "?")
        return name, address, rssi, path
    except Exception:
        # logger.exception(e, exc_info=True)
        return None, None, None, None

# -----------------------------------------------------------------------------
async def scanner(
    loop: asyncio.AbstractEventLoop,
    outqueue: asyncio.Queue,
    stopevent: asyncio.Event,
    device: str = 'hci0',
    **kwargs
):
    """Perform a continuous Bluetooth LE Scan
    Args:
        loop: async event loop
        outqueue:  outgoing queue
        stopevent: stop event
        device: bluetooth device

    """
    logger.info(f'>>> scanner:linux device:{device}')

    q = queue.Queue(QUEUE_SIZE)
    devices = {}
    cached_devices = {}
    rules = list()

# -----------------------------------------------------------------------------
    def queue_put(msg_path):
        try:
            if msg_path in devices:
                props = devices[msg_path]
                name, address, _, _ = _device_info(msg_path, props)
                # logger.debug(f'>>> {name} {path} {address}')
                if q and address:
                    q.put(BLEDevice(
                        address,
                        name,
                        {"path": msg_path, "props": props},
                        uuids=props.get("UUIDs", []),
                        manufacturer_data=props.get("ManufacturerData", {})
                    ))
        except:
            logger.exception(f'>>> exception')

# -----------------------------------------------------------------------------
    def parse_msg(message):
        if message.member == "InterfacesAdded":
            logger.debug(f'>>> {message.member} {message.path}:{message.body}')

            msg_path = message.body[0]
            try:
                device_interface = message.body[1].get("org.bluez.Device1", {})
            except Exception as e:
                raise e
            # store device
            devices[msg_path] = ({**devices[msg_path], **device_interface} if msg_path in devices else device_interface)

            # put BLEDevice object to the queue
            logger.debug(f'>>> InterfacesAdded body:{msg_path}')
            queue_put(msg_path)
        elif message.member == "PropertiesChanged":
            logger.debug(f'>>> {message.member} {message.path}:{message.body}')
            msg_path = message.path
            iface, changed, _ = message.body
            if iface != DEVICE_INTERFACE:
                return

            # store changed info
            if msg_path not in devices and msg_path in cached_devices:
               devices[msg_path] = cached_devices[msg_path]
            devices[msg_path] = ({**devices[msg_path], **changed} if msg_path in devices else changed)

            # put BLEDevice object to the queue
            logger.debug(f'>>> PropertiesChanged body:{msg_path}')
            queue_put(msg_path)
        elif message.member == "InterfacesRemoved":
            logger.debug(f'>>> {message.member} {message.path}:{message.body}')
            return
        else:
            msg_path = message.path
            logger.warning(
                "{0}, {1} ({2}): {3}".format(
                    message.member, message.interface, message.path, message.body
                )
            )

# -----------------------------------------------------------------------------
    try:
        logger.info(f'>>> Starting...')
        # Connect to the txdbus
        reactor = AsyncioSelectorReactor(loop)
        bus = await client.connect(reactor, "system").asFuture(loop)

        # Add signal listeners
        rules.append(
            await bus.addMatch(
                parse_msg,
                interface="org.freedesktop.DBus.ObjectManager",
                member="InterfacesAdded",
            ).asFuture(loop)
        )
        rules.append(
            await bus.addMatch(
                parse_msg,
                interface="org.freedesktop.DBus.ObjectManager",
                member="InterfacesRemoved",
            ).asFuture(loop)
        )
        rules.append(
            await bus.addMatch(
                parse_msg,
                interface="org.freedesktop.DBus.Properties",
                member="PropertiesChanged",
            ).asFuture(loop)
        )

        # Find the HCI device to use for scanning and get cached device properties
        objects = await bus.callRemote(
            "/",
            "GetManagedObjects",
            interface=OBJECT_MANAGER_INTERFACE,
            destination=BLUEZ_SERVICE,
        ).asFuture(loop)
        adapter_path, interface = _filter_on_adapter(objects, device)
        logger.info(f'>>> device:{device} adapter_path:{adapter_path}')
        logger.debug(f'>>> interface:{interface}')
        cached_devices = dict(_filter_on_device(objects))
        logger.debug(f">>> cached_devices:{cached_devices}")

        # Running Discovery loop.
        await bus.callRemote(
            adapter_path,
            "SetDiscoveryFilter",
            interface="org.bluez.Adapter1",
            destination="org.bluez",
            signature="a{sv}",
            body=[{"Transport": "le"}],
        ).asFuture(loop)
        await bus.callRemote(
            adapter_path,
            "StartDiscovery",
            interface="org.bluez.Adapter1",
            destination="org.bluez",
        ).asFuture(loop)

        # Run Communication loop
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
                    break
            except:
                logger.exception(f'>>> exception')
                break
        try:
            await bus.callRemote(
                adapter_path,
                "StopDiscovery",
                interface="org.bluez.Adapter1",
                destination="org.bluez",
            ).asFuture(loop)
        except RemoteError:
            logger.error(f'>>> RemoteError')
    except: 
        logger.exception(f'>>> exception')

    # Stop discovery
    logger.info(f'>>> Disconnecting...')
    for rule in rules:
        await bus.delMatch(rule).asFuture(loop)
    rules.clear()
    # Disconnect txdbus client

    try:
        bus.disconnect()
    except Exception as l_e:
        logger.error(f'>>> Attempt to disconnect system bus failed: {l_e}')

    try:
        reactor.stop()
    except ReactorNotRunning as l_e:
        logger.error(f'>>> Attempt to stop reactor failed: {l_e}')

    bus = None
    reactor = None
