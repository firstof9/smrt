"""Provide network interfacing functions."""

import netifaces
import socket, random, logging

from .protocol import Protocol
from .binary import byte2ports, mac_to_str, mac_to_bytes

logger = logging.getLogger(__name__)


class ConnectionProblem(Exception):
    pass


class InterfaceProblem(Exception):
    pass


class Network:

    BROADCAST_ADDR = "255.255.255.255"
    UDP_SEND_TO_PORT = 29808
    UDP_RECEIVE_FROM_PORT = 29809

    def __init__(self, interface=None, switch_mac="00:00:00:00:00:00"):

        # Normally, this module will be initialized with the MAC address of the switch we want to talk to
        # There are however two other modes that might be used:
        # - Specify MAC address fe:ff:ff:ff:ff:ff to go into broadcast listen mode. We use this to snoop on bidirectional traffic
        # - Specify MAC address ff:ff:ff:ff:ff:ff to go into "fake switch" mode, where we reply to other clients

        self.switch_mac = switch_mac
        if interface is None:
            self.ip_address = None
            self.host_mac = None
        else:
            self.ip_address, self.host_mac = self.get_interface(interface)

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
            self.ss = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            if switch_mac == "fe:ff:ff:ff:ff:ff" or switch_mac == "ff:ff:ff:ff:ff:ff":
                self.ss.bind((Network.BROADCAST_ADDR, Network.UDP_SEND_TO_PORT))
                self.ss.settimeout(10)
            else:
                self.ss.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                try:
                    self.ss.bind((self.ip_address, Network.UDP_RECEIVE_FROM_PORT))
                except Exception as err:
                    logger.error("Error attempting to bind interface: %s", err)
                    raise InterfaceProblem

            # Receiving socket
            self.rs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            if switch_mac == "ff:ff:ff:ff:ff:ff":
                # This is a signal that we'll be operating in fake switch mode, rather than sending out commands
                # For this, we need to switch the way that the recieving socket binds, to bind locally instead.
                self.rs.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                self.rs.bind((self.ip_address, Network.UDP_SEND_TO_PORT))

            else:

                # Receiving socket
                self.rs.bind((Network.BROADCAST_ADDR, Network.UDP_RECEIVE_FROM_PORT))
                self.rs.settimeout(10)

    def get_interface(self, interface=None) -> list | tuple:
        if interface is None:
            interfaces = netifaces.interfaces()
            if "lo" in interfaces:
                interfaces.remove("lo")
            if len(interfaces) >= 1:
                return interfaces
            return []

        settings = []
        addrs = netifaces.ifaddresses(interface)
        logger.debug("addrs:" + repr(addrs))
        if netifaces.AF_INET not in addrs:
            raise InterfaceProblem("not AF_INET address")
        if netifaces.AF_LINK not in addrs:
            raise InterfaceProblem("not AF_LINK address")

        mac = addrs[netifaces.AF_LINK][0]["addr"]
        # take first address of interface
        addr = addrs[netifaces.AF_INET][0]
        if "broadcast" not in addr or "addr" not in addr:
            raise InterfaceProblem("no addr or broadcast for address")
        ip = addr["addr"]

        logger.debug("get_interface: %s %s %s " % (interface, ip, mac))

        return ip, mac

    def send(self, op_code, payload):
        self.sequence_id = (self.sequence_id + 1) % 1000
        self.header.update(
            {
                "sequence_id": self.sequence_id,
                "op_code": op_code,
            }
        )
        packet = Protocol.assemble_packet(self.header, payload)
        logger.debug("Sending Packet: " + packet.hex())
        packet = Protocol.encode(packet)
        logger.debug("Sending Header:  " + str(self.header))
        logger.debug("Sending Payload: " + str(payload))
        if self.switch_mac == "ff:ff:ff:ff:ff:ff":
            self.rs.sendto(
                packet, (Network.BROADCAST_ADDR, Network.UDP_RECEIVE_FROM_PORT)
            )
        else:
            self.ss.sendto(packet, (Network.BROADCAST_ADDR, Network.UDP_SEND_TO_PORT))

    def setHeader(self, header):
        self.header = header

    def receive(self):
        data = self.receive_socket(self.rs)
        if data:
            data = Protocol.decode(data)
            logger.debug("Receive Packet: " + data.hex())
            header, payload = Protocol.split(data)
            header, payload = Protocol.interpret_header(
                header
            ), Protocol.interpret_payload(payload)
            logger.debug("Received Header:  " + str(header))
            logger.debug("Received Payload: " + str(payload))
            self.header["token_id"] = header["token_id"]
            return header, payload
        else:
            raise ConnectionProblem()

    def receive_socket(self, socket):
        data = False
        try:
            data, addr = socket.recvfrom(1500)
        except:
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
