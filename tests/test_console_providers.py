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
    """synth/player を持たない最小 provider。"""
    def build_workers(self, ingest, config):
        return []


class TestBuildService(unittest.TestCase):
    def test_assembles_service_with_workers_and_ingest(self):
        p = _FakeProvider()
        svc = build_service(p, {"bpb": {}}, console_state=ConsoleState())
        # build_workers に service.ingest が渡る (循環解消の順序)
        self.assertEqual(p.ingest_seen, svc.ingest)
        # supervisor に worker がセットされる
        self.assertEqual([w["name"] for w in svc.supervisor.status()], ["w"])
        # synth/player が結線され ingest で再生まで到達
        played = []
        svc.player = lambda wav: played.append(wav)
        svc.ingest("hi")
        self.assertEqual(svc.get_state()["current"]["text"], "hi")
        self.assertEqual(played, [b"WAV"])

    def test_minimal_provider_without_synth_player(self):
        svc = build_service(_MinimalProvider(), {}, console_state=ConsoleState())
        self.assertIsNone(svc.synth)
        self.assertIsNone(svc.player)
        self.assertEqual(svc.supervisor.status(), [])
        # synth 無しでも ingest はテキストを積む
        svc.ingest("text")
        self.assertEqual(svc.get_state()["current"]["text"], "text")


if __name__ == "__main__":
    unittest.main()
