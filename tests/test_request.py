import unittest
from companion_core.request import make_request


class TestMakeRequest(unittest.TestCase):
    def test_builds_kind_payload(self):
        r = make_request("shop", {"round": 3})
        self.assertEqual(r["kind"], "shop")
        self.assertEqual(r["payload"], {"round": 3})


if __name__ == "__main__":
    unittest.main()
