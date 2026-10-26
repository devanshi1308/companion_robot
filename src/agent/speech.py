"""The robot's voice: what the robot says out loud (check-in, first-aid guidance, reminders) is spoken with the computer's own text-to-speech.

macOS: the built-in `say` command (offline, nothing leaves the machine). Other systems: no sound, the text still appears in the log and on the family page.
Voice: COMPANION_VOICE (default: an installed male Enhanced/Premium voice, else Rishi (Indian English, male)); rate COMPANION_RATE words per minute (default 150, slow and calm); volume COMPANION_VOLUME 0-1 (default 0.7). For the most natural sound download an Enhanced or Premium voice in System Settings, Accessibility, Spoken Content, System Voice, Manage Voices.
Simulation only: this plays through the laptop speakers; it is never a real call. Experiments never use it (the harness leaves the speaker unset).

    python src/agent/speech.py "Hello, I am Momo."
"""
import os
import queue
import shutil
import subprocess
import sys
import threading

RATE = os.environ.get("COMPANION_RATE", "150")
VOLUME = os.environ.get("COMPANION_VOLUME", "0.7")      # 0 to 1: a soft voice, not a loud one


def pick_voice():
    """A gentle voice: an installed Enhanced or Premium English voice if there is one (they sound far more natural), else Rishi (a calm male voice)."""
    if os.environ.get("COMPANION_VOICE"):
        return os.environ["COMPANION_VOICE"]
    male = ("Rishi", "Daniel", "Evan", "Tom", "Aaron", "Oliver", "Lee", "Reed", "Alex", "Arthur", "Gordon")        # the robot is male
    try:
        out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, timeout=10).stdout
        for tag in ("Premium", "Enhanced"):
            for line in out.splitlines():
                name = line.split("  ")[0].strip()
                if tag in name and " en_" in line and any(m in name for m in male):
                    return name
    except Exception:
        pass
    return "Rishi"


VOICE = pick_voice() if shutil.which("say") else "Rishi"


def soften(text, volume=VOLUME):
    """Gentler delivery: lower volume, small pauses after commas and sentences so it sounds like speech, not a read-out."""
    t = text.replace(". ", ". [[slnc 420]] ").replace("? ", "? [[slnc 420]] ").replace(", ", ", [[slnc 160]] ").replace(": ", ": [[slnc 200]] ")
    return f"[[volm {volume}]] {t}"


class Speaker:
    def __init__(self, voice=VOICE, rate=RATE):
        self.voice, self.rate = voice, str(rate)
        self.ok = shutil.which("say") is not None
        self.q = queue.Queue()
        self.proc = None
        if self.ok:
            threading.Thread(target=self._run, daemon=True).start()

    def say(self, text, urgent=False):
        """Queue a sentence. An urgent one (first aid for a bystander) cuts off whatever is being said."""
        if not self.ok or not text:
            return
        if urgent:
            self.stop(clear=True)
        self.q.put(str(text).replace("[URGENT]", "").strip())

    def stop(self, clear=False):
        if clear:
            try:
                while True:
                    self.q.get_nowait()
            except queue.Empty:
                pass
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

    def _run(self):
        while True:
            text = self.q.get()
            try:
                self.proc = subprocess.Popen(["say", "-v", self.voice, "-r", self.rate, soften(text)])
                self.proc.wait()
            except Exception:
                pass


if __name__ == "__main__":
    sp = Speaker()
    sp.say(" ".join(sys.argv[1:]) or "Hello, I am Momo. I am here with you.")
    import time
    time.sleep(6)
