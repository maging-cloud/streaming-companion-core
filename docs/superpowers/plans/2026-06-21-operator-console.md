# Operator Console Implementation Plan (core side)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `companion_core` に generic な operator console (live 制御の backend + web UI) を追加し、配信パイプラインを GUI から start/stop/mute/replay・設定編集できるようにする。

**Architecture:** stdlib のみの ThreadingHTTPServer backend。ロジックは `ConsoleService` に集約し HTTP handler は薄い委譲。worker lifecycle は BPB から lift した `Supervisor`。TTS 合成・再生は backend が所有 (`ConsoleService.ingest` が sink として comment を受け、synth→player)。UI は単一静的 HTML (依存ゼロ)、安定 API 越しで後から Rust/Qt に差し替え可能。

**Tech Stack:** Python 3.11+ stdlib (`http.server`, `threading`, `queue`, `subprocess`, `winsound`, `tomllib`), 保存のみ `tomli-w` (optional extra `console`)。テストは `unittest`、注入で headless 化。

参照 spec: `docs/superpowers/specs/2026-06-21-operator-console-design.md`

---

## File Structure

- Create `src/companion_core/supervisor.py` — `Worker` / `worker_loop` / `Supervisor` (generic worker lifecycle)
- Create `src/companion_core/console/__init__.py`
- Create `src/companion_core/console/state.py` — `ConsoleState` (live 状態 + SSE 購読)
- Create `src/companion_core/console/playback.py` — `make_player` (platform 分岐 WAV 再生)
- Create `src/companion_core/console/service.py` — `ConsoleService` (全ロジック、HTTP 非依存)
- Create `src/companion_core/console/backend.py` — `make_handler` / `serve` / `main` (HTTP/SSE/static)
- Create `src/companion_core/console/static/index.html` — web UI (layout A, CSS/JS 埋め込み)
- Modify `src/companion_core/config.py` — `save_config` 追加
- Modify `pyproject.toml` — `console` extra + `companion-console` script + wheel に static 同梱
- Modify `tests/test_boundary.py` — console パッケージの純度確認 (既存ガードで自動的に対象)
- Create tests: `tests/test_supervisor.py` / `test_console_state.py` / `test_console_playback.py` / `test_console_service.py` / `test_console_backend.py`

> **スコープ外 (この PR):** `companion_settings` の config 統合 (重複 save の解消) は別 PR。meta(round/gold) の構造化表示は generic sink 契約 (`sink(text)`) に収まらないため後日。BPB 側 refactor は core merge 後の follow-up。

---

## Task 1: Supervisor (worker lifecycle を core に lift)

