"""General first-aid and medicine knowledge the robot can talk about. FIXED, REVIEWED TEXT (never written by a language model, never a diagnosis).

The robot is not a doctor and cannot touch anyone. It can read out the standard first steps and explain what a common medicine is for. It never tells
anyone to start, stop or change a medicine or a dose: that is for her doctor or pharmacist. In India, call 108 (ambulance) or 112 (all emergencies).

Sources for the first-aid steps: AHA 2020 adult basic life support (Panchal et al., Circulation 2020, doi 10.1161/CIR.0000000000000916) for CPR, and the
usual lay first-aid guidance (Red Cross, NHS) for the rest. Medicine facts are general, standard product information. This text must be reviewed by a
clinician or pharmacist before any real use; it is a simulation demo.
"""
import re

CAUTION = "I am not a doctor. This is general information: ask her doctor or pharmacist before any change, and call 108 in an emergency."

# ---- first aid: topic -> (trigger words, steps) -------------------------------------------------------------------------------
FIRST_AID = {
    "cpr": (
        ("cpr", "chest compression", "resuscitat", "cardiac arrest", "not breathing", "no pulse", "unresponsive", "collapsed and not"),
        "If she does not answer and is not breathing normally (or only gasping): 1. Shout for help and call 108 now, on speaker. 2. Lay her flat on her back on a firm floor. "
        "3. Kneel beside her, put the heel of one hand on the centre of her chest, the other hand on top. 4. Push hard and fast, at least 5 centimetres deep, "
        "100 to 120 times a minute (about two pushes a second), and let the chest rise fully each time. 5. Do not stop until help arrives, she starts breathing, "
        "or an AED is ready. If you are trained, give 2 breaths after every 30 pushes. 6. If a defibrillator (AED) is there, switch it on and follow its voice. "
        "Do not stop to check her pulse again and again."),
    "aed": (
        ("aed", "defibrillat", "shock"),
        "AED: switch it on, it talks you through the steps. Bare her chest, dry it, stick the pads where the pictures show (upper right chest, lower left side), "
        "make sure nobody touches her, and let the machine analyse. If it says shock, press the button after everyone steps back. Then go straight back to chest compressions."),
    "heart_attack": (
        ("heart attack", "chest pain", "chest pressure", "tight chest", "pain in arm", "jaw pain"),
        "Signs of a heart attack: pressure, squeezing or pain in the centre of the chest, spreading to the arm, jaw, neck or back, with sweating, breathlessness, "
        "nausea or feeling faint. Women and older people can have milder or unusual signs. Call 108 immediately. Sit her down, rest and keep her calm, loosen tight clothes. "
        "If she is not allergic and the 108 operator advises it, she can chew one regular aspirin. If she has her own prescribed chest-pain spray or tablet (GTN), "
        "she can use it as her doctor told her. If she collapses and is not breathing normally, start CPR."),
    "stroke": (
        ("stroke", "face droop", "slurred", "weakness one side", "numb"),
        "Stroke: use FAST. Face drooping on one side, Arm weak or numb, Speech slurred or confused, Time to call 108 immediately. Note the time it started. "
        "Keep her sitting or lying with the head slightly raised, give nothing to eat or drink, and stay with her."),
    "choking": (
        ("choking", "choke", "something stuck in throat"),
        "Choking: if she can cough, let her cough. If she cannot speak, cough or breathe: give up to 5 firm back blows between the shoulder blades, then up to 5 abdominal thrusts "
        "(stand behind her, fist above the belly button, pull sharply in and up). Alternate until it clears. Call 108. If she goes limp and unresponsive, start CPR."),
    "bleeding": (
        ("bleeding", "bleed", "cut", "wound", "blood"),
        "Bleeding: press firmly on the wound with a clean cloth and keep pressing, do not lift it to look. If it soaks through, add more cloth on top. "
        "Raise the injured arm or leg if you can. Call 108 for heavy bleeding. Keep her lying down and warm."),
    "fall": (
        ("fall", "fell", "fallen", "hip", "fracture", "broken bone", "head injury", "hit her head"),
        "After a fall: do not rush her up. Ask where it hurts. If she has neck, back or hip pain, cannot move a leg, or hit her head and is drowsy or confused, "
        "do not move her; keep her warm and call 108. If nothing hurts, help her roll to her side, up to hands and knees, then onto a sturdy chair, slowly. "
        "She should be checked by a doctor after any fall, and if she is on blood thinners even a small head knock needs a check."),
    "faint": (
        ("faint", "fainted", "dizzy", "dizziness", "passed out", "blackout"),
        "Fainting or dizziness: lay her flat and raise her legs about 30 centimetres, loosen tight clothes, give air. She should wake within a minute. "
        "If she does not wake, is not breathing normally, or has chest pain, call 108. Do not sit her up quickly or give drinks until she is fully awake. Tell her doctor afterwards."),
    "low_sugar": (
        ("low sugar", "hypoglyc", "sugar low", "shaky and sweating"),
        "Low blood sugar (a risk with diabetes medicines such as insulin): shaky, sweaty, confused, hungry. If she is awake and can swallow, give fast sugar: "
        "3 glucose tablets, or half a glass of juice or a sugary drink, then check again in 15 minutes and give a snack. If she is drowsy or unconscious, give nothing by mouth and call 108."),
    "burn": (
        ("burn", "scald"),
        "Burn: cool it under cool running water for at least 10 minutes, take off rings or tight items near it, cover loosely with cling film or a clean cloth. "
        "No ice, creams or butter. Call 108 for large, deep or face burns."),
}

