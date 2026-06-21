import unittest

from companion_core.console_providers import build_service
from companion_core.console.state import ConsoleState
from companion_core.supervisor import Worker


class _FakeProvider:
    """テスト用 provider。synth/player と build_workers を提供する。"""
    def __init__(self):
        self.ingest_seen = None
    def synth(self, config):
        return lambda text: b"WAV"
    def player(self, config):
        return lambda wav: None
    def build_workers(self, ingest, config):
        self.ingest_seen = ingest
        return [Worker("w", lambda: None, 0.0)]


class _MinimalProvider:
    """build_workers のみ。synth/player は core 既定が使われる。"""
    def build_workers(self, ingest, config):
        return []


class TestBuildService(unittest.TestCase):
    def test_provider_synth_player_override_is_used(self):
        p = _FakeProvider()
        # provider が synth/player を持つ場合は core 既定より優先される
        svc = build_service(p, {"bpb": {}}, console_state=ConsoleState(),
                            make_synth=lambda c: (_ for _ in ()).throw(AssertionError("既定が呼ばれた")),
                            make_player=lambda c: (_ for _ in ()).throw(AssertionError("既定が呼ばれた")))
        # build_workers に service.ingest が渡る (循環解消の順序)
        self.assertEqual(p.ingest_seen, svc.ingest)
        self.assertEqual([w["name"] for w in svc.supervisor.status()], ["w"])
        played = []
        svc.player = lambda wav: played.append(wav)
        svc.ingest("hi")
        self.assertEqual(svc.get_state()["current"]["text"], "hi")
        self.assertEqual(played, [b"WAV"])

    def test_core_default_synth_player_when_provider_omits_them(self):
        # provider が synth/player を持たない → core 既定 (make_synth/make_player) が使われる
        made = {}
        def make_synth(cfg):
            made["synth_cfg"] = cfg
            return lambda text: b"DEFWAV"
        def make_player(cfg):
            made["player_cfg"] = cfg
            return lambda wav: None
        cfg = {"voicevox": {"speaker": 3}}
        svc = build_service(_MinimalProvider(), cfg, console_state=ConsoleState(),
                            make_synth=make_synth, make_player=make_player)
        self.assertIs(made["synth_cfg"], cfg)     # 既定構築に config が渡る
        played = []
        svc.player = lambda wav: played.append(wav)
        svc.ingest("text")
        self.assertEqual(svc.get_state()["current"]["text"], "text")
        self.assertEqual(played, [b"DEFWAV"])     # core 既定 synth が結線された

    def test_default_synth_reads_voicevox_section(self):
        # _default_synth は [voicevox] の speaker/base_url を読む (VOICEVOX へは接続しない)
        from companion_core.console_providers import _default_synth
        synth = _default_synth({"voicevox": {"speaker": 7, "base_url": "http://x:1"}})
        self.assertTrue(callable(synth))


if __name__ == "__main__":
    unittest.main()
