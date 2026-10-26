"""
The companion robot's behaviour: watch -> (fall suspected) approach -> check in -> alert the family.

  WATCH     sits on its dock, head scanning / tracking her. Face: cyan eyes.
  APPROACH  fall suspected: plan a route to a standoff pose about 1.0 m from her (preferably beside her body, where the
            pose estimator sees best), follow it, brake for anything the range sensor finds. Face: worried (amber).
  CHECK_IN  face her, ask "Are you okay?" (again after 5 s), watch for any movement. Face: worried.
  ALERT     she did not respond: message the family with a blurred snapshot, call the ambulance, keep watching and send
            updates. Face: red.
If she gets up or answers, the alarm is cancelled and nothing is sent beyond the text-only heads-up.

Everything the robot "knows" comes from its own sensors: camera + depth (via MediaPipe), wheel odometry, a simulated
range sensor (rays at 5 cm height). The simulator's ground truth is only used for logging.
"""
import os
import sys

import mujoco
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ("robot", "sim", "vision", "agent"):
    sys.path.insert(0, os.path.join(HERE, "..", sub))
import robot_spec as S  # noqa: E402
import apartment_layout as L  # noqa: E402
from dispatch import blur_face, clock  # noqa: E402
from localization import Localizer  # noqa: E402
from first_aid import CONSCIOUS_CHECK, CONSCIOUS_OK, BYSTANDER  # noqa: E402
from health_knowledge import COACH  # noqa: E402
from script import INTRO, LINES  # noqa: E402
from navigation import PathFollower, turn_to, wrap  # noqa: E402
from robot_interface import quat_to_yaw  # noqa: E402
from companion_agent import PlainVoice  # noqa: E402

LIDAR_GROUPS = np.array([1, 0, 0, 1, 1, 0], dtype=np.uint8)      # furniture + colliders + her body (not skins / full-height wall copies)
LIDAR_ANGLES = np.radians(np.arange(-60, 61, 10))
LIDAR_RANGE = 2.0
STANDOFF_LO, STANDOFF_HI = 0.95, 1.10      # m: range-sensor distance to her at which the robot stops (standards: 0.8 to 1.2 m)


class Params:
    follow = False             # companion mode: keep her in view by following her around the flat
    follow_dist = 1.3          # m: where the robot tries to stay behind her
    follow_near = 1.0
    follow_far = 1.6           # m: start driving when she is farther than this
    follow_vmax = 0.8          # standards manual: at most 0.80 m/s among people
    follow_replan_s = 0.4
    patrol_s = 8.0             # waiting on the dock / not seeing her this long: go and look for her (patrol)
    lost_s = 2.5               # not seen for this long: go and look for her
    regain_s = 0.6             # seen steadily for this long again: back to following
    checkin_s = 10.0
    reprompt_s = 5.0
    stop_range = 0.25          # m: brake if something the map does not know (her body, a moving obstacle) is this close straight ahead
    resume_range = 0.35
    wall_stop_range = 0.07     # m: known walls/furniture: the planner already keeps clear, brake only if a collision is imminent
    blocked_replan_s = 1.5     # blocked this long: treat the blocker as an obstacle and re-route
    replan_s = 0.5
    update_every_s = 15.0
    move_thresh_m = 0.35       # "she moved": hip moved this far from where she lay when the check-in began ...
    move_pitch_deg = 35.0      # ... or the torso angle changed this much, for this long:
    move_hold_s = 1.0
    approach_timeout_s = 40.0
    vertical_sweep = True      # while looking around, nod the camera up and down (the guide's robot looks from 1.15 m: a person on the floor is far below the horizon)
    siren = False              # collapse + no answer: sound a loud alarm to attract people (family-platform demo; off in the measured experiments)
    siren_level_db = 95.0      # sound level at 1 m
    siren_cardiac_db = 100.0   # ... when a chest-clutch pattern was seen just before the collapse
    siren_max_s = 180.0
    cardiac_cues = False       # run the pre-collapse cue monitor (src/vision/prodrome.py) and mention a chest-clutch pattern in the alert
    snapshot_consent = False   # the patient allows a face-blurred snapshot to be sent to the family on request


