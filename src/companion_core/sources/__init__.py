"""companion_core.sources: 入力 source (ゲーム非依存)。sink と対称。

- chat: チャットメッセージ規約 + from_chat (CommentRequest 化) + ChatRouter (kind 振り分け) + keyword_matcher。
- twitch: Twitch IRC の transport/parse (PRIVMSG/PING)。実接続は open_twitch_irc (要 network)。

source は「外部入力 → CommentRequest」を担い、handler/comment/sink へ繋ぐ。
ゲーム固有の判定 (何が『ゲーム関連』か) は ChatRouter のルールとして利用側が注入する。
"""
