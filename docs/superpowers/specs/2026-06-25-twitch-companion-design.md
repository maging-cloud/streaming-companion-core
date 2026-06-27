# streaming-companion-twitch 設計 (2026-06-25)

## 目的

Twitch のチャット・チャンネルイベント (フォロー / サブスク / ギフト / ビッツ / レイド) に
**ずんだもん実況で反応する配信 companion** を新規プラグインとして作る。
`companion_core` を切り出した狙い —「core が汎用 3rd-party プラグインを支える」— の実証も兼ねる。

ゲーム非依存・解析成果物なしで完全に汎用なので **公開リポジトリ**にできる。

## スコープ

**含む (v1, core 側)**:
- **`companion_core` に汎用の EventQueue (優先度/bounded/coalesce) + reactive pump を追加** —
  push 型 companion 共通のバースト吸収・反応ループ。core の minor を上げて tag

**含む (v1, twitch 側)**:
- EventSub WebSocket 接続・7種購読 (follow / subscribe / subscription.message(resub) / subscription.gift / cheer / raid / chat.message)
- イベント正規化 + coalesce (gift bomb、message_id 冪等、chat トリガ選別) → core.EventQueue へ push
- TwitchEventHandler / TwitchChatHandler (テンプレ + LLM 任意)、ずんだもん persona、NG 安全ゲート
- config / env 認証、再接続 / keepalive
- core の sink (text / file / voicevox / voicevoxplay) 再利用
- 純ロジックのテスト一式 (fake ws / opener で接続もテスト)

**含まない (後フェーズ)**:
- console 連携 (`console_provider` / `console_settings`) → まず CLI のみ
- chat の TTL 破棄、OAuth refresh token 自動更新、moderation 系イベント、overlay 演出、複数チャンネル

## リポジトリ / 依存

- **公開** `streaming-companion-twitch`、import 名 `companion_twitch`、MIT、src-layout (`src/companion_twitch/`)
- uv / Python 3.14 / hatchling。`companion_core` を uv git dep (tag 固定) で参照。依存方向は **twitch → core の一方向** (core は entry-point で handler を discover、twitch を import しない)
- **追加実行時依存は `websocket-client` のみ** (sync・async フレームワーク不要)。Helix REST / OAuth 検証 / JSON は stdlib `urllib` / `json`
- secret (OAuth token, client_id) は **リポジトリに焼かず env / config で注入**

## アーキテクチャ

```
[twitch] eventsub接続(注入) → normalize(純) ──┐ (priority/dedup_key 付き CommentRequest を push)
                                              ▼
[core]   EventQueue(優先度/coalesce) → pump worker → comment(handler) → fan_out(sinks)
```

**multi-repo 原則: 汎用機構は `companion_core` に置き、プラグインは source + 正規化 + handler だけ持つ。**
push 型 companion (Twitch/Discord/YouTube 等) はどれも「バーストを溜めて重要イベントを 1 件ずつ
喋る」反応ループを必要とするので、キューと pump は core 側の再利用部品にする。Twitch 固有なのは
EventSub source と正規化 (notification → priority/dedup_key 付き CommentRequest) と handler のみ。

IO (ネットワーク) に触れるのは `eventsub/` だけ。WS 接続と HTTP opener を注入可能にし、
正規化・handler は純ロジックでテストする。

### companion_core への汎用追加 (本 repo `streaming-companion-core`)

```
companion_core/
  queue.py      # EventQueue: bounded・優先度・dedup_key で coalesce (純データ構造)
                #   item = (priority:int, dedup_key:str|None, request:CommentRequest)
  pump.py       # run_pump(queue, sinks, *, client, ngwords, persona, gate, get_handler):
                #   queue を drain し item ごとに get_handler(kind)→comment→fan_out。
                #   単一 worker = TTS 1件ずつのペーサ。SpeechGate 併用、comment/sink 例外は隔離。
                #   source は注入 (queue へ push するのはプラグイン側)
```

