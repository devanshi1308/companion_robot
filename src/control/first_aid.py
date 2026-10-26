"""First-aid guidance the robot SAYS (fixed scripts, never written by a language model, never a diagnosis).

The robot has no arms: it cannot touch or treat anyone. What it can do is keep her calm and still, and talk a bystander or the family through the
standard first steps while help is coming. Sources: hands-only CPR steps follow the AHA 2020 adult basic life support guideline (Panchal et al.,
Circulation 2020, doi 10.1161/CIR.0000000000000916); the 'do not get up quickly' advice is the usual lay guidance after a fall. Simulation only:
no real call is placed. These texts should be reviewed by a clinician before any real use.
"""

CONSCIOUS_CHECK = ("Please stay where you are and do not try to get up quickly. I am scanning you now. Tell me if anything hurts, especially your chest, head, neck, hip or back. "
                   "On a scale of one to ten, how would you rate your pain?")
CONSCIOUS_OK = ("Your voice sounds steady. I am glad you are well. Stay still for a moment and breathe slowly. If nothing hurts, roll to your side, rest on your hands and knees, "
                "and get up slowly using a sturdy chair. If anything hurts, stay down and tell me, and I will get help.")
BYSTANDER = ("Someone please help. She is not answering. Call 108 now. Check if she is breathing normally. "
             "If she is not breathing normally, start chest compressions: push hard and fast in the centre of her chest, "
             "about 100 to 120 times a minute, and do not stop until help arrives. If there is a defibrillator nearby, send someone to fetch it.")
FAMILY_STEPS = ("While you wait for the ambulance: call 108 yourself if you are near, and if someone is with her, they should check her breathing "
                "and, if she is not breathing normally, start hard, fast chest compressions (100 to 120 a minute) until help arrives.")
