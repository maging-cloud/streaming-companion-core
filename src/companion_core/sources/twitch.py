#!/usr/bin/env python3
"""Twitch IRC の transport / parse (ゲーム非依存)。

parse_irc_line: IRC 1 行 → {"type":"privmsg",user,channel,text} / {"type":"ping",token} / None。
TwitchChatSource: 行イテレータ (注入) を消費して privmsg dict を yield、PING には PONG を自動応答。

実接続 (open_twitch_irc) は socket と OAuth トークンが要るため network 依存 (ユニットテスト対象外)。
パース/source 本体は注入で完全にテスト可能。
"""


def parse_irc_line(line):
    """IRC 1 行をパースする。対象外は None。"""
    line = (line or "").rstrip("\r\n")
    if not line:
        return None
    if line.startswith("PING "):
        return {"type": "ping", "token": line[len("PING ") :].lstrip(":")}
    # :nick!user@host PRIVMSG #channel :message
    if line.startswith(":") and " PRIVMSG " in line:
        prefix, rest = line[1:].split(" ", 1)
        user = prefix.split("!", 1)[0]
        # rest = "PRIVMSG #channel :message"
        try:
            _privmsg, after = rest.split(" ", 1)  # after = "#channel :message"
            channel, text = after.split(" :", 1)
        except ValueError:
            return None
        return {"type": "privmsg", "user": user, "channel": channel, "text": text}
    return None


class TwitchChatSource:
    """注入された行イテレータから privmsg を yield する。PING は PONG 自動応答。"""

    def __init__(self, recv_lines, send=None):
        self._recv = recv_lines  # iterable[str]
        self._send = send or (lambda _s: None)  # callable(str): IRC へ送信

    def messages(self):
        """privmsg dict を順に yield する。"""
        for line in self._recv:
            parsed = parse_irc_line(line)
            if parsed is None:
                continue
            if parsed["type"] == "ping":
                self._send(f"PONG :{parsed['token']}")
                continue
            if parsed["type"] == "privmsg":
                yield parsed


def open_twitch_irc(token, nick, channel, host="irc.chat.twitch.tv", port=6667):  # pragma: no cover
    """Twitch IRC に接続し (recv_lines, send) を返す (network 依存・テスト対象外)。

    token は oauth:xxxx 形式。channel は "#name"。返り値の recv_lines を TwitchChatSource に渡す。
    """
    import socket

    sock = socket.create_connection((host, port))
    sock_file = sock.makefile("r", encoding="utf-8", newline="\r\n")

    def send(msg):
        sock.sendall((msg + "\r\n").encode("utf-8"))

    send(f"PASS {token}")
    send(f"NICK {nick}")
    send(f"JOIN {channel}")

    def recv_lines():
        yield from sock_file

    return recv_lines(), send