既存の `registry.get_handler` / `comment` / `fan_out` / `SpeechGate` を組み合わせる薄い層。
ゲーム・プラットフォーム非依存なので core に置ける (BPB を一切 import しない原則は維持)。
core の minor バージョンを上げて tag、twitch はその tag を uv git dep で参照。

### companion_twitch のモジュール構成

```
src/companion_twitch/
  eventsub/
    client.py    # EventSubClient: WS 接続・welcome/keepalive/reconnect・Helix で購読作成
                 #   → 生 notification dict を yield (ws と opener を注入可)
    helix.py     # Helix REST 薄ラッパ (urllib): create_subscription / validate_token / get_user_id
  normalize.py   # 純: notification dict → (priority, dedup_key, CommentRequest)。coalesce 判定・
                 #   chat トリガ選別・message_id 冪等。core.EventQueue に push する形を返す
  handlers.py    # TwitchEventHandler(kind="twitch_event") / TwitchChatHandler(kind="twitch_chat")
  live.py        # runner: client→normalize→core.EventQueue→core.run_pump。CLI _main
  config.py      # [twitch] セクション解決。secret は env/config 注入
```

(旧 `policy.py` の EventQueue・消費ループは core へ移動。twitch 側には残さない。)

## データフロー

```
1. EventSubClient が wss://eventsub.wss.twitch.tv/ws へ接続
2. session_welcome → session_id 取得
3. Helix POST /eventsub/subscriptions を7種作成 (transport=websocket, session_id)
4. notification 受信ループ → 各メッセージを yield
5. [twitch] normalize: notification → (priority, dedup_key, CommentRequest)。捨てる場合は None
6. [core] EventQueue.put: 優先度付き投入、dedup_key 一致は coalesce
7. [core] pump worker(単一): get → get_handler(kind) → comment(handler,persona,ngwords,client) → fan_out(sinks)
       worker は TTS 1件ずつ = 自然なペーサ。発話中にキューがバーストを吸収
8. [twitch] keepalive / reconnect / token失効 はループ内で処理
```

## 正規化イベント

```python
{
  "type": "sub" | "resub" | "giftbomb" | "cheer" | "raid" | "follow" | "chat",
  "user": "視聴者名",
  "payload": { ... 型ごと: months, tier, bits, viewers, gift_total, message ... },
  "priority": int,        # cheer/giftbomb/raid=高, sub/resub=中, follow=低, chat=最低
  "dedup_key": str | None # coalesce/重複抑制のキー
}
```

### 正規化・coalesce ルール

- **gift sub**: `channel.subscription.gift` (total 付き) を `giftbomb` として採用。直後の個別
  `channel.subscribe(is_gift=true)` は dedup_key (gifter + 時間窓) で抑制し喋らない
- **cheer**: bits 額を payload に。大口は `payload.big=True` (handler で強め実況)
- **raid**: viewers 数を payload に
- **chat**: 選択的トリガ (メンション / `!`コマンド / 初コメ) 合致 or サンプリング当選のみ正規化。
  それ以外は None を返してキューに入れない
- **冪等**: Twitch は at-least-once 配信。`message_id` の重複は無視

## EventQueue / pump (core: `companion_core.queue` / `companion_core.pump`)

汎用部品として core に置く (Twitch 以外の push 型 companion でも再利用)。

- **EventQueue (bounded)**: 上限超過時は最低優先度 (chat) から押し出す
- **優先度**: 高い順に取り出し、同優先度は FIFO
- **coalesce**: 同 `dedup_key` (例: 同一 gifter の連続ギフト) は1件に統合 (カウント加算)
- **pump worker (単一)**: `get()` → `get_handler(kind)` → `comment` → `fan_out(sinks)`。発話の所要
  時間が実質のレート。core の SpeechGate で最小間隔の床も併用 (chat の TTL 破棄は後フェーズ)。
  comment/sink 例外は隔離して worker を止めない
- twitch 側は normalize の出力 `(priority, dedup_key, CommentRequest)` を EventQueue に push するだけ

## Handler / persona / NG

- core の `comment(request, handler, client, ngwords, persona)` を使う。BPB の ShopHandler と
  同型で `build_user(payload)` + `template(request)` を実装
