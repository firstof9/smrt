"""Provide a package for tplink-ess-lib."""
from __future__ import annotations

import logging

from .protocol import Protocol
from .network import Network, ConnectionProblem, MissingMac

_LOGGER = logging.getLogger(__name__)

class tplink_ess:
    """Represent a tplink ess switch."""

    result_field_lookup = {
        'Status': {
            0: 'Enabled',
            1: 'Disabled',
        },
        'Link Status': {
            0: 'Link Down',
            1: 'AUTO',
            2: 'MH10',
            3: 'MF10',
            4: 'MH100',
            5: '100Full',
            6: '1000Full',
        }
    }

    result_type_fields = {
        'stats': ('Port', 'Status', 'Link Status', 'TxGoodPkt', 'TxBadPkt', 'RxGoodPkt', 'RxBadPkt')
    }

    def __init__(
        self, host_mac: str = "", user: str = "", pwd: str = "", switch_mac = "",
    ) -> None:
        """Connect or discover a tplink ess switch on the network."""
        self._user = user
        self._pwd = pwd
        self._host_mac = host_mac
        self._switch_mac = switch_mac
        self._data = {}

    async def discovery(self) -> list[dict]:
        """Return result of auto discovery as dict."""
        if not self._host_mac:
            _LOGGER.error("MAC address missing.")
            raise MissingMac

        switches = []
        with Network(self._host_mac) as net:
            net.send(Protocol.DISCOVERY, {})
            while True:
                try:
                    header, payload = net.receive()
                    switches.append(self.parse_payload(payload))
                except ConnectionProblem:
                    break
        return switches

    async def query(self, switch_mac: str, action: str) -> dict:
        """send a query to a specific switch and return the results as a dict"""
        if not self._host_mac:
            _LOGGER.error("MAC address missing.")
            raise MissingMac

        with Network(mac=self._host_mac, switch_mac=switch_mac) as net:
            header, payload = net.query(Protocol.GET, [(Protocol.tp_ids[action], b'')])
            return self.parse_query_response(payload)


    async def update_data(self) -> dict:
        """Refresh switch data."""
        try:
            net = Network(self._host_mac, self._switch_mac)
        except MissingMac as e:
            _LOGGER.error("Problems with network interface: %s", e)
            raise MissingMac
        # Login to switch
        net.login(self._user, self._pwd)
        actions = Protocol.tp_ids

        for action in actions:
            header, payload = net.query(Protocol.GET, [(actions[action], b"")])
            self._data[action] = self.parse_payload(payload)

        return self._data

    def parse_payload(self, payload) -> dict:
        """Parse the payload into a dict."""
        _LOGGER.debug("Payload in: %s", payload)
        output = {}
        for item in payload:
            type_id, type_name, data = item
            output[type_name] = data
        _LOGGER.debug("Payload parse: %s", output)
        return output

    def parse_query_response(self, payload) -> list[dict]:
        """Parse a list of records of the same type into a list of dicts"""
        output = []
        for type_id, type_name, data in payload:
            if fields := self.result_type_fields.get(type_name):
                data = {k: self.result_field_lookup.get(k, {}).get(v, v) for k, v in zip(fields, data)}
            output.append(data)
        return output
