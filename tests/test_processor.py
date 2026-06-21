import unittest

from companion_core.processor import SAFE_GENERIC, make_ng_filter, run_pipeline, sanitize


class TestSanitize(unittest.TestCase):
    def test_removes_quotes_parens_newline(self):
        # 括弧除去で あ・い は隣接、改行は空白化 → "あい う"
        self.assertEqual(sanitize("「あ」（い）\nう"), "あい う")

    def test_removes_emoji_and_collapses_space(self):
        self.assertEqual(sanitize("やった😀  のだ"), "やった のだ")

    def test_length_cap_80(self):
        self.assertEqual(len(sanitize("あ" * 200)), 80)


class TestNgFilter(unittest.TestCase):
    def test_clean_passthrough(self):
        f = make_ng_filter(["死ね"], lambda req: "代替なのだ")
        self.assertEqual(f("いい流れなのだ", {}), "いい流れなのだ")

    def test_ng_replaced_with_fallback(self):
        f = make_ng_filter(["死ね"], lambda req: "安全なのだ")
        self.assertEqual(f("死ねなのだ", {}), "安全なのだ")  # NG → fallback

    def test_fallback_also_ng_uses_safe_generic(self):
        f = make_ng_filter(["あ"], lambda req: "あ語なのだ")  # fallback も NG 含む
        self.assertEqual(f("あ", {}), SAFE_GENERIC)


class TestRunPipeline(unittest.TestCase):
    def test_applies_in_order(self):
        def p1(t, r):
            return t + "1"

        def p2(t, r):
            return t + "2"

        self.assertEqual(run_pipeline("x", {}, [p1, p2]), "x12")


if __name__ == "__main__":
    unittest.main()