- **TwitchEventHandler (kind `twitch_event`)**: sub/resub/giftbomb/cheer/raid/follow を整形。
  LLM 接続時はイベント要約を user prompt にしてずんだもん実況、未接続時は型ごとテンプレ fallback。
  大口 cheer/giftbomb は強めの語彙
- **TwitchChatHandler (kind `twitch_chat`)**: トリガ種別に応じて返答。`!ask ...` は本文を LLM へ、
  初コメは歓迎テンプレ
- **persona は core 既定のずんだもん**を再利用 (config `[persona]`)
- **NG 安全ゲート必須**: 視聴者名・チャット本文という外部入力を喋るため core の ngword に従う。
  twitch 追加 NG (`ngwords.txt`) も合成

## Config / 認証 (config.py)

```ini
[twitch]
channel = your_channel            # broadcaster
triggers = mention,command,firstmsg   # chat 選択トリガの初期セット
chat_sampling = 0.0               # 0=雑談サンプリング無効 (>0 で確率)
command_prefix = !
# 認証は env 優先 (config にも置けるが推奨は env):
#   TWITCH_CLIENT_ID, TWITCH_OAUTH_TOKEN (user access token)
```

- **必要スコープ**: `moderator:read:followers`(follow) / `channel:read:subscriptions`(sub) /
  `bits:read`(cheer) / `user:read:chat`(chat)
- 起動時に `validate_token` で scope 不足を警告。token 失効 (401) は再認証を促して停止
  (refresh token 自動更新は後フェーズ)

## エラー処理 / 再接続 (eventsub/client.py)

- **keepalive**: `session_keepalive` 無受信がタイムアウト (既定 10s 超) なら接続死とみなし再接続
- **reconnect**: `session_reconnect` 受信で新 URL に張り替え。突然の切断は指数バックオフ
- **購読作成失敗**: scope 不足 / 403 は明示エラーで起動中断、一時エラーはリトライ
- **token 失効 (401)**: 再認証を促して停止
- **冪等**: `message_id` 重複は無視
- **発話 / sink 例外は隔離**: 1件の comment/TTS 失敗で worker を止めない (握りつぶしログ → 次へ)

## テスト戦略 (ネット・依存なしで完結)

- `normalize` (twitch): 各イベント種別の notification 実サンプル → (priority, dedup_key, CommentRequest)。
  gift-bomb coalesce / 個別 is_gift 抑制 / chat トリガ判定 (拾う/捨てる) / message_id 冪等 を重点
- `queue` / `pump` (**core**): 優先度順取り出し / bounded 押し出し / dedup coalesce / pump が
  get_handler→comment→fan_out を呼ぶ / 例外隔離。fake handler・fake sink で完結
- `handlers` (twitch): 型ごとテンプレ fallback、大口フラグ、NG 適用
- `eventsub/client`: fake ws (メッセージ列を yield) + fake opener で welcome→subscribe→
  notification→keepalive→reconnect の状態遷移
- `helix`: fake opener で REST 組み立て・scope 検証
- 公開 repo 側に `test_boundary.py` (twitch→core 一方向、core が twitch を import しない)

## entry-points / CLI

```toml
[project.scripts]
twitch-companion = "companion_twitch.live:_main"   # 常駐: 接続→実況
[project.entry-points."companion_core.handlers"]
twitch_event = "companion_twitch.handlers:TwitchEventHandler"
twitch_chat  = "companion_twitch.handlers:TwitchChatHandler"
```

```
twitch-companion --sinks "text,voicevoxplay"   # 接続して実況、自動発話
```

## 配置メモ

本設計は **core repo (`streaming-companion-core`) の `docs/superpowers/specs/`** に置く。
汎用部 (queue/pump) が core の設計であり、かつ ecosystem 共有 (twitch/console 等が参照) のため。
実装時に新規 repo `streaming-companion-twitch` を作成する。core 側の queue/pump 追加 → minor tag →
twitch がその tag を参照、の順で進める。
