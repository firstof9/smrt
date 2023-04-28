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
            0: "Disabled",
            1: "Enabled",
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

    def __init__(
        self, host_mac: str = "", user: str = "", pwd: str = "", testing: bool = False
    ) -> None:
        """Connect or discover a TP-Link ESS switch on the network."""
        if not host_mac:
            _LOGGER.error("MAC address missing.")
            raise MissingMac

        self._user = user
        self._pwd = pwd
        self._host_mac = host_mac
        self._data: Dict[Any, Any] = {}
        self._testing = testing

    async def discovery(self) -> list[dict]:
        """Return a list of unique switches found by discovery."""
        switches = {}
        with Network(self._host_mac, testing=self._testing) as net:
            net.send(Network.BROADCAST_MAC, Protocol.DISCOVERY, {})
            while True:
                try:
                    header, payload = net.receive()
                    switches[header["switch_mac"]] = TpLinkESS.parse_response(payload)
                except ConnectionProblem:
                    break
        return list(switches.values())

    async def query(self, switch_mac: str, action: str) -> dict:
        """
        Send a query.

        Sends a query to a specific switch and return the results
        as a dict.
        """
        with Network(host_mac=self._host_mac, testing=self._testing) as net:
            header, payload = net.query(  # pylint: disable=unused-variable
                switch_mac=switch_mac,
                op_code=Protocol.GET,
                payload=[(Protocol.tp_ids[action], b"")],
            )
            return TpLinkESS.parse_response(payload)

    async def update_data(self, switch_mac, action_names=None) -> dict:
        """Refresh switch data. Optional list of items to query (default all)."""
        try:
            net = Network(host_mac=self._host_mac, testing=self._testing)
        except OSError as err:
            _LOGGER.error("Problems with network interface: %s", err)
            raise err
        # Login to switch
        net.login(switch_mac, self._user, self._pwd)
        if action_names is None:
            actions = TpLinkESS.working_ids_tp
        else:
            actions = {
                TpLinkESS.tp_ids[name]: TpLinkESS.working_ids_tp[TpLinkESS.tp_ids[name]]
                for name in action_names
            }

        for action in actions:
            try:
                header, payload = net.query(  # pylint: disable=unused-variable
                    switch_mac=switch_mac,
                    op_code=Protocol.GET,
                    payload=[(action, b"")],
                )
                index = TpLinkESS.working_ids_tp[action][1]
                self._data[index] = TpLinkESS.parse_response(payload)
            except ConnectionProblem:
                break

        return self._data

    @staticmethod
    def _map_data_fields(type_name: str, data):
        """Map data fields to a dict."""
        if fields := TpLinkESS.RESULT_TYPE_FIELDS.get(type_name):
            mapped_data = {}
            for k, v in zip(fields, data):  # pylint: disable=invalid-name
                # pylint: disable-next=invalid-name
                if mv := TpLinkESS.RESULT_FIELD_LOOKUP.get(k):
                    mapped_data[k] = mv.get(v)
                    mapped_data[k + " Raw"] = v
                else:
                    mapped_data[k] = v
            return mapped_data
        return data

    @staticmethod
    def parse_response(payload) -> Dict[str, Any]:
        """Parse the payload into a dict."""
        # all payloads are list of tuple:3.
        # if the third value is a tuple/list, it can be field-mapped.
        # if there are duplicate type_name, return a list.
        _LOGGER.debug("Payload in: %s", payload)
        output: Dict[str, Any] = {}
        for type_id, type_name, data in payload:  # pylint: disable=unused-variable
            if isinstance(data, (tuple, list)):
                data = TpLinkESS._map_data_fields(type_name, data)
                output[type_name] = output.get(type_name, []) + [data]
            else:
                if type_name in output:
                    if isinstance(output[type_name], list):
                        output[type_name].append(data)
                    else:
                        output[type_name] = [output[type_name], data]
                else:
                    output[type_name] = data

        _LOGGER.debug("Payload parse: %s", output)
        return output
