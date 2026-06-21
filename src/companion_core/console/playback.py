"""WAV bytes を OS 既定デバイスへ非同期再生する player を作る。

依存ゼロ (stdlib): Windows=winsound, macOS=afplay, Linux=aplay (subprocess)。
デバイス選択は OS 既定にルーティングする前提 (VB-CABLE を既定にする等)。
アプリ内デバイス選択は将来の optional extra。
"""

import os
import subprocess
import sys
from pathlib import Path

DEFAULT_PLAY_PATH = Path.home() / ".streaming-companion" / "last.wav"


def make_player(play_path=None, platform=None, popen=None, winsound_mod=None):
    """player(wav_bytes) を返す。wav を play_path に書いてから platform 別に再生。"""
    play_path = str(play_path) if play_path is not None else str(DEFAULT_PLAY_PATH)
    platform = platform if platform is not None else sys.platform
    popen = popen or (lambda args: subprocess.Popen(args))  # 非ブロッキング

    def player(wav_bytes):
        if not wav_bytes:
            return
        os.makedirs(os.path.dirname(play_path) or ".", exist_ok=True)
        with open(play_path, "wb") as f:
            f.write(wav_bytes)
        if platform == "win32":
            ws = winsound_mod
            if ws is None:
                import winsound as ws  # noqa: PLC0415
            ws.PlaySound(play_path, ws.SND_FILENAME | ws.SND_ASYNC)
        elif platform == "darwin":
            popen(["afplay", play_path])
        else:
            popen(["aplay", "-q", play_path])

    return player
