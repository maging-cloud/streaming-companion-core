#!/usr/bin/env python3
"""CommentRequest + handler → (system, user) プロンプト骨格。ゲーム/ペルソナ非依存。

handler 規約 (duck typing):
  handler.role   : str  (推奨) — role 文字列。Persona.system(role) で system を構築。
                   .role がある場合、persona 引数 (省略時 ZUNDAMON) の voice/fewshot を使う。
  handler.persona: str  (後方互換) — .role を持たない旧 handler は .persona をそのまま使う。
  handler.fewshot: str (空可)   — 後方互換 (.role なし handler 用)。
  handler.build_user(payload) -> str
"""


def build_prompt(request, handler, persona=None):
    """CommentRequest + handler + persona → (system, user)。

    handler が .role を持てば persona.system(role) + persona.fewshot を使う。
    .role を持たない旧 handler は .persona / .fewshot をそのまま使う (後方互換)。
    """
    from .persona import ZUNDAMON

    persona = persona or ZUNDAMON
    role = getattr(handler, "role", None)
    if role is None:
        system = getattr(handler, "persona", "")
        fewshot = getattr(handler, "fewshot", "")
    else:
        system = persona.system(role)
        fewshot = persona.fewshot
    system = system + ("\n" + fewshot if fewshot else "")
    user = handler.build_user(request.get("payload", {}))
    return system, user
