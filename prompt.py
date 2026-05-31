#!/usr/bin/env python3
"""CommentRequest + handler → (system, user) プロンプト骨格。ゲーム/ペルソナ非依存。

handler 規約 (duck typing):
  handler.persona : str
  handler.fewshot : str (空可)
  handler.build_user(payload) -> str
"""


def build_prompt(request, handler):
    """CommentRequest + handler → (system, user)。BPB 知識ゼロ。"""
    system = handler.persona + ("\n" + handler.fewshot if handler.fewshot else "")
    user = handler.build_user(request.get("payload", {}))
    return system, user
