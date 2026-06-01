import unittest
from companion_core.chat_handler import ChatHandler, ZundamonChatHandler


class TestChatHandlerBase(unittest.TestCase):
    def test_default_role_nonempty(self):
        self.assertTrue(ChatHandler().role)

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

    def test_role_injectable_via_subclass(self):
        class MyChat(ChatHandler):
            role = "ROLE-X"
        self.assertEqual(MyChat().role, "ROLE-X")

    def test_role_injectable_via_init(self):
        self.assertEqual(ChatHandler(role="INJECTED").role, "INJECTED")


class TestZundamonChatHandler(unittest.TestCase):
    def test_is_chat_handler(self):
        self.assertIsInstance(ZundamonChatHandler(), ChatHandler)

    def test_role_nonempty_and_game_agnostic(self):
        role = ZundamonChatHandler.role
        self.assertTrue(role)
        self.assertNotIn("Backpack", role)

    def test_template_ends_zundamon(self):
        t = ZundamonChatHandler().template({"payload": {"user": "a", "text": "hi"}})
        self.assertIn("のだ", t)


if __name__ == "__main__":
    unittest.main()
