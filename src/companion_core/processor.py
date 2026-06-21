#!/usr/bin/env python3
"""Processor チェーン: process(text, request) -> text。sanitize と NGフィルタ。

NG は利用側 (comment.py) が必ずチェーン末尾に付与する安全ゲート (ここでは生成のみ提供)。
"""

import re
from collections.abc import Callable, Iterable
from typing import Any

SAFE_GENERIC = "いい流れなのだ"

_STRIP_CHARS = set("「」『』（）()【】［］[]\"'`" + "“”‘’")
_EMOJI = re.compile("[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f000-\U0001f0ff✀-➿←-⇿]+")


def sanitize(text: str, request: Any = None) -> str:
    """媒体非依存の安全整形: 引用符/括弧/絵文字/改行除去, 空白圧縮, 80字切り詰め。"""
    t = _EMOJI.sub("", text or "")
    t = "".join(c for c in t if c not in _STRIP_CHARS)
    t = re.sub(r"[\r\n]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:80]


def make_ng_filter(ngwords: Iterable[str], fallback: Callable[[Any], str]) -> Callable[[str, Any], str]:
    """NGフィルタ Processor を返す。NG含 → fallback(request) を sanitize、なお NG なら SAFE_GENERIC。"""
    from .ngword import contains_ng

    def process(text: str, request: Any) -> str:
        if not contains_ng(text, ngwords):
            return text
        alt = sanitize(fallback(request), request)
        return alt if not contains_ng(alt, ngwords) else SAFE_GENERIC

    return process


def run_pipeline(text: str, request: Any, processors: Iterable[Callable[[str, Any], str]]) -> str:
    """processors を順に適用。"""
    for proc in processors:
        text = proc(text, request)
    return text
