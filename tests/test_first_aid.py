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


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("PASS", n)
