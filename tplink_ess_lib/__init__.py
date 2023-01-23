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

    working_ids_tp = {
        2: ("str", "hostname", 1),
        10: ("dec", "num_ports", 0),
        4096: ("hex", "ports", 0),
        4608: ("hex", "trunk", 0),
        8192: ("hex", "mtu_vlan", 0),
        8705: ("vlan", "vlan", 1),
        8706: ("pvid", "pvid", 0),
        12288: ("bool", "qos1", 0),
        12289: ("hex", "qos2", 0),
        16640: ("hex", "mirror", 0),
        16384: ("stat", "stats", 0),
        17152: ("bool", "loop_prev", 0),
    }

    tp_ids = {v[1]: k for k, v in working_ids_tp.items()}

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

    async def query(self, switch_mac: str, action: str, testing: bool = False) -> dict:
        """
        Send a query.

        Sends a query to a specific switch and return the results
        as a dict.
        """
        with Network(host_mac=self._host_mac) as net:
            header, payload = net.query(  # pylint: disable=unused-variable
                switch_mac=switch_mac,
                op_code=Protocol.GET,
                payload=[(Protocol.tp_ids[action], b"")],
                testing=testing,
            )
            return self.parse_response(payload)

    async def update_data(self, switch_mac, testing: bool = False) -> dict:
        """Refresh switch data."""
        try:
            net = Network(host_mac=self._host_mac)
        except OSError as err:
            _LOGGER.error("Problems with network interface: %s", err)
            raise err
        # Login to switch
        net.login(switch_mac, self._user, self._pwd, testing)
        actions = TpLinkESS.working_ids_tp

        for action in actions.keys():
            try:
                header, payload = net.query(  # pylint: disable=unused-variable
                    switch_mac=switch_mac,
                    op_code=Protocol.GET,
                    payload=[(action, b"")],
                    testing=testing,
                )
                index = TpLinkESS.working_ids_tp[action][1]
                self._data[index] = self.parse_response(payload)
            except ConnectionProblem:
                break

        return self._data

    @staticmethod
    def parse_response(payload) -> Dict[str, Any]:
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
