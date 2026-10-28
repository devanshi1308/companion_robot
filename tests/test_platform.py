"""
Checks for the family platform, the siren and the medicine-taking motion (no simulation run needed).
Run:  python tests/test_platform.py
"""
import json
import os
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import mujoco
import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "family_app"))
for sub in ("agent", "sim", "experiments", "control"):
    sys.path.insert(0, os.path.join(ROOT, "src", sub))
from feed import FamilyFeed  # noqa: E402
import server as SV  # noqa: E402
import siren as SI  # noqa: E402


def test_feed_round_trip_and_command_queue():
    d = tempfile.mkdtemp()
    f = FamilyFeed(d)
    f.write_state(dict(t=1.5, robot=dict(name="Baymax")))
    f.add_event(type="momo", text="hello")
    f.add_event(type="sent", text="text")
    g = FamilyFeed(d, reset=False)                      # the server's view
    assert g.read_state()["t"] == 1.5 and [e["n"] for e in g.read_events(0)] == [0, 1] and len(g.read_events(1)) == 1
    g.send_command("say", dict(text="hi"))
    g.send_command("look", dict(direction="up"))
    got = f.new_commands()
    assert [c["cmd"] for c in got] == ["say", "look"] and f.new_commands() == []     # each command is delivered once


def _serve(feed):
    import auth
    d = tempfile.mkdtemp()
    users = auth.Users(os.path.join(d, "users.json"))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), SV.make_handler(feed, users))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def _req(base, path, body=None, cookie=None):
    r = urllib.request.Request(base + path, None if body is None else json.dumps(body).encode(), {"Content-Type": "application/json", **({"Cookie": cookie} if cookie else {})})
    try:
        resp = urllib.request.urlopen(r)
        return resp.status, resp.read(), resp.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers


def _login(base, user, pw):
    code, body, hdr = _req(base, "/api/login", dict(user=user, password=pw))
    return code, (hdr.get("Set-Cookie") or "").split(";")[0]


def test_nothing_works_without_signing_in_and_wrong_passwords_are_refused():
    feed = FamilyFeed(tempfile.mkdtemp())
    feed.write_state(dict(t=1.0))
    srv, base = _serve(feed)
    try:
        assert b"Family view" in _req(base, "/")[1]                                    # the page itself (it shows the sign-in form)
        for path in ("/api/state", "/api/events", "/api/layout", "/api/snapshot?view=above"):
            assert _req(base, path)[0] == 401, path
        assert _req(base, "/api/command", dict(cmd="say", args={"text": "x"}))[0] == 401
        assert _req(base, "/api/chat", dict(text="hi"))[0] == 401
        assert _login(base, "rohan", "wrong")[0] == 401 and _login(base, "nobody", "x")[0] == 401
        code, cookie = _login(base, "rohan", "rohan-demo")
        assert code == 200 and cookie.startswith("momo_session=")
        assert json.loads(_req(base, "/api/state", cookie=cookie)[1])["t"] == 1.0
        assert _req(base, "/api/command", dict(cmd="open_the_door"), cookie)[0] == 400
        assert _req(base, "/api/command", dict(cmd="say", args={"text": "hello"}), cookie)[0] == 200 and feed.new_commands()[0]["who"] == "rohan"
        _req(base, "/api/logout", {}, cookie)
        assert _req(base, "/api/state", cookie=cookie)[0] == 401                      # signed out
    finally:
        srv.shutdown()


def test_five_wrong_passwords_lock_the_account_for_a_minute():
    srv, base = _serve(FamilyFeed(tempfile.mkdtemp()))
    try:
        for _ in range(5):
            assert _login(base, "meera", "nope")[0] == 401
        assert _login(base, "meera", "meera-demo")[0] == 401                          # locked, even with the right password
    finally:
        srv.shutdown()


def test_each_person_sees_only_their_own_chat_and_texts():
    feed = FamilyFeed(tempfile.mkdtemp())
    feed.add_event(type="chat", who="user", user="rohan", text="private to rohan", t=1)
    feed.add_event(type="chat", who="momo", user="meera", text="private to meera", t=2)
    feed.add_event(type="sent", to="Rohan (son)", kind="heads_up", text="for rohan", t=3)
    feed.add_event(type="sent", to="Meera (daughter)", kind="heads_up", text="for meera", t=3)
    feed.add_event(type="momo", text="spoken to her", t=4)
    srv, base = _serve(feed)
    try:
        _, cookie = _login(base, "rohan", "rohan-demo")
        texts = [e["text"] for e in json.loads(_req(base, "/api/events?since=0", cookie=cookie)[1])["events"]]
        assert texts == ["private to rohan", "for rohan", "spoken to her"], texts
    finally:
        srv.shutdown()


def test_chat_goes_to_the_simulation_with_the_signed_in_name():
    feed = FamilyFeed(tempfile.mkdtemp())
    srv, base = _serve(feed)
    try:
        _, cookie = _login(base, "meera", "meera-demo")
        assert _req(base, "/api/chat", dict(text="has she taken her tablet?"), cookie)[0] == 200
        assert _req(base, "/api/chat", dict(text="   "), cookie)[0] == 400
        got = feed.new_chats()
        assert len(got) == 1 and got[0]["user"] == "meera" and "tablet" in got[0]["text"] and feed.new_chats() == []
    finally:
        srv.shutdown()


