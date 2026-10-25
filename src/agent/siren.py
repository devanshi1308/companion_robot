"""
The alarm the robot sounds when she has collapsed and does not answer: a wailing two-tone siren (650 and 950 Hz alternating twice a second, like
a personal alarm) with a harsh upper partial so it carries through walls, plus a simple sound-level model.

    python src/agent/siren.py                    writes outputs/siren_demo.wav (6 s, safe to play at normal volume: the file is scaled to -6 dBFS)
    python src/agent/siren.py --play             also plays it through the speakers (needs the sounddevice package)

In the simulation nothing is played unless a live demo asks for it (run_platform_demo.py --sound); the siren's start, stop and level are logged
and shown on the family platform. The level (dB at 1 m) is a design figure for a small speaker, not a measurement.
"""
import argparse
import os
import wave

import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SR = 22050


def synth_siren(seconds=6.0, sr=SR):
    t = np.arange(int(seconds * sr)) / sr
    f = np.where((t * 2.0) % 1.0 < 0.5, 650.0, 950.0)                       # two tones, switching every 0.25 s
    f = np.convolve(f, np.ones(200) / 200, mode="same")                      # glide between them instead of clicking
    phase = 2 * np.pi * np.cumsum(f) / sr
    x = np.sin(phase) + 0.45 * np.sin(2 * phase) + 0.25 * np.sin(3 * phase)  # harsh harmonics carry further
    x = x / np.abs(x).max() * 0.5                                            # -6 dBFS
    return x.astype(np.float32)


def write_wav(path, x, sr=SR):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    return path


def level_at(distance_m, level_db_1m=95.0, wall_loss_db=0.0):
    """Sound level (dB) at a distance in free field (-6 dB per doubling) minus a loss for walls in between (a closed door is roughly 25 dB)."""
    return level_db_1m - 20.0 * np.log10(max(distance_m, 0.1)) - wall_loss_db


def distance_for_level(target_db, level_db_1m=95.0, wall_loss_db=0.0):
    """How far away the siren is still at least target_db (e.g. 60 dB = noticeable over a conversation)."""
    return 10 ** ((level_db_1m - wall_loss_db - target_db) / 20.0)


class SirenPlayer:
    """Plays the siren in a loop through the speakers while it is 'on' (live demo only)."""

    def __init__(self):
        self.stream = None

    def start(self):
        import sounddevice as sd
        x = synth_siren(2.0)
        pos = [0]

        def cb(out, frames, time_info, status):
            idx = (np.arange(frames) + pos[0]) % len(x)
            out[:, 0] = x[idx]
            pos[0] += frames

        self.stream = sd.OutputStream(samplerate=SR, channels=1, callback=cb)
        self.stream.start()

    def stop(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--play", action="store_true")
    a = ap.parse_args()
    path = write_wav(os.path.join(ROOT, "outputs", "siren_demo.wav"), synth_siren())
    print("wrote", os.path.relpath(path, ROOT))
    print(f"design level 95 dB at 1 m: {level_at(5):.0f} dB at 5 m in the same room, still {level_at(5, wall_loss_db=25):.0f} dB at 5 m behind a closed door; "
          f"60 dB is reached out to {distance_for_level(60):.0f} m in the open and {distance_for_level(60, wall_loss_db=25):.1f} m through one closed door")
    if a.play:
        import sounddevice as sd
        sd.play(synth_siren(), SR)
        sd.wait()
