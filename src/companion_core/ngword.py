#!/usr/bin/env python3
"""NGワード管理 (配信規約順守)。1 行 1 語、部分一致・大小無視。

リスト = 呼び出し側が渡すパス列をマージ。汎用 seed は core/ngwords.txt。
CLI `--list` で現在の NGワードを列挙。
"""
import os


def load_ngwords(paths):
    """複数ファイルから NGワードをマージ (#コメント/空行無視, 小文字化, 順序保持・重複除去)。"""
    words, seen = [], set()
    for p in paths:
        if not p or not os.path.isfile(p):
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                w = line.strip()
                if not w or w.startswith("#"):
                    continue
                lw = w.lower()
                if lw not in seen:
                    seen.add(lw)
                    words.append(lw)
    return words


def contains_ng(text, ngwords):
    """text が NGワードのいずれかを部分一致 (大小無視) で含むか。"""
    t = (text or "").lower()
    return any(w in t for w in ngwords)


def default_paths():
    import importlib.resources
    seed = importlib.resources.files("companion_core") / "ngwords.txt"
    user = os.path.expanduser("~/bb-analysis/ngwords_user.txt")
    return [str(seed), user]


def _main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="現在の NGワードを列挙")
    a = ap.parse_args()
    words = load_ngwords(default_paths())
    if a.list:
        for w in words:
            print(w)
        print(f"-- {len(words)} 語 (companion_core/ngwords.txt + ~/bb-analysis/ngwords_user.txt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
