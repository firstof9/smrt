"""Provide common pytest fixtures."""

import socket
from unittest import mock
from unittest.mock import call, mock_open, patch

import pytest

from tests.common import load_fixture

# TODO: get wireshark captures of packets for tests?

SWITCH_DISCOVERY_PACKET = ""
SWITCH_STATS_PACKET = ""


@pytest.fixture()
def mock_socket_discovery(mock_socket):
    """Mock discovery response."""
    mock_socket.recvfrom.return_value = [SWITCH_DISCOVERY_PACKET, ""]
    yield mock_socket


@pytest.fixture()
def mock_socket_stats(mock_socket):
    """Mock discovery response."""
    mock_socket.recvfrom.return_value = [SWITCH_STATS_PACKET, ""]
    yield mock_socket


@pytest.fixture
def mock_socket():
    """Fixture to mock socket calls."""
    with mock.Mock(spec=socket.socket) as m:
        yield m
