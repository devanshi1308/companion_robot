"""
Family platform: a small web page where signed-in family members see how she is, chat with Momo (the companion robot) and ask it to do things.

    python src/family_platform/server.py            then open http://127.0.0.1:8765 and sign in (start a simulation that writes the feed, see run_platform_demo.py)
    demo accounts: rohan / rohan-demo, meera / meera-demo, iyer / iyer-demo      (src/family_platform/auth.py)

What you can do after signing in: read how she is (room, what she is doing, last seen, tablet taken or not and whether the robot SAW it, alerts, the siren), read
the messages Momo sent YOU, chat with Momo (ask questions, ask it to remind her, check on her, tell her something, look up or down, send a picture, silence the
siren). Privacy: nothing works without signing in; each person sees only their own chat and the texts sent to them; there is no video stream; pictures only if
she agreed, face blurred; the server listens on this computer only. Standard library only. Demo-grade security (no HTTPS): do not expose it to a network.
"""
import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from auth import Users  # noqa: E402
from feed import DEFAULT_DIR, FamilyFeed  # noqa: E402
from publisher import LAYOUT  # noqa: E402

COMMANDS = {"say", "remind", "check", "look", "snapshot", "siren_off"}
COOKIE = "momo_session"


def make_handler(feed, users):
    page = open(os.path.join(HERE, "index.html"), "rb").read()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _user(self):
            c = SimpleCookie(self.headers.get("Cookie", ""))
            return users.user_for(c[COOKIE].value) if COOKIE in c else None

        def _send(self, code, body, ctype="application/json", headers=None):
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            try:
                n = int(self.headers.get("Content-Length", "0"))
                return json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return None

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/":
                return self._send(200, page, "text/html; charset=utf-8")
            me = self._user()
            if u.path == "/api/me":
                return self._send(200, dict(user=me))
            if me is None:
                return self._send(401, dict(error="please sign in"))
            if u.path == "/api/state":
                return self._send(200, feed.read_state() or dict(waiting=True))
            if u.path == "/api/layout":
                return self._send(200, LAYOUT)
            if u.path == "/api/events":
                since = int(parse_qs(u.query).get("since", ["0"])[0])
                out = []
                for e in feed.read_events(since):
                    if e["type"] == "chat" and e.get("user") != me["id"]:
                        continue                                    # other people's chats are private
                    if e["type"] == "sent" and e.get("to") != me["display"]:
                        continue                                    # texts that went to somebody else
                    out.append(e)
                n_all = since + len(feed.read_events(since))
                return self._send(200, dict(events=out, next=n_all))
            if u.path == "/api/snapshot":
                view = parse_qs(u.query).get("view", [None])[0]
                if view not in (None, "ahead", "above", "below", "emergency"):
                    return self._send(400, dict(error="unknown view"))
                p = feed.snapshot_path(view)
                if os.path.exists(p):
                    return self._send(200, open(p, "rb").read(), "image/png")
                return self._send(404, dict(error="no snapshot"))
            return self._send(404, dict(error="not found"))

        def do_POST(self):
            u = urlparse(self.path)
            req = self._body()
            if req is None:
                return self._send(400, dict(error="bad json"))
            if u.path == "/api/login":
                tok = users.login(req.get("user", ""), req.get("password", ""))
                if tok is None:
                    return self._send(401, dict(error="wrong username or password (5 wrong tries lock the account for a minute)"))
                return self._send(200, dict(user=users.user_for(tok)), headers={"Set-Cookie": f"{COOKIE}={tok}; HttpOnly; SameSite=Strict; Path=/"})
            me = self._user()
            if u.path == "/api/logout":
                c = SimpleCookie(self.headers.get("Cookie", ""))
                if COOKIE in c:
                    users.logout(c[COOKIE].value)
                return self._send(200, dict(ok=True), headers={"Set-Cookie": f"{COOKIE}=; Max-Age=0; Path=/"})
            if me is None:
                return self._send(401, dict(error="please sign in"))
            if u.path == "/api/chat":
                text = str(req.get("text", "")).strip()
                if not text:
                    return self._send(400, dict(error="empty message"))
                feed.send_chat(me["id"], text)
                return self._send(200, dict(ok=True))
            if u.path == "/api/command":
                if req.get("cmd") not in COMMANDS:
                    return self._send(400, dict(error="unknown command"))
                feed.send_command(req["cmd"], req.get("args"), who=me["id"])
                return self._send(200, dict(ok=True))
            return self._send(404, dict(error="not found"))

    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--dir", default=DEFAULT_DIR)
    a = ap.parse_args()
    feed = FamilyFeed(a.dir, reset=False)
    srv = ThreadingHTTPServer((a.host, a.port), make_handler(feed, Users()))
    print(f"Family platform on http://{a.host}:{a.port}  (feed: {a.dir}). Demo logins: rohan / rohan-demo, meera / meera-demo, iyer / iyer-demo", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
