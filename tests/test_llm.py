import unittest

from companion_core.llm import ENV_BASE, ENV_KEY, ENV_MODEL, OpenAIClient, make_client_from_env


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

    def test_legacy_bpb_prefix_fallback(self):
        """旧 BPB_LLM_* キーだけの env でも OpenAIClient が返る (後方互換 fallback)。"""
        env = {
            "BPB_LLM_BASE_URL": "http://legacy/v1",
            "BPB_LLM_API_KEY": "legacy-key",
            "BPB_LLM_MODEL": "legacy-model",
        }
        c = make_client_from_env(env)
        self.assertIsInstance(c, OpenAIClient)
        self.assertEqual(c.base_url, "http://legacy/v1")
        self.assertEqual(c.api_key, "legacy-key")
        self.assertEqual(c.model, "legacy-model")

    def test_new_prefix_precedence(self):
        """COMPANION_LLM_* と BPB_LLM_* が両方あるとき、COMPANION_LLM_* 側が優先される。"""
        env = {
            ENV_BASE: "http://new/v1",
            ENV_KEY: "new-key",
            ENV_MODEL: "new-model",
            "BPB_LLM_BASE_URL": "http://legacy/v1",
            "BPB_LLM_API_KEY": "legacy-key",
            "BPB_LLM_MODEL": "legacy-model",
        }
        c = make_client_from_env(env)
        self.assertIsInstance(c, OpenAIClient)
        self.assertEqual(c.base_url, "http://new/v1")
        self.assertEqual(c.api_key, "new-key")
        self.assertEqual(c.model, "new-model")


if __name__ == "__main__":
    unittest.main()
