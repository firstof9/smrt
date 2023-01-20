"""Library tests."""

import asyncio
import base64
from unittest.mock import patch

import pytest

import tplink_ess_lib
from tplink_ess_lib import MissingMac
from tplink_ess_lib.network import InterfaceProblem, Network

pytestmark = pytest.mark.asyncio

SWITCH_DISCOVERY_PACKET_1 = """
NWQ3NjcyYTI4YTAyMzA2M2ZiNjcyZjA3YmM3MDdkYzY0MjJiYTJmNWQ3MzBhZWVkNTA4ZjA1YTJjMj
AyOTA5YTViMTI4MWNkNzM2NjA2NjUwZWU4NzA4ZmY0MDU2OTI0NWI3MTQ3N2UzMzYzYzgzMDA5MjQ0
ZTU4MzZlMWYyOTg1NDI4ZTUxYTRjNTllODYyOGMyMjRjMWYxNjBmMWE5ZTk4YTZhZWQxYjc3ZTk1ZT
BiNGIzYWVhYzhjYmJjZTdmMzZmMDdjMTc5NzgwYTVlOTAyZDJlNWY5Y2M4MDhhNWQxMmNlZjQ4NDJi
OThlN2MwYjc5MjQxOTlhNmMyZmQyMGUxZjg4ZjVmYTE1MDJhYWMyMmY3YWMyYjkwMTBhYjE5MjIzMD
ZmZjA0MGYxN2M3Y2I2NzBiNzA4OTIwNmEy
"""
SWITCH_DISCOVERY_PACKET_2 = """
NWQ3NjFhNGIyYTM3ZDFkOGZiNjcyZjA3YmM3MDdkYzY0MjJiYTJmNWQ3MzVhZWVkNTA4ZjA1YTJjMj
AyOTA5YTViMTI4MWNjNzM2NjA2NjUwZWU4NzA4MmUxNDA2OTI2NTk3OTNmNWQxNjNhZjgxZjBmMTQ3
NjBiNzNlNzgyZDQwM2E3OWNkNmJiZTI2OGFjYmQwYjdjMmUxNzAxNjhjNWMzZWE4ODg0ZWMyMmMwZj
ZiNmI0YWVhZjljZGM5OTI1Mzg5MTIxNGQ4OTg2OTFkZjMyZTZlYmFkODhhZGQ2NGU2ZmQzOTI4NjNh
OWJmMWEwZjJiMjc5Yjc5N2MyZmQyZGUxZmQ0ZmY3YTQzZDJlNjk4YWYyNTBkNDZhMTBhZmUwZGRjYm
FmNTg0N2Y1ODc4M2I2NzA=
"""
SWITCH_STATS_PACKET = """
NWQ3NjFhNGIyYTM3ZDFkOGU3NzAwYjI2ODUzMTdlNWM0MjJiYTJmNWQ3MzhhZWVkNTA4ZjAyYThjMj
AyOTA5YTFiMTM4MWQ1MjYyYjJkMzZkMDNjYzJiN2E0NDA2OTI0NDk0NGQzMmE3ZjRlOWIzNzM4MTQ2
NTBhNzJlMWYyOWI1NDJlZmRiY2JiZTU2OGIzOGMyNTRjMDAyNzIxNmFiMGFhOTVlZmE1ZDgxMzkxMj
RiZDgzOWY5YWJjOGU3ZGNlNmJhMjE5N2JiOWYzOTFkZjI5ZTJlNGY5YzQ4MDg1MDk1ZWUzYTdjMzFh
YThkZjkwZjJiMjcwYjdkNmMyZmQzYWU0Zjg4OTVmMzE2ZTg3NmM4YWY2YWYyYWU4OWJhM2U2ZGRjZj
c2MGZiOWYxNzg=
"""
TEST_HOST_MAC = "00:00:00:00:00:00"
TEST_SWITCH_MAC = "70:4f:57:89:61:6a"


async def test_discovery():
    """Test switch discovery."""
    with patch("tplink_ess_lib.network.socket.socket") as mock_socket:
        mock_socket = mock_socket.return_value
        packet = bytes.fromhex(
            base64.b64decode(SWITCH_DISCOVERY_PACKET_1).decode("utf-8")
        )
        mock_socket.recvfrom.side_effect = [(packet, ""), ("", "")]

        tplink = tplink_ess_lib.TpLinkESS(host_mac=TEST_HOST_MAC)

        result = await tplink.discovery(testing=True)

        # Verify timeout called with proper value
        mock_socket.settimeout.assert_called_with(10)
        # Verify socket bound with proper broadcast address
        mock_socket.bind.assert_called_with(
            (Network.BROADCAST_ADDR, Network.UDP_RECEIVE_FROM_PORT)
        )

        assert result == [
            {
                "dhcp": False,
                "firmware": "1.0.2 Build 20160526 Rel.34684",
                "gateway": "0.0.0.0",
                "hardware": "TL-SG108PE 1.0",
                "hostname": "TL-SG108PE",
                "ip_addr": "192.168.1.3",
                "ip_mask": "255.255.255.0",
                "mac": "18:a6:f7:bc:80:d1",
                "type": "TL-SG108PE",
            }
        ]


