import tomllib
import tomli_w
from pathlib import Path

DEFAULT_PATH = Path.home() / ".streaming-companion" / "config.toml"


def load(path=None):
    """config.toml を読み込む。ファイルがなければ空 dict を返す。"""
    p = Path(path) if path is not None else DEFAULT_PATH
    if not p.exists():
        return {}
    with open(p, "rb") as f:
        return tomllib.load(f)


def save(cfg: dict, path=None):
    """config.toml に書き込む。親ディレクトリを自動作成する。"""
    p = Path(path) if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        tomli_w.dump(cfg, f)
