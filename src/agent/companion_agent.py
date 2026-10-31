"""
Baymax: the companion robot's voice, a Strands agent with feelings.

Every sentence the robot says to her (check-in, reminder, siren call-out) and every text it sends to the family goes through Baymax, so the
family hears one consistent, caring voice whose tone follows how the robot feels (see emotion.py). The facts never come from the language
model: the simulator and the state machine decide WHAT happens and what must be said (room, time, 'not responding', 'ambulance called');
Baymax only decides HOW to say it.

    voice = CompanionAgent("Asha")                  # picks a model automatically, or runs offline
    text = voice.phrase("emergency", dict(room="living room", clock="14:02", seconds=10), default_text, audience="family")

Models (first that is available; none = offline templates, which is also what the experiments use):
    GROQ_API_KEY           Groq free tier (llama-3.3-70b-versatile), OpenAI-compatible
    GEMINI_API_KEY         Google AI Studio free tier (gemini-2.0-flash)
    ANTHROPIC_API_KEY      Anthropic model via Strands (COMPANION_MODEL, default claude-haiku-5-5)
    OLLAMA_HOST            a local model via Ollama (COMPANION_OLLAMA_MODEL): nothing leaves the machine
    AWS credentials        Amazon Bedrock (Strands default)
    COMPANION_LLM=off      force offline templates

Privacy and safety rules, enforced here:
  * The model only ever sees short text facts, never images, landmarks or video.
  * With a REMOTE model, only messages that leave the robot anyway (family, neighbour, siren call-out) are phrased by it; what the robot
    says to her in the room is phrased on the robot (templates) unless the model is local.
  * The ambulance call script is never given to the model: it stays the factual template.
  * Output is checked: it must contain every required fact, must not claim a diagnosis, and must be short; otherwise the template is used.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from emotion import Emotion  # noqa: E402

NAME = "Baymax"
SYSTEM = f"""You are {NAME}, a small, gentle companion robot who lives with an older woman and looks after her. You speak in short, warm, plain sentences.
You have feelings that change with what is happening; your current feelings are available from the tool current_feelings, and your tone must match them:
calm and friendly when all is well, concerned when she is out of sight or slow to answer, worried when she is on the floor, alarmed when she has collapsed and does not answer, relieved and happy when she is fine.
Rules you never break:
- Say exactly the facts you are given (room, time, what happened, what you did). Never invent facts, names or numbers.
- You never diagnose. You may say a collapse is serious or that it could be a cardiac emergency, never that she is having a heart attack.
- If you are told the audience is the family, write a short text message in the first person ("I"). If the audience is the patient, speak to her directly and kindly.
- If the audience is bystanders (a call-out for help), be loud, clear and urgent: what happened, where, what to do (call 108, come in).
- Reply with the message text only: no quotes, no explanations, no emoji, at most {{max_words}} words."""

MAX_WORDS = {"patient": 30, "family": 60, "bystander": 28}
BANNED = re.compile(r"(is having a heart attack|has had a heart attack|diagnos|stroke)", re.I)


def pick_model():
    """Returns (model, description, remote) or (None, 'offline templates', False)."""
    if os.environ.get("COMPANION_LLM", "").lower() == "off":
        return None, "offline templates (COMPANION_LLM=off)", False
    try:
        if os.environ.get("ANTHROPIC_API_KEY"):
            from strands.models.anthropic import AnthropicModel
            mid = os.environ.get("COMPANION_MODEL", "claude-haiku-5-5")
            return AnthropicModel(client_args={"api_key": os.environ["ANTHROPIC_API_KEY"]}, model_id=mid, max_tokens=300), f"Anthropic {mid}", True
        if os.environ.get("GROQ_API_KEY"):                       # free tier, OpenAI-compatible endpoint
            from strands.models.openai import OpenAIModel
            mid = os.environ.get("COMPANION_GROQ_MODEL", "llama-3.3-70b-versatile")
            return OpenAIModel(client_args={"api_key": os.environ["GROQ_API_KEY"], "base_url": "https://api.groq.com/openai/v1"}, model_id=mid, params={"max_tokens": 300}), f"Groq {mid} (free tier)", True
        if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):          # free tier from Google AI Studio
            from strands.models.gemini import GeminiModel
            mid = os.environ.get("COMPANION_GEMINI_MODEL", "gemini-2.0-flash")
            return GeminiModel(client_args={"api_key": os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"]}, model_id=mid, params={"max_output_tokens": 300}), f"Gemini {mid} (free tier)", True
        if os.environ.get("OLLAMA_HOST"):
            from strands.models.ollama import OllamaModel
            mid = os.environ.get("COMPANION_OLLAMA_MODEL", "llama3.2")
            return OllamaModel(os.environ["OLLAMA_HOST"], model_id=mid, keep_alive="30m", max_tokens=140, temperature=0.4), f"Ollama {mid} (local)", False
        import boto3
        if boto3.Session().get_credentials() is not None:
            from strands.models import BedrockModel
            return BedrockModel(), "Amazon Bedrock", True
    except Exception as e:                                      # a missing extra or bad credentials must never stop the robot
        return None, f"offline templates (model setup failed: {type(e).__name__})", False
    return None, "offline templates (no model credentials found)", False


# ---- offline wording: used when no model is available, and as the fallback when a model answer fails the checks -------------------------
OPENER = {
    "calm": "", "cheerful": "", "happy": "", "relieved": "That's a relief. ",
    "concerned": "Hmm. ", "worried": "I'm worried. ", "alarmed": "This is serious. ",
}


def offline_text(kind, f, label, name):
    o = OPENER.get(label, "")
    room, clock, who = f.get("room", "the flat"), f.get("clock", ""), f.get("patient", "she")
    secs = int(f.get("seconds", 10))
    her = str(f.get("label", "your tablet")).replace("your ", "her ")
    T = {
        "check_in": f"{o}I am Baymax, your personal healthcare companion. {who}, I noticed you are on the floor. Are you hurt?",
        "reprompt": f"{who}, I did not hear you. If you can hear me, please say something or wave. I am staying with you.",
        "heads_up": f"{o}I think {who} may have fallen at {clock}. She is on the floor in the {room} and has not moved. I am going to her now.",
        "emergency": f"{o}{who} collapsed in the {room} at {clock} and is not answering me ({secs} s). It could be a cardiac emergency. I have called an ambulance. Please come or call her now.",
        "update": f"{o}{who} is still not responding, {secs} s since the collapse. The ambulance is on its way and I am staying with her.",
        "all_clear": f"{o}Good news: {who} answered me and says she is fine. No ambulance is needed.",
        "reminder": f"{who}, it is time for {f.get('label', 'your tablet')}. Please take it with a glass of water, and say OK when you have.",
        "reminder_repeat": f"{who}, a gentle reminder: {f.get('label', 'your tablet')}. Say OK when you have taken it.",
        "reminder_ack": f"{o}{who} said OK to the reminder for {her}, but I did not see her take it.",
        "tablet_taken": f"I saw {who} take {her}.",
        "reminder_missed": f"{o}{who} has not acknowledged the reminder for {her}. She looks well; please check in with her when you can.",
        "welfare_check": f"{who}, your family asked me to say hello. How are you feeling?",
        "welfare_missed": f"{o}{who} did not answer when I checked on her. She looks well; please call her when you can.",
        "siren_shout": f"HELP! A woman has collapsed in the {room}! Please come now and call 108!",
        "siren_neighbour": f"{o}A loud alarm is sounding in {who}'s flat ({room}). She has collapsed and is not responding.{' She pressed a hand to her chest just before.' if f.get('cardiac_cue') else ''} Please come if you can; an ambulance has been called.",
        "chat_reply": f.get("answer", ""),
        "relief_note": f"{who} is up again. I am glad.",
    }
    return T.get(kind, f.get("default", ""))


class PlainVoice:
    """No agent: every message keeps the simulator's own wording (this is what the experiments use)."""
    emotion = None
    mode = "plain"

    def phrase(self, kind, facts, default, audience="family", t=None):
        return default

    def feel(self, t, event):
        pass

    def mood(self):
        return None


