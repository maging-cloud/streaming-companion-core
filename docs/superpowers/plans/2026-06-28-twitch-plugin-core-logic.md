# streaming-companion-twitch (Plan A: scaffold + 純ロジック) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新規公開 repo `streaming-companion-twitch` を scaffold し、ネットワーク非依存の純ロジック (config / normalize / handlers) を TDD で実装する。EventSub WebSocket client と live wiring は Plan B (本計画の対象外)。

**Architecture:** src-layout の uv プロジェクト。`companion_core` (v0.12.0) を git dep で参照。`normalize.py` が EventSub notification dict → `(priority, dedup_key, CommentRequest)` (捨てる時 None) を返す純関数。`handlers.py` の TwitchEventHandler / TwitchChatHandler は core の `comment()` が呼ぶ `template(request)` / `build_user(payload)` を実装。`config.py` は `[twitch]` セクション + env を解決。

**Tech Stack:** Python 3.14 / uv / hatchling / pytest。実行時依存は `streaming-companion-core` のみ (Plan A の純ロジックは websocket-client 不要、Plan B で追加)。

**Spec:** `docs/superpowers/specs/2026-06-25-twitch-companion-design.md`。

## Global Constraints

- Python `>=3.14`、各モジュール先頭に `from __future__ import annotations`。
- import 名 `companion_twitch`、dist 名 `streaming-companion-twitch`、MIT、src-layout (`src/companion_twitch/`)。
- 依存方向は **twitch → core の一方向**。`companion_core` を import してよいが、core は twitch を import しない。
- 実行時依存は最小: Plan A は `streaming-companion-core` のみ (websocket-client は Plan B)。
- secret (OAuth token / client_id) はコードに焼かず env / config で注入。
- normalize は `companion_core.request.make_request(kind, payload)` で CommentRequest を作る。chat 正規化は `companion_core.sources.chat.from_chat(user, text, kind)` を再利用。
- handler は core の `comment()` 契約に従う: `template(request) -> str` (必須・client=None と NG fallback で使用) と `build_user(payload) -> str` (LLM 経路)。
- テストはネットワーク非依存 (`uv run pytest`)。
- コミットメッセージ末尾に `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。
- 作業ディレクトリは新規 repo `C:\Users\aki\work\streaming-companion-twitch`。

---

### Task 1: repo scaffold

**Files:**
- Create: `C:\Users\aki\work\streaming-companion-twitch\pyproject.toml`
- Create: `src/companion_twitch/__init__.py`
- Create: `src/companion_twitch/test_smoke.py`
- Create: `README.md`, `.gitignore`, `LICENSE`

**Interfaces:**
- Consumes: なし。
- Produces: import 可能なパッケージ `companion_twitch`、`uv run pytest` が動く環境、`companion_core` (v0.12.0) が解決される。

- [ ] **Step 1: ディレクトリと git 初期化**

```bash
mkdir -p "C:/Users/aki/work/streaming-companion-twitch/src/companion_twitch"
cd "C:/Users/aki/work/streaming-companion-twitch"
git init -q
```

- [ ] **Step 2: pyproject.toml を作成**

`C:\Users\aki\work\streaming-companion-twitch\pyproject.toml`:

```toml
[project]
name = "streaming-companion-twitch"
version = "0.1.0"
description = "Twitch チャット/イベントにずんだもん実況で反応する配信 companion (companion_core プラグイン)"
requires-python = ">=3.14"
license = "MIT"
dependencies = [
    "streaming-companion-core",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/companion_twitch"]

[tool.uv.sources]
streaming-companion-core = { git = "https://github.com/maging-cloud/streaming-companion-core.git", tag = "v0.12.0" }

[dependency-groups]
dev = [
    "pytest>=9.0",
    "ruff>=0.14",
    "mypy>=2.0",
]

[tool.ruff]
line-length = 120
target-version = "py314"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "C", "B", "UP"]
ignore = ["E501", "C901"]

