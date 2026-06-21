#!/usr/bin/env python3
"""OpenAI 互換 LLM クライアント (汎用, 標準ライブラリのみ)。

設定 (環境変数):
  COMPANION_LLM_BASE_URL  例 https://api.openai.com/v1 / 互換エンドポイント
  COMPANION_LLM_API_KEY   API キー (ローカル endpoint では空でも可)
  COMPANION_LLM_MODEL     例 gpt-4o-mini 等

旧 BPB_LLM_BASE_URL / BPB_LLM_API_KEY / BPB_LLM_MODEL も後方互換 fallback として受け付ける。
COMPANION_LLM_* が設定されている場合は常にそちらが優先される。
"""

import json
import os
import urllib.request

ENV_BASE = "COMPANION_LLM_BASE_URL"
ENV_KEY = "COMPANION_LLM_API_KEY"
ENV_MODEL = "COMPANION_LLM_MODEL"

_LEGACY = {
    ENV_BASE: "BPB_LLM_BASE_URL",
    ENV_KEY: "BPB_LLM_API_KEY",
    ENV_MODEL: "BPB_LLM_MODEL",
}


def _get(env, key):
    v = env.get(key)
    return v if v is not None else env.get(_LEGACY[key])


class OpenAIClient:
    """OpenAI 互換 /chat/completions クライアント (標準ライブラリのみ)。"""

    def __init__(self, base_url, api_key, model, timeout=60):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def complete(self, system, user):
        body = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": 0,
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(self.base_url + "/chat/completions", data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            resp = json.loads(r.read().decode("utf-8"))
        return resp["choices"][0]["message"]["content"]


def make_client_from_env(env=None):
    """env に OpenAI 互換設定が十分あれば OpenAIClient、無ければ None。
    新 prefix COMPANION_LLM_* を優先し、旧 BPB_LLM_* を後方互換 fallback として受け付ける。"""
    env = env if env is not None else os.environ
    base = _get(env, ENV_BASE)
    model = _get(env, ENV_MODEL)
    if base and model:
        return OpenAIClient(base, _get(env, ENV_KEY), model)
    return None
