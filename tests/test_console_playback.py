import os
import tempfile
import unittest
from companion_core.console.playback import make_player


class TestPlayer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "out.wav")

    def test_writes_wav_then_calls_popen_on_mac(self):
        calls = []
        player = make_player(play_path=self.path, platform="darwin",
                             popen=lambda args: calls.append(args))
        player(b"RIFFdata")
        self.assertTrue(os.path.exists(self.path))
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), b"RIFFdata")
        self.assertEqual(calls, [["afplay", self.path]])

    def test_linux_uses_aplay(self):
        calls = []
        player = make_player(play_path=self.path, platform="linux",
                             popen=lambda args: calls.append(args))
        player(b"x")
        self.assertEqual(calls, [["aplay", "-q", self.path]])

    def test_windows_uses_winsound(self):
        calls = []
        class _WS:
            SND_FILENAME = 1
            SND_ASYNC = 2
            def PlaySound(self, path, flags):
                calls.append((path, flags))
        player = make_player(play_path=self.path, platform="win32",
                             winsound_mod=_WS())
        player(b"x")
        self.assertEqual(calls, [(self.path, 1 | 2)])

    def test_empty_wav_is_noop(self):
        calls = []
        player = make_player(play_path=self.path, platform="darwin",
                             popen=lambda args: calls.append(args))
        player(b"")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
