"""Provide a package for tplink-ess-lib."""
from __future__ import annotations

import logging

from .protocol import Protocol
from .network import Network, ConnectionProblem, InterfaceProblem

_LOGGER = logging.getLogger(__name__)


class MissingInterface(Exception):
    """Exception for missing interface."""


class tplink_ess:
    """Represent a tplink ess switch."""

    def __init__(
        self, mac: str = "", interface: str = "", user: str = "", pwd: str = ""
    ) -> None:
        """Connect or discover a tplink ess switch on the network."""
        self._user = user
        self._pwd = pwd
        self._mac = mac
        self._interface = interface
        self._data = {}

    async def discovery(self) -> dict:
        """Return result of auto discovery as dict."""
        if not self._interface:
            _LOGGER.error("Interface not setup.")
            raise MissingInterface
        net = Network(self._interface)
        net.send(Protocol.DISCOVERY, {})
        switches = {}
        i = 0
        while True:
            try:
                header, payload = net.receive()
                switches[i] = (header, payload)
            except ConnectionProblem:
                break
        return switches

    async def interfaces(self) -> list:
        """Return result of interface discovery."""
        interfaces = []
        interface = None
        net = Network(interface)
        interfaces = net.get_interface()
        return interfaces

    async def update_data(self) -> dict:
        """Refresh switch data."""
        try:
            net = Network(self._interface, self._mac)
        except InterfaceProblem as e:
            _LOGGER.error("Problems with network interface: %s", e)
            raise InterfaceProblem
        # Login to switch
        net.login(self._user, self._pwd)
        actions = Protocol.tp_ids

        for action in actions:
            header, payload = net.query(Protocol.GET, [(actions[action], b"")])
            self._data[action] = payload

        return self._data
