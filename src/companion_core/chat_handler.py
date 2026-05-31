#!/usr/bin/env python3
"""汎用 ChatHandler 基底 (persona 注入式・ゲーム/ペルソナ非依存)。

handler 規約 (persona/fewshot/build_user/template) を満たす。persona は空既定で、
サブクラス or コンストラクタ引数で注入する (core はキャラを持たない)。
ゲーム/キャラ固有の chat handler は本基底を継承し persona と template を与える。
"""


class ChatHandler:
    """視聴者コメントに返答する汎用 handler。persona は注入される。"""

    persona = ""
    fewshot = ""

    def __init__(self, persona=None, fewshot=None):
        if persona is not None:
            self.persona = persona
        if fewshot is not None:
            self.fewshot = fewshot

    def build_user(self, payload):
        user = payload.get("user") or "視聴者"
        text = payload.get("text") or ""
        return f"{user} さんのコメント: {text}\nこれに短く返答してほしい"

    def template(self, request):
        return "コメントありがとう"
