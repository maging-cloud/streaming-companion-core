#!/usr/bin/env python3
"""チャット入力の規約・ルーティング (ゲーム非依存)。

- make_chat_message(user, text, channel) → 正規化 dict。
- from_chat(user, text, kind) → CommentRequest{kind, payload:{user,text}}。
- keyword_matcher(words) → message dict を部分一致 (大小無視) で判定する matcher。
- ChatRouter(rules, default_kind) → message を kind に振り分ける。
  rules = [(matcher, kind), ...] を順に評価し最初に一致した kind、無ければ default_kind。

「何がゲーム関連か」等の語彙はゲーム固有なので、利用側が keyword_matcher 等で ChatRouter に注入する。
"""


def make_chat_message(user, text, channel=None):
    """チャットメッセージを正規化 dict にする。"""
    return {"user": user, "text": text, "channel": channel}


def from_chat(user, text, kind="chat"):
    """チャット → CommentRequest{kind, payload:{user,text}}。kind は ChatRouter が決める。"""
    return {"kind": kind, "payload": {"user": user, "text": text}}


def keyword_matcher(words):
    """message['text'] が words のいずれかを部分一致 (大小無視) で含むか判定する matcher を返す。"""
    lowered = [w.lower() for w in words]

    def matcher(message):
        t = (message.get("text") or "").lower()
        return any(w in t for w in lowered)

    return matcher


class ChatRouter:
    """チャットメッセージを kind に振り分ける。"""

    def __init__(self, rules=None, default_kind="chat"):
        self.rules = list(rules or [])
        self.default_kind = default_kind

    def route(self, message):
        """message dict → kind。rules を順に評価し最初に一致、無ければ default_kind。"""
        for matcher, kind in self.rules:
            if matcher(message):
                return kind
        return self.default_kind
