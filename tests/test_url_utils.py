"""Tests for utils.url_utils (static helpers that don't need the network)."""

from leftovers.utils.url_utils import is_ip_address


def test_is_ip_address_positive():
    assert is_ip_address("127.0.0.1") is True
    assert is_ip_address("192.168.1.255") is True


def test_is_ip_address_negative():
    assert is_ip_address("example.com") is False
    assert is_ip_address("sub.example.co.uk") is False
    assert is_ip_address("not.an.ip.address.xyz") is False