**Files:**
- Create: `src/companion_core/supervisor.py`
- Test: `tests/test_supervisor.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_supervisor.py
import unittest
from companion_core.supervisor import Worker, worker_loop, Supervisor


class _Stop:
    """is_set() が n 回目以降 True を返す手動 stop。"""
    def __init__(self, after):
        self.after = after
        self.n = 0
    def is_set(self):
        self.n += 1
        return self.n > self.after
    def set(self):
        self.after = -1


class _FakeThread:
    def __init__(self, target, name, daemon):
        self.target, self.name, self.daemon = target, name, daemon
        self.started = self.joined = False
        self._alive = False
    def start(self):
        self.started = True
        self._alive = True
        self.target()          # 同期実行 (テスト用)
        self._alive = False
    def join(self, timeout=None):
        self.joined = True
    def is_alive(self):
        return self._alive


class TestWorkerLoop(unittest.TestCase):
    def test_runs_tick_until_stop(self):
        calls = []
        stop = _Stop(after=3)               # 3 周回して止まる
        worker_loop(lambda: calls.append(1), 0.0, stop, sleeper=lambda s: None)
        self.assertEqual(len(calls), 3)

    def test_tick_exception_does_not_break_loop(self):
        calls = []
        def tick():
            calls.append(1)
            raise RuntimeError("boom")
        stop = _Stop(after=2)
        worker_loop(tick, 0.0, stop, sleeper=lambda s: None)
        self.assertEqual(len(calls), 2)     # 例外でも継続


class TestSupervisor(unittest.TestCase):
    def _spawn(self):
        made = []
        def spawn(target, name, daemon):
            t = _FakeThread(target, name, daemon)
            made.append(t)
            return t
        return spawn, made

    def test_start_spawns_one_thread_per_worker(self):
        spawn, made = self._spawn()
        ticks = []
        sup = Supervisor(
            [Worker("a", lambda: ticks.append("a"), 0.0)],
            spawn=spawn, sleeper=lambda s: None, max_ticks=2)
        sup.start()
        self.assertEqual(len(made), 1)
        self.assertTrue(made[0].started)
        self.assertEqual(ticks, ["a", "a"])

    def test_status_reports_names(self):
        spawn, made = self._spawn()
        sup = Supervisor(
            [Worker("a", lambda: None, 0.0), Worker("b", lambda: None, 0.0)],
            spawn=spawn, sleeper=lambda s: None, max_ticks=1)
        sup.start()
        names = [w["name"] for w in sup.status()]
        self.assertEqual(names, ["a", "b"])

    def test_stop_is_idempotent_and_sets_not_running(self):
        spawn, made = self._spawn()
        sup = Supervisor([Worker("a", lambda: None, 0.0)],
                         spawn=spawn, sleeper=lambda s: None, max_ticks=1)
        sup.start()
        sup.stop()
        sup.stop()
        self.assertFalse(sup.running)
        self.assertTrue(made[0].joined)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_supervisor.py -v` (or `python -m unittest tests.test_supervisor`)
Expected: FAIL — `ModuleNotFoundError: companion_core.supervisor`

- [ ] **Step 3: Write minimal implementation**

```python
# src/companion_core/supervisor.py
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
        return [{"name": w.name, "alive": (t.is_alive() if t else False)}
                for w, t in zip(self.workers, self._threads or [None] * len(self.workers))]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_supervisor.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/companion_core/supervisor.py tests/test_supervisor.py
git commit -m "feat(core): generic worker lifecycle Supervisor"
```

---

## Task 2: ConsoleState

**Files:**
- Create: `src/companion_core/console/__init__.py` (空)
- Create: `src/companion_core/console/state.py`
- Test: `tests/test_console_state.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_console_state.py
import unittest
from companion_core.console.state import ConsoleState


class TestConsoleState(unittest.TestCase):
    def test_snapshot_defaults(self):
        s = ConsoleState()
        snap = s.snapshot()
        self.assertFalse(snap["running"])
        self.assertFalse(snap["muted"])
        self.assertIsNone(snap["current"])
        self.assertEqual(snap["history"], [])

    def test_push_comment_sets_current_and_history(self):
        s = ConsoleState()
        s.push_comment("hello", ts=1.0)
        snap = s.snapshot()
        self.assertEqual(snap["current"]["text"], "hello")
        self.assertEqual(snap["current"]["ts"], 1.0)
        self.assertEqual(len(snap["history"]), 1)

    def test_history_capped(self):
        s = ConsoleState(history_limit=2)
        for i in range(5):
            s.push_comment(f"c{i}", ts=float(i))
        hist = s.snapshot()["history"]
        self.assertEqual([h["text"] for h in hist], ["c4", "c3"])  # 新しい順

    def test_setters(self):
        s = ConsoleState()
        s.set_running(True)
        s.set_muted(True)
        s.set_workers([{"name": "a", "alive": True}])
        snap = s.snapshot()
        self.assertTrue(snap["running"])
        self.assertTrue(snap["muted"])
        self.assertEqual(snap["workers"], [{"name": "a", "alive": True}])

    def test_subscribe_receives_snapshot_on_change(self):
        s = ConsoleState()
        q = s.subscribe()
        s.push_comment("x", ts=2.0)
        got = q.get_nowait()
        self.assertEqual(got["current"]["text"], "x")
        s.unsubscribe(q)

    def test_unsubscribe_stops_delivery(self):
        s = ConsoleState()
        q = s.subscribe()
        s.unsubscribe(q)
        s.push_comment("y", ts=1.0)
        self.assertTrue(q.empty())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_console_state.py -v`
