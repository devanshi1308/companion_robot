"""
Logins for the family platform: each family member has their own username and password; the page and the API only work after signing in.

    users = Users(path)                     # config/family_users.json (password hashes only: PBKDF2-SHA256, random salt, 200k rounds)
    token = users.login("rohan", "...")     # None if wrong; 5 wrong tries lock that user out for 60 s
    user  = users.user_for(token)           # dict(id, display) or None

Demo accounts (made by `python family_app/auth.py`, passwords are for this demo only): rohan / rohan-demo, meera / meera-demo, iyer / iyer-demo.
Sessions live in memory (restarting the server signs everybody out) and travel in an HttpOnly, SameSite=Strict cookie.
This is demo-grade: no HTTPS, no password reset; do not expose it beyond this computer.
"""
import hashlib
import hmac
import json
import os
import secrets
import time

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DEFAULT_PATH = os.path.join(ROOT, "config", "family_users.json")
DEMO = [("rohan", "Rohan (son)", "rohan-demo"), ("meera", "Meera (daughter)", "meera-demo"), ("iyer", "Mrs. Iyer (neighbour)", "iyer-demo")]
ROUNDS = 200_000


def hash_password(pw, salt=None):
    salt = salt or secrets.token_bytes(16)
    return dict(salt=salt.hex(), hash=hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, ROUNDS).hex())


def make_demo_file(path=DEFAULT_PATH):
    users = [dict(id=u, display=d, **hash_password(pw)) for u, d, pw in DEMO]
    with open(path, "w") as f:
        json.dump(dict(_note="DEMO accounts only. Fictional people. Password hashes, no plain passwords.", users=users), f, indent=1)
    return path


class Users:
    def __init__(self, path=DEFAULT_PATH):
        if not os.path.exists(path):
            make_demo_file(path)
        self.users = {u["id"]: u for u in json.load(open(path))["users"]}
        self.sessions = {}                       # token -> user id
        self.fails = {}                          # user id -> (count, first_fail_time)

    def login(self, user, password):
        u = self.users.get(str(user).lower())
        now = time.time()
        n, t0 = self.fails.get(str(user).lower(), (0, now))
        if n >= 5 and now - t0 < 60:
            return None
        ok = False
        if u is not None:
            h = hashlib.pbkdf2_hmac("sha256", str(password).encode(), bytes.fromhex(u["salt"]), ROUNDS).hex()
            ok = hmac.compare_digest(h, u["hash"])
        else:
            hashlib.pbkdf2_hmac("sha256", b"x", b"y" * 16, ROUNDS)         # same work for unknown users (no timing hint)
        if not ok:
            self.fails[str(user).lower()] = (n + 1 if now - t0 < 60 else 1, t0 if now - t0 < 60 else now)
            return None
        self.fails.pop(u["id"], None)
        tok = secrets.token_urlsafe(24)
        self.sessions[tok] = u["id"]
        return tok

    def user_for(self, token):
        uid = self.sessions.get(token)
        return None if uid is None else dict(id=uid, display=self.users[uid]["display"])

    def logout(self, token):
        self.sessions.pop(token, None)


if __name__ == "__main__":
    print("wrote", make_demo_file())
    print("demo logins:", ", ".join(f"{u} / {p}" for u, _, p in DEMO))
