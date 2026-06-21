"""config.toml リーダー (標準ライブラリのみ, Python 3.11+ 向け)。"""

import tomllib
from pathlib import Path

DEFAULT_PATH = Path.home() / ".streaming-companion" / "config.toml"


def load_config(path=None):
    """config.toml を読み込む。ファイルがなければ空 dict を返す。"""
    p = Path(path) if path is not None else DEFAULT_PATH
    if not p.exists():
        return {}
    with open(p, "rb") as f:
        return tomllib.load(f)


def make_client_from_config(cfg):
    """cfg の [llm] セクションから OpenAIClient を生成。未設定なら None。"""
    from .llm import OpenAIClient

    llm = cfg.get("llm", {})
    base = llm.get("base_url")
    model = llm.get("model")
    if base and model:
        return OpenAIClient(base, llm.get("api_key", ""), model)
    return None


def save_config(cfg, path=None):
    """cfg を config.toml に書き出す。tomli-w が要る (optional extra `console`/`ui`)。"""
    import tomli_w

    p = Path(path) if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        tomli_w.dump(cfg, f)
