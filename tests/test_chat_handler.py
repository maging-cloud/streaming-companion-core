import unittest
from companion_core.chat_handler import ChatHandler, ZundamonChatHandler


class TestChatHandlerBase(unittest.TestCase):
    def test_default_persona_empty(self):
        self.assertEqual(ChatHandler().persona, "")

    def test_build_user_includes_user_and_text(self):
        u = ChatHandler().build_user({"user": "alice", "text": "good game?"})
        self.assertIn("alice", u)
        self.assertIn("good game?", u)

    def test_build_user_missing_fields(self):
        u = ChatHandler().build_user({})
        self.assertIsInstance(u, str)
        self.assertTrue(u)

    def test_template_is_generic_string(self):
        t = ChatHandler().template({"payload": {"user": "a", "text": "hi"}})
        self.assertIsInstance(t, str)
        self.assertTrue(t)

    def test_persona_injectable_via_subclass(self):
        class MyChat(ChatHandler):
            persona = "P-CHARACTER"
            fewshot = "F"
        h = MyChat()
        self.assertEqual(h.persona, "P-CHARACTER")
        self.assertEqual(h.fewshot, "F")

    def test_persona_injectable_via_init(self):
        h = ChatHandler(persona="INJECTED", fewshot="FS")
        self.assertEqual(h.persona, "INJECTED")
        self.assertEqual(h.fewshot, "FS")


class TestZundamonChatHandler(unittest.TestCase):
    def test_is_chat_handler(self):
        self.assertIsInstance(ZundamonChatHandler(), ChatHandler)

    def test_persona_zundamon(self):
        self.assertIn("ずんだもん", ZundamonChatHandler.persona)
        self.assertIn("のだ", ZundamonChatHandler.persona)

    def test_template_ends_zundamon(self):
        t = ZundamonChatHandler().template({"payload": {"user": "a", "text": "hi"}})
        self.assertIn("のだ", t)

    def test_persona_is_game_agnostic(self):
        # core の persona に特定ゲーム名が入っていないこと
        blob = ZundamonChatHandler.persona + ZundamonChatHandler.fewshot
        self.assertNotIn("Backpack", blob)
        self.assertNotIn("BPB", blob)


if __name__ == "__main__":
    unittest.main()
