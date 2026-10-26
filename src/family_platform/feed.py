"""
The link between the robot (simulation) and the family platform: three small files in one folder.

    state.json       the robot's latest status (written by the simulation about 4 times a second, replaced atomically)
    events.jsonl     everything Baymax said or sent, one JSON line each (append only)
    commands.jsonl   what the family asked for in the browser (appended by the server, read by the simulation)
    snapshot.png     the latest face-blurred picture, only if the patient agreed

Keeping it to files means the platform server and the simulation are separate processes that can be started, stopped and tested on their own.
Privacy by design: the feed carries status and text only. There is no video stream; a picture exists only after the family asks AND the patient
has agreed (Params.snapshot_consent), and the face is blurred on the robot before it is written.
"""
import json
import os
import time

DEFAULT_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "outputs", "platform"))


class FamilyFeed:
    def __init__(self, root=DEFAULT_DIR, reset=True):
        self.root = root
        os.makedirs(root, exist_ok=True)
        self.p_state = os.path.join(root, "state.json")
        self.p_events = os.path.join(root, "events.jsonl")
        self.p_cmds = os.path.join(root, "commands.jsonl")
        self.p_snap = os.path.join(root, "snapshot.png")
        self.p_chat = os.path.join(root, "chat_inbox.jsonl")
        self._chat_pos = 0
        self._cmd_pos = 0
        self.n_events = 0
        if reset:
            for p in (self.p_events, self.p_cmds, self.p_chat, self.p_snap, self.p_state, *(self.snapshot_path(v) for v in ('above', 'below', 'emergency'))):
                if os.path.exists(p):
                    os.remove(p)
            open(self.p_cmds, "w").close()
            open(self.p_chat, "w").close()

    # ---- simulation side -----------------------------------------------------------------------
    def write_state(self, state):
        tmp = self.p_state + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f)
        os.replace(tmp, self.p_state)

    def add_event(self, **ev):
        ev["n"] = self.n_events
        self.n_events += 1
        with open(self.p_events, "a") as f:
            f.write(json.dumps(ev) + "\n")

    def new_commands(self):
        """Commands the family sent since the last call."""
        if not os.path.exists(self.p_cmds):
            return []
        with open(self.p_cmds) as f:
            f.seek(self._cmd_pos)
            lines = f.readlines()
            self._cmd_pos = f.tell()
        out = []
        for ln in lines:
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
        return out

    def snapshot_path(self, view=None):
        return self.p_snap if view in (None, "", "ahead") else os.path.join(self.root, f"snapshot_{view}.png")

    def send_chat(self, user, text):
        """A signed-in family member's message to Baymax (server side)."""
        with open(self.p_chat, "a") as f:
            f.write(json.dumps(dict(user=user, text=str(text)[:300], wall=time.time())) + "\n")

    def new_chats(self):
        """Chat messages typed since the last call (simulation side)."""
        if not os.path.exists(self.p_chat):
            return []
        with open(self.p_chat) as f:
            f.seek(self._chat_pos)
            lines = f.readlines()
            self._chat_pos = f.tell()
        out = []
        for ln in lines:
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
        return out

    def write_snapshot(self, pil_image, view=None):
        path = self.snapshot_path(view)
        tmp = path + ".tmp.png"
        pil_image.save(tmp)
        os.replace(tmp, path)

    # ---- server side ---------------------------------------------------------------------------
    def read_state(self):
        try:
            with open(self.p_state) as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def read_events(self, since=0):
        out = []
        try:
            with open(self.p_events) as f:
                for i, ln in enumerate(f):
                    if i >= since:
                        out.append(json.loads(ln))
        except (OSError, ValueError):
            pass
        return out

    def send_command(self, cmd, args=None, who="family"):
        with open(self.p_cmds, "a") as f:
            f.write(json.dumps(dict(cmd=cmd, args=args or {}, who=who, wall=time.time())) + "\n")