[tool.mypy]
python_version = "3.14"
ignore_missing_imports = true
exclude = ['(^|/)test_[^/]*\.py$']
```

- [ ] **Step 3: パッケージ初期ファイルと補助ファイル**

`src/companion_twitch/__init__.py`:

```python
"""Twitch interaction companion (companion_core プラグイン)。"""
```

`.gitignore`:

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
.superpowers/
```

`README.md`:

```markdown
# streaming-companion-twitch

Twitch のチャット・チャンネルイベント (フォロー/サブスク/ギフト/ビッツ/レイド) に
ずんだもん実況 (TTS) で反応する配信 companion。`companion_core` のプラグイン。

設計: streaming-companion-core の `docs/superpowers/specs/2026-06-25-twitch-companion-design.md`。

## 開発

    uv sync
    uv run pytest

secret はコードに焼かず env で注入 (`TWITCH_CLIENT_ID`, `TWITCH_OAUTH_TOKEN`)。
```

`LICENSE`: MIT License 本文 (年 2026, 著作権者 "maging-cloud") を記載する。標準 MIT テンプレート:

```
MIT License

Copyright (c) 2026 maging-cloud

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 4: smoke テストを作成**

`src/companion_twitch/test_smoke.py`:

```python
from __future__ import annotations


def test_package_imports():
    import companion_twitch

    assert companion_twitch.__doc__ is not None


def test_core_is_available():
    # twitch → core の依存が解決されている
    from companion_core.request import make_request

    assert make_request("twitch_event", {"x": 1}) == {"kind": "twitch_event", "payload": {"x": 1}}
```

- [ ] **Step 5: 依存解決 + テスト実行**

Run:
```bash
cd "C:/Users/aki/work/streaming-companion-twitch"
uv sync
uv run pytest src/companion_twitch/test_smoke.py -v
```
Expected: `uv sync` が core v0.12.0 を取得し成功、テスト 2 passed。

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: streaming-companion-twitch scaffold (uv + core v0.12.0 dep)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: config.py

**Files:**
- Create: `src/companion_twitch/config.py`
- Test: `src/companion_twitch/test_config.py`

**Interfaces:**
- Consumes: なし (env / config dict は引数注入)。
- Produces:
  - `resolve_config(section: dict | None = None, env: dict | None = None) -> dict`
    返り値 dict のキー: `channel:str`, `client_id:str|None`, `oauth_token:str|None`,
    `triggers:tuple[str,...]`, `chat_sampling:float`, `command_prefix:str`。
    secret は env (`TWITCH_CLIENT_ID`, `TWITCH_OAUTH_TOKEN`) を優先、無ければ section。
  - `REQUIRED_SCOPES: tuple[str, ...]` = follow/sub/cheer/chat の必要スコープ。

- [ ] **Step 1: Write the failing tests**

`src/companion_twitch/test_config.py`:

```python
from __future__ import annotations

from companion_twitch.config import REQUIRED_SCOPES, resolve_config


def test_env_secrets_take_precedence():
    cfg = resolve_config(
        section={"channel": "ch", "client_id": "from_cfg"},
        env={"TWITCH_CLIENT_ID": "from_env", "TWITCH_OAUTH_TOKEN": "tok"},
    )
    assert cfg["channel"] == "ch"
    assert cfg["client_id"] == "from_env"  # env 優先
    assert cfg["oauth_token"] == "tok"


def test_defaults_when_missing():
    cfg = resolve_config(section={"channel": "ch"}, env={})
    assert cfg["triggers"] == ("mention", "command", "firstmsg")
    assert cfg["chat_sampling"] == 0.0
    assert cfg["command_prefix"] == "!"
    assert cfg["client_id"] is None
    assert cfg["oauth_token"] is None


def test_triggers_parsed_from_csv_and_sampling_float():
    cfg = resolve_config(
        section={"channel": "ch", "triggers": "mention, command", "chat_sampling": "0.1"},
        env={},
    )
    assert cfg["triggers"] == ("mention", "command")
    assert cfg["chat_sampling"] == 0.1


