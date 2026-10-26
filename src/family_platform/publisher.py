"""
Turns the robot's internal state into what the family sees (feed.py) and applies the family's commands.

    pub = FamilyPublisher(feed, comp, sim_start_clock="08:00:00")
    pub.tick(t, d, m)        # call a few times per simulated second

What the family gets: where she is (room), what she is doing (standing, sitting, lying on the floor), when she was last seen, whether the medicine was
taken (and whether the robot SAW it), alerts and the siren, Baymax's feelings, and everything Baymax said or texted. What they do not get: video.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ("sim", "control", "agent"):
    sys.path.insert(0, os.path.join(HERE, "..", sub))
import apartment_layout as L  # noqa: E402
from dispatch import clock  # noqa: E402

HELP_SHORT = "Try: where is she? how is she? has she taken her tablet? remind her. tell her ..."
STATE_LABEL = {"WATCH": "Watching", "FOLLOW": "Following her", "SEARCH": "Looking for her", "OBSERVE": "Watching her on the floor", "SUSPECT": "Checking a possible fall",
               "APPROACH": "Going to her", "CHECK_IN": "Talking to her", "ALERT": "Emergency"}

LAYOUT = dict(
    bounds=[L.X0, L.X1, L.Y0, L.Y1],
    rooms=[dict(name="Living-dining", x0=L.X0, x1=L.PART_X, y0=L.HALL_Y, y1=L.Y1), dict(name="Bedroom", x0=L.PART_X, x1=L.X1, y0=L.HALL_Y, y1=L.Y1),
           dict(name="Hallway", x0=L.X0, x1=L.X1, y0=L.Y0, y1=L.HALL_Y)],
    doors=[dict(x=L.DOOR_LIVING[0], y=L.HALL_Y, w=L.DOOR_LIVING[1]), dict(x=L.DOOR_BEDROOM[0], y=L.HALL_Y, w=L.DOOR_BEDROOM[1])],
    furniture=[dict(n="sofa", x0=-0.56, x1=0.44, y0=-1.2, y1=0.6), dict(n="coffee table", x0=-1.83, x1=-1.28, y0=-0.8, y1=0.2), dict(n="TV", x0=-3.4, x1=-3.1, y0=-0.9, y1=0.3),
               dict(n="dining table", x0=-1.3, x1=0.1, y0=1.13, y1=1.93), dict(n="kitchen", x0=-3.44, x1=-1.2, y0=2.4, y1=2.94), dict(n="bed", x0=1.52, x1=3.08, y0=0.94, y1=2.94),
               dict(n="wardrobe", x0=0.66, x1=1.26, y0=0.2, y1=1.8)],
)


def posture(feat, hip_est):
    """Standing / sitting / lying from the robot's own estimates (hip height and torso angle), or None."""
    if not feat or "hip_z" not in feat:
        return None
    z, pitch = feat["hip_z"], feat.get("pitch", 0.0)
    if z <= 0.40 and pitch >= 40:
        return "lying on the floor"
    if z >= 0.75:
        return "standing"
    if z >= 0.40:
        return "sitting"
    return "low (crouching or sitting on the floor)"