Expected: FAIL — `ModuleNotFoundError: companion_core.console`

- [ ] **Step 3: Write minimal implementation**

```python
# src/companion_core/console/__init__.py
```
(空ファイル)

```python
# src/companion_core/console/state.py
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
        self._current = None       # {"text","ts"} | None
        self._history = []         # 新しい順
        self._subs = set()         # set[queue.Queue]
        self.last_wav = None       # 直近合成 WAV bytes (replay 用)

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
            del self._history[self._history_limit:]
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_console_state.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/companion_core/console/__init__.py src/companion_core/console/state.py tests/test_console_state.py
git commit -m "feat(core): ConsoleState (live 状態 + SSE 購読)"
```

---

## Task 3: playback player (platform 分岐)

**Files:**
- Create: `src/companion_core/console/playback.py`
- Test: `tests/test_console_playback.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_console_playback.py
import os
import tempfile
import unittest
from companion_core.console.playback import make_player


class TestPlayer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "out.wav")

    def test_writes_wav_then_calls_popen_on_mac(self):
        calls = []
        player = make_player(play_path=self.path, platform="darwin",
                             popen=lambda args: calls.append(args))
        player(b"RIFFdata")
        self.assertTrue(os.path.exists(self.path))
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), b"RIFFdata")
        self.assertEqual(calls, [["afplay", self.path]])

    def test_linux_uses_aplay(self):
        calls = []
        player = make_player(play_path=self.path, platform="linux",
                             popen=lambda args: calls.append(args))
        player(b"x")
        self.assertEqual(calls, [["aplay", "-q", self.path]])

    def test_windows_uses_winsound(self):
        calls = []
        class _WS:
            SND_FILENAME = 1
            SND_ASYNC = 2
            def PlaySound(self, path, flags):
                calls.append((path, flags))
        player = make_player(play_path=self.path, platform="win32",
                             winsound_mod=_WS())
        player(b"x")
        self.assertEqual(calls, [(self.path, 1 | 2)])

    def test_empty_wav_is_noop(self):
        calls = []
        player = make_player(play_path=self.path, platform="darwin",
                             popen=lambda args: calls.append(args))
        player(b"")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_console_playback.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/companion_core/console/playback.py
"""WAV bytes を OS 既定デバイスへ非同期再生する player を作る。

依存ゼロ (stdlib): Windows=winsound, macOS=afplay, Linux=aplay (subprocess)。
デバイス選択は OS 既定にルーティングする前提 (VB-CABLE を既定にする等)。
アプリ内デバイス選択は将来の optional extra。
"""
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_PLAY_PATH = Path.home() / ".streaming-companion" / "last.wav"


def make_player(play_path=None, platform=None, popen=None, winsound_mod=None):
    """player(wav_bytes) を返す。wav を play_path に書いてから platform 別に再生。"""
    play_path = str(play_path) if play_path is not None else str(DEFAULT_PLAY_PATH)
    platform = platform if platform is not None else sys.platform
    popen = popen or (lambda args: subprocess.Popen(args))  # 非ブロッキング

    def player(wav_bytes):
        if not wav_bytes:
            return
        os.makedirs(os.path.dirname(play_path) or ".", exist_ok=True)
        with open(play_path, "wb") as f:
            f.write(wav_bytes)
        if platform == "win32":
            ws = winsound_mod
            if ws is None:
                import winsound as ws  # noqa: PLC0415
            ws.PlaySound(play_path, ws.SND_FILENAME | ws.SND_ASYNC)
        elif platform == "darwin":
            popen(["afplay", play_path])
        else:
            popen(["aplay", "-q", play_path])

    return player
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_console_playback.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/companion_core/console/playback.py tests/test_console_playback.py
git commit -m "feat(core): platform 分岐の WAV player (stdlib)"
```

