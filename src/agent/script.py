"""Baymax's script: what the robot says in each situation. Calm, caring, literal, short sentences, in the style of a gentle healthcare companion.

All lines are original wording written for this project (the robot's name and manner are inspired by the film character; no dialogue is copied).
Safety lines (first aid, CPR, the ambulance script) live in src/control/first_aid.py and are never re-worded by a language model.
Only the patient-facing and bystander-facing lines are spoken aloud; family texts stay text on the family page.
"""

NAME = "Baymax"

INTRO = ("Hello. I am Baymax, your personal healthcare assistant robot. "
         "I am here to look after your health and keep you safe. "
         "I will walk with you, watch for falls, remind you about your medicine, and call for help if you need it. "
         "If anything hurts, please tell me.")

LINES = {
    # --- every day --------------------------------------------------------------------------------------------------
    "greet_morning": "Good morning. I hope you slept well. How are you feeling today?",
    "greet_evening": "Good evening. Shall we make sure everything is in order before you rest?",
    "following": "I will stay close to you, but not too close.",
    "lost_you": "I cannot see you right now. I am coming to find you.",
    "found_you": "There you are. I am glad I found you.",
    "idle": "I am here if you need me.",
    # --- medicine ---------------------------------------------------------------------------------------------------
    "reminder": "It is time for {label}. Please take it with a glass of water, and say OK when you have.",
    "reminder_repeat": "A gentle reminder about {label}. Please say OK when you have taken it.",
    "tablet_taken": "Thank you. I saw you take {label}. That was well done.",
    "tablet_missed": "I did not see you take {label}. I will let your family know, so nobody worries.",
    # --- a fall -----------------------------------------------------------------------------------------------------
    "found_on_floor": "I noticed you are on the floor. I am coming to you now. Please stay where you are.",
    "scanning": "I am scanning you now. Please stay still.",
    "check_in": "I am Baymax, your personal healthcare assistant robot. I noticed you are on the floor. Are you hurt?",
    "pain_scale": "On a scale of one to ten, how would you rate your pain?",
    "reprompt": "I did not hear you. If you can hear me, please say something or wave. I am staying with you.",
    "reassure": "You are not alone. I am here with you, and help is on the way.",
    "all_clear": "Your voice sounds steady. I am glad you are well. Stay still for a moment, then get up slowly.",
    "get_up": "When you are ready, roll onto your side, come up onto your hands and knees, and use the chair to stand. Slowly, please.",
    "satisfied": "Are you feeling better now? I will stay nearby.",
    # --- no answer: the emergency (spoken to anyone nearby) -----------------------------------------------------------
    "emergency_alert": "Someone please help. She is not answering me.",
    "family_notified": "I have told her family and called an ambulance. They are coming.",
    # --- shutdown -----------------------------------------------------------------------------------------------------
    "goodbye": "I will rest now. If you need me, say my name, Baymax, and I will be right here.",
}


def line(key, **kw):
    return LINES[key].format(**kw)