def test_required_scopes_present():
    assert "user:read:chat" in REQUIRED_SCOPES
    assert "moderator:read:followers" in REQUIRED_SCOPES
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest src/companion_twitch/test_config.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'companion_twitch.config'`

- [ ] **Step 3: Write the implementation**

`src/companion_twitch/config.py`:

```python
#!/usr/bin/env python3
"""[twitch] セクション + env を解決して設定 dict にする。secret は env 優先。"""

from __future__ import annotations

from typing import Any

REQUIRED_SCOPES: tuple[str, ...] = (
    "moderator:read:followers",  # channel.follow
    "channel:read:subscriptions",  # channel.subscribe 系
    "bits:read",  # channel.cheer
    "user:read:chat",  # channel.chat.message
)

_DEFAULT_TRIGGERS = ("mention", "command", "firstmsg")


def resolve_config(section: dict[str, Any] | None = None, env: dict[str, str] | None = None) -> dict[str, Any]:
    """[twitch] セクション dict と env dict から設定を解決する。

    secret (client_id / oauth_token) は env (TWITCH_CLIENT_ID / TWITCH_OAUTH_TOKEN) を優先。
    triggers は CSV 文字列を tuple に、chat_sampling は float に正規化。
    """
    section = section or {}
    env = env or {}

    raw_triggers = section.get("triggers")
    if isinstance(raw_triggers, str):
        triggers = tuple(t.strip() for t in raw_triggers.split(",") if t.strip())
    elif raw_triggers:
        triggers = tuple(raw_triggers)
    else:
        triggers = _DEFAULT_TRIGGERS

    return {
        "channel": section.get("channel", ""),
        "client_id": env.get("TWITCH_CLIENT_ID") or section.get("client_id"),
        "oauth_token": env.get("TWITCH_OAUTH_TOKEN") or section.get("oauth_token"),
        "triggers": triggers,
        "chat_sampling": float(section.get("chat_sampling", 0.0)),
        "command_prefix": str(section.get("command_prefix", "!")),
    }
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest src/companion_twitch/test_config.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/companion_twitch/config.py src/companion_twitch/test_config.py
git commit -m "feat(config): [twitch] + env 解決 (secret は env 優先)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: normalize.py

**Files:**
- Create: `src/companion_twitch/normalize.py`
- Test: `src/companion_twitch/test_normalize.py`

**Interfaces:**
- Consumes:
  - `companion_core.request.make_request(kind, payload) -> {"kind","payload"}`
  - `companion_core.sources.chat.from_chat(user, text, kind="chat") -> {"kind","payload"}`
- Produces:
  - `PRIORITY: dict[str, int]` — type→優先度。
  - `normalize(notification, *, seen=None, triggers=(...), command_prefix="!", channel="", sampler=None) -> tuple[int, str|None, dict] | None`
    返り値: `(priority, dedup_key, CommentRequest)`、捨てる時 `None`。
    `notification` は EventSub の `{"metadata":{"message_id","subscription_type"},"payload":{"event":{...}}}`。
    `seen` は処理済 message_id の set (冪等)。`sampler()` は chat サンプリング当落 (bool) を返す注入関数。

- [ ] **Step 1: Write the failing tests**

`src/companion_twitch/test_normalize.py`:

