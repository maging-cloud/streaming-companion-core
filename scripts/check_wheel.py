#!/usr/bin/env python3
"""ビルド済み wheel が必須の同梱アセットを含むか検証する (CI 用ガード)。

CI が editable install (`pip install -e .`) のテストしか回さないと、wheel 固有の
packaging 不具合 (force-include による二重追加で build 失敗 / アセット欠落) を
見逃す。本スクリプトは `uv build --wheel` 後に dist の wheel を開き、必須アセットの
同梱を検証する。stdlib のみ。

使い方:
    uv build --wheel
    python scripts/check_wheel.py
"""

import glob
import sys
import zipfile

REQUIRED = [
    "companion_core/console_providers.py",
    "companion_core/console/service.py",
    "companion_core/supervisor.py",
]


def main():
    wheels = glob.glob("dist/*.whl")
    if not wheels:
        print("ERROR: dist/*.whl が見つからない (wheel build に失敗?)", file=sys.stderr)
        return 1
    wheel = sorted(wheels)[-1]
    names = set(zipfile.ZipFile(wheel).namelist())
    missing = [r for r in REQUIRED if r not in names]
    if missing:
        print(f"ERROR: wheel に必須アセットが無い: {missing}", file=sys.stderr)
        print(f"  wheel: {wheel}", file=sys.stderr)
        return 1
    print(f"OK: {wheel} は必須アセットを同梱: {REQUIRED}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
