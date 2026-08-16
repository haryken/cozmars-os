"""In-process pub/sub — thay CLAD/UDP của Vector."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Awaitable, Callable, DefaultDict, List

Handler = Callable[[Any], Awaitable[None] | None]


class Bus:
    def __init__(self) -> None:
        self._subs: DefaultDict[str, List[Handler]] = defaultdict(list)

    def subscribe(self, topic: str, fn: Handler) -> None:
        self._subs[topic].append(fn)

    async def publish(self, topic: str, payload: Any = None) -> None:
        for fn in list(self._subs.get(topic, ())):
            res = fn(payload)
            if asyncio.iscoroutine(res):
                await res
