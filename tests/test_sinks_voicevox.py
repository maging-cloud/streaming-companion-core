import io
import json
import os
import tempfile
import unittest
from companion_core.sinks.voicevox import VoicevoxSink, DEFAULT_BASE_URL


class _FakeResp(io.BytesIO):
    """urlopen 戻り値を模した context manager。"""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
        return False


class _FakeOpener:
    """urllib.request.urlopen 差し替え。リクエストを記録し順に応答を返す。"""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def __call__(self, req, timeout=None):
        self.calls.append((req.full_url, req.get_method(), req.data, timeout))
        return _FakeResp(self._responses.pop(0))


def _opener():
    query = json.dumps({"accent_phrases": [], "speedScale": 1.0}).encode("utf-8")
    wav = b"RIFF....fakewav"
    return _FakeOpener([query, wav])


class TestVoicevoxSink(unittest.TestCase):
    def test_synthesize_returns_wav_bytes(self):
        opener = _opener()
        wav = VoicevoxSink(speaker=3, opener=opener).synthesize("こんにちは")
        self.assertEqual(wav, b"RIFF....fakewav")
        self.assertEqual(len(opener.calls), 2)
        q_url, q_method, _q_data, _ = opener.calls[0]
        self.assertIn("/audio_query", q_url)
        self.assertIn("speaker=3", q_url)
        self.assertIn("text=", q_url)
        self.assertEqual(q_method, "POST")
        s_url, s_method, s_data, _ = opener.calls[1]
        self.assertIn("/synthesis", s_url)
        self.assertIn("speaker=3", s_url)
        self.assertEqual(s_method, "POST")
        self.assertEqual(json.loads(s_data.decode("utf-8"))["speedScale"], 1.0)

    def test_call_invokes_player_and_returns_wav(self):
        played = []
        out = VoicevoxSink(opener=_opener(), player=played.append)("テスト")
        self.assertEqual(out, b"RIFF....fakewav")
        self.assertEqual(played, [b"RIFF....fakewav"])

    def test_call_saves_wav_when_save_path(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "out.wav")
            VoicevoxSink(opener=_opener(), save_path=p)("テスト")
            with open(p, "rb") as f:
                self.assertEqual(f.read(), b"RIFF....fakewav")

    def test_default_base_url(self):
        self.assertEqual(DEFAULT_BASE_URL, "http://localhost:50021")
        self.assertEqual(VoicevoxSink().base_url, "http://localhost:50021")

    def test_base_url_trailing_slash_stripped(self):
        self.assertEqual(VoicevoxSink(base_url="http://host:50021/").base_url,
                         "http://host:50021")


if __name__ == "__main__":
    unittest.main()
