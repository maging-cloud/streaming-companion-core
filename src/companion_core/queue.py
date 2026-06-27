#!/usr/bin/env python3
"""push 型 companion 用の汎用イベントキュー (優先度 + bounded + coalesce)。

バーストする入力 (Twitch のレイド / ギフト爆撃 / チャット洪水) を溜め、pump worker が
TTS ペースで 1 件ずつ取り出す。プラットフォーム非依存・純データ構造。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class QueuedItem:
    priority: int
    seq: int
    request: dict[str, Any]  # CommentRequest {kind, payload}
    dedup_key: str | None = None
    count: int = 1  # 同 dedup_key を coalesce した回数


class EventQueue:
    """優先度付き bounded キュー。同 dedup_key は coalesce (先勝ち + count 加算)。"""

    def __init__(self, maxsize: int = 200) -> None:
        self.maxsize = maxsize
        self._items: list[QueuedItem] = []
        self._by_key: dict[str, QueuedItem] = {}
        self._seq = 0

    def __len__(self) -> int:
        return len(self._items)

    def put(self, priority: int, request: dict[str, Any], dedup_key: str | None = None) -> None:
        """投入。dedup_key が既存と一致すれば coalesce (count++、新規追加しない)。
        満杯なら最低優先度・同率最古を 1 件押し出してから追加。"""
        if dedup_key is not None and dedup_key in self._by_key:
            self._by_key[dedup_key].count += 1
            return
        if len(self._items) >= self.maxsize:
            victim = min(self._items, key=lambda it: (it.priority, it.seq))
            self._remove(victim)
        item = QueuedItem(priority=priority, seq=self._seq, request=request, dedup_key=dedup_key)
        self._seq += 1
        self._items.append(item)
        if dedup_key is not None:
            self._by_key[dedup_key] = item

    def get(self) -> QueuedItem | None:
        """最高優先度・同率は FIFO (最古) を 1 件取り出す。空なら None。"""
        if not self._items:
            return None
        item = max(self._items, key=lambda it: (it.priority, -it.seq))
        self._remove(item)
        return item

    def _remove(self, item: QueuedItem) -> None:
        self._items.remove(item)
        if item.dedup_key is not None:
            self._by_key.pop(item.dedup_key, None)
