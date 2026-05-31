# core — 配信実況コンパニオン 汎用基盤 (ゲーム非依存)

推薦/イベント等の構造化入力 → 安全な実況文を生成する汎用機構。ゲーム固有の知識は持たず、
handler 注入で各ゲーム/ペルソナのプラグインを受け取る。最終的に公開リポジトリへ切り出す対象。

## モジュール
- request.py: CommentRequest{kind,payload} 規約 + make_request(kind, payload)。
- registry.py: kind → handler 登録 (register/get_handler)。
- prompt.py: build_prompt(request, handler) — handler.persona/fewshot/build_user から (system,user)。
- processor.py: sanitize (媒体非依存の安全整形) + make_ng_filter (NGフィルタ) + run_pipeline。
- ngword.py: NGワード管理 (load_ngwords/contains_ng)、--list 列挙。汎用 seed は core/ngwords.txt。
- sink.py: 出力 Sink (テキスト既定) + fan_out (複数同時)。
- comment.py: comment(request, handler, client, processors, ngwords) — NG を末尾に常時付与する安全ゲート。
- llm.py: OpenAI 互換 LLM client (OpenAIClient/make_client_from_env、env BPB_LLM_BASE_URL/API_KEY/MODEL)。

## handler 規約 (duck typing)
- persona: str / fewshot: str (空可) / build_user(payload) -> str / template(request) -> str

## 境界
core/ は commenter/scorer/tools/evaluator 等の BPB 固有モジュールを import しない (一方向依存)。
core/test_boundary.py が自動ガード。

## 利用例 (BPB アダプタ = commenter/)
- python commenter/cli.py        # recommendation.json → ShopHandler → core.comment → text sink
- python core/ngword.py --list   # 汎用 NGワード一覧