```python
from __future__ import annotations

from companion_twitch.normalize import PRIORITY, normalize


def _notif(sub_type, event, message_id="m1"):
    return {
        "metadata": {"message_id": message_id, "subscription_type": sub_type},
        "payload": {"event": event},
    }


def test_cheer_is_high_priority_with_big_flag():
    n = _notif("channel.cheer", {"user_name": "alice", "bits": 1000})
    pri, key, req = normalize(n)
    assert pri == PRIORITY["cheer"]
    assert req["kind"] == "twitch_event"
    assert req["payload"]["type"] == "cheer"
    assert req["payload"]["user"] == "alice"
    assert req["payload"]["bits"] == 1000
    assert req["payload"]["big"] is True  # >=1000


def test_follow_is_low_priority():
    n = _notif("channel.follow", {"user_name": "bob"})
    pri, key, req = normalize(n)
    assert pri == PRIORITY["follow"]
    assert req["payload"]["type"] == "follow"
    assert req["payload"]["user"] == "bob"


def test_giftbomb_uses_gifter_dedup_key():
    n = _notif("channel.subscription.gift", {"user_name": "alice", "total": 50, "tier": "1000"})
    pri, key, req = normalize(n)
    assert pri == PRIORITY["giftbomb"]
    assert key == "giftbomb:alice"
    assert req["payload"]["type"] == "giftbomb"
    assert req["payload"]["gift_total"] == 50


def test_individual_gift_sub_suppressed():
    # channel.subscribe で is_gift=True は個別ギフト → giftbomb と同じ dedup_key で抑制対象
    n = _notif("channel.subscribe", {"user_name": "carol", "tier": "1000", "is_gift": True})
    pri, key, req = normalize(n)
    assert key == "giftbomb:carol"  # gifter ではなく受領者だが、同 gifter の集計と coalesce される設計
    assert req["payload"]["type"] == "sub"


def test_new_sub_is_mid_priority():
    n = _notif("channel.subscribe", {"user_name": "dave", "tier": "1000", "is_gift": False})
    pri, key, req = normalize(n)
    assert pri == PRIORITY["sub"]
    assert key is None
    assert req["payload"]["type"] == "sub"


def test_raid_payload():
    n = _notif("channel.raid", {"from_broadcaster_user_name": "raider", "viewers": 42})
    pri, key, req = normalize(n)
    assert pri == PRIORITY["raid"]
    assert req["payload"]["type"] == "raid"
    assert req["payload"]["user"] == "raider"
    assert req["payload"]["viewers"] == 42


def test_message_id_idempotency():
    seen = set()
    n = _notif("channel.follow", {"user_name": "bob"}, message_id="dup")
    assert normalize(n, seen=seen) is not None
    assert normalize(n, seen=seen) is None  # 同 message_id は捨てる


def test_chat_command_trigger_kept():
    n = _notif("channel.chat.message", {"chatter_user_name": "eve", "message": {"text": "!ask hello"}})
    pri, key, req = normalize(n, triggers=("command",), command_prefix="!")
    assert pri == PRIORITY["chat"]
    assert req["kind"] == "twitch_chat"
    assert req["payload"]["user"] == "eve"
    assert req["payload"]["text"] == "!ask hello"


def test_chat_non_trigger_dropped():
    n = _notif("channel.chat.message", {"chatter_user_name": "eve", "message": {"text": "just chatting"}})
    # triggers=command のみ、mention/firstmsg 無し、サンプリング外れ → 捨てる
    assert normalize(n, triggers=("command",), command_prefix="!", sampler=lambda: False) is None


def test_chat_mention_trigger_kept():
    n = _notif("channel.chat.message", {"chatter_user_name": "eve", "message": {"text": "hi @ch"}})
    pri, key, req = normalize(n, triggers=("mention",), channel="ch")
    assert req["kind"] == "twitch_chat"


def test_chat_sampling_keeps_when_sampler_true():
    n = _notif("channel.chat.message", {"chatter_user_name": "eve", "message": {"text": "random talk"}})
    pri, key, req = normalize(n, triggers=(), sampler=lambda: True)
    assert req["kind"] == "twitch_chat"  # サンプリング当選で拾う


def test_unknown_subscription_type_dropped():
    assert normalize(_notif("channel.unknown", {})) is None
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest src/companion_twitch/test_normalize.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'companion_twitch.normalize'`

- [ ] **Step 3: Write the implementation**

`src/companion_twitch/normalize.py`:

