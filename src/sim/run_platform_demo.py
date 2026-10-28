"""
Live demo of the family platform: the simulation runs (about real time) and writes the feed; the platform page shows it and can send commands back.

    MUJOCO_GL=glfw python src/sim/run_platform_demo.py --scenario medicine     then open http://127.0.0.1:8765 and sign in
    MUJOCO_GL=glfw python src/sim/run_platform_demo.py --scenario cardiac --sound
    options: --agent (Baymax as a Strands agent; uses ANTHROPIC_API_KEY / OLLAMA_HOST / AWS credentials if present, else offline wording)
             --consent (she agrees to face-blurred snapshots)   --pace 1.0 (simulated seconds per wall second, 0 = as fast as possible)
             --no-serve (write the feed only; start family_app/server.py yourself)

Scenarios (DEMO ONLY, not part of the measured experiment set):
    medicine  she sits on the sofa; at 08:00 Baymax reminds her, she says OK, and takes the tablet (hand to mouth): the family page shows 'taken, seen'
    cardiac   she walks, slows, presses a hand to her chest, hunches, collapses and does not answer: heads-up, emergency, the SIREN and Baymax's call for help
    fall      a plain trip that she answers (check-in, all clear)
Try on the page: talk to her, remind now, check on her, camera up / down, ask for a picture, silence the siren.
"""
import argparse
import json
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO_START = (-1.05, -1.10, 180.0)     # where the live demos start: from here the robot sees her fall side-on (the experiments start from random places)
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "family_app"))
for sub in ("experiments", "agent", "control", "sim"):
    sys.path.insert(0, os.path.join(ROOT, "src", sub))
import apartment_layout as L  # noqa: E402
import dispatch  # noqa: E402
import run_trial as RT  # noqa: E402
import scenarios as SC  # noqa: E402
import trial_setup as TS  # noqa: E402
from companion_agent import CompanionAgent, PlainVoice  # noqa: E402
from auth import Users  # noqa: E402
from feed import DEFAULT_DIR, FamilyFeed  # noqa: E402
from publisher import FamilyPublisher  # noqa: E402

BASE = dict(split="demo", seed=77, friction_scale=1.0, n_clutter=0, vacuum_speed=0.25, vacuum_phase=0.0, odom_noise=0.01, push=None, blackout=None,
            robot_start_mode="near", robot_start_seed=5)


