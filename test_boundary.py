import os, unittest

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
# core が import してはいけない BPB 固有モジュール/シンボル
FORBIDDEN = ("commenter", "scorer", "evaluator", "tools",
             "llm_match", "shop_handler", "recommendation")


class TestCoreBoundary(unittest.TestCase):
    def test_no_bpb_imports(self):
        offenders = []
        for fn in sorted(os.listdir(CORE_DIR)):
            if not fn.endswith(".py") or fn.startswith("test_"):
                continue
            with open(os.path.join(CORE_DIR, fn), encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    s = line.strip()
                    if not (s.startswith("import ") or s.startswith("from ")):
                        continue
                    for bad in FORBIDDEN:
                        if bad in s:
                            offenders.append(f"{fn}:{i}: {s}")
        self.assertEqual(offenders, [], "core に BPB 依存 import: " + "; ".join(offenders))


if __name__ == "__main__":
    unittest.main()
