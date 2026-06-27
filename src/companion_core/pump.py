#!/usr/bin/env python3
"""EventQueue を drain して実況する pump worker (汎用)。

queue から 1 件取り出し → get_handler(kind) → comment → fan_out。supervisor.Worker に
載せて並行起動する。worker_loop が tick 例外を隔離するので 1 件の失敗で止まらない。
sinks に voicevoxplay 等の同期再生を入れると fan_out がブロックし自然なペーサになる。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from companion_core.comment import comment
from companion_core.sink import fan_out
from companion_core.supervisor import Worker


def make_pump_worker(
    queue: Any,
    sinks: Iterable[Callable[[str], Any]],
    *,
    get_handler: Callable[[str], Any],
    client: Any = None,
    ngwords: Iterable[str] | None = None,
    persona: Any = None,
    gate: Any = None,
    name: str = "pump",
    interval: float = 0.2,
) -> Worker:
    """queue を 1 tick = 1 件処理する Worker を返す。

    gate(SpeechGate) を渡すと should_speak(kind=...) が False の item はスキップ。
    get_handler は kind → handler (例: companion_core.registry.get_handler)。
    """
    sinks = list(sinks)

    def tick() -> None:
        item = queue.get()
        if item is None:
            return
        kind = item.request.get("kind")
        if gate is not None and not gate.should_speak(kind=kind):
            return
        handler = get_handler(kind)
        text = comment(item.request, handler, client=client, ngwords=ngwords, persona=persona)
        fan_out(text, sinks)

    return Worker(name, tick, interval)
