#!/usr/bin/env python3
"""ChatHandler 基底 (persona 注入式) と既定 persona 実装。

- ChatHandler: 視聴者コメント返答の汎用 handler 基底。handler 規約
  (persona/fewshot/build_user/template) を満たす。persona は空既定で、
  サブクラス or コンストラクタ引数で注入できる。
- ZundamonChatHandler: 既定 persona「ずんだもん」(VOICEVOX の汎用キャラ) の実装。
  ゲーム非依存。アプリは entry-point でそのまま登録するか、ドメイン文脈だけ足して継承する。

ずんだもん persona はゲーム解析知識を含まない汎用キャラなので core に同梱する
(batteries included)。特定ゲームへの言及・戦略知識はアプリ側が持つ。
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


class ZundamonChatHandler(ChatHandler):
    """既定 persona「ずんだもん」の chat handler (ゲーム非依存・雑談向け)。"""

    persona = (
        "あなたは配信のマスコット「ずんだもん」なのだ。"
        "語尾は必ず「〜のだ」「〜なのだ」、一人称は「ボク」。"
        "視聴者のコメントにゆるく短く (20〜50字・1文) 親しみを込めて返す。"
        "引用符・括弧・絵文字・改行は使わない。"
    )
    fewshot = (
        "例) コメント=今日暑いね -> ボクも溶けそうなのだ。水分とるのだ\n"
        "例) コメント=こんばんは -> こんばんはなのだ。来てくれて嬉しいのだ"
    )

    def template(self, request):
        user = request.get("payload", {}).get("user") or "みんな"
        return f"{user}、コメントありがとうなのだ"
