import os
import tempfile
import unittest

from companion_core.supervisor import Supervisor, Worker
from companion_core.console.state import ConsoleState
from companion_core.console.service import ConsoleService

try:
    import tomli_w  # noqa: F401
    HAS_TOMLI_W = True
except ImportError:
    HAS_TOMLI_W = False


class _Noop:
    def start(self): pass
    def join(self, timeout=None): pass
    def is_alive(self): return True


def _service(synth=None, player=None, config_path=None, clock=None):
    sup = Supervisor([Worker("a", lambda: None, 0.0)],
                     spawn=lambda target, name, daemon: _Noop(),
                     sleeper=lambda s: None, max_ticks=0)
    state = ConsoleState()
    return ConsoleService(sup, state, synth=synth, player=player,
                          config_path=config_path, clock=clock or (lambda: 1.0))


class TestConsoleService(unittest.TestCase):
    def test_ingest_pushes_comment_and_plays(self):
        played = []
        svc = _service(synth=lambda t: b"WAV", player=lambda w: played.append(w))
        svc.ingest("hello")
        snap = svc.get_state()
        self.assertEqual(snap["current"]["text"], "hello")
        self.assertEqual(played, [b"WAV"])

    def test_mute_blocks_playback_but_keeps_text(self):
        played = []
        svc = _service(synth=lambda t: b"WAV", player=lambda w: played.append(w))
        svc.control("mute")
        svc.ingest("hi")
        self.assertEqual(played, [])
        self.assertEqual(svc.get_state()["current"]["text"], "hi")
        self.assertTrue(svc.get_state()["muted"])

    def test_synth_failure_still_records_text(self):
        def boom(t):
            raise RuntimeError("voicevox down")
        svc = _service(synth=boom, player=lambda w: None)
        svc.ingest("text-anyway")
        self.assertEqual(svc.get_state()["current"]["text"], "text-anyway")

    def test_replay_replays_last_wav(self):
        played = []
        svc = _service(synth=lambda t: b"W1", player=lambda w: played.append(w))
        svc.ingest("one")
        svc.control("replay")
        self.assertEqual(played, [b"W1", b"W1"])

    def test_start_stop_toggles_running(self):
        svc = _service()
        svc.control("start")
        self.assertTrue(svc.get_state()["running"])
        svc.control("stop")
        self.assertFalse(svc.get_state()["running"])

    def test_unknown_action_returns_error(self):
        svc = _service()
        res = svc.control("frobnicate")
        self.assertFalse(res["ok"])

    @unittest.skipUnless(HAS_TOMLI_W, "tomli-w 未インストール")
    def test_config_get_put_roundtrip(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "config.toml")
        svc = _service(config_path=path)
        res = svc.put_config({"speech": {"min_interval": 3.0}})
        self.assertTrue(res["ok"])
        self.assertTrue(res["restart_required"])
        self.assertEqual(svc.get_config()["speech"]["min_interval"], 3.0)


if __name__ == "__main__":
    unittest.main()