---

## Task 4: config に save_config を追加

**Files:**
- Modify: `src/companion_core/config.py`
- Test: `tests/test_config_save.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config_save.py
import os
import tempfile
import unittest

try:
    import tomli_w  # noqa: F401
    HAS_TOMLI_W = True
except ImportError:
    HAS_TOMLI_W = False

from companion_core.config import load_config, save_config


@unittest.skipUnless(HAS_TOMLI_W, "tomli-w 未インストール")
class TestSaveConfig(unittest.TestCase):
    def test_roundtrip(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "config.toml")
        save_config({"console": {"port": 8765}, "speech": {"min_interval": 5.0}}, path)
        cfg = load_config(path)
        self.assertEqual(cfg["console"]["port"], 8765)
        self.assertEqual(cfg["speech"]["min_interval"], 5.0)

    def test_creates_parent_dir(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "nested", "config.toml")
        save_config({"a": {"b": 1}}, path)
        self.assertTrue(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config_save.py -v`
Expected: FAIL — `ImportError: cannot import name 'save_config'`

- [ ] **Step 3: Write minimal implementation** — append to `src/companion_core/config.py`:

```python
def save_config(cfg, path=None):
    """cfg を config.toml に書き出す。tomli-w が要る (optional extra `console`/`ui`)。"""
    import tomli_w
    p = Path(path) if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        tomli_w.dump(cfg, f)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config_save.py -v`
Expected: PASS (2 tests; tomli-w 未インストールなら skip)

- [ ] **Step 5: Commit**

```bash
git add src/companion_core/config.py tests/test_config_save.py
git commit -m "feat(core): config save_config を追加"
```

---

## Task 5: ConsoleService (全ロジック、HTTP 非依存)

**Files:**
- Create: `src/companion_core/console/service.py`
- Test: `tests/test_console_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_console_service.py
import os
import tempfile
import unittest

from companion_core.supervisor import Supervisor, Worker
from companion_core.console.state import ConsoleState
from companion_core.console.service import ConsoleService

try:
    import tomli_w  # noqa: F401
    HAS_TOMLI_W = True
except ImportError:
    HAS_TOMLI_W = False


def _service(synth=None, player=None, config_path=None, clock=None):
    sup = Supervisor([Worker("a", lambda: None, 0.0)],
                     spawn=lambda target, name, daemon: _Noop(),
                     sleeper=lambda s: None, max_ticks=0)
    state = ConsoleState()
    return ConsoleService(sup, state, synth=synth, player=player,
                          config_path=config_path, clock=clock or (lambda: 1.0))


class _Noop:
    def start(self): pass
    def join(self, timeout=None): pass
    def is_alive(self): return True


class TestConsoleService(unittest.TestCase):
    def test_ingest_pushes_comment_and_plays(self):
        played = []
        svc = _service(synth=lambda t: b"WAV", player=lambda w: played.append(w))
        svc.ingest("hello")
        snap = svc.get_state()
        self.assertEqual(snap["current"]["text"], "hello")
        self.assertEqual(played, [b"WAV"])

    def test_mute_blocks_playback_but_keeps_text(self):
        played = []
        svc = _service(synth=lambda t: b"WAV", player=lambda w: played.append(w))
        svc.control("mute")
        svc.ingest("hi")
        self.assertEqual(played, [])
        self.assertEqual(svc.get_state()["current"]["text"], "hi")
        self.assertTrue(svc.get_state()["muted"])

    def test_synth_failure_still_records_text(self):
        def boom(t):
            raise RuntimeError("voicevox down")
        svc = _service(synth=boom, player=lambda w: None)
        svc.ingest("text-anyway")
        self.assertEqual(svc.get_state()["current"]["text"], "text-anyway")

    def test_replay_replays_last_wav(self):
        played = []
        svc = _service(synth=lambda t: b"W1", player=lambda w: played.append(w))
        svc.ingest("one")
        svc.control("replay")
        self.assertEqual(played, [b"W1", b"W1"])

    def test_start_stop_toggles_running(self):
        svc = _service()
        svc.control("start")
        self.assertTrue(svc.get_state()["running"])
        svc.control("stop")
        self.assertFalse(svc.get_state()["running"])

    def test_unknown_action_returns_error(self):
        svc = _service()
        res = svc.control("frobnicate")
        self.assertFalse(res["ok"])

    @unittest.skipUnless(HAS_TOMLI_W, "tomli-w 未インストール")
    def test_config_get_put_roundtrip(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "config.toml")
        svc = _service(config_path=path)
        res = svc.put_config({"speech": {"min_interval": 3.0}})
        self.assertTrue(res["ok"])
        self.assertTrue(res["restart_required"])
        self.assertEqual(svc.get_config()["speech"]["min_interval"], 3.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_console_service.py -v`
