import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from companion_core.supervisor import Supervisor, Worker
from companion_core.console.state import ConsoleState
from companion_core.console.service import ConsoleService
from companion_core.console.backend import make_handler


class _Noop:
    def start(self): pass
    def join(self, timeout=None): pass
    def is_alive(self): return True


def _make_server():
    sup = Supervisor([Worker("a", lambda: None, 0.0)],
                     spawn=lambda target, name, daemon: _Noop(),
                     sleeper=lambda s: None, max_ticks=0)
    svc = ConsoleService(sup, ConsoleState(), synth=lambda t: b"WAV",
                         player=lambda w: None, clock=lambda: 1.0)
    handler = make_handler(svc)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, svc


def _get(srv, path):
    port = srv.server_address[1]
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
        return r.status, r.read()


def _post(srv, path, obj):
    port = srv.server_address[1]
    data = json.dumps(obj).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, json.loads(r.read())


class TestBackend(unittest.TestCase):
    def setUp(self):
        self.srv, self.svc = _make_server()
        self.addCleanup(self.srv.shutdown)

    def test_index_served(self):
        status, body = _get(self.srv, "/")
        self.assertEqual(status, 200)
        self.assertIn(b"<html", body.lower())

    def test_state_json(self):
        status, body = _get(self.srv, "/state")
        self.assertEqual(status, 200)
        snap = json.loads(body)
        self.assertIn("running", snap)

    def test_control_start(self):
        status, res = _post(self.srv, "/control", {"action": "start"})
        self.assertEqual(status, 200)
        self.assertTrue(res["ok"])
        self.assertTrue(res["state"]["running"])

    def test_control_unknown_action(self):
        status, res = _post(self.srv, "/control", {"action": "nope"})
        self.assertFalse(res["ok"])

    def test_404_unknown_path(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            _get(self.srv, "/no-such")
        self.assertEqual(cm.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