def make_spec(name):
    if name == "medicine":
        return dict(BASE, id="demo_medicine", kind="adl", subtype="take_tablet", route="adl", path=SC.ROUTE_SOFA, speed=0.7, hold_s=60.0, intake_after_s=17.0,
                    conscious=True, reply_latency=4.0), (-1.05, -1.10, 150.0)
    if name == "cardiac":
        return dict(BASE, id="demo_cardiac", kind="fall", subtype="cardiac", route="bed_to_living", path=L.ROUTES["bed_to_living"].tolist(), speed=0.8,
                    prodrome_start_s=6.0, prodrome_s=9.0, chest_side="right", omega=0.6, tau=0.12, side=1.0, lateral=False, conscious=False, reply_latency=3.0), DEMO_START
    if name == "fall":
        return dict(BASE, id="demo_fall", kind="fall", subtype="trip", route="bed_to_living", path=L.ROUTES["bed_to_living"].tolist(), speed=0.75, fall_s=8.0,
                    omega=1.9, tau=0.45, conscious=True, reply_latency=4.5), DEMO_START
    raise ValueError(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", choices=["medicine", "cardiac", "fall"], default="medicine")
    ap.add_argument("--agent", action="store_true")
    ap.add_argument("--sound", action="store_true")
    ap.add_argument("--voice", action="store_true", help="speak what the robot says out loud (macOS text-to-speech, offline)")
    ap.add_argument("--consent", action="store_true")
    ap.add_argument("--pace", type=float, default=1.0)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--view", action="store_true", help="also open the live MuJoCo window (run with mjpython)")
    ap.add_argument("--no-serve", action="store_true")
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--max-t", type=float, default=120.0)
    ap.add_argument("--until-closed", action="store_true", help="do not stop when the scenario is over: run for up to 15 simulated minutes")
    a = ap.parse_args()

    spec, start = make_spec(a.scenario)
    clip = TS.clip_for(spec, os.path.join(ROOT, "outputs", "experiments", "clips_demo"))
    ctx = TS.TrialContext(spec, clip, [], start)
    feed = FamilyFeed(a.dir, reset=True)
    voice = CompanionAgent("Asha") if a.agent else PlainVoice()
    print("Baymax's voice:", getattr(voice, "mode", "plain wording"), flush=True)
    if a.scenario == "medicine":
        t_seat = clip.meta["t_event"] + 3.0
        reminder_at = t_seat + 3.0
        h = 8 * 3600 - int(reminder_at)
        dispatch.START_CLOCK = f"{h // 3600:02d}:{h // 60 % 60:02d}:{h % 60:02d}"          # the reminder lands on 08:00
    pcfg = {}
    pp = os.path.join(ROOT, "outputs", "experiments", "frozen_prodrome.json")
    if os.path.exists(pp):
        pcfg = json.load(open(pp))["prodrome_config"]
    params = dict(vertical_sweep=True, siren=True, cardiac_cues=True, prodrome_cfg=pcfg, snapshot_consent=a.consent)

    if not a.no_serve:
        from http.server import ThreadingHTTPServer
        import server as SV
        srv = ThreadingHTTPServer(("127.0.0.1", a.port), SV.make_handler(FamilyFeed(a.dir, reset=False), Users()))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        print(f"Family platform: http://127.0.0.1:{a.port}   sign in as rohan / rohan-demo (or meera / meera-demo, iyer / iyer-demo)", flush=True)

    pub, player, wall0 = [None], [None], time.time()
    siren_on = [False]

    def on_tick(t, comp, d, m, rb):
        if pub[0] is None:
            pub[0] = FamilyPublisher(feed, comp, agent=voice if a.agent else None, consent=a.consent)
        pub[0].tick(t, d, m)
        if a.voice and comp.on_speech is None:
            from speech import Speaker
            spk = Speaker()
            comp.on_speech = lambda text, loud=False: spk.say(text, urgent=loud)
            comp.introduce(t)                                   # Baymax says who he is before anything else happens
        if a.sound:
            on = comp.siren is not None and comp.siren["t_off"] is None
            if on and not siren_on[0]:
                from siren import SirenPlayer
                player[0] = SirenPlayer(); player[0].start()
            if not on and siren_on[0] and player[0]:
                player[0].stop()
            siren_on[0] = on
        if a.pace > 0:
            ahead = t / a.pace - (time.time() - wall0)
            if ahead > 0:
                time.sleep(ahead)

    def stop_when(t, comp):
        if a.until_closed:
            return False                                      # keep going so you can chat and give commands; close the MuJoCo window or press Ctrl-C to stop
        if a.scenario == "medicine":
            r = comp.reminder
            return r is not None and (r["t_taken_seen"] or r["t_missed"]) and t - (r["t_taken_seen"] or r["t_missed"]) > 12.0
        if comp.siren is not None and comp.siren["t_off"] is not None and t - comp.siren["t_off"] > 8.0:
            return True
        return comp.state == "WATCH" and comp.responded and t - comp.checkin_started_t > 25.0 if comp.checkin_started_t else False

    cfg = dict(wide_view=True, params=params, voice=voice, on_tick=on_tick, stop_when=stop_when, post_alert_s=1e9, view=a.view, t_end=900.0 if a.until_closed else None)      # stay in the emergency until the siren is silenced
    if a.scenario == "medicine":
        cfg["reminder_at"] = reminder_at
    out = os.path.join(ROOT, "outputs", "platform_demo_" + a.scenario)
    s = RT.run_robot(ctx, out, cfg)
    if pub[0] is not None:
        pub[0].tick(s["t_end"], None, None, force=True)
    if player[0]:
        player[0].stop()
    print("simulation finished; the family page keeps showing the last state (Ctrl-C to quit)", flush=True)
    print(json.dumps({k: s[k] for k in ("t_heads_up", "t_emergency", "t_ambulance", "reminder", "max_collision_force_N", "bytes_off_board_total")}, indent=1, default=str))
    if not a.no_serve:
        try:
            while True:
                if pub[0] is not None:
                    pub[0].idle(s["t_end"])                       # keep answering chat questions after the simulation has ended
                time.sleep(0.4)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
