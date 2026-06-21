import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

if HAS_PYSIDE6:
    from companion_settings.panels.voicevox import VoicevoxPanel


@unittest.skipUnless(HAS_PYSIDE6, "PySide6 未インストール")
class TestVoicevoxPanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _panel(self, cfg=None):
        self.applied = []
        self.persisted = []
        return VoicevoxPanel(cfg or {"speaker": 3, "base_url": "http://localhost:50021"},
                             apply_cb=lambda c: self.applied.append(c),
                             persist_cb=lambda c: self.persisted.append(c))

    def test_initial_fields_from_cfg(self):
        p = self._panel({"speaker": 7, "base_url": "http://x:1"})
        self.assertEqual(p.get_config(), {"speaker": 7, "base_url": "http://x:1"})
        self.assertEqual(self.applied, [])      # 初期化では live 反映しない

    def test_speaker_change_applies_live(self):
        p = self._panel()
        p._speaker.setValue(5)                  # commit → live 反映
        self.assertEqual(self.applied[-1], {"speaker": 5, "base_url": "http://localhost:50021"})

    def test_save_applies_and_persists(self):
        p = self._panel()
        p._speaker.setValue(9)
        self.applied.clear()
        p._on_save()
        self.assertEqual(self.applied[-1]["speaker"], 9)   # 保存でも apply
        self.assertEqual(self.persisted[-1]["speaker"], 9) # 永続化される

    def test_discard_reverts_fields_and_reapplies_baseline(self):
        p = self._panel({"speaker": 3, "base_url": "http://localhost:50021"})
        p._speaker.setValue(9)                  # 未保存の編集
        self.applied.clear()
        p._on_discard()
        self.assertEqual(p.get_config()["speaker"], 3)     # baseline に戻る
        self.assertEqual(self.applied[-1]["speaker"], 3)   # live も baseline に戻す

    def test_save_updates_baseline_so_discard_keeps_saved(self):
        p = self._panel({"speaker": 3, "base_url": "http://localhost:50021"})
        p._speaker.setValue(9)
        p._on_save()                            # baseline = 9
        p._speaker.setValue(1)
        p._on_discard()
        self.assertEqual(p.get_config()["speaker"], 9)     # 保存後の値に戻る


@unittest.skipUnless(HAS_PYSIDE6, "PySide6 未インストール")
class TestWindowApplyVoicevox(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_apply_voicevox_rebuilds_service_synth(self):
        from companion_core.console.state import ConsoleState
        from companion_core.console.service import ConsoleService
        from companion_core.supervisor import Supervisor
        from companion_settings.window import MainWindow
        svc = ConsoleService(Supervisor([]), ConsoleState(), synth=None, player=lambda w: None)
        win = MainWindow(cfg={}, console_service=svc)
        win._apply_voicevox({"speaker": 5, "base_url": "http://localhost:50021"})
        self.assertTrue(callable(svc.synth))    # synth が作り直されて差し替わる


if __name__ == "__main__":
    unittest.main()