# ---- medicines: name -> (what it is, what it is for, cautions) ----------------------------------------------------------------
MEDICINES = {
    "aspirin": ("a blood-thinning pain reliever", "protecting against heart attack and stroke (low dose) and pain or fever",
                "can cause stomach bleeding; not for people allergic to it or with active ulcers unless a doctor says; extra bleeding risk with warfarin; take with food"),
    "paracetamol": ("a pain and fever medicine (acetaminophen)", "mild pain and fever",
                    "do not exceed the daily limit on the pack (usually 4 grams in 24 hours for adults, often less for frail older people); check other cold medicines for hidden paracetamol; too much harms the liver"),
    "ibuprofen": ("an anti-inflammatory pain medicine (NSAID)", "pain, swelling, fever",
                  "can upset the stomach, raise blood pressure and harm kidneys; older people and people on blood thinners or with heart or kidney problems should ask a doctor first"),
    "metformin": ("a diabetes tablet", "controlling blood sugar in type 2 diabetes",
                  "take with meals; stomach upset is common; tell the doctor if vomiting, dehydrated or having a scan with contrast; kidney function should be checked"),
    "insulin": ("a hormone injection", "controlling blood sugar in diabetes",
                "too much or a missed meal can cause low sugar (shaky, sweaty, confused); the dose and timing are set by her doctor; store as directed"),
    "amlodipine": ("a calcium-channel blocker", "high blood pressure and angina",
                   "can cause ankle swelling, flushing, dizziness; stand up slowly; do not stop suddenly"),
    "atenolol": ("a beta-blocker", "high blood pressure, heart rhythm and angina",
                 "slows the heart; can cause tiredness, cold hands, dizziness; do not stop suddenly; can hide the signs of low sugar"),
    "metoprolol": ("a beta-blocker", "high blood pressure, heart failure and rhythm problems",
                   "slows the heart; can cause tiredness and dizziness; do not stop suddenly"),
    "losartan": ("an angiotensin receptor blocker (ARB)", "high blood pressure and kidney protection",
                 "can cause dizziness and raise potassium; kidney tests are needed; not in pregnancy"),
    "enalapril": ("an ACE inhibitor", "high blood pressure and heart failure",
                  "can cause a dry cough, dizziness; rarely swelling of lips or face (call 108); kidney and potassium tests needed"),
    "atorvastatin": ("a statin", "lowering cholesterol and protecting the heart",
                     "report unexplained muscle pain or weakness; usually taken once a day, often in the evening; avoid large amounts of grapefruit juice"),
    "warfarin": ("a blood thinner", "preventing clots (irregular heartbeat, clots in legs or lungs, some valves)",
                 "needs regular INR blood tests; bleeding and bruising risk; falls and head knocks need a doctor even if small; many medicines and foods rich in vitamin K change its effect"),
    "clopidogrel": ("an antiplatelet", "preventing clots after a heart attack, stent or stroke",
                    "bleeding and bruising risk; tell dentists and surgeons; do not stop on your own"),
    "furosemide": ("a water tablet (loop diuretic)", "fluid build-up in heart failure and swelling, and high blood pressure",
                   "makes her pass more urine; risk of dizziness, dehydration and low potassium; often taken in the morning; a fall risk"),
    "levothyroxine": ("thyroid hormone", "an underactive thyroid",
                      "take on an empty stomach, 30 to 60 minutes before breakfast, apart from calcium or iron; blood tests guide the dose"),
    "pantoprazole": ("an acid-reducing medicine (PPI)", "heartburn and stomach ulcers",
                     "usually taken before breakfast; long use can lower magnesium or B12; ask the doctor how long to continue"),
    "nitroglycerin": ("a chest-pain medicine (GTN)", "relieving or preventing angina, a squeezing chest pain",
                      "used under the tongue or as a spray, sitting down because it can drop blood pressure and cause dizziness; if the pain is not relieved as her doctor described, call 108; never with sildenafil-type medicines"),
    "donepezil": ("a memory medicine", "mild to moderate Alzheimer's disease",
                  "can cause nausea, slow heartbeat, vivid dreams; do not stop suddenly; report fainting"),
    "gabapentin": ("a nerve-pain and seizure medicine", "nerve pain and some seizures",
                   "can cause drowsiness, dizziness and unsteadiness, so it raises fall risk; do not stop suddenly"),
    "levodopa": ("a Parkinson's medicine", "Parkinson's disease",
                 "timing matters; can cause dizziness on standing and nausea; protein-rich meals can reduce its effect; do not stop suddenly"),
}

