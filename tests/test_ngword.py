import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ngword import load_ngwords, contains_ng


class TestContainsNg(unittest.TestCase):
    def test_substring_case_insensitive(self):
        ng = ["死ね", "fuck"]
        self.assertTrue(contains_ng("お前死ねなのだ", ng))
        self.assertTrue(contains_ng("This is FUCK ok", ng))   # 大小無視

    def test_clean(self):
        self.assertFalse(contains_ng("いい流れなのだ", ["死ね", "fuck"]))

    def test_empty(self):
        self.assertFalse(contains_ng("any", []))
        self.assertFalse(contains_ng("", ["x"]))


class TestLoadNgwords(unittest.TestCase):
    def test_merge_dedup_skip_comments(self):
        d = tempfile.mkdtemp()
        a = os.path.join(d, "a.txt"); b = os.path.join(d, "b.txt")
        with open(a, "w", encoding="utf-8") as fh:
            fh.write("# comment\n死ね\nfuck\n\n")
        with open(b, "w", encoding="utf-8") as fh:
            fh.write("FUCK\n殺す\n")   # FUCK は重複(小文字化)
        words = load_ngwords([a, b, "/no/such/file"])
        self.assertEqual(words, ["死ね", "fuck", "殺す"])      # 順序保持・重複除去・小文字

    def test_missing_files_ok(self):
        self.assertEqual(load_ngwords(["/no/file", None]), [])


if __name__ == "__main__":
    unittest.main()
