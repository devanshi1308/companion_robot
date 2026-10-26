"""
The robot's feelings: a small, explicit emotional state that colours how it talks and how its face looks.

Four continuous feelings (0 to 1) change with what happens and fade back towards a calm resting state:
    worry   she is out of sight, lying on the floor, slow to answer
    alarm   she has collapsed and does not answer (peaks when the emergency starts)
    joy     she answered, got up, took her tablet, is chatting
    calm    nothing is wrong (the resting state; also the relief after trouble is over)

`label()` names the dominant feeling (calm, curious, concerned, worried, alarmed, relieved, happy) and `face()` maps it to the robot's
screen mood (watching, worried, happy, alert). These are an engineering device for tone and for the family to read the robot's state at
a glance; the robot does not "really" feel, and feelings never change a safety decision (thresholds, timers and dispatch are untouched).
"""
import numpy as np

# how much each event moves the feelings: (worry, alarm, joy, calm)
EFFECTS = {
    "lost_sight": (0.25, 0.0, 0.0, -0.1),
    "found_her": (-0.2, 0.0, 0.15, 0.2),
    "she_is_on_the_floor": (0.45, 0.1, -0.2, -0.3),
    "fall_suspected": (0.5, 0.2, -0.3, -0.4),
    "fall_confirmed": (0.4, 0.35, -0.3, -0.4),
    "checking_in": (0.1, 0.0, 0.0, 0.0),
    "no_answer_yet": (0.2, 0.15, 0.0, -0.1),
    "emergency": (0.1, 0.8, -0.5, -0.5),
    "she_answered": (-0.6, -0.8, 0.5, 0.5),
    "she_got_up": (-0.5, -0.6, 0.45, 0.5),
    "reminder_due": (0.0, 0.0, 0.1, 0.0),
    "reminder_acknowledged": (-0.1, 0.0, 0.4, 0.2),
    "tablet_taken": (-0.1, 0.0, 0.5, 0.3),
    "reminder_missed": (0.3, 0.0, -0.2, -0.2),
    "family_message": (0.0, 0.0, 0.2, 0.1),
    "alarm_over": (-0.3, -0.5, 0.2, 0.4),
}
HALF_LIFE_S = {"worry": 25.0, "alarm": 40.0, "joy": 20.0}


class Emotion:
    def __init__(self):
        self.worry, self.alarm, self.joy, self.calm = 0.0, 0.0, 0.2, 0.8
        self.t = 0.0
        self.history = []                     # (t, event, label)

    def decay(self, t):
        dt = max(t - self.t, 0.0)
        self.t = t
        for name, hl in HALF_LIFE_S.items():
            setattr(self, name, getattr(self, name) * 0.5 ** (dt / hl))
        self.calm = float(np.clip(1.0 - max(self.worry, self.alarm), 0.0, 1.0))

    def feel(self, t, event):
        """Something happened: move the feelings."""
        self.decay(t)
        dw, da, dj, dc = EFFECTS.get(event, (0, 0, 0, 0))
        self.worry = float(np.clip(self.worry + dw, 0, 1))
        self.alarm = float(np.clip(self.alarm + da, 0, 1))
        self.joy = float(np.clip(self.joy + dj, 0, 1))
        self.calm = float(np.clip(self.calm + dc, 0, 1))
        self.history.append((round(float(t), 2), event, self.label()))

    def label(self):
        if self.alarm >= 0.55:
            return "alarmed"
        if self.worry >= 0.6:
            return "worried"
        if self.worry >= 0.3:
            return "concerned"
        if self.joy >= 0.65:
            return "happy"
        if self.joy >= 0.45 and self.history and self.history[-1][1] in ("she_answered", "she_got_up", "alarm_over"):
            return "relieved"
        if self.joy >= 0.4:
            return "cheerful"
        return "calm"

    def face(self):
        """Mood of the robot's screen face (robot_interface.MOODS)."""
        lab = self.label()
        return {"alarmed": "alert", "worried": "worried", "concerned": "concerned", "happy": "happy", "relieved": "relieved", "cheerful": "happy"}.get(lab, "watching")

    def snapshot(self):
        return dict(label=self.label(), worry=round(self.worry, 2), alarm=round(self.alarm, 2), joy=round(self.joy, 2), calm=round(self.calm, 2))