class CompanionAgent(PlainVoice):
    def __init__(self, patient="Asha", model="auto", name=NAME, verbose=False):
        self.name, self.patient = name, patient
        self.emotion = Emotion()
        self.outbox = []                       # every message Baymax produced: dict(t, kind, audience, text, feeling, source)
        self.recent = []
        self.model, self.remote = None, False
        self.mode = "offline templates"
        if model == "auto":
            self.model, self.mode, self.remote = pick_model()
        elif model is not None:
            self.model, self.mode, self.remote = model, "custom model", True
        self.agent = None
        if self.model is not None:
            self._build_agent()

    # ---- Strands agent ---------------------------------------------------------------------------------
    def _build_agent(self):
        from strands import Agent, tool
        emotion, recent = self.emotion, self.recent

        @tool
        def current_feelings() -> str:
            """Your current feelings as numbers between 0 and 1 and the dominant one (calm, worried, alarmed, relieved, happy, ...)."""
            return str(emotion.snapshot())

        @tool
        def recent_events() -> str:
            """The last few things that happened, oldest first."""
            return "; ".join(recent[-6:]) or "nothing yet"

        self.agent = Agent(model=self.model, system_prompt=SYSTEM.replace("{max_words}", "40"), tools=[current_feelings, recent_events], callback_handler=None)

    # ---- feelings -------------------------------------------------------------------------------------------
    def feel(self, t, event):
        self.emotion.feel(t, event)
        self.recent.append(f"{t:.0f}s {event}")

    def mood(self):
        return self.emotion.face()

    # ---- messages ------------------------------------------------------------------------------------------
    def phrase(self, kind, facts, default, audience="family", t=None):
        facts = dict(facts, patient=facts.get("patient", self.patient))
        label = self.emotion.label()
        text, source = None, "template"
        use_model = self.agent is not None and (self.remote is False or audience in ("family", "bystander"))
        if use_model and kind != "ambulance_call":
            try:
                text = self._ask(kind, facts, audience)
                source = "model"
            except Exception:
                text = None
        if not text:
            text = offline_text(kind, facts, label, self.name) or default
            source = "template"
        self.outbox.append(dict(t=None if t is None else round(float(t), 2), kind=kind, audience=audience, text=text, feeling=self.emotion.snapshot(), source=source))
        return text

    def _ask(self, kind, facts, audience):
        words = MAX_WORDS.get(audience, 40)
        must = [str(facts[k]) for k in ("room", "clock") if facts.get(k)]
        if kind == "chat_reply":                                    # the re-worded answer must keep every number and time of the factual answer
            must += re.findall(r"\d[\d:]*", str(facts.get("answer", "")))
        prompt = (f"Write the message of type '{kind}' for the audience '{audience}'. Use these facts exactly: "
                  + "; ".join(f"{k} = {v}" for k, v in facts.items() if k != "default")
                  + f". Say it in at most {words} words, in your current feelings (check current_feelings).")
        self.agent.messages.clear()
        out = str(self.agent(prompt)).strip().strip('"')
        low = out.lower()
        junk = out[:1] in ('{', '[') or '"parameters"' in out or '"name":' in out or len(out.split()) < 3     # a small model sometimes emits a tool call or a fragment
        if not out or junk or len(out.split()) > words + 15 or BANNED.search(out) or any(m.lower() not in low for m in must):
            raise ValueError("model answer failed the checks")
        return out
