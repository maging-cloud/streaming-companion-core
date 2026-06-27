# core reactive queue + pump 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** push 型 companion (Twitch/Discord/YouTube 等) が共有する「バーストを溜めて重要イベントを 1 件ずつ喋る」反応ループを `companion_core` の汎用部品 (EventQueue + pump worker) として追加する。

**Architecture:** 新規 `queue.py` に優先度付き bounded + coalesce の `EventQueue` を置く。`pump.py` は queue を 1 tick = 1 件 drain し `get_handler(kind)→comment→fan_out` する Worker を組み立てる薄い層 (既存 `supervisor.Worker` / `comment` / `fan_out` / `SpeechGate` を再利用、新規ロジックは増やさない)。プラグインは normalize の出力 `(priority, dedup_key, CommentRequest)` を EventQueue に push するだけ。

**Tech Stack:** Python 3.14 / uv / hatchling / pytest。標準ライブラリのみ (新規依存なし)。

**Spec:** `docs/superpowers/specs/2026-06-25-twitch-companion-design.md` の「companion_core への汎用追加」「EventQueue / pump」節。

## Global Constraints

- Python `>=3.14`、`from __future__ import annotations` を各モジュール先頭に置く (既存慣習)。
- **新規実行時依存を増やさない** (標準ライブラリのみ)。
- ゲーム・プラットフォーム非依存 (BPB/Twitch を一切 import しない)。純データ構造 + 既存 core API の再利用に留める。
- 既存の公開 API を壊さない (追加のみ)。`companion_core.__init__` から新規シンボルを re-export する。
- テストはネットワーク・外部依存なしで完結 (fake handler / fake sink / fake queue)。
- コミットメッセージ末尾に既存慣習通り Co-Authored-By 行を付ける。

---

### Task 1: EventQueue (優先度 + bounded + coalesce)

**Files:**
- Create: `src/companion_core/queue.py`
- Test: `src/companion_core/test_queue.py`

**Interfaces:**
- Consumes: なし (標準ライブラリのみ)。
- Produces:
  - `class QueuedItem` — `dataclass(priority:int, seq:int, request:dict, dedup_key:str|None=None, count:int=1)`
  - `class EventQueue`:
    - `__init__(self, maxsize:int=200)`
    - `put(self, priority:int, request:dict, dedup_key:str|None=None) -> None`
    - `get(self) -> QueuedItem | None` (最高優先度・同率は FIFO=最古)
    - `__len__(self) -> int`

- [ ] **Step 1: Write the failing tests**

Create `src/companion_core/test_queue.py`:

```python
from companion_core.queue import EventQueue, QueuedItem


def _req(kind, **payload):
    return {"kind": kind, "payload": payload}


def test_get_returns_highest_priority_first():
    q = EventQueue()
    q.put(0, _req("chat"))
    q.put(5, _req("cheer"))
    q.put(2, _req("sub"))
    assert q.get().request["kind"] == "cheer"
    assert q.get().request["kind"] == "sub"
    assert q.get().request["kind"] == "chat"
    assert q.get() is None


def test_same_priority_is_fifo():
    q = EventQueue()
    q.put(1, _req("chat", n=1))
    q.put(1, _req("chat", n=2))
    assert q.get().request["payload"]["n"] == 1  # 最古が先
    assert q.get().request["payload"]["n"] == 2


def test_coalesce_same_dedup_key_increments_count_no_new_item():
    q = EventQueue()
    q.put(5, _req("giftbomb", total=5), dedup_key="gifter:alice")
    q.put(2, _req("sub"), dedup_key="gifter:alice")  # 同 key → coalesce (追加しない)
    assert len(q) == 1
    item = q.get()
    assert item.request["kind"] == "giftbomb"  # 先勝ち
    assert item.count == 2


def test_bounded_evicts_lowest_priority_oldest():
    q = EventQueue(maxsize=2)
    q.put(0, _req("chat", n=1))   # 最低優先・最古 → 押し出される
    q.put(0, _req("chat", n=2))
    q.put(9, _req("raid"))        # 満杯 → victim を1件押し出して追加
    assert len(q) == 2
    kinds = [q.get().request for _ in range(2)]
    assert {"raid"} <= {r["kind"] for r in kinds}
    assert all(r["payload"].get("n") != 1 for r in kinds)  # n=1 は押し出された


def test_len_and_empty_get():
    q = EventQueue()
    assert len(q) == 0
    assert q.get() is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest src/companion_core/test_queue.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'companion_core.queue'`

- [ ] **Step 3: Write the implementation**

Create `src/companion_core/queue.py`:

