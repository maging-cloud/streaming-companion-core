#!/usr/bin/env python3
"""発話タイミング制御 (Orchestrator)。ゲーム非依存。

毎入力で喋ると配信のテンポが死ぬため、発話するかどうかを判定する:
  - 重要イベント (important_kinds) または force → 常に発話 (cooldown 無視)
  - それ以外 → スコア変動が閾値以上 (score_delta) かつ 前回発話から min_interval 経過 で発話

発話した時のみ内部状態 (前回発話時刻・基準スコア) を更新する。黙った呼び出しでは
基準スコアを動かさない (じわじわ変動して発話機会を逃すのを防ぐ)。

時刻は `clock` (引数なしで monotonic 秒を返す callable) で注入でき、テスト可能。
"""

import time
from collections.abc import Callable, Iterable


class SpeechGate:
    """発話判定ゲート。`should_speak(...)` が True を返した時だけ状態を更新する。"""

    def __init__(
        self,
        min_interval: float = 5.0,
        score_delta: float = 0.1,
        important_kinds: Iterable[str] = (),
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.min_interval = min_interval
        self.score_delta = score_delta
        self.important_kinds = set(important_kinds)
        self._clock = clock or time.monotonic
        self._last_spoken: float | None = None  # 最後に発話した時刻 (None = 未発話)
        self._baseline: float | None = None  # 最後に発話したときのスコア基準

    def _speak(self, score: float | None) -> bool:
        self._last_spoken = self._clock()
        if score is not None:
            self._baseline = score
        return True

    def should_speak(self, *, score: float | None = None, kind: str | None = None, force: bool = False) -> bool:
        """発話すべきか。True のとき内部状態を更新する。"""
        if force or kind in self.important_kinds:
            return self._speak(score)

        if score is None:
            return False

        # 初回 (基準なし) は発話
        if self._baseline is None:
            return self._speak(score)

        # 変動が閾値未満なら黙る (基準は維持)
        if abs(score - self._baseline) < self.score_delta:
            return False

        # 変動は十分。cooldown 未経過なら黙る (基準は維持)
        if self._last_spoken is not None and (self._clock() - self._last_spoken) < self.min_interval:
            return False

        return self._speak(score)
