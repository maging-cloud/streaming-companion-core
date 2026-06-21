import unittest

from companion_core.orchestrator import SpeechGate


class _Clock:
    """注入用の手動クロック (monotonic 秒)。"""

    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


class TestSpeechGate(unittest.TestCase):
    def test_first_score_speaks(self):
        self.assertTrue(SpeechGate(clock=_Clock()).should_speak(score=0.5))

    def test_small_delta_within_cooldown_silent(self):
        clk = _Clock()
        g = SpeechGate(min_interval=5.0, score_delta=0.1, clock=clk)
        self.assertTrue(g.should_speak(score=0.5))
        clk.advance(1.0)
        self.assertFalse(g.should_speak(score=0.52))

    def test_large_delta_still_waits_for_cooldown(self):
        clk = _Clock()
        g = SpeechGate(min_interval=5.0, score_delta=0.1, clock=clk)
        self.assertTrue(g.should_speak(score=0.1))
        clk.advance(1.0)
        self.assertFalse(g.should_speak(score=0.9))

    def test_large_delta_after_cooldown_speaks(self):
        clk = _Clock()
        g = SpeechGate(min_interval=5.0, score_delta=0.1, clock=clk)
        self.assertTrue(g.should_speak(score=0.1))
        clk.advance(6.0)
        self.assertTrue(g.should_speak(score=0.9))

    def test_small_delta_after_cooldown_still_silent(self):
        clk = _Clock()
        g = SpeechGate(min_interval=5.0, score_delta=0.1, clock=clk)
        self.assertTrue(g.should_speak(score=0.5))
        clk.advance(10.0)
        self.assertFalse(g.should_speak(score=0.51))

    def test_important_kind_bypasses_cooldown(self):
        clk = _Clock()
        g = SpeechGate(min_interval=60.0, important_kinds=("battle_lost",), clock=clk)
        self.assertTrue(g.should_speak(score=0.5))
        clk.advance(1.0)
        self.assertTrue(g.should_speak(kind="battle_lost"))

    def test_force_bypasses_everything(self):
        clk = _Clock()
        g = SpeechGate(min_interval=60.0, clock=clk)
        self.assertTrue(g.should_speak(score=0.5))
        clk.advance(0.1)
        self.assertTrue(g.should_speak(score=0.5, force=True))

    def test_speaking_resets_cooldown_and_baseline(self):
        clk = _Clock()
        g = SpeechGate(min_interval=5.0, score_delta=0.1, clock=clk)
        self.assertTrue(g.should_speak(score=0.1))
        clk.advance(6.0)
        self.assertTrue(g.should_speak(score=0.5))
        clk.advance(1.0)
        self.assertFalse(g.should_speak(score=0.55))

    def test_silent_call_does_not_update_baseline(self):
        clk = _Clock()
        g = SpeechGate(min_interval=5.0, score_delta=0.1, clock=clk)
        self.assertTrue(g.should_speak(score=0.5))
        clk.advance(1.0)
        self.assertFalse(g.should_speak(score=0.55))
        clk.advance(6.0)
        self.assertTrue(g.should_speak(score=0.62))


if __name__ == "__main__":
    unittest.main()