```python
#!/usr/bin/env python3
"""push 型 companion 用の汎用イベントキュー (優先度 + bounded + coalesce)。

バーストする入力 (Twitch のレイド / ギフト爆撃 / チャット洪水) を溜め、pump worker が
TTS ペースで 1 件ずつ取り出す。プラットフォーム非依存・純データ構造。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class QueuedItem:
    priority: int
    seq: int
    request: dict[str, Any]  # CommentRequest {kind, payload}
    dedup_key: str | None = None
    count: int = 1  # 同 dedup_key を coalesce した回数


class EventQueue:
    """優先度付き bounded キュー。同 dedup_key は coalesce (先勝ち + count 加算)。"""

    def __init__(self, maxsize: int = 200) -> None:
        self.maxsize = maxsize
        self._items: list[QueuedItem] = []
        self._by_key: dict[str, QueuedItem] = {}
        self._seq = 0

    def __len__(self) -> int:
        return len(self._items)

    def put(self, priority: int, request: dict[str, Any], dedup_key: str | None = None) -> None:
        """投入。dedup_key が既存と一致すれば coalesce (count++、新規追加しない)。
        満杯なら最低優先度・同率最古を 1 件押し出してから追加。"""
        if dedup_key is not None and dedup_key in self._by_key:
            self._by_key[dedup_key].count += 1
            return
        if len(self._items) >= self.maxsize:
            victim = min(self._items, key=lambda it: (it.priority, it.seq))
            self._remove(victim)
        item = QueuedItem(priority=priority, seq=self._seq, request=request, dedup_key=dedup_key)
        self._seq += 1
        self._items.append(item)
        if dedup_key is not None:
            self._by_key[dedup_key] = item

    def get(self) -> QueuedItem | None:
        """最高優先度・同率は FIFO (最古) を 1 件取り出す。空なら None。"""
        if not self._items:
            return None
        item = max(self._items, key=lambda it: (it.priority, -it.seq))
        self._remove(item)
        return item

    def _remove(self, item: QueuedItem) -> None:
        self._items.remove(item)
        if item.dedup_key is not None:
            self._by_key.pop(item.dedup_key, None)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest src/companion_core/test_queue.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/companion_core/queue.py src/companion_core/test_queue.py
git commit -m "feat(queue): 優先度 + bounded + coalesce の EventQueue を追加

push 型 companion 共通のバースト吸収用。同 dedup_key は coalesce (先勝ち+count)、
満杯時は最低優先度・最古を押し出す。純データ構造・標準ライブラリのみ。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: pump worker (queue を drain して実況)

**Files:**
- Create: `src/companion_core/pump.py`
- Test: `src/companion_core/test_pump.py`

**Interfaces:**
- Consumes:
  - `EventQueue.get() -> QueuedItem | None` (Task 1)
  - 既存 `companion_core.comment.comment(request, handler, client=None, processors=None, ngwords=None, persona=None) -> str`
  - 既存 `companion_core.sink.fan_out(text, sinks) -> list`
  - 既存 `companion_core.supervisor.Worker(name, tick, interval)`
  - 既存 `SpeechGate.should_speak(*, score=None, kind=None, force=False) -> bool` (companion_core.orchestrator)
- Produces:
  - `make_pump_worker(queue, sinks, *, get_handler, client=None, ngwords=None, persona=None, gate=None, name="pump", interval=0.2) -> Worker`

- [ ] **Step 1: Write the failing tests**

Create `src/companion_core/test_pump.py`:

```python
from companion_core.pump import make_pump_worker
from companion_core.queue import EventQueue


class _FakeHandler:
    # comment(request, handler, client=None) は client 無しで handler.template を使う
    def template(self, request):
        return f"{request['payload']['user']} さんなのだ"


def _get_handler(kind):
    return _FakeHandler()


def test_tick_pops_one_item_and_fans_out():
    q = EventQueue()
    q.put(5, {"kind": "twitch_event", "payload": {"user": "alice"}})
    out = []
    w = make_pump_worker(q, [out.append], get_handler=_get_handler)
    w.tick()
    assert out == ["alice さんなのだ"]
    assert len(q) == 0  # 1 件消費


def test_empty_queue_tick_is_noop():
    q = EventQueue()
    out = []
    w = make_pump_worker(q, [out.append], get_handler=_get_handler)
    w.tick()
    assert out == []


def test_gate_suppresses_item():
    q = EventQueue()
    q.put(0, {"kind": "twitch_chat", "payload": {"user": "bob"}})
    out = []

    class _Gate:
        def should_speak(self, *, score=None, kind=None, force=False):
            return False

    w = make_pump_worker(q, [out.append], get_handler=_get_handler, gate=_Gate())
    w.tick()
    assert out == []  # gate が抑制


