"""companion_core.sinks: 追加 Sink 実装 (ゲーム非依存)。

- file.file_sink(path): テキストを file へ書く Sink (OBS テキストソース等のオーバーレイ用)。
- voicevox.VoicevoxSink: VOICEVOX HTTP で text → 音声 (WAV)。HTTP は stdlib (urllib)、
  音声再生は player callback で注入し本体の依存ゼロを保つ。

いずれも `sink(text)` 規約 (呼び出し可能オブジェクト) を満たし fan_out に渡せる。
"""
