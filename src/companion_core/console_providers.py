"""console provider の discover。ゲーム非依存。

operator console は UI 非依存の制御ロジック (ConsoleService/Supervisor) を持つが、
実際に動かす worker 群・TTS は consumer 固有。consumer は entry-point group
`companion_core.console_providers` に provider を登録し、汎用 console がそれを discover
して ConsoleService を組み立てる。

provider 契約 (duck typing):
    label: str                                   # 表示名 (任意)
    build_workers(ingest, config) -> list[Worker] # ingest を sink に注入して worker を組む
    synth(config) / player(config)               # 任意 override。通常は不要。

TTS 合成 (synth) と音声再生 (player) は generic なので **core が config から既定構築**する
(VOICEVOX = `[voicevox]` セクション、player = OS 既定デバイス)。provider が同名メソッドを
持つ場合のみ override される (ゲーム単位の TTS 差し替えは稀なので既定で十分)。

本パッケージは provider を import しない (entry-point 文字列で discover、一方向依存)。
"""
import importlib.metadata

_GROUP = "companion_core.console_providers"


def _default_synth(config):
    """config の [voicevox] から VOICEVOX 合成関数を作る (core 既定)。"""
    from .sinks.voicevox import VoicevoxSink, DEFAULT_BASE_URL
    vv = config.get("voicevox", {})
    return VoicevoxSink(speaker=vv.get("speaker", 1),
                        base_url=vv.get("base_url", DEFAULT_BASE_URL)).synthesize


def _default_player(config):
    """OS 既定デバイスへ再生する player を作る (core 既定)。"""
    from .console.playback import make_player
    return make_player()


def discover_console_providers():
    """登録された console provider を検索・instantiate して返す。失敗は握りつぶす。"""
    providers = []
    for ep in importlib.metadata.entry_points(group=_GROUP):
        try:
            providers.append(ep.load()())
        except Exception:  # noqa: BLE001 - 壊れた plugin で host を落とさない
            pass
    return providers


def build_service(provider, config, *, console_state=None, service_cls=None,
                  supervisor_cls=None, make_synth=None, make_player=None):
    """provider と config から ConsoleService を組み立てる。

    synth/player は core が config から既定構築する (provider が同名メソッドを持てば override)。
    循環 (worker は ingest 必要 / service は synth・player 必要) を、synth/player を
    先に取得 → service 生成 → build_workers(service.ingest) の順で解消する。
    make_synth/make_player はテスト用の既定構築 override。
    """
    if service_cls is None:
        from .console.service import ConsoleService as service_cls
    if supervisor_cls is None:
        from .supervisor import Supervisor as supervisor_cls
    if console_state is None:
        from .console.state import ConsoleState
        console_state = ConsoleState()
    make_synth = make_synth or _default_synth
    make_player = make_player or _default_player

    synth = provider.synth(config) if hasattr(provider, "synth") else make_synth(config)
    player = provider.player(config) if hasattr(provider, "player") else make_player(config)
    svc = service_cls(None, console_state, synth=synth, player=player)
    workers = provider.build_workers(svc.ingest, config)
    svc.supervisor = supervisor_cls(workers)
    console_state.set_workers(svc.supervisor.status())
    return svc