def test_highest_priority_spoken_first_across_ticks():
    q = EventQueue()
    q.put(0, {"kind": "twitch_chat", "payload": {"user": "low"}})
    q.put(9, {"kind": "twitch_event", "payload": {"user": "high"}})
    out = []
    w = make_pump_worker(q, [out.append], get_handler=_get_handler)
    w.tick()
    w.tick()
    assert out == ["high さんなのだ", "low さんなのだ"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest src/companion_core/test_pump.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'companion_core.pump'`

- [ ] **Step 3: Write the implementation**

Create `src/companion_core/pump.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest src/companion_core/test_pump.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/companion_core/pump.py src/companion_core/test_pump.py
git commit -m "feat(pump): EventQueue を drain して実況する pump worker を追加

queue→get_handler→comment→fan_out を 1 tick=1件で処理する Worker を組み立てる薄い層。
既存 supervisor.Worker / comment / fan_out / SpeechGate を再利用 (新規ロジックなし)。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: re-export + バージョン up + tag

**Files:**
- Modify: `src/companion_core/__init__.py`
- Modify: `pyproject.toml:3` (version `0.11.0` → `0.12.0`)
- Test: `src/companion_core/test_queue.py` (import 経路の追加確認は既存テストで足りるため新規不要)

**Interfaces:**
- Produces: `from companion_core import EventQueue, make_pump_worker` が解決する。

- [ ] **Step 1: 公開 import を確認するテストを追加**

`src/companion_core/test_queue.py` の末尾に追記:

```python
def test_public_exports():
    import companion_core

    assert hasattr(companion_core, "EventQueue")
    assert hasattr(companion_core, "make_pump_worker")
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest src/companion_core/test_queue.py::test_public_exports -v`
Expected: FAIL with `AssertionError` (まだ re-export していない)

- [ ] **Step 3: `__init__.py` に re-export を追加**

`src/companion_core/__init__.py` の既存 import 群の末尾に追記 (既存の `__all__` がある場合は両シンボルを追加):

```python
from companion_core.pump import make_pump_worker
from companion_core.queue import EventQueue, QueuedItem
```

`__all__` が定義されている場合は `"EventQueue"`, `"QueuedItem"`, `"make_pump_worker"` を追加する。
(無ければこの追記のみでよい。)

- [ ] **Step 4: Run to verify it passes + 全テスト緑**

Run: `uv run pytest src/companion_core/test_queue.py::test_public_exports -v`
Expected: PASS

Run: `uv run pytest -q`
Expected: 全テスト PASS (既存 + 新規 queue/pump)

- [ ] **Step 5: バージョン up**

`pyproject.toml` の `version = "0.11.0"` を `version = "0.12.0"` に変更 (minor up = 後方互換の機能追加)。

- [ ] **Step 6: Commit + tag + push**

```bash
git add src/companion_core/__init__.py pyproject.toml
git commit -m "chore: EventQueue/make_pump_worker を re-export し v0.12.0 に

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git tag v0.12.0
git push origin HEAD
git push origin v0.12.0
```

(ブランチ運用に従い、main 直押しでなく PR 経由なら: ブランチを切って push → PR → マージ後に
main で `git tag v0.12.0 && git push origin v0.12.0`。)

---

## 次プラン (本計画の対象外)

`streaming-companion-twitch` 新規 repo の実装は **別プラン**とする (本 core v0.12.0 tag に依存)。
内容: `eventsub/{client,helix}`、`normalize.py` (notification → `(priority, dedup_key, CommentRequest)`、
core.EventQueue へ push)、`handlers.py` (TwitchEventHandler/TwitchChatHandler)、`live.py` (client→
normalize→EventQueue→make_pump_worker→Supervisor)、`config.py`。chat 正規化は core の
`sources/chat.py` (`from_chat`/`ChatRouter`/`keyword_matcher`) を再利用。core v0.12.0 がマージ・tag
された後に着手する。

## Self-Review

- **Spec coverage**: EventQueue (優先度/bounded/coalesce) = Task 1 ✓。pump (drain→get_handler→
  comment→fan_out、SpeechGate 併用、例外隔離=Worker 再利用) = Task 2 ✓。re-export + minor tag = Task 3 ✓。
  spec の `companion_core への汎用追加`「EventQueue / pump」節を網羅。twitch 固有 (eventsub/normalize/
  handlers/config) は別プランに明示分離。
- **Placeholder scan**: 各 step に実コード・実コマンド・期待出力あり。TBD/TODO なし。`__init__.py` の
  `__all__` は「あれば追加」と条件付きだが、追記する具体シンボル名を明示済み。
- **Type consistency**: `EventQueue.put(priority, request, dedup_key)` / `get() -> QueuedItem` / `QueuedItem.request`
  ・`.count` は Task 1 と Task 2 のテスト・実装で一致。`make_pump_worker(..., get_handler=, gate=)` の
  キーワードは Task 2 のテストと実装で一致。`comment(request, handler, client=None, ngwords=, persona=)` は
  既存シグネチャと一致。