Expected: FAIL — `ModuleNotFoundError: companion_core.console.service`

- [ ] **Step 3: Write minimal implementation**

```python
# src/companion_core/console/service.py
"""console の全ロジック。HTTP 非依存で単体テスト可能。

`ingest(text)` は sink として live worker から呼ばれ、comment を state に積み、
TTS 合成 (synth) → 再生 (player) を駆動する (mute 時は再生しない)。start/stop は
Supervisor を直叩き。config は companion_core.config を再利用。
"""
import time

from .. import config as _config


class ConsoleService:
    def __init__(self, supervisor, state, synth=None, player=None,
                 config_path=None, clock=None):
        self.supervisor = supervisor
        self.state = state
        self.synth = synth          # callable(text) -> wav bytes | None
        self.player = player        # callable(wav bytes)
        self.config_path = config_path
        self._clock = clock or time.time

    # ---- sink (live worker から呼ばれる) ----
    def ingest(self, text):
        self.state.push_comment(text, ts=self._clock())
        wav = None
        if self.synth is not None:
            try:
                wav = self.synth(text)
            except Exception as e:  # noqa: BLE001 - TTS 落ちでもテキストは出す
                print(f"TTS 合成失敗 (継続): {e}")
                wav = None
        if wav:
            self.state.last_wav = wav
            if self.player is not None and not self.state.muted:
                self.player(wav)
        return text

    # ---- control ----
    def control(self, action):
        if action == "start":
            self.supervisor.start()
            self.state.set_workers(self.supervisor.status())
            self.state.set_running(True)
        elif action == "stop":
            self.supervisor.stop()
            self.state.set_running(False)
        elif action == "mute":
            self.state.set_muted(True)
        elif action == "unmute":
            self.state.set_muted(False)
        elif action == "replay":
            if self.state.last_wav and self.player is not None:
                self.player(self.state.last_wav)
        else:
            return {"ok": False, "error": f"unknown action: {action}",
                    "state": self.state.snapshot()}
        return {"ok": True, "state": self.state.snapshot()}

    # ---- state / config ----
    def get_state(self):
        return self.state.snapshot()

    def get_config(self):
        return _config.load_config(self.config_path)

    def put_config(self, cfg):
        _config.save_config(cfg, self.config_path)
        return {"ok": True, "restart_required": True}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_console_service.py -v`
Expected: PASS (7 tests; 1 は tomli-w 無しで skip)

- [ ] **Step 5: Commit**

```bash
git add src/companion_core/console/service.py tests/test_console_service.py
git commit -m "feat(core): ConsoleService (制御/TTS/config ロジック)"
```

---

## Task 6: HTTP backend (handler / serve / SSE / main)

