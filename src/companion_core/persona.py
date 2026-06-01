#!/usr/bin/env python3
"""Persona: LLM system プロンプトの口調 (voice) + 汎用例文 (fewshot)。差し替え可能。

handler が供給する role (中立なタスク説明) と合成して system プロンプトを作る。
ゲーム非依存。ずんだもん voice を既定として同梱する (batteries included)。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    name: str           # config 選択用の識別子
    voice: str          # 口調ルール + キャラ枠組み (system 前半)
    fewshot: str = ""   # 汎用例文 (口調を示す, タスク非依存)

    def system(self, role: str) -> str:
        """voice + role を 1 つの system プロンプトに結合する。

        fewshot は含めない。build_prompt が system 末尾に別途追記する契約
        (既存の handler.persona + handler.fewshot と同じ構成)。
        """
        return f"{self.voice} {role}".strip()


ZUNDAMON = Persona(
    name="zundamon",
    voice=("あなたは配信のマスコット「ずんだもん」なのだ。"
           "語尾は必ず「〜のだ」「〜なのだ」、一人称は「ボク」。"
           "引用符・括弧・絵文字・改行は使わない。"),
    fewshot=("例) こんにちは -> こんにちはなのだ。来てくれて嬉しいのだ\n"
             "例) 今日は暑いね -> ボクも溶けそうなのだ。水分とるのだ"),
)


def persona_from_config(cfg: dict) -> Persona:
    """config dict の [persona] セクションから生成。未設定なら ZUNDAMON。"""
    p = cfg.get("persona")
    if not p:
        return ZUNDAMON
    return Persona(name=p.get("name", "custom"),
                   voice=p["voice"], fewshot=p.get("fewshot", ""))
