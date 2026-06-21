import unittest

from companion_core.phrasebook import pick, pick_index


class TestPickIndex(unittest.TestCase):
    def test_in_range(self):
        for seed in ["a", "b", "Leather Bag", "", "ずんだ", "12345"]:
            self.assertTrue(0 <= pick_index(seed, 5) < 5)

    def test_deterministic(self):
        self.assertEqual(pick_index("Leather Bag", 4), pick_index("Leather Bag", 4))

    def test_different_seeds_can_differ(self):
        idxs = {pick_index(s, 8) for s in ["a", "b", "c", "d", "e", "f", "g", "h"]}
        self.assertGreater(len(idxs), 1)  # 全部同じにはならない

    def test_n_one_always_zero(self):
        self.assertEqual(pick_index("anything", 1), 0)

    def test_n_zero_raises(self):
        with self.assertRaises(ValueError):
            pick_index("x", 0)

    def test_seed_normalized_to_str(self):
        # 非文字列 seed も決定的に扱える
        self.assertEqual(pick_index(42, 3), pick_index("42", 3))


class TestPick(unittest.TestCase):
    def test_returns_member(self):
        opts = ["x", "y", "z"]
        self.assertIn(pick("seed", opts), opts)

    def test_deterministic(self):
        opts = ["a", "b", "c", "d"]
        self.assertEqual(pick("Battery", opts), pick("Battery", opts))

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            pick("s", [])

    def test_single_option(self):
        self.assertEqual(pick("anything", ["only"]), "only")

    def test_format_kwargs(self):
        # {name} 等のプレースホルダを埋められる
        opts = ["{name} を取るのだ", "{name} がいいのだ"]
        out = pick("k", opts, name="Battery")
        self.assertIn("Battery", out)
        self.assertTrue(out.endswith("のだ"))


if __name__ == "__main__":
    unittest.main()
