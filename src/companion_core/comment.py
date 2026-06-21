#!/usr/bin/env python3
"""commentary core: CommentRequest + handler -> 安全な実況文 (NG 末尾常時, ゲーム非依存)。

生文 = client.complete(LLM) or handler.template(request)。
Processor チェーン = (processors or [sanitize]) + [make_ng_filter(ngwords, handler.template)]。
NG を必ず末尾に付与し出力に NG が残らないことを保証する安全ゲート。
"""

from collections.abc import Callable, Iterable, Sequence
from typing import Any

from .persona import ZUNDAMON, Persona
from .processor import make_ng_filter, run_pipeline, sanitize
from .prompt import build_prompt


def comment(
    request: dict[str, Any],
    handler: Any,
    client: Any = None,
    processors: Sequence[Callable[..., str]] | None = None,
    ngwords: Iterable[str] | None = None,
    persona: Persona | None = None,
) -> str:
    """request + handler -> 安全な実況文。client=None で handler.template。NG を必ず適用。

    persona は LLM 経路の口調 (未指定は ZUNDAMON)。template fallback は persona 非依存
    (= ずんだもん固定)。
    """
    persona = persona or ZUNDAMON
    if client is not None:
        system, user = build_prompt(request, handler, persona)
        text = client.complete(system, user)
    else:
        text = handler.template(request)
    procs = list(processors) if processors is not None else [sanitize]
    procs = procs + [make_ng_filter(ngwords or [], handler.template)]  # NG を末尾に常時付与
    return run_pipeline(text, request, procs)
