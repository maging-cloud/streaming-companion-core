# Architecture — `companion_core`

`companion_core` は **構造化入力 → 安全な実況文** を生成する汎用パイプライン。ゲーム・ペルソナ・媒体に
依存しない。各アプリは **handler** (ペルソナ + 整形ロジック) を plugin として注入し、core はその handler を
通して system/user プロンプトを組み立て、LLM 生文を安全に整形して出力する。

## データフロー

```
入力源 (アプリ固有)
    │  CommentRequest{kind, payload} を生成
    ▼
get_handler(kind)            ← entry-point plugin discovery (registry)
    │  handler を解決
    ▼
comment(request, handler, client, processors, ngwords)
    │
    ├─ client あり → build_prompt(request, handler) → client.complete(system, user)  (LLM 生文)
    ├─ client なし → handler.template(request)                                       (決定的 fallback)
    │
    ▼
processor チェーン = (processors or [sanitize]) + [make_ng_filter(ngwords, handler.template)]
    │  sanitize → ... → NG フィルタ (末尾常時)
    ▼
安全な実況文 (str)
    │
    ▼
fan_out(text, [sink, ...])   ← text / その他 Sink へ出力
```

## モジュール

| module | 責務 |
|---|---|
| `request` | `CommentRequest{kind, payload}` の規約 + `make_request(kind, payload)`。core は payload の内部構造を仮定しない。 |
| `registry` | `kind → handler`。`register()` で明示登録、`get_handler()` が entry-point group `companion_core.handlers` を遅延 discover。 |
| `prompt` | `build_prompt(request, handler) → (system, user)`。`handler.persona`/`fewshot`/`build_user(payload)` から組み立てる。 |
| `processor` | `sanitize` (媒体非依存の整形) + `make_ng_filter` (NG フィルタ生成) + `run_pipeline`。 |
| `ngword` | NG ワード管理 (`load_ngwords`/`contains_ng`/`default_paths`)。seed は同梱 `ngwords.txt`。 |
| `sink` | 出力 Sink (`text` 既定) + `fan_out`。追加 Sink (音声/配信連携等) もゲーム非依存なため本パッケージに属する。 |
| `sinks.file` | `file_sink(path, append=False)` — 実況文を file へ書く Sink (OBS テキストソース等のオーバーレイ)。stdlib のみ。 |
| `sinks.voicevox` | `VoicevoxSink(speaker, base_url, player, save_path)` — VOICEVOX HTTP で text→WAV。HTTP は stdlib、音声再生は `player` callback で注入し依存ゼロを維持。 |
| `comment` | `comment(...)` オーケストレーション。LLM 生文 or handler.template を取り、NG を末尾常時付与して安全文を返す。 |
| `orchestrator` | `SpeechGate` — 発話タイミング制御。スコア変動閾値 + クールダウン + 重要イベント/force で「喋るか」を判定。 |
| `chat_handler` | `ChatHandler` (汎用基底, persona 注入式) + `ZundamonChatHandler` (既定 persona ずんだもん, ゲーム非依存)。 |
| `sources.chat` | `make_chat_message` / `from_chat` (chat→CommentRequest) / `keyword_matcher` / `ChatRouter` (kind 振り分け)。 |
| `sources.twitch` | `parse_irc_line` (PRIVMSG/PING) + `TwitchChatSource` (注入行→privmsg、PING 自動 PONG)。実接続 `open_twitch_irc` は network 依存。 |
| `llm` | OpenAI 互換 client (`make_client_from_env`、env `COMPANION_LLM_BASE_URL`/`API_KEY`/`MODEL`)。 |

## handler 規約 (duck typing)

handler は基底クラス強制なし。以下のメンバを満たすオブジェクトであればよい:

```python
class Handler:
    persona: str               # system プロンプトのキャラ設定
    fewshot: str               # few-shot 例 (空文字可)

    def build_user(self, payload) -> str:   # user プロンプト生成
        ...

    def template(self, request) -> str:     # 決定的 fallback / NG 差替先
        ...
```

- `prompt.build_prompt` は `system = persona + ("\n" + fewshot if fewshot else "")`、`user = build_user(payload)`。
- `comment` は LLM 不在時 (`client=None`) や NG 検出時に `handler.template(request)` を使う。

## 安全ゲート (core が必ず担保)

`comment` は processor チェーンの **末尾に NG フィルタを常時付与**する:

```python
procs = (processors or [sanitize]) + [make_ng_filter(ngwords or [], handler.template)]
```

- NG 語を含む生文は `handler.template(request)` を sanitize した代替に差し替える。
- それでも NG が残る場合は `processor.SAFE_GENERIC` (最終 fallback の安全文字列) を返す。
- これにより **NG 語が出力に残らないこと**を core が保証する。アプリ側は NG 語リストを追加するだけでよい。

> `SAFE_GENERIC` は二重 NG 時の最終 fallback。ペルソナ非依存の中立文を想定する
> (アプリ固有の口調が必要なら handler.template 側で表現する)。

## plugin の作り方

1. handler クラスを実装 (上記規約を満たす)。
2. パッケージの `pyproject.toml` で entry-point を宣言:

   ```toml
   [project.entry-points."companion_core.handlers"]
   chat = "yourpkg.handlers:ChatHandler"
   ```

