#!/usr/bin/env python3
"""ChatHandler 基底 (role 規約式) と既定実装。

- ChatHandler: 視聴者コメント返答の汎用 handler 基底。handler 規約
  (role/build_user/template) を満たす。role はここに持ち、voice/口調は
  companion_core.persona.Persona が担う (comment/build_prompt 経由で注入)。
- ZundamonChatHandler: ずんだもん固定 template のチャット handler。
  role のみ持ち、persona (声色・語尾) は外部 Persona から注入される。
  ゲーム非依存。アプリは entry-point でそのまま登録するか、ドメイン文脈だけ足して継承する。

ずんだもん固定 template はゲーム解析知識を含まない汎用フォールバックなので core に同梱する
(batteries included)。特定ゲームへの言及・戦略知識はアプリ側が持つ。
"""

from typing import Any


class ChatHandler:
    """視聴者コメントに返答する汎用 handler。voice は persona、role はここ。"""

    role = "視聴者のコメントに短く親しみを込めて返す。"

    def __init__(self, role: str | None = None) -> None:
        if role is not None:
            self.role = role

    def build_user(self, payload: dict[str, Any]) -> str:
        user = payload.get("user") or "視聴者"
        text = payload.get("text") or ""
        return f"{user} さんのコメント: {text}\nこれに短く返答してほしい"

    def template(self, request: dict[str, Any]) -> str:
        return "コメントありがとう"


class ZundamonChatHandler(ChatHandler):
    """既定 persona「ずんだもん」前提の chat handler (role + ずんだもん固定 template)。"""

    role = "視聴者のコメントにゆるく短く20〜50字・1文で親しみを込めて返す。"

    def template(self, request: dict[str, Any]) -> str:
        user = request.get("payload", {}).get("user") or "みんな"
        return f"{user}、コメントありがとうなのだ"
