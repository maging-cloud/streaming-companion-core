#!/usr/bin/env python3
"""commentary core: CommentRequest + handler -> 安全な実況文 (NG 末尾常時, ゲーム非依存)。

生文 = client.complete(LLM) or handler.template(request)。
Processor チェーン = (processors or [sanitize]) + [make_ng_filter(ngwords, handler.template)]。
NG を必ず末尾に付与し出力に NG が残らないことを保証する安全ゲート。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def comment(request, handler, client=None, processors=None, ngwords=None):
    """request + handler -> 安全な実況文。client=None で handler.template。NG を必ず適用。"""
    from prompt import build_prompt
    from processor import sanitize, make_ng_filter, run_pipeline
    if client is not None:
        system, user = build_prompt(request, handler)
        text = client.complete(system, user)
    else:
        text = handler.template(request)
    procs = list(processors) if processors is not None else [sanitize]
    procs = procs + [make_ng_filter(ngwords or [], handler.template)]   # NG を末尾に常時付与
    return run_pipeline(text, request, procs)
