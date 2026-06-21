"""console の全ロジック。HTTP 非依存で単体テスト可能。

`ingest(text)` は sink として live worker から呼ばれ、comment を state に積み、
TTS 合成 (synth) → 再生 (player) を駆動する (mute 時は再生しない)。start/stop は
Supervisor を直叩き。config は companion_core.config を再利用。
"""

import time

from .. import config as _config


class ConsoleService:
    def __init__(self, supervisor, state, synth=None, player=None, config_path=None, clock=None):
        self.supervisor = supervisor
        self.state = state
        self.synth = synth  # callable(text) -> wav bytes | None
        self.player = player  # callable(wav bytes)
        self.config_path = config_path
        self._clock = clock or time.time

    # ---- sink (live worker から呼ばれる) ----
    def ingest(self, text):
        self.state.push_comment(text, ts=self._clock())
        wav = None
        if self.synth is not None:
            try:
                wav = self.synth(text)
            except Exception as e:  # noqa: BLE001 - TTS 落ちでもテキストは出す
                print(f"TTS 合成失敗 (継続): {e}")
                wav = None
        if wav:
            self.state.last_wav = wav
            if self.player is not None and not self.state.muted:
                self.player(wav)
        return text

    # ---- control ----
    def control(self, action):
        if action == "start":
            self.supervisor.start()
            self.state.set_workers(self.supervisor.status())
            self.state.set_running(True)
        elif action == "stop":
            self.supervisor.stop()
            self.state.set_running(False)
        elif action == "mute":
            self.state.set_muted(True)
        elif action == "unmute":
            self.state.set_muted(False)
        elif action == "replay":
            if self.state.last_wav and self.player is not None:
                self.player(self.state.last_wav)
        else:
            return {"ok": False, "error": f"unknown action: {action}", "state": self.state.snapshot()}
        return {"ok": True, "state": self.state.snapshot()}

    # ---- state / config ----
    def get_state(self):
        return self.state.snapshot()

    def get_config(self):
        return _config.load_config(self.config_path)

    def put_config(self, cfg):
        _config.save_config(cfg, self.config_path)
        return {"ok": True, "restart_required": True}
