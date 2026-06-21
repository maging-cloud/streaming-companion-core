#!/usr/bin/env python3
"""kind → handler レジストリ + entry-point plugin discovery。

handler は build_prompt/comment が期待する規約 (role/build_user/template) を満たすオブジェクト。
persona/fewshot は旧規約として legacy fallback で引き続きサポートされる。
外部パッケージは entry-point group "companion_core.handlers" に handler クラスを登録でき、
get_handler 初回 miss 時に遅延 discover される。companion_core は plugin を import しない (boundary 維持)。
"""

import importlib.metadata
from typing import Any

ENTRY_POINT_GROUP = "companion_core.handlers"

_HANDLERS: dict[str, object] = {}
_discovered = False


def register(kind: str, handler: object) -> None:
    """programmatic 登録 (テスト/明示注入)。discovery より優先される。"""
    _HANDLERS[kind] = handler


def _discover() -> None:
    global _discovered
    if _discovered:
        return
    _discovered = True
    for ep in importlib.metadata.entry_points(group=ENTRY_POINT_GROUP):
        try:
            _HANDLERS.setdefault(ep.name, ep.load()())  # ep 値 "pkg.mod:Handler" → instance 化
        except Exception:
            pass  # 壊れた plugin は無視 (host は落ちない)


def get_handler(kind: str) -> Any:
    if kind not in _HANDLERS:
        _discover()
    h = _HANDLERS.get(kind)
    if h is None:
        raise ValueError(f"未登録の kind: {kind}")
    return h