def test_momo_answers_from_the_facts_and_acts_on_requests():
    import chat
    f = dict(patient="Asha", person=dict(room="living room", posture="sitting", seen_now=True), alert=dict(title="All well", emergency=False),
             doses=[dict(label="your 8 o'clock tablet", status="taken", clock_taken="08:00:14", clock_due="08:00:01", welfare=False)], robot=dict(feeling=dict(label="happy")))
    r, a = chat.answer("Has she taken her tablet?", f)
    assert "08:00:14" in r and a == []
    f["doses"][0]["status"] = "missed"
    assert "did not answer" in chat.answer("did she take her medicine", f)[0]
    r, a = chat.answer("where is she?", f)
    assert "living room" in r and "sitting" in r
    r, a = chat.answer("tell her dinner is at seven", f)
    assert a == [dict(cmd="say", args=dict(text="dinner is at seven"))]
    assert chat.answer("remind her", f)[1][0]["cmd"] == "remind" and chat.answer("go and check on her", f)[1][0]["cmd"] == "check"
    assert chat.answer("look around", f)[1][0]["args"]["view"] == "both"
    r, a = chat.answer("call 108", f)
    assert a == [] and "cannot place calls" in r                                        # it never places a call on request
    assert chat.answer("silence the siren", f)[1] == []                                 # nothing to silence


def test_above_and_below_pictures_have_their_own_files_and_unknown_views_are_refused():
    from PIL import Image
    d = tempfile.mkdtemp()
    feed = FamilyFeed(d)
    feed.write_snapshot(Image.new("RGB", (8, 8), (200, 0, 0)), "above")
    feed.write_snapshot(Image.new("RGB", (8, 8), (0, 0, 200)), "below")
    srv, base = _serve(feed)
    try:
        _, ck = _login(base, "rohan", "rohan-demo")
        assert _req(base, "/api/snapshot?view=above", cookie=ck)[1][:4] == b"\x89PNG"
        assert _req(base, "/api/snapshot?view=below", cookie=ck)[0] == 200
        assert _req(base, "/api/snapshot?view=../../etc/passwd", cookie=ck)[0] == 400       # an unknown view must be refused
        assert _req(base, "/api/snapshot", cookie=ck)[0] == 404                             # no plain snapshot was taken
    finally:
        srv.shutdown()


def test_siren_signal_and_levels():
    x = SI.synth_siren(2.0)
    assert x.dtype == np.float32 and abs(x).max() <= 0.51 and len(x) == 2 * SI.SR
    spec = np.abs(np.fft.rfft(x))
    f = np.fft.rfftfreq(len(x), 1 / SI.SR)
    peak = f[np.argmax(spec)]
    assert 600 < peak < 1000, peak                        # the two tones sit around 650 and 950 Hz
    assert abs(SI.level_at(1.0) - 95) < 1e-6 and abs(SI.level_at(2.0) - 89) < 0.1 and SI.level_at(2.0, wall_loss_db=25) < 65
    print(f"  siren: strongest component {peak:.0f} Hz; 60 dB out to {SI.distance_for_level(60):.0f} m open, {SI.distance_for_level(60, wall_loss_db=25):.1f} m behind one closed door")


def test_taking_a_tablet_brings_the_hand_to_the_mouth():
    import human_motion as HM
    import motions as M
    m = mujoco.MjModel.from_xml_path(os.path.join(ROOT, "models", "scene_with_human.xml"))
    rig = HM.Rig(m)
    sv = M._sites(m)
    spec = dict(kind="adl", subtype="take_tablet", path=[(-2.2, -1.3), (-2.2, 0.55), (-1.0, 0.55), M.SOFA_STAND], speed=0.7, hold_s=5.0, intake_after_s=6.0, seed=1)
    clip = M.make_clip(m, rig, spec)
    best = 9.0
    for t in np.arange(clip.meta["t_intake"] - 0.5, clip.meta["t_intake"] + 4.0, 0.1):
        rig.d.qpos[rig.sl_q] = clip.at(t)
        mujoco.mj_kinematics(m, rig.d)
        X = rig.d.site_xpos
        best = min(best, np.linalg.norm(X[sv[16]] - 0.5 * (X[sv[9]] + X[sv[10]])))
    print(f"  closest wrist-to-mouth distance while taking the tablet: {best * 100:.1f} cm")
    assert best < 0.08


def test_open_questions_go_to_the_model_or_get_an_honest_answer():
    import chat
    import companion_agent as CA
    assert chat.answer("what is the capital of France?", dict(patient="Asha"))[0].startswith(chat.FALLBACK)        # no built-in answer -> the agent is asked
    r = chat.answer("she has chest pain, what do I do", dict(patient="Asha", alert=dict(title="All well")))[0]
    assert "call 108" in r.lower()                                                                                # urgent symptoms never wait for a model
    v = CA.CompanionAgent("Asha", model=None)
    assert v.open_chat("rohan", "tell me a joke", {}) is None                                                     # offline: no model, so the page says so
    class Fake:
        def __init__(self): self.msgs = []
        def __call__(self, t): self.msgs.append(t); return "Paris is the capital of France."
    v.model = object()
    v._chats["rohan"] = Fake()
    assert v.open_chat("rohan", "what is the capital of France?", {"x": 1}) == "Paris is the capital of France."
    v._chats["rohan"] = lambda t: "She is having a heart attack."                                                  # a diagnosis is rejected
    assert v.open_chat("rohan", "is she ok?", {}) is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
