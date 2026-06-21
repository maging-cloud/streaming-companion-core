import threading
import unittest
from companion_core.supervisor import Worker, worker_loop, Supervisor


def _stop_after(n):
    """n イテレーション (sleeper 呼び出し n 回) で set される Event と sleeper を返す。"""
    stop = threading.Event()
    count = {"n": 0}
    def sleeper(_s):
        count["n"] += 1
        if count["n"] >= n:
            stop.set()
    return stop, sleeper


class _FakeThread:
    def __init__(self, target, name, daemon):
        self.target, self.name, self.daemon = target, name, daemon
        self.started = self.joined = False
        self._alive = False
    def start(self):
        self.started = True
        self._alive = True
        self.target()          # 同期実行 (テスト用)
        self._alive = False
    def join(self, timeout=None):
        self.joined = True
    def is_alive(self):
        return self._alive


class TestWorkerLoop(unittest.TestCase):
    def test_runs_tick_until_stop(self):
        calls = []
        stop, sleeper = _stop_after(3)      # 3 周回して止まる
        worker_loop(lambda: calls.append(1), 0.0, stop, sleeper=sleeper)
        self.assertEqual(len(calls), 3)

    def test_tick_exception_does_not_break_loop(self):
        calls = []
        def tick():
            calls.append(1)
            raise RuntimeError("boom")
        stop, sleeper = _stop_after(2)
        worker_loop(tick, 0.0, stop, sleeper=sleeper)
        self.assertEqual(len(calls), 2)     # 例外でも継続


class TestSupervisor(unittest.TestCase):
    def _spawn(self):
        made = []
        def spawn(target, name, daemon):
            t = _FakeThread(target, name, daemon)
            made.append(t)
            return t
        return spawn, made

    def test_start_spawns_one_thread_per_worker(self):
        spawn, made = self._spawn()
        ticks = []
        sup = Supervisor(
            [Worker("a", lambda: ticks.append("a"), 0.0)],
            spawn=spawn, sleeper=lambda s: None, max_ticks=2)
        sup.start()
        self.assertEqual(len(made), 1)
        self.assertTrue(made[0].started)
        self.assertEqual(ticks, ["a", "a"])

    def test_status_reports_names(self):
        spawn, made = self._spawn()
        sup = Supervisor(
            [Worker("a", lambda: None, 0.0), Worker("b", lambda: None, 0.0)],
            spawn=spawn, sleeper=lambda s: None, max_ticks=1)
        sup.start()
        names = [w["name"] for w in sup.status()]
        self.assertEqual(names, ["a", "b"])

    def test_stop_is_idempotent_and_sets_not_running(self):
        spawn, made = self._spawn()
        sup = Supervisor([Worker("a", lambda: None, 0.0)],
                         spawn=spawn, sleeper=lambda s: None, max_ticks=1)
        sup.start()
        sup.stop()
        sup.stop()
        self.assertFalse(sup.running)
        self.assertTrue(made[0].joined)


if __name__ == "__main__":
    unittest.main()