class Companion:
    def __init__(self, m, d, robot, grid, observer, detector, dispatcher, params=None, voice=None):
        self.voice = voice if voice is not None else PlainVoice()      # the agent that phrases everything the robot says (src/agent)
        self.checkin_started_t = None
        self.look_override = None            # (until_t, tilt_deg): the family asked the camera to look up / down
        self.siren = None                    # dict(t_on, level_db, cardiac_cue, t_off, reason) while / after a siren
        self.prodrome = None
        self.snapshot_request = False
        self.family_snapshot = None
        self.look_plan = []                  # pictures the family asked for above / below: [dict(view, tilt, t0)]
        self.family_views = {}               # view -> (PIL image, t): face-blurred pictures from the up / down camera views
        self.last_utterance = None
        self.utterances = []                 # (t, kind, text) everything the robot said or texted, for the family platform
        self.commands_done = []
        self.m, self.d, self.rb, self.grid = m, d, robot, grid
        self.observer, self.detector, self.disp = observer, detector, dispatcher
        self.p = params or Params()
        if self.p.cardiac_cues:
            from prodrome import ProdromeMonitor
            self.prodrome = ProdromeMonitor(**getattr(self.p, 'prodrome_cfg', {}))
        self.state = "WATCH"
        self.on_event = None                  # optional callback (t, text), e.g. print
        self.events = []                      # (t, text)
        self.screen_text = ""
        self.obs, self.t_seen = None, -99.0
        self.person_hip = None                # last known hip position (world, estimated)
        self.person_axis = np.array([0.0, 1.0])
        self.hip_track = []
        self.body_hist = []                  # (t, (33, 3) world landmarks with NaN where invalid)
        self.follower, self.goal, self.dyn = None, None, []        # dyn = [(x, y, r, expires)]
        self.t_replan = 0.0
        self.t_state = 0.0
        self.t_impact = None
        self.t_alert = None
        self.t_update = None
        self.sent_heads_up = False
        self.coach_i = 0
        self.introduced = False
        self.on_speech = None                          # set by a live demo to speak the robot's words aloud (src/agent/speech.py); experiments leave it None
        self.front_range = LIDAR_RANGE
        self.front_unknown = self.front_known = LIDAR_RANGE
        self.blocked = False
        self.baseline = None
        self.still_since = None
        self.moved_since = None
        self.snapshot = None
        self.pan_cmd, self.tilt_cmd = 0.0, 0.0
        self.responded = False
        self.purpose = "fall"                 # "fall" (check-in after a fall) or "reminder" (medicine reminder, demo only: outside the authorised scope)
        self.reminder = None                 # dict(label, t_due, t_ack, t_missed)
        self.suppress = False                 # she answered or moved: do not raise the same alarm again until the detector sees her up
        self.following = False
        self.seen_run = None
        self.search_goal = None
        self.search_phase = "goto"
        self.search_visited = set()
        self.t_scan = 0.0
        self.t_follow_replan = -9.0
        self.last_v = 0.0
        self.timed_out = False
        self.person_range = None
        self.fine_since = None
        self.blocked_since = 0.0
        self.front_hit = None
        self.loc = Localizer(m, grid)
        self.t_loc = -9.0
        self.pose_corrections = 0
        self.bad_fit = 0
        self.bad_wide = 0
        self.force_global = False
        self.stuck_since = None
        self.recover = None                  # (until_t, v, w): a short manoeuvre to get free of a wall
        self.body_ids = {m.body(n).id for n in ("robot", "wheel_l", "wheel_r", "robot_neck", "robot_head")}
        self.set_mood("watching")

    # ---- small helpers ------------------------------------------------------------------------
    def say(self, t, text):
        self.events.append((round(float(t), 2), text))
        if self.on_event is not None:
            self.on_event(round(float(t), 2), text)

    def set_mood(self, mood):
        self.rb.set_mood(mood)

    def feel(self, t, event):
        """Something happened that Baymax (the agent) reacts to emotionally; the robot's face follows its feelings."""
        self.voice.feel(t, event)
        m = self.voice.mood()
        if m:
            self.set_mood(m)

    def utter(self, t, kind, facts, default, audience="patient", loud=False):
        """The robot speaks (or texts): the agent decides the wording, the simulator decides the facts."""
        text = self.voice.phrase(kind, facts, default, audience=audience, t=t)
        self.say(t, f'Robot says{" (louder)" if loud else ""}: "{text}"')
        self.last_utterance = (t, kind, text)
        self.utterances.append((round(float(t), 2), kind, text))
        if self.on_speech is not None and audience in ("patient", "bystander"):
            self.on_speech(text, loud)
        return text

    def speak_fixed(self, t, kind, text, audience="patient", loud=False):
        """A fixed, reviewed script (first aid): never re-worded by the language model."""
        self.say(t, f'Robot says{" (louder)" if loud else ""}: "{text}"')
        self.last_utterance = (t, kind, text)
        self.utterances.append((round(float(t), 2), kind, text))
        if self.on_speech is not None:
            self.on_speech(text, loud)
        return text

    def introduce(self, t):
        """Baymax introduces himself once (a live demo calls this when the voice is on)."""
        if not self.introduced:
            self.introduced = True
            self.speak_fixed(t, "introduction", INTRO)

    def go(self, t, state, mood=None, text=None):
        self.state, self.t_state = state, t
        if mood:
            self.set_mood(mood)
            vm = self.voice.mood()
            if vm:
                self.set_mood(vm)                                  # with the agent the face shows Baymax's feelings, not a fixed mood per state
        if text is not None:
            self.screen_text = text

    # ---- range sensor ------------------------------------------------------------------------
    def scan(self, t):
        """Simulated range sensor: rays at 5 cm height over +/-60 deg. Unknown hits become temporary obstacles."""
        true = self.rb.true_pose()
        est = self.rb.est
        gid = np.zeros(1, dtype=np.int32)
        rmin_front, front_hit = LIDAR_RANGE, None
        unknown = []
        f_unknown = f_known = LIDAR_RANGE
        for a in LIDAR_ANGLES:
            th = true[2] + a
            org = np.array([true[0] + S.LIDAR_X * np.cos(true[2]), true[1] + S.LIDAR_X * np.sin(true[2]), S.LIDAR_Z])
            vec = np.array([np.cos(th), np.sin(th), 0.0])
            r = mujoco.mj_ray(self.m, self.d, org, vec, LIDAR_GROUPS, 1, self.m.body("robot").id, gid)
            if r < 0 or r > LIDAR_RANGE:
                continue
            r_tot = r + S.LIDAR_X
            hit = np.array([est[0] + r_tot * np.cos(est[2] + a), est[1] + r_tot * np.sin(est[2] + a)])
            i, j = self.grid.to_cell(*hit)
            near_known = self.grid.clear_low[max(i - 2, 0):i + 3, max(j - 2, 0):j + 3].min() < 0.08
            if abs(a) <= np.radians(15):
                rmin_front = min(rmin_front, r)
                front_hit = (r, a)
                if near_known:
                    f_known = min(f_known, r)
                else:
                    f_unknown = min(f_unknown, r)
            if not near_known and gid[0] >= 0 and self.m.geom_bodyid[gid[0]] not in self.body_ids:
                unknown.append((a, r_tot))
                c = hit + 0.15 * vec[:2]                                   # centre of a disc-shaped thing behind the hit point
                self.dyn = [x for x in self.dyn if np.hypot(x[0] - c[0], x[1] - c[1]) > 0.25] + [(c[0], c[1], 0.17, t + 1.5)]
        self.dyn = [x for x in self.dyn if x[3] > t]
        # her body shows up as hits the static map does not know: its distance in the forward fan is the personal-space reading
        near = [r for a, r in unknown if abs(a) <= np.radians(40)]
        self.person_range = min(near) if near else None
        self.front_range = rmin_front
        self.front_unknown, self.front_known = f_unknown, f_known
        self.front_hit = None if front_hit is None else np.array([est[0] + (front_hit[0] + S.LIDAR_X) * np.cos(est[2] + front_hit[1]), est[1] + (front_hit[0] + S.LIDAR_X) * np.sin(est[2] + front_hit[1])])

    # ---- perception tick (about 31 Hz) -------------------------------------------------------
    def update_perception(self, t, rgb, depth):
        pan, tilt = self.rb.neck_angles_deg()
        obs = self.observer.observe(rgb, depth, self.rb.est, pan, tilt)
        if obs is not None and obs.hip is not None and not (L.X0 - 0.3 < obs.hip[0] < L.X1 + 0.3 and L.Y0 - 0.3 < obs.hip[1] < L.Y1 + 0.3):
            obs = None                                          # a 'person' outside the flat (seen through a window or a depth error) is not her
        self.obs = obs
        if obs is not None and obs.hip is not None:
            self.t_seen = t
            self.person_hip = obs.hip.copy()
            ax = obs.body_axis_xy()
            if ax is not None:
                self.person_axis = ax
            self.hip_track.append((t, obs.hip.copy(), obs.torso_pitch_deg()))
            self.hip_track = [h for h in self.hip_track if t - h[0] < 6.0]
            ok = obs.valid & (obs.vis > 0.3)
            lm = obs.world.copy()
            lm[~ok] = np.nan
            self.body_hist.append((t, lm))
            self.body_hist = [b for b in self.body_hist if t - b[0] < 1.0]
        self.watch_medicine(t, obs)
        if self.prodrome is not None:
            self.prodrome.update(t, obs)
        if self.snapshot_request:
            self.serve_snapshot(t, rgb, obs)
        if self.look_plan:
            self.step_look_plan(t, rgb, obs)
        det_state = self.detector.update(t, obs)
        if det_state == "normal":
            self.suppress = False
        if obs is not None and obs.hip is not None:
            self.seen_run = self.seen_run if self.seen_run is not None else t
        elif t - self.t_seen > 0.4:
            self.seen_run = None
        lying = self.detector.lying_since is not None and t - self.detector.lying_since >= 0.5        # low and horizontal for half a second
        standing = obs is not None and obs.hip is not None and self.detector.features.get("hip_z", 0) > 0.55
        if self.p.follow and det_state == "normal" and self.state in ("FOLLOW", "SEARCH", "WATCH", "OBSERVE") and lying and t - self.t_seen < 0.3:
            if self.state != "OBSERVE":
                self.say(t, "She is on the floor: stopping to see whether she moves")
                self.feel(t, "she_is_on_the_floor")
                self.go(t, "OBSERVE", "worried", "Are you hurt?")
            self.follower, self.following = None, False
        elif self.state == "OBSERVE" and det_state == "normal" and standing and self.seen_run is not None and t - self.seen_run > self.p.regain_s and not lying:
            self.say(t, "She is up again: following her")
            self.feel(t, "she_got_up")
            self.go(t, "FOLLOW", "watching", "")
        elif self.state == "OBSERVE" and det_state == "normal" and t - self.t_seen > self.p.lost_s:
            self.go(t, "SEARCH", "worried", "Where are you?")
            self.search_goal = None
        elif self.p.follow and det_state == "normal" and self.person_hip is not None and t - self.t_seen < 0.3 and self.state in ("WATCH", "SEARCH") \
                and standing and self.seen_run is not None and t - self.seen_run > self.p.regain_s:
            self.go(t, "FOLLOW", "watching", "")
            self.say(t, "Following her")
            self.search_goal = None
        elif self.state == "FOLLOW" and t - self.t_seen > self.p.lost_s:
            self.say(t, "Lost sight of her: going to where I last saw her")
            self.feel(t, "lost_sight")
            self.go(t, "SEARCH", "worried", "Where are you?")
            self.search_goal = None
        elif self.p.follow and self.state == "WATCH" and det_state == "normal" and not (lying and t - self.t_seen < 3.0) and t - max(self.t_seen, self.t_state) > self.p.patrol_s:
            self.say(t, "Have not seen her for a while: looking for her")
            self.go(t, "SEARCH", "watching", "Where are you?")
            self.search_goal = None

        if self.state in ("WATCH", "FOLLOW", "SEARCH", "OBSERVE") and det_state in ("suspect", "confirmed") and not self.suppress:
            self.t_impact = self.detector.t_impact
            self.say(t, ("Fall suspected: " if det_state == "suspect" else "Person down: ") + self.detector.log[-1][1])
            self.feel(t, "fall_suspected" if det_state == "suspect" else "fall_confirmed")
            if det_state == "confirmed":
                self.begin_approach(t)                     # found lying: nothing to wait for
            else:
                self.go(t, "SUSPECT", "worried", "Did you fall?")         # watch her settle before planning a route
        elif self.state == "SUSPECT":
            if det_state == "confirmed":
                self.begin_approach(t)
            elif det_state == "normal":
                self.say(t, "Alarm cancelled: " + (self.detector.log[-1][1] if self.detector.log else "false alarm"))
                self.cancel(t)
        elif self.state in ("APPROACH", "CHECK_IN") and det_state == "normal" and self.t_impact is not None:
            self.say(t, "Alarm cancelled: " + (self.detector.log[-1][1] if self.detector.log else "she recovered"))
            self.cancel(t)
        if self.siren is not None and self.siren["t_off"] is None and self.state == "ALERT" and det_state == "normal":
            self.stop_siren(t, "she is up again")
        if det_state == "confirmed" and not self.sent_heads_up and self.person_hip is not None:
            self.sent_heads_up = True
            self.disp.heads_up(t, self.person_hip[:2], self.detector.t_impact)
            self.say(t, "Family told (text only): possible fall, robot is checking")
        if self.state == "CHECK_IN" and self.purpose == "fall":
            self.watch_for_response(t)
        if self.state == "ALERT" and obs is not None and self.snapshot is None:
            self.take_snapshot(rgb, obs)

    def begin_approach(self, t):
        self.go(t, "APPROACH", "worried", "I'm coming to check on you")
        self.fine_since = None
        self.plan_route(t, first=True)

    def person_estimate(self):
        """Her position now: hip = median of the last second of hip estimates; body points = per-landmark median over the
        last second (a single mis-placed landmark must not decide where it is safe to drive)."""
        hips = [h[1] for h in self.hip_track[-30:]]
        hip = np.median(np.array(hips), axis=0) if hips else self.person_hip
        pts = None
        if self.body_hist:
            stack = np.stack([b[1] for b in self.body_hist])                  # (frames, 33, 3)
            with np.errstate(all="ignore"):
                med = np.nanmedian(stack, axis=0)
            med = med[np.isfinite(med).all(1)]
            pts = med[:, :2] if len(med) else None
        return hip, pts

    def plan_route(self, t, first=False):
        """First call: choose a standoff pose and a route. Later calls: only re-route to the same goal around moving obstacles."""
        est = self.rb.est
        hip, pts = self.person_estimate()
        # her body (as estimated) is an obstacle too: never plan through or next to her
        body_discs = [] if pts is None else [(x, y, 0.30) for x, y in pts]
        discs = [(x, y, r) for x, y, r, _ in self.dyn] + body_discs
        if first or self.goal is None:
            self.person_hip = hip
            target = self.grid.choose_standoff(hip[:2], self.person_axis, est[:2], body_xy=pts, extra_discs=discs)
            if target is None:
                if os.environ.get("COMPANION_DEBUG"):
                    blk = self.grid.blocked(discs)
                    st = self.grid.to_cell(*est[:2])
                    print("DEBUG standoff None: est", np.round(est, 2), "hip", np.round(hip, 2), "n pts", None if pts is None else len(pts),
                          "pts x", None if pts is None else (round(pts[:, 0].min(), 2), round(pts[:, 0].max(), 2)), "y", None if pts is None else (round(pts[:, 1].min(), 2), round(pts[:, 1].max(), 2)),
                          "start blocked", bool(blk[st]), "discs", len(discs))
                    cost, _ = self.grid._dijkstra(blk, self.grid._nearest_free(blk, st))
                    print("DEBUG reachable cells", int(np.isfinite(cost).sum()))
                self.say(t, "No free spot next to her: checking from here")
                self.follower, self.goal = None, None
                return
            x, y, heading, path = target
            self.goal = (x, y, heading)
            self.timed_out = False
            nearest = float(np.min(np.hypot(pts[:, 0] - x, pts[:, 1] - y))) if pts is not None else float("nan")
            far = np.hypot(x - est[0], y - est[1])
            self.say(t, f"Standoff chosen at ({x:.2f}, {y:.2f}): {nearest:.2f} m from her nearest body point, {far:.1f} m away")
            if far < 0.35:
                self.follower = None
                return
        else:
            path = self.grid.plan(est[:2], self.goal[:2], extra_discs=discs)
            if path is None:
                return
            x, y, _ = self.goal
        self.follower = PathFollower(path)
        self.t_replan = t

    def cancel(self, t):
        self.follower, self.goal = None, None
        self.rb.set_drive(0, 0)
        self.go(t, "WATCH", "happy", "")
        self.t_impact = None
        self.sent_heads_up = False

    # ---- response monitoring ---------------------------------------------------------------
    def watch_for_response(self, t):
        """Has she moved? Judged only while the robot itself stands still (its own motion changes the viewpoint and with it
        every landmark estimate): the baseline is the median pose over the first still second, the test compares the
        median of the last second with it."""
        if self.obs is None or self.obs.hip is None:
            return
        v, w = self.rb.last_cmd
        still = abs(v) < 0.02 and abs(w) < 0.1 and abs(self.rb.true_velocity()[0]) < 0.03 and abs(self.rb.true_velocity()[1]) < 0.1
        if not still:
            self.still_since = None
            return
        self.still_since = self.still_since if self.still_since is not None else t
        recent = [h for h in self.hip_track if t - h[0] <= 1.0 and h[0] >= self.still_since]
        if len(recent) < 12:
            return
        hip = np.median(np.array([h[1] for h in recent]), axis=0)
        pitches = [h[2] for h in recent if h[2] is not None]
        pitch = float(np.median(pitches)) if pitches else 0.0
        if self.baseline is None:
            self.baseline = (hip, pitch)
            return
        moved = np.linalg.norm(hip - self.baseline[0]) > self.p.move_thresh_m or abs(pitch - self.baseline[1]) > self.p.move_pitch_deg
        if moved:
            self.moved_since = self.moved_since or t
            if t - self.moved_since >= self.p.move_hold_s:
                self.say(t, "She moved: response detected, no emergency call")
                self.speak_fixed(t, "first_aid_get_up_slowly", CONSCIOUS_OK)
                self.feel(t, "she_answered")
                self.responded = True
                self.suppress = True
                self.disp.all_clear(t)
                self.go(t, "WATCH", "happy", "Glad you're okay!")
        else:
            self.moved_since = None

    def hear_reply(self, t):
        """The microphone picked up her voice (the experiment harness decides whether she answered and could be heard)."""
        if self.state == "CHECK_IN" and self.purpose == "reminder":
            self.say(t, 'She answered ("OK"): ' + ("check-in answered" if self.reminder.get("welfare") else "reminder acknowledged"))
            self.reminder["status"] = "acknowledged"
            self.feel(t, "reminder_acknowledged")
            self.reminder["t_ack"] = t
            self.purpose = "fall"
            self.go(t, "WATCH", "happy", "Thank you!")
            return True
        if self.state == "CHECK_IN":
            self.say(t, 'She answered ("I\'m fine"): response heard, no emergency call')
            self.speak_fixed(t, "first_aid_get_up_slowly", CONSCIOUS_OK)
            self.feel(t, "she_answered")
            self.responded = True
            self.suppress = True
            self.disp.all_clear(t)
            self.go(t, "WATCH", "happy", "Glad you're okay!")
            return True
        return False

    def watch_medicine(self, t, obs):
        """After a reminder: did the robot SEE her take it? A hand held at the mouth (wrist within 15 cm of the mouth landmarks) for a few frames."""
        r = self.reminder
        if r is None or r.get("welfare") or r["t_taken_seen"] is not None or r["t_missed"] is not None or obs is None:
            return
        if t - r["t_due"] > 150.0 or (r["t_ack"] is not None and t - r["t_ack"] > 90.0):
            if r["status"] == "acknowledged" and not r.get("reported"):
                r["reported"] = True
                self.disp.medicine_report(t, r["label"], "acknowledged")
                self.say(t, "Tablet: she said OK but the robot did not see her take it: family told by text")
            return
        mouth = [obs.world[i] for i in (9, 10) if obs.valid[i] and obs.vis[i] > 0.3]
        wrists = [obs.world[i] for i in (15, 16) if obs.valid[i] and obs.vis[i] > 0.3]
        if mouth and wrists:
            near = min(np.linalg.norm(w - np.mean(mouth, axis=0)) for w in wrists) < 0.15
            r["hand_to_mouth"] = r["hand_to_mouth"] + 1 if near else 0
            if r["hand_to_mouth"] >= 5:
                r["t_taken_seen"], r["status"] = t, "taken"
                self.say(t, "Tablet: the robot saw her take it (hand to mouth)")
                self.feel(t, "tablet_taken")
                self.disp.medicine_report(t, r["label"], "taken")
                if self.purpose == "reminder" and self.state in ("APPROACH", "CHECK_IN"):
                    self.purpose = "fall"
                    self.go(t, "WATCH", "happy", "Thank you!")

    def take_snapshot(self, rgb, obs):
        """One picture for the family, face blurred: centred on the face landmarks, sized from the ear (or shoulder) spacing."""
        face = [i for i in range(11) if obs.vis[i] > 0.3]
        if not face:
            return
        centre = obs.pix[face].mean(0)
        if obs.vis[7] > 0.3 and obs.vis[8] > 0.3:
            radius = 0.9 * np.linalg.norm(obs.pix[7] - obs.pix[8])
        elif obs.vis[11] > 0.3 and obs.vis[12] > 0.3:
            radius = 0.45 * np.linalg.norm(obs.pix[11] - obs.pix[12])
        else:
            radius = 25.0
        self.snapshot = blur_face(rgb, centre, max(radius, 18.0))

    # ---- control tick (50 Hz) -------------------------------------------------------------------
    def update_control(self, t, dt):
        rb = self.rb
        rb.update_odometry()
        if t - self.t_loc >= 0.25:                                   # state estimation: odometry corrected by matching the range scan to the map
            self.t_loc = t
            ranges = self.loc.scan(self.d, rb.true_pose())
            new, info = self.loc.correct(rb.est, ranges)
            if info["applied"]:
                rb.est = new
                self.pose_corrections += 1
            c0 = self.loc.cost(rb.est, ranges)
            lost = c0 is not None and c0[np.argmin(np.hypot(self.loc.off[:, 0], self.loc.off[:, 1]) + np.abs(self.loc.off[:, 2]))] > 0.03
            self.bad_fit = self.bad_fit + 1 if lost else 0
            if self.bad_fit >= 3 or self.force_global:                  # the map and the scan still disagree: search wider (after a bump)
                if not self.force_global:
                    new, info = self.loc.wide().correct(rb.est, ranges)
                    if info["applied"]:
                        rb.est = new
                        self.pose_corrections += 1
                        self.say(t, f"Re-localised after a bump (moved my estimate {info['shift_m']:.2f} m)")
                    c1 = self.loc.cost(rb.est, ranges)
                    still_lost = c1 is None or c1[np.argmin(np.hypot(self.loc.off[:, 0], self.loc.off[:, 1]) + np.abs(self.loc.off[:, 2]))] > 0.03
                    self.bad_wide = self.bad_wide + 1 if still_lost else 0
                    self.bad_fit = 0
                if self.force_global or self.bad_wide >= 4:             # still lost: search the whole flat at every heading
                    res = self.loc.global_search(rb.est, ranges)
                    cur = self.loc.cost(rb.est, ranges)
                    c_cur = None if cur is None else float(cur[np.argmin(np.hypot(self.loc.off[:, 0], self.loc.off[:, 1]) + np.abs(self.loc.off[:, 2]))])
                    # trust the jump only if it is a much better fit than where I think I am (her body in the scan also raises the cost)
                    if res is not None and res[1] < 0.02 and (c_cur is None or res[1] < 0.4 * c_cur):
                        rb.est = res[0]
                        self.pose_corrections += 1
                        self.say(t, "Lost: found my position again by matching the scan against the whole map")
                    self.bad_fit = self.bad_wide = 0
                    self.force_global = False
        self.scan(t)
        est = rb.est
        v, w = 0.0, 0.0
        if self.state == "OBSERVE":
            if self.person_hip is not None:
                e = wrap(np.arctan2(self.person_hip[1] - est[1], self.person_hip[0] - est[0]) - est[2])
                w = float(np.clip(1.5 * e, -1.0, 1.0)) if abs(e) > np.radians(40) else 0.0
        elif self.state == "FOLLOW":
            v, w = self.follow_control(t, dt)
        elif self.state == "SEARCH":
            v, w = self.search_control(t, dt)
        elif self.state == "APPROACH":
            if t - self.t_state > self.p.approach_timeout_s and not self.timed_out:
                self.timed_out = True
                self.say(t, "Approach timed out: checking from here")
                self.follower = None
            if self.follower is not None and not self.follower.done:
                if self.dyn and t - self.t_replan > self.p.replan_s:
                    self.plan_route(t)
                self.brake_check(t)
                if self.blocked and t - self.blocked_since > self.p.blocked_replan_s and self.front_hit is not None:
                    self.dyn.append((self.front_hit[0], self.front_hit[1], 0.12, t + 6.0))       # something in the way: go around it
                    self.say(t, "Blocked ahead: re-routing around it")
                    self.blocked_since = t + 99
                    self.plan_route(t)
                v, w = self.follower.command(est, dt, stop=self.blocked) if self.follower is not None else (0.0, 0.0)
                v = min(v, self.clear_speed(est))
            else:
                hip = self.person_hip
                heading = np.arctan2(hip[1] - est[1], hip[0] - est[0])
                w, e = turn_to(est, heading)
                if abs(e) < np.radians(6):
                    w = 0.0
                    self.fine_since = self.fine_since if self.fine_since is not None else t
                    pr = self.person_range
                    if pr is None or t - self.fine_since > 8.0:
                        self.begin_check_in(t)                       # cannot measure her distance: stay here
                    elif pr > STANDOFF_HI:
                        if self.free_for_creep(est, +0.18):
                            v = 0.12                               # creep closer until the range sensor says about 1 m
                        else:
                            self.begin_check_in(t)                 # the map says a table leg or wall is in the way: check on her from here
                    elif pr < STANDOFF_LO:
                        v = -0.10 if self.free_for_creep(est, -0.18) else 0.0         # too close: back off (only if the space behind is free)
                    else:
                        self.begin_check_in(t)
        elif self.state in ("CHECK_IN", "ALERT"):
            hip = self.person_hip
            if hip is not None:
                w, e = turn_to(est, np.arctan2(hip[1] - est[1], hip[0] - est[0]), k=1.5, w_max=0.6)
                w = 0.0 if abs(e) < np.radians(5) else w
            if self.state == "CHECK_IN":
                self.run_check_in(t)
            else:
                self.run_alert(t)
        # recovery: wedged against something (commanded to move but not moving): back off, turn, and find my position again
        if self.recover:
            until, rv, rw = self.recover[0]
            if t < until:
                v, w = rv, rw
            else:
                self.recover.pop(0)
                if self.recover:
                    self.recover[0] = (t + self.recover[0][0], self.recover[0][1], self.recover[0][2])
        else:
            wants_move = self.state == "SEARCH" or (self.state == "FOLLOW" and self.following) or (self.state == "APPROACH" and self.follower is not None and not self.follower.done)
            if wants_move and abs(v) < 0.02 and abs(w) < 0.1:
                self.stuck_since = self.stuck_since if self.stuck_since is not None else t
                if t - self.stuck_since > 3.5:
                    self.say(t, "Stuck: backing off, turning and re-checking my position")
                    self.recover = [(t + 1.2, -0.12, 0.0), (1.0, 0.0, 1.0)]
                    self.follower, self.search_goal, self.force_global, self.stuck_since = None, None, True, None
                    self.search_phase = "goto"
            else:
                self.stuck_since = None
        rb.set_drive(v, w)
        self.last_v = v
        self.drive_neck(t, dt)

    # ---- companion behaviour: follow her, look for her ------------------------------------------
    def clear_speed(self, est):
        """Speed limit from the free space around the robot on the map: slow down near furniture legs, doorframes and walls (thin legs are easy to clip
        when the robot turns), full speed in open floor."""
        i, j = self.grid.to_cell(est[0], est[1])
        c = float(self.grid.clear[min(max(i, 0), self.grid.nx - 1), min(max(j, 0), self.grid.ny - 1)])
        v = 0.15 + 2.0 * max(c - S.CHASSIS_R, 0.0)
        return min(v, S.BUBBLE_V) if c < S.BUBBLE else v

    def free_for_creep(self, est, dist):
        """Is the spot `dist` metres ahead (+) or behind (-) the robot clear of mapped obstacles for the robot's full footprint? The range sensor alone misses
        thin table legs beside the beam, and the last metre is driven reactively."""
        p = est[:2] + dist * np.array([np.cos(est[2]), np.sin(est[2])])
        i, j = self.grid.to_cell(p[0], p[1])
        return float(self.grid.clear[i, j]) >= S.CHASSIS_R + 0.02

    def brake_check(self, t):
        """Brake for something the map does not know about close ahead, or for any obstacle about to be hit."""
        was = self.blocked
        margin = 0.10 if self.blocked else 0.0                                      # hysteresis
        self.blocked = (self.front_unknown < self.p.stop_range + margin) or (self.front_known < self.p.wall_stop_range + 0.12 * abs(self.last_v) + margin)
        if self.blocked and not was:
            self.blocked_since = t
        return self.blocked

    def follow_control(self, t, dt):
        est = self.rb.est
        P = self.person_hip[:2]
        E = est[:2]
        d = float(np.hypot(*(P - E)))
        bearing = np.arctan2(P[1] - E[1], P[0] - E[0])
        if d > self.p.follow_far:
            self.following = True
        elif d <= self.p.follow_dist + 0.15:
            self.following = False
        if not self.following:
            self.follower = None
            e = wrap(bearing - est[2])
            w = float(np.clip(1.5 * e, -1.2, 1.2)) if abs(e) > np.radians(30) else 0.0   # keep facing her
            return 0.0, w
        if self.follower is None or t - self.t_follow_replan > self.p.follow_replan_s:
            self.t_follow_replan = t
            u = (E - P) / max(d, 1e-6)
            goal = P + u * self.p.follow_dist                                          # on her side of the room, behind her
            discs = [(x, y, r) for x, y, r, _ in self.dyn]
            gi = self.grid._nearest_free(self.grid.blocked(discs), self.grid.to_cell(*goal))
            path = self.grid.plan(E, self.grid.to_xy(*gi), extra_discs=discs) if gi is not None else None
            if path is not None and len(path) >= 2:
                v_max = float(np.clip(0.35 + 0.5 * (d - self.p.follow_dist), 0.35, self.p.follow_vmax))
                self.follower = PathFollower(path, v_max=v_max, a=1.2, v0=self.last_v)
        if self.follower is None:
            return 0.0, 0.0
        v, w = self.follower.command(est, dt, stop=self.brake_check(t))
        return min(v, self.clear_speed(est)), w

    def search_control(self, t, dt):
        """Lost her: (1) go where she was heading, (2) scan on the spot, (3) tour the rooms until she is seen again."""
        est = self.rb.est
        discs = [(x, y, r) for x, y, r, _ in self.dyn]
        if self.search_goal is None:
            last = self.person_hip[:2] if self.person_hip is not None else est[:2]
            vel = np.zeros(2)
            if len(self.hip_track) >= 2:
                (ta, a, _), (tb, b, _) = self.hip_track[0], self.hip_track[-1]
                vel = (b[:2] - a[:2]) / max(tb - ta, 0.5)
            self.search_visited = set()
            target = last + vel * 2.0
            if np.hypot(*(target - last)) < 1.2:                 # never drive right up to her while she is only out of sight for a moment
                u = est[:2] - last
                target = last + u / max(np.hypot(*u), 1e-6) * 1.2
            self.start_search_leg(t, target, "where she was heading")
        if self.search_phase == "goto":
            if self.follower is not None and not self.follower.done:
                v, w = self.follower.command(est, dt, stop=self.brake_check(t))
                return min(v, self.clear_speed(est)), w
            self.search_phase, self.t_scan = "scan", t
        if self.search_phase == "scan":
            yaw_true = self.rb.true_pose()[2]
            if t - self.t_scan < 1e-6 or not hasattr(self, "scan_ref"):
                self.scan_ref = (t, yaw_true, 0.0)
            t0, last, turned = self.scan_ref
            turned += abs(wrap(yaw_true - last))
            self.scan_ref = (t0, yaw_true, turned)
            stalled = (t - t0) > 1.0 and turned < 0.25 * (t - t0)                        # wheels turn but the body does not: it is jammed on something
            if stalled and (t - self.t_scan) < 5.0:
                self.say(t, "Stuck while turning on the spot: skipping the look-around")
                self.t_scan = t - 5.0
            elif t - self.t_scan < 5.0:
                i, j = self.grid.to_cell(est[0], est[1])
                tight = float(self.grid.clear[min(max(i, 0), self.grid.nx - 1), min(max(j, 0), self.grid.ny - 1)]) < S.CHASSIS_R + 0.12
                if tight:                                                                # too close to furniture to swing the corners round: look with the camera only
                    if t - self.t_scan > 2.0:
                        self.t_scan = t - 5.0
                    return 0.0, 0.0
                return 0.0, 0.8                                                          # turn on the spot and look around
            here = est[:2]
            cands = [(np.hypot(x - here[0], y - here[1]), n, (x, y)) for n, (x, y) in L.WAYPOINTS.items()
                     if n not in self.search_visited and np.hypot(x - here[0], y - here[1]) > 0.8]
            if not cands:
                self.search_visited = set()
                cands = [(np.hypot(x - here[0], y - here[1]), n, (x, y)) for n, (x, y) in L.WAYPOINTS.items() if np.hypot(x - here[0], y - here[1]) > 0.8]
            _, name, xy = min(cands)
            self.search_visited.add(name)
            self.start_search_leg(t, np.array(xy), name.replace("wp_", "the ").replace("_", " "))
        return 0.0, 0.0

    def start_search_leg(self, t, target, label):
        discs = [(x, y, r) for x, y, r, _ in self.dyn]
        gi = self.grid._nearest_free(self.grid.blocked(discs), self.grid.to_cell(*target))
        self.search_goal = self.grid.to_xy(*gi) if gi is not None else tuple(self.rb.est[:2])
        path = self.grid.plan(self.rb.est[:2], self.search_goal, extra_discs=discs)
        self.follower = PathFollower(path, v_max=0.6, a=1.2, v0=self.last_v) if path is not None and len(path) >= 2 else None
        self.search_phase = "goto"
        self.say(t, f"Searching: going to {label}")

    def start_reminder(self, t, label="your 8 o'clock tablet", welfare=False):
        """Medicine reminder (demo-only extra): drive to her, show it on the screen, say it, wait for her to acknowledge."""
        if self.person_hip is None or self.state not in ("WATCH", "FOLLOW", "SEARCH"):
            return False
        self.purpose = "reminder"
        self.reminder = dict(label=label, t_due=t, t_ack=None, t_missed=None, t_taken_seen=None, status="due", hand_to_mouth=0, welfare=welfare)
        self.say(t, f"Reminder due: {label}")
        self.feel(t, "reminder_due")
        self.follower = self.goal = None
        self.begin_approach(t)
        self.go(t, "APPROACH", "happy", "Hello!" if welfare else "Time for your tablet")
        return True

    def begin_check_in(self, t):
        if self.purpose == "reminder":
            self.go(t, "CHECK_IN", "happy", "How are you?" if self.reminder.get("welfare") else "Time for your tablet")
            if self.reminder.get("welfare"):
                self.utter(t, "welfare_check", {}, "Your family asked me to say hello. How are you feeling?")
            else:
                self.utter(t, "reminder", dict(label=self.reminder["label"]), f'It is time for {self.reminder["label"]}. Please take it and say OK.')
            self.reprompted = False
            return
        self.go(t, "CHECK_IN", "worried", "Are you okay?")
        self.checkin_started_t = t
        self.feel(t, "checking_in")
        self.utter(t, "check_in", {}, LINES["check_in"])
        self.speak_fixed(t, "first_aid_stay_still", CONSCIOUS_CHECK)
        self.baseline = None                      # set once the robot has stood still for a second (see watch_for_response)
        self.still_since = None
        self.moved_since = None
        self.reprompted = False
        pr = self.person_range
        self.say(t, f"In position, {'range sensor reads %.2f m' % pr if pr is not None else 'no range reading'}; waiting {self.p.checkin_s:.0f} s for a reply")

    def run_reminder(self, t):
        dt_in = t - self.t_state
        if not self.reprompted and dt_in >= 15.0:
            self.reprompted = True
            if self.reminder.get("welfare"):
                self.utter(t, "welfare_check", {}, "Are you there? Please say something.", loud=True)
            else:
                self.utter(t, "reminder_repeat", dict(label=self.reminder["label"]), "Your tablet, please. Say OK when you have taken it.", loud=True)
        if dt_in >= 30.0:
            self.reminder["t_missed"] = t
            self.reminder["status"] = "missed"
            self.say(t, "No acknowledgement after 30 s: family told by text (reminder missed, no emergency)")
            self.feel(t, "reminder_missed")
            if self.reminder.get("welfare"):
                self.disp.welfare_missed(t)
            else:
                self.disp.missed_reminder(t, self.reminder["label"])
            self.purpose = "fall"
            self.go(t, "WATCH", "watching", "")

    def run_check_in(self, t):
        if self.purpose == "reminder":
            return self.run_reminder(t)
        dt_in = t - self.t_state
        if not self.reprompted and dt_in >= self.p.reprompt_s:
            self.reprompted = True
            self.feel(t, "no_answer_yet")
            self.utter(t, "reprompt", {}, "Can you hear me? Say something or wave.", loud=True)
        if dt_in >= self.p.checkin_s:
            self.start_alert(t, dt_in)

    def start_alert(self, t, unresponsive_s):
        self.go(t, "ALERT", "alert", "Calling family + ambulance")
        self.t_alert = t
        self.t_update = t
        self.say(t, f"No response for {unresponsive_s:.0f} s: EMERGENCY")
        self.feel(t, "emergency")
        xy = self.person_hip[:2] if self.person_hip is not None else self.rb.est[:2]
        self.alert_pending = True
        if self.p.siren:
            self.start_siren(t, xy)

    def start_siren(self, t, xy):
        """Collapse and no answer: make a LOT of noise to attract people (neighbours, passers-by), and call for help out loud. It is not a diagnosis:
        the siren sounds for any unanswered collapse; a chest-clutch pattern seen in the last 40 s only makes it louder and is mentioned in the texts."""
        cue = bool(self.prodrome is not None and self.prodrome.t_first_flag is not None and t - self.prodrome.last_pos < 40.0)
        level = self.p.siren_cardiac_db if cue else self.p.siren_level_db
        self.siren = dict(t_on=t, level_db=level, cardiac_cue=cue, t_off=None, reason=None)
        self.say(t, f"SIREN ON ({level:.0f} dB at 1 m) to attract people" + ("; chest-clutch pattern seen just before the collapse" if cue else ""))
        self.utter(t, "siren_shout", dict(room=L.room_of(*xy)), f"HELP! A woman has collapsed in the {L.room_of(*xy)}! Please come now and call 108!", audience="bystander", loud=True)
        self.disp.siren(t, xy, level, cue)

    def stop_siren(self, t, reason):
        if self.siren is not None and self.siren["t_off"] is None:
            self.siren["t_off"], self.siren["reason"] = t, reason
            self.say(t, f"Siren off ({reason})")
            self.feel(t, "alarm_over")

    def run_alert(self, t):
        if self.siren is not None and self.siren["t_off"] is None and t - self.siren["t_on"] > self.p.siren_max_s:
            self.stop_siren(t, "time limit")
        if getattr(self, "alert_pending", False) and (self.snapshot is not None or t - self.t_alert > 0.5):
            self.alert_pending = False
            xy = self.person_hip[:2]
            evidence = f"pose tracker saw {self.obs.n_valid} of 33 body points" if self.obs else None
            f = self.detector.features
            est = self.rb.est
            telemetry = dict(
                event="collapse_unresponsive", witnessed=bool(self.detector.witnessed),
                time_of_collapse=clock(self.detector.t_impact), seconds_since_collapse=round(float(t - self.detector.t_impact), 1),
                unresponsive_for_s=self.p.checkin_s,
                location=dict(room=L.room_of(*xy), x=round(float(xy[0]), 2), y=round(float(xy[1]), 2)),
                posture=dict(hip_height_m=round(float(f.get("hip_z", float("nan"))), 2), torso_angle_deg=round(float(f.get("pitch", float("nan"))), 0),
                             box_aspect_ratio=round(float(f.get("aspect", float("nan"))), 1), still=True),
                robot=dict(x=round(float(est[0]), 2), y=round(float(est[1]), 2), distance_to_person_m=None if self.person_range is None else round(float(self.person_range), 2)),
                evidence=evidence)
            self.disp.emergency(t, xy, self.detector.t_impact, self.p.checkin_s, snapshot=self.snapshot, evidence=evidence, telemetry=telemetry)
            self.say(t, "Family messaged (with blurred photo) and ambulance called (simulated)")
            self.speak_fixed(t, "first_aid_bystander", BYSTANDER, audience="bystander", loud=True)
        elif t - self.t_update >= self.p.update_every_s:
            self.t_update = t
            self.disp.update(t, t - self.detector.t_impact)
            self.say(t, "Update sent to family: still not responding")
            self.speak_fixed(t, "first_aid_coach", COACH[self.coach_i % len(COACH)], audience="bystander")      # keeps a helper going (do not stop compressions)
            self.coach_i += 1

    # ---- the family platform can ask the robot to do things (src/platform) ----------------------------------------
    def serve_snapshot(self, t, rgb, obs):
        self.snapshot_request = False
        if not self.p.snapshot_consent:
            self.say(t, "Snapshot request declined: she has not agreed to camera pictures being sent")
            return
        if obs is None:
            self.say(t, "Snapshot request: she is not in view right now")
            return
        face = [i for i in range(11) if obs.vis[i] > 0.3]
        if not face:
            self.snapshot_request = True            # try again on the next frame
            return
        self.take_snapshot(rgb, obs)
        self.family_snapshot = self.snapshot
        self.snapshot = None
        self.say(t, "Snapshot sent to the family (face blurred, only because she agreed)")

    def step_look_plan(self, t, rgb, obs):
        """Tilt the camera to the requested view (above / below), wait until it points there, then keep one picture. If she is in the picture her face is
        blurred first; if she is in view but her face cannot be located the picture is NOT sent."""
        step = self.look_plan[0]
        if step["t0"] is None:
            step["t0"] = t
        self.look_override = (t + 1.0, step["tilt"])
        tilt = self.rb.neck_angles_deg()[1]
        if (abs(tilt - step["tilt"]) > 6.0 or t - step["t0"] < 0.8) and t - step["t0"] < 5.0:
            return
        from PIL import Image
        img = Image.fromarray(rgb)
        if obs is not None:
            face = [i for i in range(11) if obs.vis[i] > 0.3]
            if face:
                self.take_snapshot(rgb, obs)
                img, self.snapshot = self.snapshot, None
            else:
                img = None
                self.say(t, f"Picture {step['view']}: she is in view but her face cannot be located, so it is not sent")
        if img is not None:
            self.family_views[step["view"]] = (img, t)
            self.say(t, f"Picture {step['view']} sent to the family" + (" (face blurred)" if obs is not None else ""))
        self.look_plan.pop(0)
        if not self.look_plan:
            self.look_override = None

    def handle_command(self, t, cmd):
        """cmd = dict(cmd=..., args=...) from the family. The robot never obeys a command that would endanger her (no driving in an emergency)."""
        c, a = cmd.get("cmd"), cmd.get("args") or {}
        busy = self.state in ("SUSPECT", "APPROACH", "CHECK_IN", "ALERT")
        ok, note = True, ""
        if c == "say":
            text = str(a.get("text", ""))[:200]
            self.feel(t, "family_message")
            self.utter(t, "family_message_to_patient", dict(default=text), text, audience="patient")
            self.screen_text = text[:28]
        elif c == "remind":
            if busy or self.purpose == "reminder":
                ok, note = False, "robot is busy with something more important"
            else:
                ok = self.start_reminder(t, a.get("label", "your tablet"))
                note = "" if ok else "cannot find her right now"
        elif c == "check":
            if busy or self.purpose == "reminder":
                ok, note = False, "robot is busy with something more important"
            else:
                ok = self.start_reminder(t, "a check-in", welfare=True)
                note = "" if ok else "cannot find her right now"
        elif c == "look":
            d = a.get("direction", "level")
            tilt = {"up": 55.0, "down": -60.0, "level": 5.0}.get(d, 5.0)
            self.look_override = (t + 8.0, tilt)
            self.say(t, f"Family asked the camera to look {d}")
        elif c == "snapshot":
            view = a.get("view", "ahead")
            if view in ("above", "below", "both"):
                if not self.p.snapshot_consent:
                    ok, note = False, "she has not agreed to camera pictures being sent"
                    self.say(t, "Family asked for pictures above and below: declined, she has not agreed")
                else:
                    self.look_plan = [dict(view=v, tilt={"above": 55.0, "below": -60.0}[v], t0=None) for v in (["above", "below"] if view == "both" else [view])]
                    self.say(t, f"Family asked for a picture of what is {'above and below' if view == 'both' else view}: looking there")
            else:
                self.snapshot_request = True
                self.say(t, "Family asked for a snapshot")
        elif c == "siren_off":
            self.stop_siren(t, "silenced by the family")
        else:
            ok, note = False, f"unknown command {c}"
        self.commands_done.append(dict(t=round(float(t), 2), cmd=c, ok=ok, note=note))
        return ok, note

    # ---- head ----------------------------------------------------------------------------------
    def drive_neck(self, t, dt):
        rb = self.rb
        pan, tilt = rb.neck_angles_deg()
        est = rb.est
        hfov = np.degrees(2 * np.arctan(np.tan(np.radians(S.FOVY) / 2) * 640 / 480))
        fresh = self.obs is not None and t - self.t_seen < 0.25
        if fresh:
            cx, cy = self.obs.center
            pan_t = pan - 0.8 * (cx - 0.5) * hfov
            tilt_t = tilt + 0.8 * (0.5 - cy) * S.FOVY
        elif self.person_hip is not None and (self.state not in ("WATCH", "SEARCH") or t - self.t_seen < 2.0):
            dx, dy = self.person_hip[0] - est[0], self.person_hip[1] - est[1]
            pan_t = np.degrees(wrap(np.arctan2(dy, dx) - est[2]))
            tilt_t = np.degrees(np.arctan2(max(0.4 * self.person_hip[2], 0.2) - S.CAM_Z, max(np.hypot(dx, dy), 0.3)))
        else:
            pan_t, tilt_t = 55.0 * np.sin(2 * np.pi * 0.10 * t), 8.0                     # slow look-around
        if self.look_override is not None and t < self.look_override[0]:
            tilt_t = self.look_override[1]                                              # the family asked the camera to look up / down
        elif self.p.vertical_sweep and not fresh and self.state in ("WATCH", "SEARCH", "OBSERVE"):
            lo, hi = rb.tilt_range
            tilt_t = 0.5 * (lo + hi) - 5.0 + 0.35 * (hi - lo) * np.sin(2 * np.pi * 0.12 * t)       # nod up and down while looking around (a 1.15 m camera must look DOWN to see her on the floor)
        rate = 150.0 * dt
        self.pan_cmd += np.clip(pan_t - self.pan_cmd, -rate, rate)
        self.tilt_cmd += np.clip(tilt_t - self.tilt_cmd, -rate, rate)
        rb.set_neck(self.pan_cmd, self.tilt_cmd)
