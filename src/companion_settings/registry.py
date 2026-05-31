import importlib.metadata

_SETTINGS_GROUP = "companion_core.settings"
_HANDLERS_GROUP = "companion_core.handlers"


def discover_settings_panels():
    """companion_core.settings entry-point から設定パネルを検索してインスタンス化する。"""
    panels = []
    for ep in importlib.metadata.entry_points(group=_SETTINGS_GROUP):
        try:
            panels.append(ep.load()())
        except Exception:
            pass
    return panels


def discover_handler_kinds():
    """companion_core.handlers entry-point から kind 名の一覧を返す。"""
    return [ep.name for ep in importlib.metadata.entry_points(group=_HANDLERS_GROUP)]
