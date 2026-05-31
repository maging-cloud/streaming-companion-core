import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry


class TestRegistry(unittest.TestCase):
    def setUp(self):
        registry._HANDLERS.clear()

    def test_register_and_get(self):
        h = object()
        registry.register("shop", h)
        self.assertIs(registry.get_handler("shop"), h)

    def test_unknown_raises(self):
        with self.assertRaises(ValueError):
            registry.get_handler("nope")


if __name__ == "__main__":
    unittest.main()
