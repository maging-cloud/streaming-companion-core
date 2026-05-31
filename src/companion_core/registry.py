#!/usr/bin/env python3
"""kind → handler 登録 (CLI 便宜)。handler は build_prompt/comment が期待する規約を満たすオブジェクト。"""

_HANDLERS = {}


def register(kind, handler):
    _HANDLERS[kind] = handler


def get_handler(kind):
    h = _HANDLERS.get(kind)
    if h is None:
        raise ValueError(f"未登録の kind: {kind}")
    return h
