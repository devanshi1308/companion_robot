"""The robot's voice: what the robot says out loud (check-in, first-aid guidance, reminders) is spoken with the computer's own text-to-speech.

macOS: the built-in `say` command (offline, nothing leaves the machine). Other systems: no sound, the text still appears in the log and on the family page.
Voice: COMPANION_VOICE (default Samantha); speaking rate COMPANION_RATE words per minute (default 165, a little slower than normal for an older listener).
Simulation only: this plays through the laptop speakers; it is never a real call. Experiments never use it (the harness leaves the speaker unset).

    python src/agent/speech.py "Hello, I am Momo."
"""
import os
import queue
import shutil
import subprocess
import sys
import threading

VOICE = os.environ.get("COMPANION_VOICE", "Samantha")
RATE = os.environ.get("COMPANION_RATE", "165")


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
                self.proc = subprocess.Popen(["say", "-v", self.voice, "-r", self.rate, text])
                self.proc.wait()
            except Exception:
                pass


if __name__ == "__main__":
    sp = Speaker()
    sp.say(" ".join(sys.argv[1:]) or "Hello, I am Momo. I am here with you.")
    import time
    time.sleep(6)
