import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sink import text_sink, get_sink, fan_out


class TestSink(unittest.TestCase):
    def test_text_sink_returns_text(self):
        self.assertEqual(text_sink("やあなのだ"), "やあなのだ")

    def test_get_sink_text(self):
        self.assertIs(get_sink("text"), text_sink)

    def test_get_sink_unknown_raises(self):
        with self.assertRaises(ValueError):
            get_sink("voicevox")          # 未実装

    def test_fan_out_calls_all(self):
        calls = []
        s1 = lambda t: calls.append(("a", t))
        s2 = lambda t: calls.append(("b", t))
        fan_out("X", [s1, s2])
        self.assertEqual(calls, [("a", "X"), ("b", "X")])


if __name__ == "__main__":
    unittest.main()