GENERAL_MEDICINE = [
    "Keep one up-to-date list of every medicine, dose and time, including tablets from the chemist, and bring it to every doctor visit.",
    "Never stop, start or change a dose without her doctor or pharmacist. If a dose is missed, the right advice depends on the medicine, so ask the pharmacist: do not double up.",
    "Medicines that raise fall risk in older people: sleeping tablets, some blood-pressure and water tablets, nerve-pain medicines, strong painkillers. Report new dizziness.",
    "Report to a doctor: new confusion, fainting, black stools, unusual bruising or bleeding, swelling of face or lips (call 108), a rash, or a sudden change after a new medicine.",
]


def _norm(t):
    return re.sub(r"[^a-z0-9' ]", " ", t.lower())


def medicine_answer(text):
    t = _norm(text)
    aliases = {"acetaminophen": "paracetamol", "crocin": "paracetamol", "dolo": "paracetamol", "ecosprin": "aspirin", "glycomet": "metformin",
               "lasix": "furosemide", "coumadin": "warfarin", "plavix": "clopidogrel", "lipitor": "atorvastatin", "norvasc": "amlodipine",
               "gtn": "nitroglycerin", "sorbitrate": "nitroglycerin", "eltroxin": "levothyroxine", "thyronorm": "levothyroxine", "metoprolol": "metoprolol", "telmisartan": "losartan"}
    for alias, name in aliases.items():
        if re.search(rf"\b{alias}\b", t):
            t = t + " " + name
    hits = [n for n in MEDICINES if re.search(rf"\b{n}\b", t)]
    if hits:
        parts = []
        for n in hits[:3]:
            what, use, caution = MEDICINES[n]
            parts.append(f"{n.capitalize()} is {what}, used for {use}. Things to know: {caution}.")
        return " ".join(parts) + " " + CAUTION
    if re.search(r"\b(missed (a )?dose|forgot (to take )?(her )?(tablet|medicine|dose)|double (the )?dose)\b", t):
        return GENERAL_MEDICINE[1]
    if re.search(r"\b(side effect|interaction|medicine list|which medicine|all (her )?medicines|medicine safety|fall risk)\b", t):
        return " ".join(GENERAL_MEDICINE) + " " + CAUTION
    return None


PREVENTION = ("Ways to lower the risk of falls: clear tripping hazards (loose rugs, cables, clutter), keep rooms and the way to the bathroom well lit at night, "
              "fit handrails and non-slip mats in the bathroom and on stairs, wear well-fitting shoes with grip, keep daily gentle exercise that builds balance and leg strength "
              "(for example a physiotherapist's programme or tai chi), get eyesight and hearing checked, rise slowly from bed or a chair, and ask the doctor or pharmacist to review "
              "her medicines because some cause dizziness. A bed or chair that is easy to get out of helps too. " + CAUTION)


def first_aid_answer(text):
    t = _norm(text)
    if re.search(r"\b(prevent|avoid|stop|reduce|lower|tips?|safer|risk of)\b.*\b(fall|falls|falling|fallen)\b|\b(fall|falls|falling)\b.*\b(prevent|prevention|avoid|tips?)\b", t):
        return PREVENTION
    best = None
    for name, (words, steps) in FIRST_AID.items():
        if any(w in t for w in words):
            best = best or (name, steps)
            if name in ("cpr", "heart_attack", "stroke", "choking") and any(w in t for w in words):
                best = (name, steps)
                break
    if best is None:
        if re.search(r"\b(first aid|emergency steps|what (should|do) i do)\b", t):
            return ("I can talk you through: CPR, a defibrillator (AED), heart attack signs, stroke, choking, bleeding, a fall, fainting, low blood sugar and burns. Say which one. "
                    "In any emergency call 108 first.")
        return None
    return best[1] + " Call 108 first. " + CAUTION


def lookup(text):
    """Answer a first-aid or medicine question from the fixed knowledge, or None."""
    return first_aid_answer(text) or medicine_answer(text)


# What the robot says out loud, step by step, while she is down and not answering: keeps the helper going (AHA: do not stop compressions).
COACH = [
    "Keep going. Push hard and fast in the centre of her chest, about two pushes every second.",
    "You are doing well. Let the chest come back up fully between pushes, and do not stop.",
    "If someone is with you, take turns every two minutes, and change quickly so the pushes do not stop.",
    "Is there a defibrillator nearby? If so, send someone to fetch it, and switch it on when it arrives.",
    "Help is on the way. Keep pushing, I am here with you.",
]
