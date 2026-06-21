#!/usr/bin/env python3
"""決定的フレーズ選択 (ゲーム非依存)。

実況テンプレを単調にしないため、候補文から **入力 seed に基づき決定的に 1 つ選ぶ**。
ランダムではなく seed のハッシュで選ぶので、同一局面 → 同一文 / 異なる局面 → 異なる文 になる
(「ちゃんと見てる感」が出る + テスト/resume が安定する)。

ハンドラは局面特徴 (アイテム名・スコア帯・連勝数など) を seed にし、トーン別の候補集合から選ぶ。
"""

import hashlib
from collections.abc import Sequence
from typing import Any


def pick_index(seed: Any, n: int) -> int:
    """seed (任意の値) に対し決定的に [0, n) の index を返す。n<=0 は ValueError。"""
    if n <= 0:
        raise ValueError(f"n は 1 以上: {n}")
    if n == 1:
        return 0
    h = hashlib.sha1(str(seed).encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big") % n


def pick(seed: Any, options: Sequence[str], **fmt: Any) -> str:
    """options から seed で決定的に 1 つ選ぶ。fmt があれば str.format で埋める。空は ValueError。"""
    if not options:
        raise ValueError("options が空")
    chosen = options[pick_index(seed, len(options))]
    return chosen.format(**fmt) if fmt else chosen
