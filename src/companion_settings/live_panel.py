"""ライブ制御タブ。headless な ConsoleService を Qt から直接駆動する (HTTP 無し)。

start/stop/mute/replay ボタンと now-speaking / history / workers 表示を持つ。ライブ更新は
ConsoleState.subscribe() の queue を別スレッドで drain し、Qt signal で GUI スレッドへ転送する。
設定保存 (MainWindow._on_ok) とは独立 — ここは runtime action であって config 書き込みではない。
"""
import queue
import threading

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget,
)


class LivePanel(QWidget):
    """ConsoleService を駆動する Qt widget。"""

    snapshot = Signal(dict)  # 別スレッド → GUI スレッドへ状態を転送

    def __init__(self, service):
        super().__init__()
        self.service = service
        self._last = {}
        self._q = None
        self._pump_stop = False
        self._pump_thread = None
        self._build_ui()
        self.snapshot.connect(self._apply_snapshot)
        self._apply_snapshot(service.get_state())

    # ---- UI ----
    def _build_ui(self):
        root = QVBoxLayout(self)

        bar = QHBoxLayout()
        self._status = QLabel("STOPPED")
        self._btn_toggle = QPushButton("▶ START")
        self._btn_mute = QPushButton("🔇 MUTE")
        self._btn_replay = QPushButton("🔁 再生")
        self._btn_toggle.clicked.connect(self._on_toggle)
        self._btn_mute.clicked.connect(self._on_mute)
        self._btn_replay.clicked.connect(self._on_replay)
        bar.addWidget(self._status)
        bar.addStretch(1)
        bar.addWidget(self._btn_toggle)
        bar.addWidget(self._btn_mute)
        bar.addWidget(self._btn_replay)
        root.addLayout(bar)

        root.addWidget(QLabel("NOW SPEAKING"))
        self._now = QLabel("—")
        self._now.setWordWrap(True)
        root.addWidget(self._now)

        root.addWidget(QLabel("history"))
        self._history = QListWidget()
        root.addWidget(self._history, 1)

    # ---- 状態反映 (テスト可能、スレッド非依存) ----
    def _apply_snapshot(self, snap):
        self._last = snap or {}
        running = bool(self._last.get("running"))
        muted = bool(self._last.get("muted"))
        self._status.setText("RUNNING" if running else "STOPPED")
        self._btn_toggle.setText("⏹ STOP" if running else "▶ START")
        self._btn_mute.setText("🔈 UNMUTE" if muted else "🔇 MUTE")
        cur = self._last.get("current")
        self._now.setText(cur["text"] if cur else "—")
        self._history.clear()
        for h in self._last.get("history", []):
            self._history.addItem(h.get("text", ""))

    # ---- ボタン ----
    def _on_toggle(self):
        running = bool(self._last.get("running"))
        res = self.service.control("stop" if running else "start")
        self._apply_snapshot(res.get("state", self.service.get_state()))

    def _on_mute(self):
        muted = bool(self._last.get("muted"))
        res = self.service.control("unmute" if muted else "mute")
        self._apply_snapshot(res.get("state", self.service.get_state()))

    def _on_replay(self):
        self.service.control("replay")

    # ---- ライブ更新ポンプ (queue → signal) ----
    def start_pump(self):
        if self._pump_thread is not None:
            return
        self._q = self.service.state.subscribe()
        self._pump_stop = False
        self._pump_thread = threading.Thread(target=self._pump, daemon=True)
        self._pump_thread.start()

    def _pump(self):
        while not self._pump_stop:
            try:
                snap = self._q.get(timeout=0.2)
            except queue.Empty:
                continue
            self.snapshot.emit(snap)

    def stop_pump(self):
        self._pump_stop = True
        if self._q is not None:
            self.service.state.unsubscribe(self._q)
            self._q = None
        self._pump_thread = None
