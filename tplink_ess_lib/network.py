"""Provide network interfacing functions."""

import logging
import random
import socket

from .binary import mac_to_bytes
from .protocol import Protocol

_LOGGER = logging.getLogger(__name__)


class ConnectionProblem(Exception):
    """Exception for connection problems."""


class InterfaceProblem(Exception):
    """Exception for interface problems."""


class MissingMac(Exception):
    """Exception for missing MAC address."""


class Network:

    BROADCAST_ADDR = "255.255.255.255"
    UDP_SEND_TO_PORT = 29808
    UDP_RECEIVE_FROM_PORT = 29809

    def __init__(self, mac=None, switch_mac="00:00:00:00:00:00"):

        self.switch_mac = switch_mac
        self.host_mac = mac

        if self.host_mac is None:
            raise MissingMac
        else:
            self.sequence_id = random.randint(0, 1000)

            self.header = Protocol.header["blank"].copy()
            self.header.update(
                {
                    "sequence_id": self.sequence_id,
                    "host_mac": mac_to_bytes(self.host_mac),
                    "switch_mac": mac_to_bytes(self.switch_mac),
                }
            )

            # Sending socket
            self.ss = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

            # Set sending socket options
            self.ss.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.ss.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

            # Receiving socket
            self.rs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Receiving socket
            try:
                self.rs.bind((Network.BROADCAST_ADDR, Network.UDP_RECEIVE_FROM_PORT))
            except OSError:
                self.rs.bind(('', Network.UDP_RECEIVE_FROM_PORT))
            except Exception as err:
                _LOGGER.error("Problem creating listener: %s", err)
                raise InterfaceProblem
            self.rs.settimeout(10)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.rs.close()

    def send(self, op_code, payload):
        self.sequence_id = (self.sequence_id + 1) % 1000
        self.header.update(
            {
                "sequence_id": self.sequence_id,
                "op_code": op_code,
            }
        )
        packet = Protocol.assemble_packet(self.header, payload)
        _LOGGER.debug("Sending Packet: " + packet.hex())
        packet = Protocol.encode(packet)
        _LOGGER.debug("Sending Header:  " + str(self.header))
        _LOGGER.debug("Sending Payload: " + str(payload))

        # Send packet
        self.ss.sendto(packet, (Network.BROADCAST_ADDR, Network.UDP_SEND_TO_PORT))

    def receive(self):
        data = self.receive_socket()
        if data:
            data = Protocol.decode(data)
            _LOGGER.debug("Receive Packet: " + data.hex())
            header, payload = Protocol.split(data)
            header, payload = Protocol.interpret_header(
                header
            ), Protocol.interpret_payload(payload)
            _LOGGER.debug("Received Header:  " + str(header))
            _LOGGER.debug("Received Payload: " + str(payload))
            self.header["token_id"] = header["token_id"]
            return header, payload
        else:
            raise ConnectionProblem()

    def receive_socket(self):
        data = False
        try:
            data, addr = self.rs.recvfrom(1500)
        except Exception as err:
            _LOGGER.debug("Error: %s", err)
            return False
        return data

    def query(self, op_code, payload):
        self.send(op_code, payload)
        header, payload = self.receive()
        return header, payload

    def login_dict(self, username, password):
        return [
            (Protocol.get_id("username"), username.encode("ascii") + b"\x00"),
            (Protocol.get_id("password"), password.encode("ascii") + b"\x00"),
        ]

    def login(self, username, password):
        self.query(Protocol.GET, [(Protocol.get_id("get_token_id"), b"")])
        self.query(Protocol.LOGIN, self.login_dict(username, password))

    def set(self, username, password, payload):
        self.query(Protocol.GET, [(Protocol.get_id("get_token_id"), b"")])
        real_payload = self.login_dict(username, password)
        real_payload += payload
        header, payload = self.query(Protocol.LOGIN, real_payload)
        return header, payload
