import os
import tempfile
import unittest
from companion_core.sinks.file import file_sink


class TestFileSink(unittest.TestCase):
    def test_writes_text_and_returns_it(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "overlay.txt")
            out = file_sink(p)("こんにちはなのだ")
            self.assertEqual(out, "こんにちはなのだ")
            with open(p, encoding="utf-8") as f:
                self.assertEqual(f.read(), "こんにちはなのだ")

    def test_overwrites_on_each_call(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "overlay.txt")
            sink = file_sink(p)
            sink("一回目")
            sink("二回目")
            with open(p, encoding="utf-8") as f:
                self.assertEqual(f.read(), "二回目")

    def test_append_mode(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "log.txt")
            sink = file_sink(p, append=True)
            sink("a")
            sink("b")
            with open(p, encoding="utf-8") as f:
                self.assertEqual(f.read(), "a\nb\n")

    def test_creates_parent_dir(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "nested", "deep", "overlay.txt")
            file_sink(p)("x")
            self.assertTrue(os.path.isfile(p))


if __name__ == "__main__":
    unittest.main()