**Files:**
- Create: `src/companion_core/console/backend.py`
- Test: `tests/test_console_backend.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_console_backend.py
import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from companion_core.supervisor import Supervisor, Worker
from companion_core.console.state import ConsoleState
from companion_core.console.service import ConsoleService
from companion_core.console.backend import make_handler


class _Noop:
    def start(self): pass
    def join(self, timeout=None): pass
    def is_alive(self): return True


def _make_server():
    sup = Supervisor([Worker("a", lambda: None, 0.0)],
                     spawn=lambda target, name, daemon: _Noop(),
                     sleeper=lambda s: None, max_ticks=0)
    svc = ConsoleService(sup, ConsoleState(), synth=lambda t: b"WAV",
                         player=lambda w: None, clock=lambda: 1.0)
    handler = make_handler(svc)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, svc


def _get(srv, path):
    port = srv.server_address[1]
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
        return r.status, r.read()


def _post(srv, path, obj):
    port = srv.server_address[1]
    data = json.dumps(obj).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, json.loads(r.read())


class TestBackend(unittest.TestCase):
    def setUp(self):
        self.srv, self.svc = _make_server()
        self.addCleanup(self.srv.shutdown)

    def test_index_served(self):
        status, body = _get(self.srv, "/")
        self.assertEqual(status, 200)
        self.assertIn(b"<html", body.lower())

    def test_state_json(self):
        status, body = _get(self.srv, "/state")
        self.assertEqual(status, 200)
        snap = json.loads(body)
        self.assertIn("running", snap)

    def test_control_start(self):
        status, res = _post(self.srv, "/control", {"action": "start"})
        self.assertEqual(status, 200)
        self.assertTrue(res["ok"])
        self.assertTrue(res["state"]["running"])

    def test_control_unknown_action(self):
        status, res = _post(self.srv, "/control", {"action": "nope"})
        self.assertFalse(res["ok"])

    def test_404_unknown_path(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            _get(self.srv, "/no-such")
        self.assertEqual(cm.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_console_backend.py -v`
Expected: FAIL — `ModuleNotFoundError: companion_core.console.backend`

- [ ] **Step 3: Write minimal implementation**

```python
# src/companion_core/console/backend.py
"""ThreadingHTTPServer による console backend。安定 API を提供し静的 UI を配信する。

ロジックは ConsoleService に委譲。handler は薄い HTTP アダプタ。
  GET  /          静的 UI (index.html)
  GET  /state     現在状態 (JSON)
  GET  /events    SSE (状態変化を push)
  GET  /config    config (JSON)
  POST /control   {"action": start|stop|mute|unmute|replay}
  PUT  /config    config を保存
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_STATIC = Path(__file__).parent / "static"


def make_handler(service):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # noqa: A003 - ログ抑制
            pass

        def _json(self, obj, status=200):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_body(self):
            n = int(self.headers.get("Content-Length", 0))
            if not n:
                return {}
            return json.loads(self.rfile.read(n).decode("utf-8"))

        def do_GET(self):
            if self.path == "/" or self.path == "/index.html":
                self._serve_index()
            elif self.path == "/state":
                self._json(service.get_state())
            elif self.path == "/config":
                self._json(service.get_config())
            elif self.path == "/events":
                self._serve_events()
            else:
                self._json({"error": "not found"}, status=404)

        def do_POST(self):
            if self.path == "/control":
                try:
                    body = self._read_body()
                except Exception:
                    return self._json({"ok": False, "error": "bad json"}, status=400)
                self._json(service.control(body.get("action", "")))
            else:
                self._json({"error": "not found"}, status=404)

        def do_PUT(self):
            if self.path == "/config":
                try:
                    body = self._read_body()
                except Exception:
                    return self._json({"ok": False, "error": "bad json"}, status=400)
                self._json(service.put_config(body))
            else:
                self._json({"error": "not found"}, status=404)

        def _serve_index(self):
            try:
                data = (_STATIC / "index.html").read_bytes()
            except FileNotFoundError:
                data = b"<html><body>console UI missing</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _serve_events(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            q = service.state.subscribe()
            try:
                # 接続直後に現状を 1 回送る
                self._send_event(service.get_state())
                while True:
                    snap = q.get()
                    self._send_event(snap)
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                service.state.unsubscribe(q)

        def _send_event(self, obj):
            payload = "event: state\ndata: " + json.dumps(obj) + "\n\n"
            self.wfile.write(payload.encode("utf-8"))
            self.wfile.flush()

    return Handler


def serve(service, host="127.0.0.1", port=8765):  # pragma: no cover - 実 runtime
    srv = ThreadingHTTPServer((host, port), make_handler(service))
    print(f"operator console: http://{host}:{port}")
    srv.serve_forever()


def main(argv=None):  # pragma: no cover - CLI 配線
    """workers を持たない core 単体起動 (UI/設定編集の確認用)。"""
    from ..supervisor import Supervisor
    from .state import ConsoleState
    from .service import ConsoleService
    from .playback import make_player
    from ..config import load_config

    cfg = load_config()
    console = cfg.get("console", {})
    svc = ConsoleService(Supervisor([]), ConsoleState(),
                         synth=None, player=make_player())
    serve(svc, console.get("host", "127.0.0.1"), int(console.get("port", 8765)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_console_backend.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/companion_core/console/backend.py tests/test_console_backend.py
git commit -m "feat(core): console HTTP backend (state/control/config/SSE)"
```

