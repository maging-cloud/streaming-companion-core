import unittest
from companion_core.comment import comment


class FakeHandler:
    persona = "ボク解説なのだ"
    fewshot = ""

    def build_user(self, payload):
        return f"top={payload.get('top')}"

    def template(self, request):
        return f"おすすめは {request['payload'].get('top')} なのだ"


class FakeClient:
    def __init__(self, text):
        self._text = text

    def complete(self, system, user):
        return self._text


REQ = {"kind": "shop", "payload": {"top": "Battery"}}


class TestComment(unittest.TestCase):
    def test_template_when_no_client(self):
        out = comment(REQ, FakeHandler(), client=None)
        self.assertIn("Battery", out)
        self.assertIn("のだ", out)

    def test_client_output_sanitized(self):
        out = comment(REQ, FakeHandler(), client=FakeClient("「やった」のだ😀"))
        self.assertNotIn("「", out)
        self.assertNotIn("😀", out)
        self.assertIn("のだ", out)

    def test_ng_not_in_output(self):
        out = comment(REQ, FakeHandler(), client=FakeClient("死ねなのだ"), ngwords=["死ね"])
        self.assertNotIn("死ね", out)
        self.assertIn("Battery", out)   # fallback=handler.template に Battery


if __name__ == "__main__":
    unittest.main()