async def test_discovery_multi():
    """Test switch discovery with multple switches."""
    with patch("tplink_ess_lib.network.socket.socket") as mock_socket:
        mock_socket = mock_socket.return_value
        packet1 = bytes.fromhex(
            base64.b64decode(SWITCH_DISCOVERY_PACKET_1).decode("utf-8")
        )
        packet2 = bytes.fromhex(
            base64.b64decode(SWITCH_DISCOVERY_PACKET_2).decode("utf-8")
        )
        mock_socket.recvfrom.side_effect = [(packet1, ""), (packet2, ""), ("", "")]

        tplink = tplink_ess_lib.TpLinkESS(host_mac=TEST_HOST_MAC)

        result = await tplink.discovery(testing=True)

        # Verify timeout called with proper value
        mock_socket.settimeout.assert_called_with(10)
        # Verify socket bound with proper broadcast address
        mock_socket.bind.assert_called_with(
            (Network.BROADCAST_ADDR, Network.UDP_RECEIVE_FROM_PORT)
        )

        assert result == [
            {
                "dhcp": False,
                "firmware": "1.0.2 Build 20160526 Rel.34684",
                "gateway": "0.0.0.0",
                "hardware": "TL-SG108PE 1.0",
                "hostname": "TL-SG108PE",
                "ip_addr": "192.168.1.3",
                "ip_mask": "255.255.255.0",
                "mac": "18:a6:f7:bc:80:d1",
                "type": "TL-SG108PE",
            },
            {
                "dhcp": False,
                "firmware": "1.0.0 Build 20160715 Rel.38605",
                "gateway": "192.168.1.4",
                "hardware": "TL-SG105E 3.0",
                "hostname": "switch7",
                "ip_addr": "192.168.1.109",
                "ip_mask": "255.255.255.0",
                "mac": "70:4f:57:89:61:6a",
                "type": "TL-SG105E",
            },
        ]


async def test_stats_query():
    """Test stats query."""
    with patch("tplink_ess_lib.network.socket.socket") as mock_socket:
        mock_socket = mock_socket.return_value
        packet = bytes.fromhex(base64.b64decode(SWITCH_STATS_PACKET).decode("utf-8"))
        mock_socket.recvfrom.side_effect = [(packet, ""), ("", "")]

        tplink = tplink_ess_lib.TpLinkESS(host_mac=TEST_HOST_MAC)

        result = await tplink.query(TEST_SWITCH_MAC, "stats", testing=True)

        # Verify timeout called with proper value
        mock_socket.settimeout.assert_called_with(10)
        # Verify socket bound with proper broadcast address
        mock_socket.bind.assert_called_with(
            (Network.BROADCAST_ADDR, Network.UDP_RECEIVE_FROM_PORT)
        )

        assert result == {
            "stats": [
                {
                    "Port": 1,
                    "Status": "Disabled",
                    "Status Raw": 1,
                    "Link Status": "1000Full",
                    "Link Status Raw": 6,
                    "TxGoodPkt": 10085762,
                    "TxBadPkt": 0,
                    "RxGoodPkt": 1062303,
                    "RxBadPkt": 0,
                },
                {
                    "Port": 2,
                    "Status": "Disabled",
                    "Status Raw": 1,
                    "Link Status": "Link Down",
                    "Link Status Raw": 0,
                    "TxGoodPkt": 0,
                    "TxBadPkt": 0,
                    "RxGoodPkt": 0,
                    "RxBadPkt": 0,
                },
                {
                    "Port": 3,
                    "Status": "Disabled",
                    "Status Raw": 1,
                    "Link Status": "1000Full",
                    "Link Status Raw": 6,
                    "TxGoodPkt": 23127099,
                    "TxBadPkt": 0,
                    "RxGoodPkt": 8488829,
                    "RxBadPkt": 0,
                },
                {
                    "Port": 4,
                    "Status": "Disabled",
                    "Status Raw": 1,
                    "Link Status": "Link Down",
                    "Link Status Raw": 0,
                    "TxGoodPkt": 0,
                    "TxBadPkt": 0,
                    "RxGoodPkt": 0,
                    "RxBadPkt": 0,
                },
                {
                    "Port": 5,
                    "Status": "Disabled",
                    "Status Raw": 1,
                    "Link Status": "1000Full",
                    "Link Status Raw": 6,
                    "TxGoodPkt": 9715369,
                    "TxBadPkt": 0,
                    "RxGoodPkt": 25004812,
                    "RxBadPkt": 25,
                },
            ]
        }


async def test_missing_hostmac_exception():
    """Test missing host mac address exception."""
    with pytest.raises(MissingMac):
        tplink_ess_lib.TpLinkESS()


async def test_binding_exceptions():
    """Test socket binding exceptions."""
    with patch("tplink_ess_lib.network.socket.socket") as mock_socket:
        mock_socket = mock_socket.return_value
        mock_socket.bind.side_effect = OSError
        with pytest.raises(OSError):
            tplink = tplink_ess_lib.TpLinkESS(host_mac=TEST_HOST_MAC)
            await tplink.discovery(testing=True)
        mock_socket.bind.side_effect = InterfaceProblem
        with pytest.raises(InterfaceProblem):
            tplink = tplink_ess_lib.TpLinkESS(host_mac=TEST_HOST_MAC)
            await tplink.discovery(testing=True)