class FamilyPublisher:
    def __init__(self, feed, comp, patient="Asha", start_clock=None, agent=None, consent=False):
        self.feed, self.comp, self.patient, self.start_clock, self.agent, self.consent = feed, comp, patient, start_clock, agent, consent
        self.n_log = self.n_sent = self.n_utt = self.n_cmd = 0
        self.last_state_t = -1.0
        self.lying_since = None
        self.last_snapshot_n = 0
        self.sent_views = {}
        self.facts = None
        self.pending = []
        from concurrent.futures import ThreadPoolExecutor
        self.pool = ThreadPoolExecutor(1)
        self.frozen = False                      # the simulation has ended: Baymax can still answer questions, but cannot act
        self.doses = []
        self.t_seen_person = None
        self.person_room = None

    def clk(self, t):
        return clock(t, self.start_clock)

    def _events(self, t):
        c = self.comp
        for (te, text) in c.events[self.n_log:]:
            self.feed.add_event(type="log", t=te, clock=self.clk(te), text=text)
        self.n_log = len(c.events)
        for (te, kind, text) in c.utterances[self.n_utt:]:
            fe = self.agent.emotion.snapshot()["label"] if self.agent is not None and self.agent.emotion else None
            self.feed.add_event(type="momo", t=te, clock=self.clk(te), kind=kind, text=text, feeling=fe)
        self.n_utt = len(c.utterances)
        for rec in c.disp.sent[self.n_sent:]:
            att = rec.get("attachment")
            if att and os.path.exists(att):
                import shutil
                shutil.copyfile(att, self.feed.snapshot_path("emergency"))              # the face-blurred picture that goes with the urgent text
            self.feed.add_event(type="sent", t=rec["t"], clock=self.clk(rec["t"]), kind=rec["kind"], to=rec["to"], channel=rec["channel"], text=rec["text"],
                                attachment=bool(att and os.path.exists(att)))
        self.n_sent = len(c.disp.sent)

    def apply_chats(self, t):
        """Family members chatting with Baymax: answer from the robot's facts, act on requests, and keep every message in the feed."""
        from chat import answer
        for ch in self.feed.new_chats():
            self.feed.add_event(type="chat", who="user", user=ch["user"], t=round(float(t), 2), clock=self.clk(t), text=ch["text"])
            reply, actions = answer(ch["text"], self.facts or dict(patient=self.patient))
            from chat import FALLBACK
            if reply.startswith(FALLBACK):
                if self.agent is not None and self.agent.model is not None:
                    # a language model call can take seconds: do it in a thread so the simulation keeps running; the answer is posted when it arrives
                    self.pending.append((ch["user"], self.pool.submit(self.agent.open_chat, ch["user"], ch["text"], dict(self.facts or {}))))
                    continue
                else:
                    reply = ("I can answer questions about her and about me, and do things like remind her or tell her something. "
                             "For other questions I need a language model connected (set GROQ_API_KEY or GEMINI_API_KEY for a free tier, or run a local model with OLLAMA_HOST) and none is connected right now. "
                             + HELP_SHORT)
            elif self.agent is not None and getattr(self.agent, "agent", None) is not None:
                reply = self.agent.phrase("chat_reply", dict(answer=reply, patient=self.patient), reply, audience="family", t=t)
            note = ""
            for act in actions:
                if self.frozen:
                    reply, note = "The demo simulation has ended, so I cannot do that any more. I can still answer questions.", ""
                    break
                ok, why = self.comp.handle_command(t, dict(act, who=ch["user"]))
                if not ok:
                    note = f" But I could not do that now: {why}."
            self.feed.add_event(type="chat", who="momo", user=ch["user"], t=round(float(t), 2), clock=self.clk(t), text=reply + note)

    def idle(self, t):
        """After the simulation ended: keep answering chat questions from the last known state."""
        self.frozen = True
        self.apply_chats(t)
        self.finish_open_chats(t)
        if self.facts is not None and not self.facts.get("ended"):
            self.facts["ended"] = True
            self.feed.write_state(self.facts)

    def finish_open_chats(self, t):
        for item in list(self.pending):
            user, fut = item
            if fut.done():
                self.pending.remove(item)
                text = None
                try:
                    text = fut.result()
                except Exception:
                    pass
                self.feed.add_event(type="chat", who="momo", user=user, t=round(float(t), 2), clock=self.clk(t),
                                    text=text or "Sorry, I could not reach my language model just now. Ask me about her or about me and I can answer those.")

    def apply_commands(self, t):
        for cmd in self.feed.new_commands():
            ok, note = self.comp.handle_command(t, cmd)
            self.feed.add_event(type="command", t=round(float(t), 2), clock=self.clk(t), cmd=cmd.get("cmd"), args=cmd.get("args"), ok=ok, note=note)

    def tick(self, t, d, m, force=False):
        self.apply_commands(t)
        self.apply_chats(t)
        self.finish_open_chats(t)
        self._events(t)
        if t - self.last_state_t < 0.25 and not force:
            return
        self.last_state_t = t
        c, rb = self.comp, self.comp.rb
        feat = c.detector.features
        seen_now = c.obs is not None and t - c.t_seen < 0.5
        hip = c.person_hip
        if seen_now:
            self.t_seen_person = t
        room = L.room_of(*hip[:2]) if hip is not None else None
        post = posture(feat, hip) if (self.t_seen_person is not None and t - self.t_seen_person < 6.0) else None
        if post == "lying on the floor":
            self.lying_since = self.lying_since if self.lying_since is not None else t
        else:
            self.lying_since = None
        rem = c.reminder
        if rem is not None and (not self.doses or self.doses[-1]["t_due"] != rem["t_due"]):
            self.doses.append(rem)
        doses = [dict(label=r["label"], welfare=bool(r.get("welfare")), status=r["status"], t_due=r["t_due"], clock_due=self.clk(r["t_due"]),
                      t_ack=r["t_ack"], t_taken_seen=r["t_taken_seen"], clock_taken=None if r["t_taken_seen"] is None else self.clk(r["t_taken_seen"])) for r in self.doses]
        siren = c.siren
        level, title = 0, "All well"
        if c.state == "ALERT":
            level, title = 2, "EMERGENCY: she collapsed and is not answering"
        elif c.state in ("SUSPECT", "APPROACH", "CHECK_IN") and c.purpose == "fall":
            level, title = 1, "Baymax is checking on her (possible fall)"
        elif c.sent_heads_up and c.state != "WATCH":
            level, title = 1, "Baymax is checking on her"
        elif any(r["status"] == "missed" and not r.get("welfare") for r in self.doses[-1:]):
            level, title = 1, "A medicine reminder was missed"
        emo = self.agent.emotion.snapshot() if self.agent is not None else dict(label=rb.mood, worry=0, alarm=0, joy=0, calm=1)
        pan, tilt = rb.neck_angles_deg()
        est = rb.est
        state = dict(
            t=round(float(t), 2), clock=self.clk(t), patient=self.patient,
            robot=dict(name="Baymax", state=c.state, state_label=STATE_LABEL.get(c.state, c.state), mood=rb.mood, feeling=emo, screen_text=c.screen_text,
                       x=round(float(est[0]), 2), y=round(float(est[1]), 2), yaw=round(float(est[2]), 3), pan_deg=round(pan, 1), tilt_deg=round(tilt, 1),
                       room=L.room_of(est[0], est[1]), agent_mode=getattr(self.agent, "mode", "plain wording")),
            person=dict(room=room, x=None if hip is None else round(float(hip[0]), 2), y=None if hip is None else round(float(hip[1]), 2), seen_now=bool(seen_now),
                        last_seen_ago=None if self.t_seen_person is None else round(float(t - self.t_seen_person), 1), posture=post,
                        lying_s=None if self.lying_since is None else round(float(t - self.lying_since), 1)),
            doses=doses,
            alert=dict(level=level, title=title, heads_up=bool(c.sent_heads_up), emergency=any(s["kind"] == "emergency" for s in c.disp.sent)),
            siren=None if siren is None else dict(on=siren["t_off"] is None, level_db=siren["level_db"], cardiac_cue=siren["cardiac_cue"], t_on=siren["t_on"], t_off=siren["t_off"], reason=siren["reason"]),
            privacy=dict(video_streamed=False, snapshot_consent=bool(self.consent), bytes_off_board=int(c.disp.bytes_off_board)),
            has_snapshot=c.family_snapshot is not None,
            commands=c.commands_done[-5:],
            views={},
        )
        if c.family_snapshot is not None and self.last_snapshot_n != id(c.family_snapshot):
            self.feed.write_snapshot(c.family_snapshot)
            self.last_snapshot_n = id(c.family_snapshot)
            state["snapshot_t"] = round(float(t), 1)
        for view, (img, tv) in list(c.family_views.items()):
            if self.sent_views.get(view) != tv:
                self.feed.write_snapshot(img, view)
                self.sent_views[view] = tv
            state["views"][view] = round(float(tv), 1)
        state["ended"] = self.frozen
        self.facts = state
        self.feed.write_state(state)
