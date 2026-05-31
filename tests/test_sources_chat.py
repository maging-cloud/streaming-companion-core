import unittest
from companion_core.sources.chat import (
    make_chat_message, from_chat, ChatRouter, keyword_matcher,
)


class TestChatMessage(unittest.TestCase):
    def test_make_chat_message(self):
        m = make_chat_message("alice", "hello", channel="#bob")
        self.assertEqual(m, {"user": "alice", "text": "hello", "channel": "#bob"})

    def test_make_chat_message_default_channel(self):
        m = make_chat_message("alice", "hi")
        self.assertIsNone(m["channel"])


class TestFromChat(unittest.TestCase):
    def test_default_kind(self):
        req = from_chat("alice", "hello")
        self.assertEqual(req["kind"], "chat")
        self.assertEqual(req["payload"]["user"], "alice")
        self.assertEqual(req["payload"]["text"], "hello")

    def test_explicit_kind(self):
        req = from_chat("alice", "何買う?", kind="chat_game")
        self.assertEqual(req["kind"], "chat_game")


class TestKeywordMatcher(unittest.TestCase):
    def test_matches_substring_case_insensitive(self):
        m = keyword_matcher(["build", "買"])
        self.assertTrue(m({"text": "What BUILD is this?"}))
        self.assertTrue(m({"text": "なに買うの"}))
        self.assertFalse(m({"text": "天気いいね"}))

    def test_empty_text(self):
        self.assertFalse(keyword_matcher(["x"])({"text": ""}))
        self.assertFalse(keyword_matcher(["x"])({}))


class TestChatRouter(unittest.TestCase):
    def test_default_kind_when_no_rule_matches(self):
        r = ChatRouter(default_kind="chat")
        self.assertEqual(r.route({"text": "hi"}), "chat")

    def test_first_matching_rule_wins(self):
        r = ChatRouter(rules=[
            (keyword_matcher(["買", "build"]), "chat_game"),
        ], default_kind="chat")
        self.assertEqual(r.route({"text": "何を買う?"}), "chat_game")
        self.assertEqual(r.route({"text": "おやつ食べた"}), "chat")

    def test_rules_evaluated_in_order(self):
        r = ChatRouter(rules=[
            (lambda m: "urgent" in m["text"], "chat_urgent"),
            (keyword_matcher(["build"]), "chat_game"),
        ], default_kind="chat")
        # 両方該当でも先勝ち
        self.assertEqual(r.route({"text": "urgent build question"}), "chat_urgent")


if __name__ == "__main__":
    unittest.main()
