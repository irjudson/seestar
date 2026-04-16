"""Tests for UDP discovery protocol."""

import json
from unittest.mock import patch

from seestar.discovery import (
    _get_broadcast_addresses,
    _make_scan_message,
    _parse_response,
)
from seestar.models import DiscoveredDevice


def test_make_scan_message():
    msg = _make_scan_message(1)
    assert msg.endswith(b"\r\n")
    data = json.loads(msg.decode("utf-8").strip())
    assert data["method"] == "scan_iscope"
    assert data["id"] == 1


def test_make_scan_message_incrementing():
    msg1 = json.loads(_make_scan_message(1).strip())
    msg5 = json.loads(_make_scan_message(5).strip())
    assert msg1["id"] == 1
    assert msg5["id"] == 5


def test_parse_valid_response():
    response = json.dumps({
        "code": 0,
        "id": 1,
        "method": "scan_iscope",
        "result": {
            "ssid": "Seestar_TEST",
            "sn": "SN12345",
            "model": "Seestar",
            "bssid": "AA:BB:CC:DD:EE:FF",
            "is_verified": True,
            "product_model": "Seestar S50",
            "tcp_client_num": 0,
        },
    }).encode("utf-8")

    device = _parse_response(response, ("198.51.100.1", 4720))
    assert device is not None
    assert isinstance(device, DiscoveredDevice)
    assert device.host == "198.51.100.1"
    assert device.info.sn == "SN12345"
    assert device.info.product_model == "Seestar S50"


def test_parse_invalid_json():
    device = _parse_response(b"not json", ("198.51.100.2", 4720))
    assert device is None


def test_parse_wrong_method():
    response = json.dumps({
        "code": 0,
        "method": "other_method",
        "result": {},
    }).encode("utf-8")
    device = _parse_response(response, ("198.51.100.3", 4720))
    assert device is None


def test_get_broadcast_addresses_fallback():
    """When netifaces is unavailable and /proc/net/dev is missing, falls back to 255.255.255.255."""
    with patch("builtins.__import__", side_effect=ImportError):
        with patch("builtins.open", side_effect=FileNotFoundError):
            addrs = _get_broadcast_addresses()
    assert "255.255.255.255" in addrs


def test_get_broadcast_addresses_returns_list():
    addrs = _get_broadcast_addresses()
    assert isinstance(addrs, list)
    assert len(addrs) >= 1
