# streaming-companion-core (`companion_core`)

配信実況コンパニオンの汎用基盤 (ゲーム非依存)。構造化入力 (推薦/イベント等) → 安全な実況文を生成する。
ゲーム固有知識は持たず、**handler 注入 / entry-point plugin** で各ゲーム・ペルソナを差し込む。

## インストール
```
uv pip install -e .              # 開発
# または git 依存として:
# streaming-companion-core = { git = "https://github.com/maging-cloud/streaming-companion-core.git", tag = "v0.1.0" }
```

## モジュール (`companion_core`)
- request.py: CommentRequest{kind,payload} 規約 + make_request。
- registry.py: kind → handler 登録 + entry-point discovery (group `companion_core.handlers`)。
- prompt.py: build_prompt(request, handler) — handler.persona/fewshot/build_user から (system,user)。
- processor.py: sanitize + make_ng_filter + run_pipeline。
- ngword.py: NGワード管理 (load_ngwords/contains_ng/default_paths)、`--list`。seed は同梱 ngwords.txt。
- sink.py: 出力 Sink (text 既定) + fan_out。
- sinks/file.py: file_sink(path) — 実況文を file へ書く Sink (OBS テキストソース用)。
- sinks/voicevox.py: VoicevoxSink — VOICEVOX HTTP で text→音声 (WAV)。HTTP は stdlib、再生は player 注入で依存ゼロ。
- comment.py: comment(request, handler, client, processors, ngwords) — NG を末尾常時付与する安全ゲート。
- orchestrator.py: SpeechGate — 発話タイミング制御 (スコア変動 + クールダウン + 重要イベント)。
- chat_handler.py: ChatHandler — 視聴者コメント返答の汎用 handler 基底 (persona 注入式)。
- sources/chat.py: from_chat (chat→CommentRequest) + ChatRouter (kind 振り分け) + keyword_matcher。
- sources/twitch.py: Twitch IRC parse + TwitchChatSource (PING 自動 PONG)。実接続 open_twitch_irc は network 依存。
- llm.py: OpenAI 互換 client (env COMPANION_LLM_BASE_URL/API_KEY/MODEL、旧 BPB_LLM_* も fallback 可)。

設計の詳細・データフロー・plugin の作り方は [ARCHITECTURE.md](ARCHITECTURE.md) を参照。

## plugin 規約 (handler, duck typing)
persona: str / fewshot: str (空可) / build_user(payload) -> str / template(request) -> str

外部パッケージは entry-point で handler を登録できる:
```
[project.entry-points."companion_core.handlers"]
shop = "yourpkg.handler:YourHandler"
```
`registry.get_handler("shop")` が遅延 discover する。本パッケージは plugin を import しない (一方向依存)。

## テスト
```
uv pip install -e .
python -m unittest discover -s tests -p "test_*.py"
```

## License
MIT
