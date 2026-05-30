#!/usr/bin/env python3
"""出力 Sink プラグイン。Sink = emit(text)。複数 Sink に fan-out 可能。

本 module はテキスト Sink (既定) のみ。VOICEVOX/OBS/Twitch 等は同 interface の後段プラグイン。
"""


def text_sink(text):
    """既定 Sink: print して text を返す。"""
    print(text)
    return text


def get_sink(name):
    """名前 → Sink。今回 "text" のみ。未知は ValueError。"""
    if name == "text":
        return text_sink
    raise ValueError(f"未知の sink: {name}")


def fan_out(text, sinks):
    """各 sink に text を emit。返り値 = 各 sink の戻り値リスト。"""
    return [s(text) for s in sinks]
