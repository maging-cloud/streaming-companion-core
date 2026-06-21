"""ThreadingHTTPServer による console backend。安定 API を提供し静的 UI を配信する。

ロジックは ConsoleService に委譲。handler は薄い HTTP アダプタ。
  GET  /          静的 UI (index.html)
  GET  /state     現在状態 (JSON)
  GET  /events    SSE (状態変化を push)
  GET  /config    config (JSON)
  POST /control   {"action": start|stop|mute|unmute|replay}
  PUT  /config    config を保存
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_STATIC = Path(__file__).parent / "static"


def make_handler(service):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # noqa: A003 - ログ抑制
            pass

        def _json(self, obj, status=200):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_body(self):
            n = int(self.headers.get("Content-Length", 0))
            if not n:
                return {}
            return json.loads(self.rfile.read(n).decode("utf-8"))

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._serve_index()
            elif self.path == "/state":
                self._json(service.get_state())
            elif self.path == "/config":
                self._json(service.get_config())
            elif self.path == "/events":
                self._serve_events()
            else:
                self._json({"error": "not found"}, status=404)

        def do_POST(self):
            if self.path == "/control":
                try:
                    body = self._read_body()
                except Exception:
                    return self._json({"ok": False, "error": "bad json"}, status=400)
                self._json(service.control(body.get("action", "")))
            else:
                self._json({"error": "not found"}, status=404)

        def do_PUT(self):
            if self.path == "/config":
                try:
                    body = self._read_body()
                except Exception:
                    return self._json({"ok": False, "error": "bad json"}, status=400)
                self._json(service.put_config(body))
            else:
                self._json({"error": "not found"}, status=404)

        def _serve_index(self):
            try:
                data = (_STATIC / "index.html").read_bytes()
            except FileNotFoundError:
                data = b"<html><body>console UI missing</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _serve_events(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            q = service.state.subscribe()
            try:
                self._send_event(service.get_state())  # 接続直後に現状を 1 回
                while True:
                    snap = q.get()
                    self._send_event(snap)
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                service.state.unsubscribe(q)

        def _send_event(self, obj):
            payload = "event: state\ndata: " + json.dumps(obj) + "\n\n"
            self.wfile.write(payload.encode("utf-8"))
            self.wfile.flush()

    return Handler


def serve(service, host="127.0.0.1", port=8765):  # pragma: no cover - 実 runtime
    srv = ThreadingHTTPServer((host, port), make_handler(service))
    print(f"operator console: http://{host}:{port}")
    srv.serve_forever()


def main(argv=None):  # pragma: no cover - CLI 配線
    """workers を持たない core 単体起動 (UI/設定編集の確認用)。"""
    from ..supervisor import Supervisor
    from ..config import load_config
    from .state import ConsoleState
    from .service import ConsoleService
    from .playback import make_player

    cfg = load_config()
    console = cfg.get("console", {})
    svc = ConsoleService(Supervisor([]), ConsoleState(),
                         synth=None, player=make_player())
    serve(svc, console.get("host", "127.0.0.1"), int(console.get("port", 8765)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
