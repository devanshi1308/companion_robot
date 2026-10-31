"""
Questions to Baymax: it answers from what the robot actually knows (facts) and from reviewed first-aid and medicine text.

    reply, actions = answer("has she taken her tablet?", facts)      # facts = the robot's state; `actions` is always empty (nothing is done on request)

Answers are built from the facts (never invented). It never places a call on request: emergency calls are automatic after an unanswered collapse.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from health_knowledge import lookup as health_lookup  # noqa: E402

FALLBACK = "I am not sure what you mean."          # the reply when there is no built-in answer
URGENT = ("chest pain", "can't breathe", "cannot breathe", "not breathing", "unconscious", "bleeding", "stroke", "heart attack", "collapsed", "fainted")
HELP = "You can ask me: where she is, how she is, whether she took her tablet, how I feel, how to do CPR or other first aid, or what a medicine is for."


def _doses(f):
    return [d for d in f.get("doses", []) if not d.get("welfare")]


def answer(text, f):
    answer.fixed = False                                       # set True when the reply is fixed, reviewed text that no model may re-word
    t = text.lower().strip()
    p, pe, rb, al = f.get("patient", "She"), f.get("person", {}), f.get("robot", {}), f.get("alert", {})
    actions = []
    if not t:
        return "I am here. " + HELP, actions
    status_q = bool(re.search(r"has she|did she|was she|taken|is she", t))
    if any(k in t for k in URGENT) and not re.search(r"has she|did she|was she|taken|tablet", t):
        steps = health_lookup(text)
        answer.fixed = True                                       # the call-108 answer is never re-worded
        return ("If someone has chest pain, cannot breathe, is unconscious or badly hurt, call 108 now. I cannot place calls on request. "
                + (f"The ambulance has already been called for {p}. " if al.get("emergency") else (al.get("title", "") + " "))
                + (steps or "")).strip(), actions
    if not status_q:
        kb = health_lookup(text)                                  # CPR and other first aid, medicine facts: fixed, reviewed text
        if kb:
            answer.fixed = True                                   # the page must NOT let a model re-word this
            return kb, actions
    if re.search(r"ambulance|108|emergency number|call (the )?(doctor|hospital)", t):
        if al.get("emergency"):
            return f"The ambulance has already been called for {p} (simulated). I am staying with her.", actions
        return "I cannot place calls on request. If she collapses and does not answer me, I call the ambulance and text you myself.", actions
    if re.search(r"tablet|pill|medic|dose|drug", t) and not re.search(r"remind", t):
        ds = _doses(f)
        if not ds:
            return f"I have not reminded {p} about any medicine yet today.", actions
        d = ds[-1]
        if d["status"] == "taken":
            return f"Yes. I saw {p} take {d['label'].replace('your ', 'her ')} at {d['clock_taken']}.", actions
        if d["status"] == "acknowledged":
            return f"{p} said OK to the reminder for {d['label'].replace('your ', 'her ')}, but I have not seen her take it.", actions
        if d["status"] == "missed":
            return f"No. {p} did not answer my reminder at {d['clock_due']} for {d['label'].replace('your ', 'her ')}.", actions
        return f"I reminded {p} at {d['clock_due']} and I am waiting for her to take {d['label'].replace('your ', 'her ')}.", actions
    if re.search(r"where|which room|room", t):
        if pe.get("room") is None:
            return f"I have not seen {p} yet.", actions
        ago = pe.get("last_seen_ago")
        seen = "I can see her now" if pe.get("seen_now") else f"I last saw her {int(ago or 0)} seconds ago"
        return f"{p} is in the {pe['room']}, {pe.get('posture') or 'posture unknown'}. {seen}.", actions
    if re.search(r"how are you|how do you feel|your feeling|are you ok", t):
        fe = rb.get("feeling", {}).get("label", "calm")
        return f"I feel {fe}. {al.get('title', 'All well')}.", actions
    if re.search(r"how is she|is she (ok|okay|fine|well|safe|alright)|what('s| is) (she|happening|going on)|status|update|everything", t):
        base = f"{al.get('title', 'All well')}."
        if pe.get("room"):
            base += f" {p} is in the {pe['room']}, {pe.get('posture') or 'posture unknown'}."
        ds = _doses(f)
        if ds and ds[-1]["status"] == "taken":
            base += f" She took her tablet at {ds[-1]['clock_taken']}."
        return base, actions
    if re.search(r"^(hi|hello|hey|good (morning|evening|afternoon))", t):
        return f"Hello. I am Baymax. {al.get('title', 'All well')}. Ask me how {p} is.", actions
    return FALLBACK + " " + HELP, actions
