"""Provide network interfacing functions."""

import logging
import random
import socket

from .binary import mac_to_bytes, mac_to_str
from .protocol import Protocol

_LOGGER = logging.getLogger(__name__)


class ConnectionProblem(Exception):
    """Exception for connection problems."""


class InterfaceProblem(Exception):
    """Exception for interface problems."""


class MissingMac(Exception):
    """Exception for missing MAC address."""


class Network:
    """Class for network functions."""

    BROADCAST_ADDR = "255.255.255.255"
    BROADCAST_MAC = "00:00:00:00:00:00"
    UDP_SEND_TO_PORT = 29808
    UDP_RECEIVE_FROM_PORT = 29809

    def __init__(self, host_mac):
        """Initialize."""
        if host_mac is None:
            raise MissingMac

        self.host_mac = host_mac
        self.sequence_id = random.randint(0, 1000)
        self.token_id = None

        # Sending socket
        self.s_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
        )
        self.s_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.s_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        # Receiving socket
        self.r_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.r_socket.bind((Network.BROADCAST_ADDR, Network.UDP_RECEIVE_FROM_PORT))
        except OSError:
            self.r_socket.bind(("", Network.UDP_RECEIVE_FROM_PORT))
        except Exception as err:
            _LOGGER.error("Problem creating listener: %s", err)
            raise err
        self.r_socket.settimeout(10)

    def __enter__(self):
        """Enter method."""
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Exit method."""
        self.r_socket.close()

    def send(self, switch_mac, op_code, payload):
        """Send a packet to the given switch."""
        self.sequence_id = (self.sequence_id + 1) % 1000

        header = Protocol.header["blank"].copy()
        header.update(
            {
                "sequence_id": self.sequence_id,
                "host_mac": mac_to_bytes(self.host_mac),
                "switch_mac": mac_to_bytes(switch_mac),
                "op_code": op_code,
            }
        )
        if self.token_id:
            header["token_id"] = self.token_id

        packet = Protocol.assemble_packet(header, payload)
        _LOGGER.debug("Sending Packet to %s: %s", switch_mac, packet.hex())
        packet = Protocol.encode(packet)
        _LOGGER.debug("Sending Header: %s", str(header))
        _LOGGER.debug("Sending Payload: %s", str(payload))

        # Send packet
        self.s_socket.sendto(packet, (Network.BROADCAST_ADDR, Network.UDP_SEND_TO_PORT))

    def receive(self):
        """Wait for an incoming packet, then return header+payload as a tuple."""
        while data := self.receive_socket():
            data = Protocol.decode(data)
            _LOGGER.debug("Receive Packet: %s", data.hex())
            header, payload = Protocol.split(data)
            header, payload = Protocol.interpret_header(
                header
            ), Protocol.interpret_payload(payload)
            _LOGGER.debug("Received Header: %s", str(header))
            _LOGGER.debug("Received Payload: %s", str(payload))
            # check sequence_id alignment
            if self.sequence_id != header["sequence_id"]:
                _LOGGER.warning("##### Ignoring sequence_id %d expected %d",
                                header["sequence_id"], self.sequence_id)
                continue
            # check host_mac alignment
            data_mac = mac_to_str(header['host_mac'])
            if self.host_mac != data_mac:
                _LOGGER.warning("##### Ignoring mac id %d expected %d",
                                data_mac, self.host_mac)
                continue
            self.token_id = header["token_id"]
            return header, payload
        raise ConnectionProblem()

    def receive_socket(self):
        """Get data from socket."""
        try:
            data, addr = self.r_socket.recvfrom(1500)  # pylint: disable=unused-variable
        except OSError as err:
            _LOGGER.debug("Error: %s", err)
            return False
        return data

    def query(self, switch_mac, op_code, payload):
        """
        Send packet to switch.

        Send a packet to the given switch, then wait for a response and
        return header+payload as a tuple.
        """
        self.send(switch_mac, op_code, payload)
        return self.receive()

    @staticmethod
    def login_dict(username, password):
        """Return login dict."""
        return [
            (Protocol.get_id("username"), username.encode("ascii") + b"\x00"),
            (Protocol.get_id("password"), password.encode("ascii") + b"\x00"),
        ]

    def login(self, switch_mac, username, password):
        """Send login credentials to switch."""
        self.query(switch_mac, Protocol.GET, [(Protocol.get_id("get_token_id"), b"")])
        self.query(switch_mac, Protocol.LOGIN, self.login_dict(username, password))

    def set(self, switch_mac, username, password, payload):
        """Authenticate to the switch."""
        self.query(switch_mac, Protocol.GET, [(Protocol.get_id("get_token_id"), b"")])
        real_payload = self.login_dict(username, password)
        real_payload += payload
        header, payload = self.query(switch_mac, Protocol.LOGIN, real_payload)
        return header, payload
