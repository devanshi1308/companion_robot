"""
Medicine-reminder demo (DEMO ONLY: reminders are outside the authorised scope of the project and are not part of any measured result).

She walks to the sofa and sits down; at a scheduled time the robot drives to a standoff about 1 m from her, shows a pill icon and says
"It is time for your 8 o'clock tablet", waits for her OK (a voice reply, modelled), repeats louder after 15 s and, if she never
acknowledges (30 s), sends the family a text (never an emergency call).

    MUJOCO_GL=glfw python src/sim/run_reminder_demo.py            (she acknowledges)
    MUJOCO_GL=glfw python src/sim/run_reminder_demo.py --missed   (she does not)
Output: outputs/reminder_demo[_missed]/{demo.gif, events_robot.json, alerts.json}
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "experiments"))
import run_trial as RT  # noqa: E402
import scenarios as SC  # noqa: E402
import trial_setup as TS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--missed", action="store_true", help="she does not acknowledge the reminder")
    ap.add_argument("--no-gif", action="store_true")
    a = ap.parse_args()
    spec = dict(id="reminder_demo", split="demo", seed=77, kind="adl", subtype="sit_sofa_slow", route="adl", path=SC.ROUTE_SOFA, speed=0.7, hold_s=45.0,
                friction_scale=1.0, n_clutter=0, vacuum_speed=0.25, vacuum_phase=0.0, odom_noise=0.01, push=None, blackout=None,
                conscious=not a.missed, reply_latency=5.0, robot_start_mode="near", robot_start_seed=5)
    out = os.path.join(ROOT, "outputs", "reminder_demo_missed" if a.missed else "reminder_demo")
    os.makedirs(out, exist_ok=True)
    ctx = TS.prepare(spec, os.path.join(ROOT, "outputs", "experiments", "clips_demo"))
    t_sit = ctx.clip.meta["t_event"] + 3.0
    s = RT.run_robot(ctx, out, dict(reminder_at=t_sit + 4.0, gif=not a.no_gif, gif_every=2, stop_after_reminder=True))
    print(json.dumps(s["reminder"], indent=1))
    ev = json.load(open(os.path.join(out, "events_robot.json")))["events"]
    for t, text in ev:
        print(f"  {t:6.2f}s  {text}")


if __name__ == "__main__":
    main()
