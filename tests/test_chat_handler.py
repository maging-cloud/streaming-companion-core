import unittest
from companion_core.chat_handler import ChatHandler


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


if __name__ == "__main__":
    unittest.main()
