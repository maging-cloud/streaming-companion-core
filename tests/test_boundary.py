import os
import unittest

PKG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "src", "companion_core")
# companion_core が import してはいけない外部 (BPB 固有) シンボル
FORBIDDEN = ("commenter", "scorer", "evaluator", "tools",
             "llm_match", "shop_handler", "recommendation",
             "companion_settings")


class TestCoreBoundary(unittest.TestCase):
    def test_no_bpb_imports(self):
        offenders = []
        for fn in sorted(os.listdir(PKG_DIR)):
            if not fn.endswith(".py"):
                continue
            with open(os.path.join(PKG_DIR, fn), encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    s = line.strip()
                    if not (s.startswith("import ") or s.startswith("from ")):
                        continue
                    for bad in FORBIDDEN:
                        if bad in s:
                            offenders.append(f"{fn}:{i}: {s}")
        self.assertEqual(offenders, [], "companion_core に BPB 依存 import: " + "; ".join(offenders))


if __name__ == "__main__":
    unittest.main()
