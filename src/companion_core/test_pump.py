from __future__ import annotations

from typing import Any

from companion_core.pump import make_pump_worker
from companion_core.queue import EventQueue


class _FakeHandler:
    # comment(request, handler, client=None) は client 無しで handler.template を使う
    def template(self, request: dict[str, Any]) -> str:
        return f"{request['payload']['user']} さんなのだ"


def _get_handler(kind: str) -> _FakeHandler:
    return _FakeHandler()


def test_tick_pops_one_item_and_fans_out() -> None:
    q = EventQueue()
    q.put(5, {"kind": "twitch_event", "payload": {"user": "alice"}})
    out: list[str] = []
    w = make_pump_worker(q, [out.append], get_handler=_get_handler)
    w.tick()
    assert out == ["alice さんなのだ"]
    assert len(q) == 0  # 1 件消費


def test_empty_queue_tick_is_noop() -> None:
    q = EventQueue()
    out: list[str] = []
    w = make_pump_worker(q, [out.append], get_handler=_get_handler)
    w.tick()
    assert out == []


def test_gate_suppresses_item() -> None:
    q = EventQueue()
    q.put(0, {"kind": "twitch_chat", "payload": {"user": "bob"}})
    out: list[str] = []

    class _Gate:
        def should_speak(self, *, score: Any = None, kind: str | None = None, force: bool = False) -> bool:
            return False

    w = make_pump_worker(q, [out.append], get_handler=_get_handler, gate=_Gate())
    w.tick()
    assert out == []  # gate が抑制


def test_highest_priority_spoken_first_across_ticks() -> None:
    q = EventQueue()
    q.put(0, {"kind": "twitch_chat", "payload": {"user": "low"}})
    q.put(9, {"kind": "twitch_event", "payload": {"user": "high"}})
    out: list[str] = []
    w = make_pump_worker(q, [out.append], get_handler=_get_handler)
    w.tick()
    w.tick()
    assert out == ["high さんなのだ", "low さんなのだ"]
