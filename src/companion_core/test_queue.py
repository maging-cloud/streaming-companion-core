from __future__ import annotations

from companion_core.queue import EventQueue


def _req(kind: str, **payload: object) -> dict[str, object]:
    return {"kind": kind, "payload": payload}


def test_get_returns_highest_priority_first() -> None:
    q = EventQueue()
    q.put(0, _req("chat"))
    q.put(5, _req("cheer"))
    q.put(2, _req("sub"))
    item = q.get()
    assert item is not None
    assert item.request["kind"] == "cheer"
    item = q.get()
    assert item is not None
    assert item.request["kind"] == "sub"
    item = q.get()
    assert item is not None
    assert item.request["kind"] == "chat"
    assert q.get() is None


def test_same_priority_is_fifo() -> None:
    q = EventQueue()
    q.put(1, _req("chat", n=1))
    q.put(1, _req("chat", n=2))
    item = q.get()
    assert item is not None
    assert item.request["payload"]["n"] == 1  # 最古が先
    item = q.get()
    assert item is not None
    assert item.request["payload"]["n"] == 2


def test_coalesce_same_dedup_key_increments_count_no_new_item() -> None:
    q = EventQueue()
    q.put(5, _req("giftbomb", total=5), dedup_key="gifter:alice")
    q.put(2, _req("sub"), dedup_key="gifter:alice")  # 同 key → coalesce (追加しない)
    assert len(q) == 1
    item = q.get()
    assert item is not None
    assert item.request["kind"] == "giftbomb"  # 先勝ち
    assert item.count == 2


def test_bounded_evicts_lowest_priority_oldest() -> None:
    q = EventQueue(maxsize=2)
    q.put(0, _req("chat", n=1))  # 最低優先・最古 → 押し出される
    q.put(0, _req("chat", n=2))
    q.put(9, _req("raid"))  # 満杯 → victim を1件押し出して追加
    assert len(q) == 2
    kinds = []
    for _ in range(2):
        item = q.get()
        assert item is not None
        kinds.append(item.request)
    assert {"raid"} <= {r["kind"] for r in kinds}
    assert all(r["payload"].get("n") != 1 for r in kinds)  # n=1 は押し出された


def test_len_and_empty_get() -> None:
    q = EventQueue()
    assert len(q) == 0
    assert q.get() is None


def test_public_exports() -> None:
    import companion_core

    assert hasattr(companion_core, "EventQueue")
    assert hasattr(companion_core, "make_pump_worker")