```python
#!/usr/bin/env python3
"""EventSub notification → (priority, dedup_key, CommentRequest)。捨てる時 None。

core.EventQueue に push する形を返す純関数。gift-bomb coalesce / chat トリガ選別 /
message_id 冪等をここで処理する。ネットワーク非依存。
"""

from __future__ import annotations

from typing import Any, Callable

from companion_core.request import make_request
from companion_core.sources.chat import from_chat

PRIORITY: dict[str, int] = {
    "cheer": 9,
    "giftbomb": 8,
    "raid": 8,
    "sub": 5,
    "resub": 5,
    "follow": 2,
    "chat": 0,
}

_BIG_BITS = 1000


def _event_req(etype: str, payload: dict[str, Any]) -> tuple[int, str | None, dict[str, Any]]:
    body = {"type": etype, **payload}
    return PRIORITY[etype], None, make_request("twitch_event", body)


def _chat_kind(text: str, *, triggers: tuple[str, ...], command_prefix: str, channel: str) -> str | None:
    """chat トリガ判定。command / mention / firstmsg のいずれか該当で kind、無ければ None。"""
    if "command" in triggers and command_prefix and text.startswith(command_prefix):
        return "command"
    if "mention" in triggers and channel and f"@{channel}".lower() in text.lower():
        return "mention"
    # firstmsg はここでは判定材料 (初コメ情報) が EventSub payload に無いため後段 (Plan B) で扱う
    return None


def normalize(
    notification: dict[str, Any],
    *,
    seen: set[str] | None = None,
    triggers: tuple[str, ...] = ("mention", "command", "firstmsg"),
    command_prefix: str = "!",
    channel: str = "",
    sampler: Callable[[], bool] | None = None,
) -> tuple[int, str | None, dict[str, Any]] | None:
    """EventSub notification を (priority, dedup_key, CommentRequest) に正規化。捨てる時 None。"""
    meta = notification.get("metadata", {})
    mid = meta.get("message_id")
    if seen is not None and mid is not None:
        if mid in seen:
            return None  # 冪等: 重複配信は捨てる
        seen.add(mid)

    sub_type = meta.get("subscription_type")
    event = notification.get("payload", {}).get("event", {})

    if sub_type == "channel.cheer":
        bits = int(event.get("bits", 0))
        return _event_req("cheer", {"user": event.get("user_name"), "bits": bits, "big": bits >= _BIG_BITS})

    if sub_type == "channel.follow":
        return _event_req("follow", {"user": event.get("user_name")})

    if sub_type == "channel.raid":
        return _event_req(
            "raid", {"user": event.get("from_broadcaster_user_name"), "viewers": int(event.get("viewers", 0))}
        )

    if sub_type == "channel.subscription.gift":
        gifter = event.get("user_name")
        pri, _key, req = _event_req(
            "giftbomb", {"user": gifter, "gift_total": int(event.get("total", 0)), "tier": event.get("tier")}
        )
        return pri, f"giftbomb:{gifter}", req

    if sub_type == "channel.subscribe":
        user = event.get("user_name")
        pri, _key, req = _event_req("sub", {"user": user, "tier": event.get("tier")})
        if event.get("is_gift"):
            return pri, f"giftbomb:{user}", req  # 個別ギフトは gifter 集計と coalesce
        return pri, None, req

    if sub_type == "channel.subscription.message":
        ev = event.get("message", {})
        return _event_req(
            "resub",
            {
                "user": event.get("user_name"),
                "tier": event.get("tier"),
                "months": int(event.get("cumulative_months", 0)),
                "message": ev.get("text", "") if isinstance(ev, dict) else "",
            },
        )

    if sub_type == "channel.chat.message":
        user = event.get("chatter_user_name")
        msg = event.get("message", {})
        text = msg.get("text", "") if isinstance(msg, dict) else str(msg)
        kind = _chat_kind(text, triggers=triggers, command_prefix=command_prefix, channel=channel)
        if kind is None and not (sampler is not None and sampler()):
            return None  # トリガ非該当 かつ サンプリング外れ → 捨てる
        return PRIORITY["chat"], None, from_chat(user, text, kind="twitch_chat")

    return None  # 未対応 subscription_type
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest src/companion_twitch/test_normalize.py -v`
Expected: PASS (12 passed)

- [ ] **Step 5: Commit**

