import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

if HAS_PYSIDE6:
    from companion_core.console.state import ConsoleState
    from companion_core.console.service import ConsoleService
    from companion_core.supervisor import Supervisor, Worker
    from companion_settings.live_panel import LivePanel


class _Noop:
    def start(self): pass
    def join(self, timeout=None): pass
    def is_alive(self): return True


def _service():
    sup = Supervisor([Worker("a", lambda: None, 0.0)],
                     spawn=lambda target, name, daemon: _Noop(),
                     sleeper=lambda s: None, max_ticks=0)
    return ConsoleService(sup, ConsoleState(), synth=lambda t: b"WAV",
                          player=lambda w: None, clock=lambda: 1.0)


@unittest.skipUnless(HAS_PYSIDE6, "PySide6 未インストール")
class TestLivePanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_apply_snapshot_updates_labels(self):
        panel = LivePanel(_service())
        panel._apply_snapshot({"running": True, "muted": False,
                               "current": {"text": "やあなのだ"}, "history": [{"text": "前のだ"}]})
        self.assertEqual(panel._status.text(), "RUNNING")
        self.assertEqual(panel._btn_toggle.text(), "⏹ STOP")
        self.assertEqual(panel._now.text(), "やあなのだ")
        self.assertEqual(panel._history.count(), 1)

    def test_toggle_button_starts_and_stops(self):
        panel = LivePanel(_service())
        panel._on_toggle()                       # START
        self.assertEqual(panel._status.text(), "RUNNING")
        panel._on_toggle()                       # STOP
        self.assertEqual(panel._status.text(), "STOPPED")

    def test_mute_button_toggles(self):
        panel = LivePanel(_service())
        panel._on_mute()
        self.assertEqual(panel._btn_mute.text(), "🔈 UNMUTE")
        self.assertTrue(panel.service.get_state()["muted"])

    def test_replay_calls_player(self):
        svc = _service()
        played = []
        svc.player = lambda w: played.append(w)
        svc.ingest("one")                        # last_wav をセット
        panel = LivePanel(svc)
        panel._on_replay()
        self.assertIn(b"WAV", played)


if __name__ == "__main__":
    unittest.main()
