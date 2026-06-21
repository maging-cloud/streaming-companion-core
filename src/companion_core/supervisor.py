#!/usr/bin/env python3
"""Generic worker lifecycle。ゲーム・UI 非依存。

各 worker は「1 tick 進める関数 (tick) + ポーリング間隔 (interval)」。worker_loop が
stop イベントまで tick を回し、tick 内の例外は握りつぶして継続する。spawn / sleeper /
max_ticks を注入でき、スレッドを使わず headless にテストできる。
"""
import sys
import threading
import time


class Worker:
    """並行起動する 1 ワーカー。"""

    def __init__(self, name, tick, interval):
        self.name = name
        self.tick = tick
        self.interval = interval


def worker_loop(tick, interval, stop, sleeper=time.sleep, max_ticks=None):
    """stop がセットされるまで tick を回す。max_ticks 指定時はその回数で抜ける (テスト用)。"""
    n = 0
    while not stop.is_set():
        try:
            tick()
        except Exception as e:  # noqa: BLE001 - 1 ワーカーの失敗で全体を止めない
            print(f"worker tick エラー (継続): {e}", file=sys.stderr)
        n += 1
        if max_ticks is not None and n >= max_ticks:
            break
        if stop.is_set():
            break
        sleeper(interval)


class Supervisor:
    """worker 群を thread で並行起動し、停止フラグで協調停止する。"""

    def __init__(self, workers, spawn=None, sleeper=time.sleep, max_ticks=None):
        self.workers = list(workers)
        self._spawn = spawn or (lambda target, name, daemon: threading.Thread(
            target=target, name=name, daemon=daemon))
        self._sleeper = sleeper
        self._max_ticks = max_ticks
        self._stop = None
        self._threads = []
        self.running = False

    def start(self):
        if self.running:
            return
        self._stop = threading.Event()
        self._threads = []
        for w in self.workers:
            t = self._spawn(
                lambda w=w: worker_loop(w.tick, w.interval, self._stop,
                                        self._sleeper, self._max_ticks),
                w.name, True)
            t.start()
            self._threads.append(t)
        self.running = True

    def stop(self):
        if not self.running:
            return
        self._stop.set()
        for t in self._threads:
            t.join(timeout=5.0)
        self.running = False

    def status(self):
        threads = self._threads or [None] * len(self.workers)
        return [{"name": w.name, "alive": (t.is_alive() if t else False)}
                for w, t in zip(self.workers, threads)]
