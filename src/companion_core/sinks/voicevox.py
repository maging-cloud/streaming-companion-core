#!/usr/bin/env python3
"""VOICEVOX Sink: text → 音声 (WAV bytes)。HTTP は標準ライブラリ (urllib) のみ。

VOICEVOX エンジン (既定 http://localhost:50021) の 2 段 API を叩く:
  1. POST /audio_query?text=...&speaker=...   → 合成クエリ (JSON)
  2. POST /synthesis?speaker=...  (body=クエリ) → WAV bytes

音声**再生**は依存が要るため本体に持たず、`player` callback (callable(wav_bytes)) で
注入する。これにより Sink 本体は stdlib のみで動き、オフラインでテスト可能 (opener 差し替え)。
将来、再生ライブラリ同梱版が必要になれば optional extra として追加する。
"""
import json
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "http://localhost:50021"


class VoicevoxSink:
    """text を VOICEVOX で合成する Sink。`sink(text)` で WAV bytes を返す。"""

    def __init__(self, speaker=1, base_url=DEFAULT_BASE_URL, timeout=10,
                 player=None, save_path=None, opener=None):
        self.speaker = speaker
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.player = player          # callable(wav_bytes): 音声再生 (注入)
        self.save_path = save_path    # 指定時は WAV を書き出す
        self._opener = opener or urllib.request.urlopen  # テストで差し替え可能

    def _post(self, path, params=None, data=None):
        url = self.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {"Content-Type": "application/json"} if data is not None else {}
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with self._opener(req, timeout=self.timeout) as r:
            return r.read()

    def synthesize(self, text):
        """text → WAV bytes。audio_query → synthesis の 2 段。"""
        query_bytes = self._post("/audio_query",
                                 params={"text": text, "speaker": self.speaker})
        query = json.loads(query_bytes.decode("utf-8"))
        return self._post("/synthesis",
                          params={"speaker": self.speaker},
                          data=json.dumps(query).encode("utf-8"))

    def __call__(self, text):
        wav = self.synthesize(text)
        if self.save_path:
            with open(self.save_path, "wb") as f:
                f.write(wav)
        if self.player:
            self.player(wav)
        return wav
