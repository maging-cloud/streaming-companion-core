import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import make_client_from_env, OpenAIClient, ENV_BASE, ENV_MODEL, ENV_KEY


class TestClientFromEnv(unittest.TestCase):
    def test_client_when_base_and_model(self):
        c = make_client_from_env({ENV_BASE: "http://x/v1", ENV_MODEL: "m", ENV_KEY: "k"})
        self.assertIsInstance(c, OpenAIClient)
        self.assertEqual(c.model, "m")

    def test_none_when_missing(self):
        self.assertIsNone(make_client_from_env({ENV_BASE: "http://x/v1"}))  # model 欠落
        self.assertIsNone(make_client_from_env({}))

    def test_base_url_stripped(self):
        c = make_client_from_env({ENV_BASE: "http://x/v1/", ENV_MODEL: "m"})
        self.assertEqual(c.base_url, "http://x/v1")


if __name__ == "__main__":
    unittest.main()