3. インストール (`uv pip install -e .` 等) すると、`registry.get_handler("chat")` が遅延 discover で解決する。

core は plugin パッケージを **import しない** (entry-point 文字列経由の遅延 load)。依存は常に
**アプリ → `companion_core` の一方向**。`tests/test_boundary.py` が core 内に外部 import が無いことを自動ガードする。

### 最小例

```python
# yourpkg/handlers.py
class ChatHandler:
    persona = "あなたは親しみやすいアシスタントです。短く前向きに話します。"
    fewshot = ""

    def build_user(self, payload):
        return f"次のイベントを一言で実況してください: {payload.get('event')}"

    def template(self, request):
        return "なるほど、いい展開ですね"
```

```python
# アプリ側の呼び出し
from companion_core.request import make_request
from companion_core.registry import get_handler
from companion_core.comment import comment
from companion_core.sink import get_sink, fan_out
from companion_core.llm import make_client_from_env
from companion_core.ngword import load_ngwords, default_paths

req = make_request("chat", {"event": "プレイヤーがレベルアップした"})
handler = get_handler("chat")                      # entry-point から解決
client = make_client_from_env()                    # env 未設定なら None → handler.template
text = comment(req, handler, client=client, ngwords=load_ngwords(default_paths()))
fan_out(text, [get_sink("text")])
```

## Sink の追加実装 (`companion_core.sinks`)

`sink` モジュールの `text_sink` / `fan_out` 規約 (callable `sink(text)`) を満たす追加 Sink:

```python
from companion_core.sink import fan_out
from companion_core.sinks.file import file_sink
from companion_core.sinks.voicevox import VoicevoxSink

# OBS のテキストソースが読むファイルに最新コメントを書く
overlay = file_sink("~/obs/comment.txt")

# VOICEVOX で音声合成。再生はアプリが player を注入 (依存ゼロを保つ)。
tts = VoicevoxSink(speaker=3, save_path="~/.streaming-companion/last.wav")

fan_out("いい流れなのだ", [overlay, tts])   # text/file/音声へ同時 fan-out
```

VOICEVOX エンジンが `http://localhost:50021` で稼働している必要がある (合成 API)。
音声再生ライブラリは利用側が `player` callback で用意する。将来、同梱再生版が要れば
optional extra として追加する。

## 発話タイミング制御 (`orchestrator.SpeechGate`)

毎入力で実況すると冗長なため、`SpeechGate` が発話可否を判定する:

```python
from companion_core.orchestrator import SpeechGate

gate = SpeechGate(min_interval=5.0, score_delta=0.1, important_kinds=("battle_lost",))

if gate.should_speak(score=rec_score, kind=event_kind):
    text = comment(request, handler, client=client, ngwords=ngwords)
    fan_out(text, sinks)
```

- 重要イベント (`important_kinds`) / `force=True` → cooldown 無視で常に発話。
- それ以外 → スコア変動が `score_delta` 以上 **かつ** 前回発話から `min_interval` 秒経過で発話。
- 発話した時だけ基準スコア・発話時刻を更新する (黙った呼び出しでは基準を動かさない)。
- 時刻は `clock` callable で注入でき、テスト可能 (実時間に依存しない)。

## 入力 source とチャット振り分け (`companion_core.sources`)

sink (出力) と対称に、source は「外部入力 → CommentRequest」を担う。Twitch chat の取り込みは
ゲーム非依存なため core に属する。「何がゲーム関連か」等の語彙はゲーム固有なので、利用側が
`keyword_matcher` で `ChatRouter` に**注入**する (core はキャラ・ゲーム語彙を持たない)。

```python
from companion_core.sources.twitch import TwitchChatSource, open_twitch_irc
from companion_core.sources.chat import ChatRouter, keyword_matcher, from_chat
from companion_core.registry import get_handler
from companion_core.comment import comment

# ゲーム関連語 (アプリ注入) → kind を振り分け
router = ChatRouter(rules=[(keyword_matcher(["買", "build", "シナジー"]), "chat_game")],
                    default_kind="chat")

recv, send = open_twitch_irc(token, nick, "#channel")   # network 依存
for msg in TwitchChatSource(recv, send=send).messages():
    kind = router.route(msg)                              # "chat_game" or "chat"
    req = from_chat(msg["user"], msg["text"], kind=kind)
    text = comment(req, get_handler(kind), client=client, ngwords=ngwords)
    fan_out(text, sinks)
```

`ChatHandler` 基底は persona 注入式で、ゲーム/キャラ固有 handler はこれを継承し persona/template を
与える (entry-point group `companion_core.handlers` に kind="chat" / "chat_game" 等で登録)。

## 設計原則

- **ゲーム/媒体/ペルソナ非依存**: それらは全て handler / config / sink 実装側に置く。core は機構のみ。
- **依存ゼロを基本とする**: core 本体は標準ライブラリのみ。外部依存が要る Sink (音声合成・配信連携等) は
  optional extra (`companion_core.sinks.*`) として隔離し、本体の依存ゼロを保つ。
- **安全ゲートは core が担保**: NG フィルタの末尾常時付与はアプリに委ねない。
- **一方向依存**: アプリ → `companion_core`。core は plugin を import しない (boundary test で自動ガード)。
