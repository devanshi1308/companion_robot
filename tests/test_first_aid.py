"""The first-aid scripts are fixed text: no diagnosis wording, and the emergency one tells a bystander to call 108 and start compressions."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "control"))
import first_aid as F  # noqa: E402

BANNED = re.compile(r"\b(heart attack|stroke|you have|she has|diagnos|myocardial|fractured|broken)\b", re.I)


def test_scripts_do_not_diagnose():
    for t in (F.CONSCIOUS_CHECK, F.CONSCIOUS_OK, F.BYSTANDER, F.FAMILY_STEPS):
        assert not BANNED.search(t), t


def test_bystander_script_has_the_key_steps():
    assert "108" in F.BYSTANDER and "100 to 120" in F.BYSTANDER and "breathing" in F.BYSTANDER and "defibrillator" in F.BYSTANDER
    assert len(F.BYSTANDER.split()) < 90


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "agent"))
import health_knowledge as H  # noqa: E402
import chat  # noqa: E402


def test_cpr_and_medicine_questions_are_answered_from_fixed_text():
    cpr = H.lookup("how do I do CPR")
    assert "108" in cpr and "100 to 120" in cpr and "5 centimetres" in cpr
    m = H.lookup("what is metformin for?")
    assert "diabetes" in m and "doctor or pharmacist" in m
    assert "Aspirin" in H.lookup("what is ecosprin")
    assert H.lookup("hello, how are you") is None


def test_knowledge_never_diagnoses_or_gives_personal_doses():
    verdict = re.compile(r"\b(she has had|she is having|you have a|she has a|diagnos)", re.I)        # naming a condition in a list of signs is fine, giving a verdict is not
    for name, (words, steps) in H.FIRST_AID.items():
        assert not verdict.search(steps), name
    for name, (what, use, caution) in H.MEDICINES.items():
        assert not re.search(r"\b\d+ ?(mg|ml|tablets? a day)\b", caution), name


def test_chat_uses_the_knowledge_but_keeps_status_questions():
    f = dict(patient="Asha", person={}, robot={}, alert={}, doses=[])
    reply, _ = chat.answer("how to do CPR?", f)
    assert "108" in reply and "100 to 120" in reply
    reply, _ = chat.answer("what is warfarin?", f)
    assert "blood thinner" in reply
    reply, _ = chat.answer("did she take her aspirin?", f)
    assert "Aspirin is" not in reply, "a status question is answered from the robot's facts, not the medicine book"


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("PASS", n)
