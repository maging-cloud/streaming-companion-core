import unittest
from companion_core.console.state import ConsoleState


class TestConsoleState(unittest.TestCase):
    def test_snapshot_defaults(self):
        s = ConsoleState()
        snap = s.snapshot()
        self.assertFalse(snap["running"])
        self.assertFalse(snap["muted"])
        self.assertIsNone(snap["current"])
        self.assertEqual(snap["history"], [])

    def test_push_comment_sets_current_and_history(self):
        s = ConsoleState()
        s.push_comment("hello", ts=1.0)
        snap = s.snapshot()
        self.assertEqual(snap["current"]["text"], "hello")
        self.assertEqual(snap["current"]["ts"], 1.0)
        self.assertEqual(len(snap["history"]), 1)

    def test_history_capped(self):
        s = ConsoleState(history_limit=2)
        for i in range(5):
            s.push_comment(f"c{i}", ts=float(i))
        hist = s.snapshot()["history"]
        self.assertEqual([h["text"] for h in hist], ["c4", "c3"])  # 新しい順

    def test_setters(self):
        s = ConsoleState()
        s.set_running(True)
        s.set_muted(True)
        s.set_workers([{"name": "a", "alive": True}])
        snap = s.snapshot()
        self.assertTrue(snap["running"])
        self.assertTrue(snap["muted"])
        self.assertEqual(snap["workers"], [{"name": "a", "alive": True}])

    def test_subscribe_receives_snapshot_on_change(self):
        s = ConsoleState()
        q = s.subscribe()
        s.push_comment("x", ts=2.0)
        got = q.get_nowait()
        self.assertEqual(got["current"]["text"], "x")
        s.unsubscribe(q)

    def test_unsubscribe_stops_delivery(self):
        s = ConsoleState()
        q = s.subscribe()
        s.unsubscribe(q)
        s.push_comment("y", ts=1.0)
        self.assertTrue(q.empty())


if __name__ == "__main__":
    unittest.main()
