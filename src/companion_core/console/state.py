"""console の live 状態。発話/状態の単一の持ち主。SSE 用に変化を購読者へ push する。"""

from __future__ import annotations

import queue
import threading
from collections.abc import Iterable
from typing import Any


class ConsoleState:
    def __init__(self, history_limit: int = 20) -> None:
        self._lock = threading.Lock()
        self._history_limit = history_limit
        self._running = False
        self._muted = False
        self._workers: list[Any] = []
        self._current: dict[str, Any] | None = None  # {"text","ts"} | None
        self._history: list[dict[str, Any]] = []  # 新しい順
        self._subs: set[queue.Queue[Any]] = set()  # set[queue.Queue]
        self.last_wav: bytes | None = None  # 直近合成 WAV bytes (replay 用)

    # ---- mutators ----
    def set_running(self, v: Any) -> None:
        with self._lock:
            self._running = bool(v)
        self._notify()

    def set_muted(self, v: Any) -> None:
        with self._lock:
            self._muted = bool(v)
        self._notify()

    def set_workers(self, workers: Iterable[Any]) -> None:
        with self._lock:
            self._workers = list(workers)
        self._notify()

    def push_comment(self, text: str, ts: float) -> None:
        item = {"text": text, "ts": ts}
        with self._lock:
            self._current = item
            self._history.insert(0, item)
            del self._history[self._history_limit :]
        self._notify()

    @property
    def muted(self) -> bool:
        with self._lock:
            return self._muted

    # ---- snapshot / pub-sub ----
    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "muted": self._muted,
                "workers": list(self._workers),
                "current": dict(self._current) if self._current else None,
                "history": [dict(h) for h in self._history],
            }

    def subscribe(self) -> queue.Queue[Any]:
        q: queue.Queue[Any] = queue.Queue(maxsize=100)
        with self._lock:
            self._subs.add(q)
        return q

    def unsubscribe(self, q: queue.Queue[Any]) -> None:
        with self._lock:
            self._subs.discard(q)

    def _notify(self) -> None:
        snap = self.snapshot()
        with self._lock:
            subs = list(self._subs)
        for q in subs:
            try:
                q.put_nowait(snap)
            except queue.Full:
                pass
