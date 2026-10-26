"""
Chatting with Baymax: a signed-in family member types a message, Baymax answers from what the robot actually knows and can act on a request.

    reply, actions = answer("has she taken her tablet?", facts)      # facts = the state the family page shows (publisher.build_facts)

Answers are built from the facts (never invented). If the Strands agent has a model, the SAME answer is then re-worded in Baymax's current feelings, and
the re-worded text must still contain every number and time of the factual answer (otherwise the factual answer is used).
Requests that change what the robot does come back as `actions` (dicts like the platform commands) and are applied by the simulation; the robot refuses
them when it is busy with a fall or an emergency. It never places a call on request: emergency calls are automatic after an unanswered collapse.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from health_knowledge import lookup as health_lookup  # noqa: E402

FALLBACK = "I am not sure what you mean."          # the reply that means "no built-in answer": the agent (language model) gets a go
URGENT = ("chest pain", "can't breathe", "cannot breathe", "not breathing", "unconscious", "bleeding", "stroke", "heart attack", "collapsed", "fainted")
HELP = ("You can ask me: where she is, how she is, whether she took her tablet, how I feel, how to do CPR or other first aid, or what a medicine is for. You can also say: remind her, check on her, tell her <message>, "
        "look up / look down / look around, send a picture, silence the siren.")


def _doses(f):
    return [d for d in f.get("doses", []) if not d.get("welfare")]


def answer(text, f):
    t = text.lower().strip()
    p, pe, rb, al = f.get("patient", "She"), f.get("person", {}), f.get("robot", {}), f.get("alert", {})
    actions = []
    if not t:
        return "I am here. " + HELP, actions
    status_q = bool(re.search(r"has she|did she|was she|taken|is she", t))
    if any(k in t for k in URGENT) and not re.search(r"has she|did she|was she|taken|tablet", t):
        steps = health_lookup(text)
        return ("If someone has chest pain, cannot breathe, is unconscious or badly hurt, call 108 now. I cannot place calls on request. "
                + (f"The ambulance has already been called for {p}. " if al.get("emergency") else (al.get("title", "") + " "))
                + (steps or "")).strip(), actions
    if not status_q:
        kb = health_lookup(text)                                  # CPR and other first aid, medicine facts: fixed, reviewed text
        if kb:
            return kb, actions
    m = re.search(r"\b(?:tell|say to|say)\b (?:her |asha )?(?:that )?(.+)", text, re.I)
    if re.search(r"\b(tell|say) ", t) and m and not t.startswith(("say how", "say where")):
        msg = m.group(1).strip().rstrip(".") if re.search(r"\b(tell|say)\b.* ", t) else ""
        if msg and not re.match(r"(me|us)\b", msg.lower()):
            actions.append(dict(cmd="say", args=dict(text=msg)))
            return f'I will tell {p}: "{msg}".', actions
    if re.search(r"silence|stop the siren|turn off the (siren|alarm)|siren off", t):
        s = f.get("siren")
        if s and s.get("on"):
            actions.append(dict(cmd="siren_off"))
            return "Silencing the siren now. Only do this if help has arrived or she is fine.", actions
        return "The siren is not sounding.", actions
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
    if re.search(r"remind", t):
        actions.append(dict(cmd="remind", args=dict(label="your tablet")))
        return f"I will go and remind {p} about her tablet now.", actions
    if re.search(r"check on|check in|go to her|go and see", t):
        actions.append(dict(cmd="check"))
        return f"I will go and check on {p} now.", actions
    if re.search(r"look around|look up and down|above and below", t):
        actions.append(dict(cmd="snapshot", args=dict(view="both")))
        return "I will look up and down and send you what I see, if she has agreed to pictures.", actions
    if re.search(r"look up|look above|ceiling", t):
        actions.append(dict(cmd="look", args=dict(direction="up")))
        return "Looking up.", actions
    if re.search(r"look down|look below|floor", t):
        actions.append(dict(cmd="look", args=dict(direction="down")))
        return "Looking down.", actions
    if re.search(r"picture|photo|snapshot|see her|show me", t):
        actions.append(dict(cmd="snapshot"))
        return "I will send a picture with her face blurred, if she has agreed to pictures.", actions
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
