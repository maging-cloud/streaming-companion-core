#!/usr/bin/env python3
"""file Sink: 実況文を file へ書き出す (OBS テキストソース等のオーバーレイ用)。

既定は上書き (最新コメントのみ表示)。append=True で追記ログにできる。
"""

import os
from collections.abc import Callable


def file_sink(path: str, append: bool = False, encoding: str = "utf-8") -> Callable[[str], str]:
    """path に text を書く Sink を返す。append=False は上書き、True は 1 行追記。

    親ディレクトリが無ければ作成する。返り値の Sink は受け取った text を返す
    (fan_out で他 Sink と結果を揃えるため)。
    """
    path = os.path.expanduser(path)

    def sink(text: str) -> str:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        mode = "a" if append else "w"
        with open(path, mode, encoding=encoding) as f:
            f.write(text + "\n" if append else text)
        return text

    return sink