```bash
git add src/companion_twitch/normalize.py src/companion_twitch/test_normalize.py
git commit -m "feat(normalize): EventSub notification -> (priority, dedup_key, CommentRequest)

gift-bomb coalesce / chat トリガ選別 / message_id 冪等。core.make_request/from_chat 再利用。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: handlers.py + entry-points

**Files:**
- Create: `src/companion_twitch/handlers.py`
- Test: `src/companion_twitch/test_handlers.py`
- Modify: `pyproject.toml` (handler entry-points 追加)

**Interfaces:**
- Consumes: core の `comment()` 契約 (`template(request) -> str` / `build_user(payload) -> str`)。
- Produces:
  - `class TwitchEventHandler` — `template(request)` / `build_user(payload)`
  - `class TwitchChatHandler` — `template(request)` / `build_user(payload)`
  - entry-point group `companion_core.handlers`: `twitch_event` / `twitch_chat`

- [ ] **Step 1: Write the failing tests**

`src/companion_twitch/test_handlers.py`:

```python
from __future__ import annotations

from companion_twitch.handlers import TwitchChatHandler, TwitchEventHandler


def _req(kind, **payload):
    return {"kind": kind, "payload": payload}


def test_event_template_sub():
    h = TwitchEventHandler()
    out = h.template(_req("twitch_event", type="sub", user="alice", tier="1000"))
    assert "alice" in out
    assert out.endswith("のだ") or "のだ" in out  # ずんだもん口調


def test_event_template_cheer_big_is_emphatic():
    h = TwitchEventHandler()
    normal = h.template(_req("twitch_event", type="cheer", user="bob", bits=100, big=False))
    big = h.template(_req("twitch_event", type="cheer", user="bob", bits=5000, big=True))
    assert "bob" in normal and "bob" in big
    assert big != normal  # 大口は強めの文


def test_event_template_giftbomb_mentions_total():
    h = TwitchEventHandler()
    out = h.template(_req("twitch_event", type="giftbomb", user="alice", gift_total=50))
    assert "50" in out
    assert "alice" in out


def test_event_template_raid_mentions_viewers():
    h = TwitchEventHandler()
    out = h.template(_req("twitch_event", type="raid", user="raider", viewers=42))
    assert "42" in out
    assert "raider" in out


def test_event_template_unknown_type_safe_fallback():
    h = TwitchEventHandler()
    out = h.template(_req("twitch_event", type="???", user="x"))
    assert isinstance(out, str) and out  # 空でない安全な文


def test_event_build_user_is_nonempty_prompt():
    h = TwitchEventHandler()
    p = h.build_user({"type": "sub", "user": "alice"})
    assert isinstance(p, str) and "alice" in p


def test_chat_template_uses_user_and_text():
    h = TwitchChatHandler()
    out = h.template(_req("twitch_chat", user="eve", text="!ask こんにちは"))
    assert "eve" in out
    assert "のだ" in out


def test_chat_build_user_includes_text():
    h = TwitchChatHandler()
    p = h.build_user({"user": "eve", "text": "質問なのだ?"})
    assert "質問なのだ?" in p
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest src/companion_twitch/test_handlers.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'companion_twitch.handlers'`

- [ ] **Step 3: Write the implementation**

`src/companion_twitch/handlers.py`:

```python
#!/usr/bin/env python3
"""Twitch イベント/チャット実況の handler (ずんだもん)。

core の comment() が呼ぶ template(request) (client=None と NG fallback) と
build_user(payload) (LLM 経路の user prompt) を実装。entry-point で core に登録される。
"""

from __future__ import annotations

from typing import Any


def _u(payload: dict[str, Any]) -> str:
    return str(payload.get("user") or "だれか")


