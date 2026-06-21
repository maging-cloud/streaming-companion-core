import unittest

from companion_core.prompt import build_prompt


class FakeHandler:
    persona = "ボクはテスト解説なのだ"
    fewshot = "例) x -> yなのだ"

    def build_user(self, payload):
        return f"round={payload.get('round')} top={payload.get('top')}"


class RoleHandler:
    role = "購入候補を解説する"

    def build_user(self, payload):
        return f"r={payload.get('round')}"


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
        self.assertNotIn("\n", system)  # fewshot 空なら persona のみ (改行付かない)


class TestBuildPromptPersona(unittest.TestCase):
    def test_role_handler_uses_injected_persona_voice(self):
        from companion_core.persona import Persona

        p = Persona(name="t", voice="VOICE-X", fewshot="FS-X")
        system, _ = build_prompt({"payload": {"round": 1}}, RoleHandler(), p)
        self.assertIn("VOICE-X", system)
        self.assertIn("購入候補を解説する", system)
        self.assertIn("FS-X", system)

    def test_role_handler_defaults_to_zundamon(self):
        system, _ = build_prompt({"payload": {}}, RoleHandler())
        self.assertIn("ずんだもん", system)

    def test_legacy_persona_handler_still_works(self):
        # .role を持たない旧 handler は .persona をそのまま使う
        system, _ = build_prompt({"payload": {}}, FakeHandler())
        self.assertIn("ボクはテスト解説", system)


if __name__ == "__main__":
    unittest.main()