---

## Task 7: web UI (layout A, 単一静的 HTML)

**Files:**
- Create: `src/companion_core/console/static/index.html`

> このタスクは静的アセットのため TDD 対象外。Task 6 の `test_index_served` が配信を担保する。
> 手動確認: `companion-console` 起動 → ブラウザで開く (Task 9 後)。

- [ ] **Step 1: Create the file**

```html
<!-- src/companion_core/console/static/index.html -->
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Operator Console</title>
<style>
  :root { color-scheme: dark; }
  body { font-family: system-ui, sans-serif; margin: 0; background:#15171c; color:#e6e6e6; }
  .bar { display:flex; justify-content:space-between; align-items:center;
         padding:10px 14px; background:#1d2026; border-bottom:1px solid #2c2f36; }
  .status { font-weight:600; }
  .dot { color:#888; } .dot.run { color:#3ad29f; }
  button { background:#2c2f36; color:#e6e6e6; border:1px solid #3a3d44;
           border-radius:6px; padding:6px 12px; cursor:pointer; font-size:14px; }
  button:hover { background:#363a42; }
  button.on { background:#7a3a3a; }
  .now { padding:18px 16px; }
  .label { font-size:11px; letter-spacing:.08em; color:#8a8f98; text-transform:uppercase; }
  .text { font-size:18px; margin:6px 0 14px; min-height:1.4em; }
  .hist div { color:#9aa0aa; padding:3px 0; border-top:1px solid #23262d; }
  details { padding:10px 16px; border-top:1px solid #2c2f36; }
  summary { cursor:pointer; color:#8a8f98; }
  .cfg { margin-top:8px; white-space:pre-wrap; font-family:ui-monospace,monospace;
         font-size:12px; color:#aab; }
</style>
</head>
<body>
  <div class="bar">
    <span class="status"><span id="dot" class="dot">●</span> <span id="st">STOPPED</span></span>
    <span>
      <button id="toggle">▶ START</button>
      <button id="mute">🔇 MUTE</button>
      <button id="replay">🔁 再生</button>
    </span>
  </div>
  <div class="now">
    <div class="label">Now Speaking</div>
    <div class="text" id="now">—</div>
    <div class="label">History</div>
    <div class="hist" id="hist"></div>
  </div>
  <details>
    <summary>設定 (config.toml)</summary>
    <div class="cfg" id="cfg">…</div>
  </details>
<script>
let running = false, muted = false;
function render(s) {
  running = s.running; muted = s.muted;
  document.getElementById("st").textContent = s.running ? "RUNNING" : "STOPPED";
  document.getElementById("dot").className = "dot" + (s.running ? " run" : "");
  document.getElementById("toggle").textContent = s.running ? "⏹ STOP" : "▶ START";
  const mb = document.getElementById("mute");
  mb.textContent = s.muted ? "🔈 UNMUTE" : "🔇 MUTE";
  mb.className = s.muted ? "on" : "";
  document.getElementById("now").textContent = s.current ? s.current.text : "—";
  document.getElementById("hist").innerHTML =
    (s.history || []).map(h => "<div>" + escapeHtml(h.text) + "</div>").join("");
}
function escapeHtml(t){return t.replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));}
async function post(action){
  const r = await fetch("/control",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({action})});
  render((await r.json()).state);
}
document.getElementById("toggle").onclick = () => post(running ? "stop" : "start");
document.getElementById("mute").onclick   = () => post(muted ? "unmute" : "mute");
document.getElementById("replay").onclick = () => post("replay");
async function loadCfg(){
  const r = await fetch("/config"); 
  document.getElementById("cfg").textContent = JSON.stringify(await r.json(), null, 2);
}
const es = new EventSource("/events");
es.addEventListener("state", e => render(JSON.parse(e.data)));
fetch("/state").then(r=>r.json()).then(render);
loadCfg();
</script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add src/companion_core/console/static/index.html
git commit -m "feat(core): operator console web UI (layout A)"
```

