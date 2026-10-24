"""
Checks for Momo (the agent with feelings) in offline mode: feelings move and fade, messages keep the facts, the ambulance script is untouched,
output validation rejects a diagnosis.   Run:  python tests/test_agent.py
"""
import os
import sys

os.environ["COMPANION_LLM"] = "off"
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for sub in ("agent", "control", "sim"):
    sys.path.insert(0, os.path.join(ROOT, "src", sub))
from companion_agent import CompanionAgent, BANNED  # noqa: E402
from dispatch import Dispatcher  # noqa: E402


def test_feelings_follow_events_and_fade():
    v = CompanionAgent("Asha")
    assert v.emotion.label() == "calm" and v.mood() == "watching"
    v.feel(10, "she_is_on_the_floor")
    v.feel(11, "fall_confirmed")
    assert v.emotion.label() in ("worried", "alarmed") and v.mood() in ("worried", "alert")
    v.feel(30, "emergency")
    assert v.emotion.label() == "alarmed" and v.mood() == "alert"
    v.feel(40, "she_answered")
    assert v.emotion.label() in ("relieved", "happy", "cheerful", "calm")
    v.emotion.decay(400)
    assert v.emotion.label() in ("calm", "cheerful")


def test_family_messages_go_through_the_agent_and_keep_the_facts():
    v = CompanionAgent("Asha")
    d = Dispatcher("/private/tmp/agent_test_out", voice=v)
    v.feel(5, "fall_confirmed")
    d.heads_up(10, (-2.0, -0.5), 8)
    d.emergency(30, (-2.0, -0.5), 8, 10.0, telemetry=dict(x=1))
    kinds = {m["kind"]: m["text"] for m in d.sent}
    assert "living room" in kinds["heads_up"] and "14:00:08" in kinds["heads_up"]
    assert "living room" in kinds["emergency"] and "ambulance" in kinds["emergency"].lower()
    assert "108" in kinds["ambulance_call"] and "Momo" not in kinds["ambulance_call"]            # the ambulance script is the factual template
    assert {o["kind"] for o in v.outbox} >= {"heads_up", "emergency"} and "ambulance_call" not in {o["kind"] for o in v.outbox}


def test_no_diagnosis_wording():
    assert BANNED.search("She is having a heart attack") and not BANNED.search("It could be a cardiac emergency")
    v = CompanionAgent("Asha")
    for kind in ("heads_up", "emergency", "update", "siren_shout", "siren_neighbour"):
        assert not BANNED.search(v.phrase(kind, dict(room="hallway", clock="14:01:00", seconds=12), "", audience="family"))


class _FakeAgent:
    """Stands in for the Strands agent (no credentials needed): returns a canned answer and records the prompt."""
    def __init__(self, answer):
        self.answer, self.messages, self.prompts = answer, [], []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        return self.answer


def test_model_answers_are_checked_before_use():
    v = CompanionAgent("Asha")
    facts = dict(room="bedroom", clock="14:05:00", seconds=10)
    v.agent, v.remote = _FakeAgent("Asha collapsed in the bedroom at 14:05:00 and is not answering. I called an ambulance."), True
    t = v.phrase("emergency", facts, "default", audience="family")
    assert t.startswith("Asha collapsed") and v.outbox[-1]["source"] == "model" and "room = bedroom" in v.agent.prompts[0]
    v.agent = _FakeAgent("Asha is having a heart attack in the bedroom at 14:05:00.")           # diagnosis -> rejected, template used
    t = v.phrase("emergency", facts, "default", audience="family")
    assert v.outbox[-1]["source"] == "template" and "heart attack" not in t
    v.agent = _FakeAgent("Something happened.")                                                 # misses the required room -> rejected
    v.phrase("heads_up", facts, "default", audience="family")
    assert v.outbox[-1]["source"] == "template"
    v.agent = _FakeAgent("Asha, are you okay?")                                                # remote model: what she hears in the room is phrased on the robot
    v.phrase("check_in", {}, "default", audience="patient")
    assert v.outbox[-1]["source"] == "template" and not v.agent.prompts[-1:] == ["x"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
