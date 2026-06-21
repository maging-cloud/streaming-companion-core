import unittest
from unittest import mock

from companion_core import registry


class _FakeHandler:
    persona = "P"
    fewshot = ""

    def build_user(self, payload):
        return ""

    def template(self, request):
        return ""


class _FakeEP:
    name = "shop"

    def load(self):
        return _FakeHandler


class _BrokenEP:
    name = "broken"

    def load(self):
        raise RuntimeError("boom")


class TestRegistry(unittest.TestCase):
    def setUp(self):
        registry._HANDLERS.clear()
        registry._discovered = False

    def test_register_and_get(self):
        h = _FakeHandler()
        registry.register("x", h)
        self.assertIs(registry.get_handler("x"), h)

    def test_unknown_raises(self):
        with mock.patch.object(registry.importlib.metadata, "entry_points", return_value=[]):
            with self.assertRaises(ValueError):
                registry.get_handler("nope")

    def test_discovery_loads_entry_point(self):
        with mock.patch.object(registry.importlib.metadata, "entry_points", return_value=[_FakeEP()]):
            h = registry.get_handler("shop")
        self.assertIsInstance(h, _FakeHandler)

    def test_register_precedes_discovery(self):
        sentinel = _FakeHandler()
        registry.register("shop", sentinel)
        with mock.patch.object(registry.importlib.metadata, "entry_points", return_value=[_FakeEP()]):
            self.assertIs(registry.get_handler("shop"), sentinel)

    def test_broken_plugin_ignored(self):
        with mock.patch.object(registry.importlib.metadata, "entry_points", return_value=[_BrokenEP()]):
            with self.assertRaises(ValueError):
                registry.get_handler("broken")


if __name__ == "__main__":
    unittest.main()
