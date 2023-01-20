"""Provide a package for tplink-ess-lib."""
from __future__ import annotations

import logging
from typing import Any, Dict

from .network import ConnectionProblem, MissingMac, Network
from .protocol import Protocol

_LOGGER = logging.getLogger(__name__)


class TpLinkESS:
    """Represent a TP-Link ESS switch."""

    RESULT_FIELD_LOOKUP = {
        "Status": {
            0: "Enabled",
            1: "Disabled",
        },
        "Link Status": {
            0: "Link Down",
            1: "AUTO",
            2: "MH10",
            3: "MF10",
            4: "MH100",
            5: "100Full",
            6: "1000Full",
        },
    }

    RESULT_TYPE_FIELDS = {
        "stats": (
            "Port",
            "Status",
            "Link Status",
            "TxGoodPkt",
            "TxBadPkt",
            "RxGoodPkt",
            "RxBadPkt",
        ),
        "vlan": ("VLAN ID", "Member Ports", "Tagged Ports", "VLAN Name"),
    }

    def __init__(self, host_mac: str = "", user: str = "", pwd: str = "") -> None:
        """Connect or discover a TP-Link ESS switch on the network."""
        if not host_mac:
            _LOGGER.error("MAC address missing.")
            raise MissingMac

        self._user = user
        self._pwd = pwd
        self._host_mac = host_mac
        self._data: Dict[Any, Any] = {}

    async def discovery(self, testing: bool = False) -> list[dict]:
        """Return a list of unique switches found by discovery."""
        switches = {}
        with Network(self._host_mac) as net:
            net.send(Network.BROADCAST_MAC, Protocol.DISCOVERY, {})
            while True:
                try:
                    header, payload = net.receive(testing)
                    switches[header["switch_mac"]] = self.parse_response(payload)
                except ConnectionProblem:
                    break
        return list(switches.values())

    async def query(self, switch_mac: str, action: str) -> dict:
        """
        Send a query.

        Sends a query to a specific switch and return the results
        as a dict.
        """
        with Network(host_mac=self._host_mac) as net:
            header, payload = net.query(  # pylint: disable=unused-variable
                switch_mac, Protocol.GET, [(Protocol.tp_ids[action], b"")]
            )
            return self.parse_response(payload)

    async def update_data(self, switch_mac) -> dict:
        """Refresh switch data."""
        try:
            net = Network(self._host_mac)
        except MissingMac as err:
            _LOGGER.error("Problems with network interface: %s", err)
            raise err
        # Login to switch
        net.login(switch_mac, self._user, self._pwd)
        actions = Protocol.tp_ids

        for action in actions:
            header, payload = net.query(  # pylint: disable=unused-variable
                switch_mac, Protocol.GET, [(actions[action], b"")]
            )
            self._data[action] = self.parse_response(payload)

        return self._data

    @staticmethod
    def parse_response(payload) -> dict:
        """Parse the payload into a dict."""
        # all payloads are list of tuple:3. if the third value is a
        # tuple/list, it can be field-mapped
        _LOGGER.debug("Payload in: %s", payload)
        output: Dict[str, Any] = {}
        for type_id, type_name, data in payload:  # pylint: disable=unused-variable
            if type(data) in [tuple, list]:
                if fields := TpLinkESS.RESULT_TYPE_FIELDS.get(type_name):
                    mapped_data = {}
                    for k, v in zip(fields, data):  # pylint: disable=invalid-name
                        # pylint: disable-next=invalid-name
                        if mv := TpLinkESS.RESULT_FIELD_LOOKUP.get(k):
                            mapped_data[k] = mv.get(v)
                            mapped_data[k + " Raw"] = v
                        else:
                            mapped_data[k] = v
                    data = mapped_data
                data_list = output.get(type_name, [])
                data_list.append(data)
                data = data_list

            output[type_name] = data
        _LOGGER.debug("Payload parse: %s", output)
        return output
