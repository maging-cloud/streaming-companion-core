#!/usr/bin/env python3
"""CommentRequest{kind, payload} の規約。各入力源 (handler 提供側) が生成する。

core は kind/payload の内部構造を仮定せず handler に委譲する。
from_recommendation のような入力源固有の生成は利用側 (例: ゲーム固有の commenter) が持つ。
"""


def make_request(kind, payload):
    """CommentRequest を組み立てる汎用コンストラクタ。"""
    return {"kind": kind, "payload": payload}
