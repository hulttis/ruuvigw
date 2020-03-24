# -*- coding: utf-8 -*-
import re

_mac_address_regex = re.compile("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
_hci_device_regex = re.compile("^hci(\\d+)$")

def validate_mac_address(address):
    return _mac_address_regex.match(address) is not None


def validate_hci_device(hci_device):
    return _hci_device_regex.match(hci_device) is not None


