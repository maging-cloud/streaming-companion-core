#!/usr/bin/env python3
"""出力 Sink プラグイン。Sink = emit(text)。複数 Sink に fan-out 可能。

本 module はテキスト Sink (既定) のみ。VOICEVOX/OBS/Twitch 等は同 interface の後段プラグイン。
"""

from collections.abc import Callable, Iterable
from typing import Any


def text_sink(text: str) -> str:
    """既定 Sink: print して text を返す。"""
    print(text)
    return text


def get_sink(name: str) -> Callable[[str], Any]:
    """名前 → Sink。今回 "text" のみ。未知は ValueError。"""
    if name == "text":
        return text_sink
    raise ValueError(f"未知の sink: {name}")


def fan_out(text: str, sinks: Iterable[Callable[[str], Any]]) -> list[Any]:
    """各 sink に text を emit。返り値 = 各 sink の戻り値リスト。"""
    return [s(text) for s in sinks]
