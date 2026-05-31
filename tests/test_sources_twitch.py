import unittest
from companion_core.sources.twitch import parse_irc_line, TwitchChatSource


class TestParseIrcLine(unittest.TestCase):
    def test_privmsg(self):
        line = ":alice!alice@alice.tmi.twitch.tv PRIVMSG #bob :hello world"
        m = parse_irc_line(line)
        self.assertEqual(m["type"], "privmsg")
        self.assertEqual(m["user"], "alice")
        self.assertEqual(m["channel"], "#bob")
        self.assertEqual(m["text"], "hello world")

    def test_privmsg_text_with_colon(self):
        line = ":a!a@a.tmi.twitch.tv PRIVMSG #c :time is 10:30 now"
        m = parse_irc_line(line)
        self.assertEqual(m["text"], "time is 10:30 now")

    def test_ping(self):
        m = parse_irc_line("PING :tmi.twitch.tv")
        self.assertEqual(m["type"], "ping")
        self.assertEqual(m["token"], "tmi.twitch.tv")

    def test_other_line_returns_none(self):
        self.assertIsNone(parse_irc_line(":tmi.twitch.tv 001 nick :Welcome"))
        self.assertIsNone(parse_irc_line(""))

    def test_trailing_crlf_stripped(self):
        m = parse_irc_line(":a!a@a PRIVMSG #c :hi\r\n")
        self.assertEqual(m["text"], "hi")


class TestTwitchChatSource(unittest.TestCase):
    def test_yields_privmsg_only(self):
        lines = [
            ":tmi.twitch.tv 001 nick :Welcome",
            ":alice!a@a PRIVMSG #bob :hello",
            ":carol!c@c PRIVMSG #bob :hi there",
        ]
        src = TwitchChatSource(lines)
        msgs = list(src.messages())
        self.assertEqual([m["user"] for m in msgs], ["alice", "carol"])
        self.assertEqual([m["text"] for m in msgs], ["hello", "hi there"])

    def test_ping_triggers_pong(self):
        sent = []
        lines = ["PING :tmi.twitch.tv", ":a!a@a PRIVMSG #c :yo"]
        src = TwitchChatSource(lines, send=sent.append)
        msgs = list(src.messages())
        self.assertEqual(sent, ["PONG :tmi.twitch.tv"])
        self.assertEqual([m["text"] for m in msgs], ["yo"])

    def test_no_send_callable_is_safe(self):
        # send 未指定でも PING で落ちない
        list(TwitchChatSource(["PING :x"]).messages())


if __name__ == "__main__":
    unittest.main()