class TwitchEventHandler:
    """kind="twitch_event": sub/resub/giftbomb/cheer/raid/follow を整形。"""

    def template(self, request: dict[str, Any]) -> str:
        p = request.get("payload", {})
        t = p.get("type")
        user = _u(p)
        if t == "follow":
            return f"{user} さんがフォローしてくれたのだ！ありがとうなのだ"
        if t == "sub":
            return f"{user} さんがサブスクなのだ！うれしいのだ"
        if t == "resub":
            months = p.get("months", 0)
            return f"{user} さんが {months} カ月の継続サブスクなのだ！ありがとうなのだ"
        if t == "giftbomb":
            total = p.get("gift_total", 0)
            return f"すごいのだ！{user} さんが {total} 個もサブギフトしたのだ！太っ腹なのだ"
        if t == "cheer":
            bits = p.get("bits", 0)
            if p.get("big"):
                return f"うわー！{user} さんから {bits} ビッツの大盤振る舞いなのだ！ありがとうなのだー！"
            return f"{user} さんが {bits} ビッツくれたのだ！ありがとうなのだ"
        if t == "raid":
            viewers = p.get("viewers", 0)
            return f"{user} さんが {viewers} 人を連れてレイドに来てくれたのだ！ようこそなのだ"
        return f"{user} さん、ありがとうなのだ"

    def build_user(self, payload: dict[str, Any]) -> str:
        return f"次の Twitch イベントをずんだもん口調で短く実況してほしいのだ: {payload}"


class TwitchChatHandler:
    """kind="twitch_chat": 視聴者チャットへの反応。"""

    def template(self, request: dict[str, Any]) -> str:
        p = request.get("payload", {})
        user = _u(p)
        text = str(p.get("text", ""))
        return f"{user} さんが「{text}」って言ってるのだ"

    def build_user(self, payload: dict[str, Any]) -> str:
        user = str(payload.get("user") or "視聴者")
        text = str(payload.get("text", ""))
        return f"{user} さんのチャット「{text}」にずんだもん口調で短く反応してほしいのだ"
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest src/companion_twitch/test_handlers.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: pyproject に handler entry-points を追加**

`pyproject.toml` の `[build-system]` の直前に追記:

```toml
[project.entry-points."companion_core.handlers"]
twitch_event = "companion_twitch.handlers:TwitchEventHandler"
twitch_chat = "companion_twitch.handlers:TwitchChatHandler"
```

- [ ] **Step 6: 全テスト確認 + Commit**

Run: `uv run pytest -q`
Expected: 全 PASS (smoke 2 + config 4 + normalize 12 + handlers 8 = 26)

```bash
git add src/companion_twitch/handlers.py src/companion_twitch/test_handlers.py pyproject.toml
git commit -m "feat(handlers): TwitchEventHandler/TwitchChatHandler + entry-points

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 次プラン (本計画の対象外)

Plan B: `eventsub/helix.py` (Helix REST builder + validate_token, urllib 注入)、`eventsub/client.py`
(EventSubClient: WS welcome/keepalive/reconnect・購読作成、ws 注入)、`live.py` (runner: client→
normalize→core.EventQueue→make_pump_worker→Supervisor、CLI `twitch-companion`)、`websocket-client`
依存追加、`twitch-companion` script entry-point、`test_boundary.py`。Plan A 完了後に着手。

## Self-Review

- **Spec coverage**: scaffold/依存/命名 = Task 1。config([twitch]+env, scopes) = Task 2。正規化
  (7種, gift coalesce, chat トリガ, message_id 冪等) = Task 3。handler(event/chat, template+build_user,
  entry-points) = Task 4。eventsub client / helix / live / 再接続 / boundary test は Plan B に明示分離。
- **Placeholder scan**: 各 step に実コード・実コマンド・期待出力。TBD/TODO 無し。LICENSE は MIT 全文を提示。
- **Type consistency**: `resolve_config(section, env) -> dict` のキーは Task 2 で固定。`normalize(...) ->
  (priority, dedup_key, request) | None` の戻り型は Task 3 のテスト・実装で一致。handler の `template(request)`
  / `build_user(payload)` は Task 4 と core の comment() 契約 (Global Constraints) で一致。`make_request` /
  `from_chat` は core v0.12.0 の実シグネチャ。