---

## Task 8: pyproject (console extra / script / static 同梱)

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Edit pyproject.toml**

`[project.optional-dependencies]` に追記:
```toml
console = ["tomli-w>=1.0"]
```

`[project.scripts]` に追記:
```toml
companion-console = "companion_core.console.backend:main"
```

`[tool.hatch.build.targets.wheel]` の後に静的アセット同梱を追記:
```toml
[tool.hatch.build.targets.wheel.force-include]
"src/companion_core/console/static" = "companion_core/console/static"
```

- [ ] **Step 2: Verify install + script resolves**

Run:
```bash
cd C:/Users/aki/work/streaming-companion-core
uv pip install -e ".[console]"
python -c "from companion_core.console.backend import main; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: 全 PASS (新規 5 ファイル + 既存)

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "build(core): console extra + companion-console script + static 同梱"
```

---

## Task 9: 手動スモーク + README 追記

**Files:**
- Modify: `README.md` (console セクション追記)

- [ ] **Step 1: 手動スモーク (UI 配信 + API)**

Run:
```bash
companion-console
```
別ターミナルで:
```bash
curl -s http://127.0.0.1:8765/state
curl -s -X POST http://127.0.0.1:8765/control -H "Content-Type: application/json" -d "{\"action\":\"start\"}"
```
ブラウザで `http://127.0.0.1:8765` を開き、START/MUTE/再生ボタンと設定表示を確認。
Expected: state JSON が返る、ボタンで running が切り替わる。

- [ ] **Step 2: README に operator console セクションを追記**

```markdown
## Operator Console

配信中の live 制御 (start/stop/mute/replay/設定) を行う web console。

    pip install streaming-companion-core[console]
    companion-console            # http://127.0.0.1:8765

API: `GET /state` · `POST /control` · `GET·PUT /config` · `GET /events`(SSE)。
UI は安定 API の薄いクライアントで、後から Rust/Qt フロントへ差し替え可能。
音声再生は OS 既定デバイス経由 (VB-CABLE を既定にすると配信へ流せる)。
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(core): operator console を README に追記"
```

---

## Self-Review チェック結果

- **Spec coverage:** Supervisor(worker lift)=T1 / ConsoleState(SSE)=T2 / realtime playback=T3 / config 拡張=T4 / TTS所有・mute・replay・start/stop=T5 / API 契約(state/control/config/events)=T6 / web UI layout A=T7 / console extra+script=T8。BPB refactor・companion_settings 統合・device picker・meta 表示はスコープ外と明記。
- **Placeholder scan:** なし (全 step に実コード)。
- **Type consistency:** `ConsoleService(supervisor, state, synth, player, config_path, clock)` は T5/T6 テストで一致。`Supervisor(workers, spawn, sleeper, max_ticks)` は T1/T5/T6 で一致。`make_player(play_path, platform, popen, winsound_mod)` は T3 で一致。`state.subscribe()/unsubscribe()/snapshot()/push_comment(text,ts)` は T2/T6 で一致。
