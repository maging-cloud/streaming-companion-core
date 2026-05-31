import unittest
from companion_core.prompt import build_prompt


class FakeHandler:
    persona = "ボクはテスト解説なのだ"
    fewshot = "例) x -> yなのだ"

    def build_user(self, payload):
        return f"round={payload.get('round')} top={payload.get('top')}"


class TestBuildPrompt(unittest.TestCase):
    def test_system_has_persona_and_fewshot(self):
        system, _ = build_prompt({"payload": {"round": 3, "top": "A"}}, FakeHandler())
        self.assertIn("ボクはテスト解説", system)
        self.assertIn("例)", system)

    def test_user_from_handler(self):
        _, user = build_prompt({"payload": {"round": 3, "top": "A"}}, FakeHandler())
        self.assertIn("round=3", user)
        self.assertIn("top=A", user)

    def test_empty_fewshot_no_extra_newline(self):
        class H(FakeHandler):
            fewshot = ""
        system, _ = build_prompt({"payload": {}}, H())
        self.assertNotIn("\n", system)   # fewshot 空なら persona のみ (改行付かない)


if __name__ == "__main__":
    unittest.main()
