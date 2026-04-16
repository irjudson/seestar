"""Event system for Seestar asynchronous notifications.

Events arrive as JSON messages with an "Event" field.  The EventRouter
dispatches them to registered callbacks by event name or category.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

from .constants import EVENT_CATEGORIES, EventCategory, EventType
from .models import EventMessage

logger = logging.getLogger(__name__)

# Callback types
EventCallback = Callable[[EventMessage], None]
AsyncEventCallback = Callable[[EventMessage], Coroutine[Any, Any, None]]
AnyCallback = EventCallback | AsyncEventCallback


class EventRouter:
    """Routes device events to registered handlers.

    Register handlers for specific event names or entire categories:

        router = EventRouter()
        router.on("AutoGoto", my_handler)
        router.on_category(EventCategory.DEVICE_STATE, my_status_handler)
        router.on_all(my_catch_all)
    """

    def __init__(self) -> None:
        self._by_name: dict[str, list[AnyCallback]] = defaultdict(list)
        self._by_category: dict[EventCategory, list[AnyCallback]] = defaultdict(list)
        self._catch_all: list[AnyCallback] = []

    def on(self, event_name: str, callback: AnyCallback) -> None:
        """Register a handler for a specific event name (e.g. "AutoGoto")."""
        self._by_name[event_name].append(callback)

    def off(self, event_name: str, callback: AnyCallback) -> None:
        """Remove a handler for a specific event name."""
        try:
            self._by_name[event_name].remove(callback)
        except ValueError:
            pass

    def on_category(self, category: EventCategory, callback: AnyCallback) -> None:
        """Register a handler for all events in a category."""
        self._by_category[category].append(callback)

    def off_category(self, category: EventCategory, callback: AnyCallback) -> None:
        """Remove a handler for a category."""
        try:
            self._by_category[category].remove(callback)
        except ValueError:
            pass

    def on_all(self, callback: AnyCallback) -> None:
        """Register a handler for all events."""
        self._catch_all.append(callback)

    def off_all(self, callback: AnyCallback) -> None:
        """Remove a catch-all handler."""
        try:
            self._catch_all.remove(callback)
        except ValueError:
            pass

    def clear(self) -> None:
        """Remove all handlers."""
        self._by_name.clear()
        self._by_category.clear()
        self._catch_all.clear()

    async def dispatch(self, event: EventMessage) -> None:
        """Dispatch an event to all matching handlers."""
        name = event.Event
        callbacks: list[AnyCallback] = []

        # Specific name handlers
        callbacks.extend(self._by_name.get(name, []))

        # Category handlers
        try:
            event_type = EventType(name)
            category = EVENT_CATEGORIES.get(event_type)
            if category is not None:
                callbacks.extend(self._by_category.get(category, []))
        except ValueError:
            pass  # Unknown event type, skip category dispatch

        # Catch-all handlers
        callbacks.extend(self._catch_all)

        for cb in callbacks:
            try:
                result = cb(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("Error in event handler for %s", name)

    def parse_and_dispatch(self, data: dict[str, Any]) -> asyncio.Task | None:
        """Parse a JSON dict as an event and schedule dispatch.

        Returns an asyncio Task if this is an event message, or None if not.
        """
        if "Event" not in data:
            return None

        try:
            event = EventMessage.model_validate(data)
        except Exception:
            logger.debug("Failed to parse event: %s", data)
            return None

        try:
            loop = asyncio.get_running_loop()
            return loop.create_task(self.dispatch(event))
        except RuntimeError:
            logger.debug("No running event loop, skipping dispatch for %s", event.Event)
            return None
