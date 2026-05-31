import unittest
from unittest.mock import MagicMock, patch


class TestDiscoverSettingsPanels(unittest.TestCase):
    def test_returns_empty_when_no_entry_points(self):
        from companion_settings.registry import discover_settings_panels
        with patch("importlib.metadata.entry_points", return_value=[]):
            panels = discover_settings_panels()
        self.assertEqual(panels, [])

    def test_returns_instantiated_panel(self):
        from companion_settings.registry import discover_settings_panels

        class FakePanel:
            section_id = "fake"
            label = "Fake"

        ep = MagicMock()
        ep.load.return_value = FakePanel
        with patch("importlib.metadata.entry_points", return_value=[ep]):
            panels = discover_settings_panels()
        self.assertEqual(len(panels), 1)
        self.assertEqual(panels[0].section_id, "fake")

    def test_skips_broken_plugin(self):
        from companion_settings.registry import discover_settings_panels

        bad_ep = MagicMock()
        bad_ep.load.side_effect = ImportError("broken")
        with patch("importlib.metadata.entry_points", return_value=[bad_ep]):
            panels = discover_settings_panels()
        self.assertEqual(panels, [])


class TestDiscoverHandlerKinds(unittest.TestCase):
    def test_returns_kind_names(self):
        from companion_settings.registry import discover_handler_kinds

        ep1, ep2 = MagicMock(), MagicMock()
        ep1.name, ep2.name = "shop", "chat"
        with patch("importlib.metadata.entry_points", return_value=[ep1, ep2]):
            kinds = discover_handler_kinds()
        self.assertEqual(sorted(kinds), ["chat", "shop"])

    def test_returns_empty_when_none(self):
        from companion_settings.registry import discover_handler_kinds
        with patch("importlib.metadata.entry_points", return_value=[]):
            self.assertEqual(discover_handler_kinds(), [])


if __name__ == "__main__":
    unittest.main()
