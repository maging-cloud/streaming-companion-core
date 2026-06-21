"""console の live 状態。発話/状態の単一の持ち主。SSE 用に変化を購読者へ push する。"""

import queue
import threading


class ConsoleState:
    def __init__(self, history_limit=20):
        self._lock = threading.Lock()
        self._history_limit = history_limit
        self._running = False
        self._muted = False
        self._workers = []
        self._current = None  # {"text","ts"} | None
        self._history = []  # 新しい順
        self._subs = set()  # set[queue.Queue]
        self.last_wav = None  # 直近合成 WAV bytes (replay 用)

    # ---- mutators ----
    def set_running(self, v):
        with self._lock:
            self._running = bool(v)
        self._notify()

    def set_muted(self, v):
        with self._lock:
            self._muted = bool(v)
        self._notify()

    def set_workers(self, workers):
        with self._lock:
            self._workers = list(workers)
        self._notify()

    def push_comment(self, text, ts):
        item = {"text": text, "ts": ts}
        with self._lock:
            self._current = item
            self._history.insert(0, item)
            del self._history[self._history_limit :]
        self._notify()

    @property
    def muted(self):
        with self._lock:
            return self._muted

    # ---- snapshot / pub-sub ----
    def snapshot(self):
        with self._lock:
            return {
                "running": self._running,
                "muted": self._muted,
                "workers": list(self._workers),
                "current": dict(self._current) if self._current else None,
                "history": [dict(h) for h in self._history],
            }

    def subscribe(self):
        q = queue.Queue(maxsize=100)
        with self._lock:
            self._subs.add(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            self._subs.discard(q)

    def _notify(self):
        snap = self.snapshot()
        with self._lock:
            subs = list(self._subs)
        for q in subs:
            try:
                q.put_nowait(snap)
            except queue.Full:
                pass
