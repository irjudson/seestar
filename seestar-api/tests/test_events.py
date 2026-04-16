"""Tests for event router."""

import asyncio

import pytest

from seestar.constants import EventCategory
from seestar.events import EventRouter
from seestar.models import EventMessage


@pytest.fixture
def router():
    return EventRouter()


@pytest.mark.asyncio
async def test_dispatch_by_name(router):
    received = []

    def handler(event: EventMessage):
        received.append(event.Event)

    router.on("AutoGoto", handler)
    event = EventMessage(Event="AutoGoto", state="working")
    await router.dispatch(event)
    assert received == ["AutoGoto"]


@pytest.mark.asyncio
async def test_dispatch_by_category(router):
    received = []

    def handler(event: EventMessage):
        received.append(event.Event)

    router.on_category(EventCategory.DEVICE_STATE, handler)
    event = EventMessage(Event="PiStatus", state="ok")
    await router.dispatch(event)
    assert received == ["PiStatus"]


@pytest.mark.asyncio
async def test_dispatch_catch_all(router):
    received = []

    def handler(event: EventMessage):
        received.append(event.Event)

    router.on_all(handler)
    await router.dispatch(EventMessage(Event="AutoGoto"))
    await router.dispatch(EventMessage(Event="PiStatus"))
    assert received == ["AutoGoto", "PiStatus"]


@pytest.mark.asyncio
async def test_dispatch_async_handler(router):
    received = []

    async def handler(event: EventMessage):
        received.append(event.Event)

    router.on("Stack", handler)
    await router.dispatch(EventMessage(Event="Stack", state="done"))
    assert received == ["Stack"]


@pytest.mark.asyncio
async def test_off_removes_handler(router):
    received = []

    def handler(event: EventMessage):
        received.append(event.Event)

    router.on("Alert", handler)
    router.off("Alert", handler)
    await router.dispatch(EventMessage(Event="Alert"))
    assert received == []


@pytest.mark.asyncio
async def test_clear(router):
    received = []
    router.on("Alert", lambda e: received.append(e.Event))
    router.on_all(lambda e: received.append("all"))
    router.clear()
    await router.dispatch(EventMessage(Event="Alert"))
    assert received == []


def test_parse_and_dispatch_non_event(router):
    task = router.parse_and_dispatch({"id": 1, "code": 0})
    assert task is None


@pytest.mark.asyncio
async def test_handler_exception_doesnt_break(router):
    received = []

    def bad_handler(event: EventMessage):
        raise ValueError("oops")

    def good_handler(event: EventMessage):
        received.append(event.Event)

    router.on("Alert", bad_handler)
    router.on("Alert", good_handler)
    await router.dispatch(EventMessage(Event="Alert"))
    assert received == ["Alert"]
