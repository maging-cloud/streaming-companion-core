import unittest
from companion_core.persona import Persona, ZUNDAMON, persona_from_config


class TestPersona(unittest.TestCase):
    def test_system_combines_voice_and_role(self):
        p = Persona(name="x", voice="V", fewshot="F")
        self.assertEqual(p.system("R"), "V R")

    def test_system_strips_when_no_role(self):
        p = Persona(name="x", voice="V")
        self.assertEqual(p.system(""), "V")

    def test_zundamon_voice_has_speech_rules(self):
        self.assertIn("のだ", ZUNDAMON.voice)
        self.assertIn("ボク", ZUNDAMON.voice)

    def test_zundamon_is_game_agnostic(self):
        blob = ZUNDAMON.voice + ZUNDAMON.fewshot
        self.assertNotIn("Backpack", blob)
        self.assertNotIn("BPB", blob)

    def test_from_config_default_is_zundamon(self):
        self.assertEqual(persona_from_config({}), ZUNDAMON)

    def test_from_config_custom(self):
        cfg = {"persona": {"name": "metan", "voice": "わたくしは四国めたん", "fewshot": "ex"}}
        p = persona_from_config(cfg)
        self.assertEqual(p.name, "metan")
        self.assertEqual(p.voice, "わたくしは四国めたん")
        self.assertEqual(p.fewshot, "ex")

    def test_from_config_custom_defaults(self):
        p = persona_from_config({"persona": {"voice": "X"}})
        self.assertEqual(p.name, "custom")
        self.assertEqual(p.fewshot, "")


if __name__ == "__main__":
    unittest.main()
