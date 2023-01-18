"""Library tests."""

import asyncio
import base64
from unittest.mock import patch

import pytest

import tplink_ess_lib
from tplink_ess_lib.network import Network

pytestmark = pytest.mark.asyncio

SWITCH_DISCOVERY_PACKET_1 = """
NWQ3NjcyYTI4YTAyMzA2M2ZiNjcyZjA3YmM3MDdkYzY0MjJiYTJmNWQ3MzBhZWVkNTA4ZjA1YTJjMj
AyOTA5YTViMTI4MWNkNzM2NjA2NjUwZWU4NzA4ZmY0MDU2OTI0NWI3MTQ3N2UzMzYzYzgzMDA5MjQ0
ZTU4MzZlMWYyOTg1NDI4ZTUxYTRjNTllODYyOGMyMjRjMWYxNjBmMWE5ZTk4YTZhZWQxYjc3ZTk1ZT
BiNGIzYWVhYzhjYmJjZTdmMzZmMDdjMTc5NzgwYTVlOTAyZDJlNWY5Y2M4MDhhNWQxMmNlZjQ4NDJi
OThlN2MwYjc5MjQxOTlhNmMyZmQyMGUxZjg4ZjVmYTE1MDJhYWMyMmY3YWMyYjkwMTBhYjE5MjIzMD
ZmZjA0MGYxN2M3Y2I2NzBiNzA4OTIwNmEy
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

async def test_discovery():
    """Test switch discovery."""
    with patch('tplink_ess_lib.network.socket.socket') as mock_socket:
        mock_socket = mock_socket.return_value
        packet = bytes.fromhex(base64.b64decode(SWITCH_DISCOVERY_PACKET_1).decode('utf-8'))
        mock_socket.recvfrom.side_effect = [(packet, ''), ('', '')]

        tplink = tplink_ess_lib.TpLinkESS(host_mac=TEST_HOST_MAC,user="admin",pwd="admin")

        result = await tplink.discovery()

        # Verify timeout called with proper value
        mock_socket.settimeout.assert_called_with(10)
        # Verify socket bound with proper broadcast address
        mock_socket.bind.assert_called_with((Network.BROADCAST_ADDR, Network.UDP_RECEIVE_FROM_PORT))

        assert result == [
            {
                'dhcp': False, 
                'firmware': '1.0.2 Build 20160526 Rel.34684', 
                'gateway': '0.0.0.0',
                'hardware': 'TL-SG108PE 1.0', 
                'hostname': 'TL-SG108PE', 
                'ip_addr': '192.168.1.3', 
                'ip_mask': '255.255.255.0', 
                'mac': '18:a6:f7:bc:80:d1', 
                'type': 'TL-SG108PE', 
            }
        ]

