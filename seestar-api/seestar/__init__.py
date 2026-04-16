"""Seestar - Python client library for ZWO Seestar smart telescopes."""

__version__ = "0.1.0"

from .alpaca import AlpacaClient, AlpacaError
from .client import ConnectionState, SeestarClient
from .constants import Cmd, ControlType, EventCategory, EventType
from .crypto import encrypt_challenge
from .discovery import discover, discover_iter
from .events import EventRouter
from .imaging import ImageStream
from .models import (
    CommandResponse,
    DeviceState,
    DiscoveredDevice,
    EquatorialCoord,
    EventMessage,
    HorizontalCoord,
    SolveResult,
    ViewData,
)

__all__ = [
    "AlpacaClient",
    "AlpacaError",
    "Cmd",
    "CommandResponse",
    "ConnectionState",
    "ControlType",
    "DeviceState",
    "DiscoveredDevice",
    "EquatorialCoord",
    "EventCategory",
    "EventMessage",
    "EventRouter",
    "EventType",
    "HorizontalCoord",
    "ImageStream",
    "SeestarClient",
    "SolveResult",
    "ViewData",
    "discover",
    "discover_iter",
    "encrypt_challenge",
]
