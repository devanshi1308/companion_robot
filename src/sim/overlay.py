"""Video overlays for the demo: robot's-eye view with landmarks, state banner, event log, robot screen, family alerts."""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

MOOD_COL = {"watching": (54, 224, 232), "worried": (255, 176, 0), "happy": (51, 204, 89), "alert": (214, 69, 61)}
KIND_COL = {"reminder_missed": (47, 111, 221), "all_clear": (51, 204, 89), "heads_up": (255, 176, 0), "emergency": (214, 69, 61), "ambulance_call": (214, 69, 61), "update": (47, 111, 221)}
_FONTS = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _FONTS:
        for path in ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"):
            if os.path.exists(path):
                try:
                    _FONTS[key] = ImageFont.truetype(path, size, index=1 if (bold and path.endswith(".ttc")) else 0)
                    break
                except Exception:
                    continue
        else:
            _FONTS[key] = ImageFont.load_default()
    return _FONTS[key]


def wrap_text(draw, text, fnt, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def robot_screen(draw, x, y, w, h, mood, text):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=(11, 12, 14), outline=(70, 74, 82), width=2)
    col = MOOD_COL[mood]
    ey = y + h * 0.36
    for sx in (-1, 1):
        cx = x + w / 2 + sx * w * 0.2
        if mood == "happy":
            draw.arc([cx - 16, ey - 12, cx + 16, ey + 14], 200, 340, fill=col, width=5)
        else:
            eh = 17 if mood != "worried" else 14
            draw.rounded_rectangle([cx - 11, ey - eh, cx + 11, ey + eh], radius=6, fill=col)
        if mood == "worried":
            draw.line([cx - sx * 16, ey - 26, cx + sx * 9, ey - 19], fill=col, width=3)
    if text.startswith("Time for"):                                   # pill icon (medicine reminder, demo only)
        px, py = x + w / 2, y + h * 0.58
        draw.rounded_rectangle([px - 18, py - 7, px + 18, py + 7], radius=7, fill=col)
        draw.rounded_rectangle([px, py - 7, px + 18, py + 7], radius=7, fill=(240, 240, 240))
    if text:
        fnt = font(13, True)
        draw.text((x + w / 2, y + h * 0.80), text, fill=col, font=fnt, anchor="mm")


def compose(overview, cam_rgb, obs, comp, disp, t, size=(640, 480), panel=250):
    W, H = size
    canvas = Image.new("RGB", (W, H + panel), (20, 22, 26))
    canvas.paste(Image.fromarray(overview), (0, 0))
    d = ImageDraw.Draw(canvas)
    # robot's-eye view (picture in picture) with landmarks
    pw, ph = 210, 158
    cam = Image.fromarray(cam_rgb).resize((pw, ph))
    cd = ImageDraw.Draw(cam)
    if obs is not None:
        for (u, v), vis in zip(obs.pix, obs.vis):
            if vis > 0.5:
                cd.ellipse([u / W * pw - 2, v / H * ph - 2, u / W * pw + 2, v / H * ph + 2], fill=(255, 40, 40))
    canvas.paste(cam, (W - pw - 8, 8))
    d.rectangle([W - pw - 8, 8, W - 8, 8 + ph], outline=(255, 255, 255), width=2)
    d.text((W - pw - 4, 10), "robot's eye (on-board only)", fill=(255, 255, 255), font=font(11, True))
    # banner
    banner = {"WATCH": "WATCHING", "FOLLOW": "FOLLOWING HER", "SEARCH": "LOOKING FOR HER", "OBSERVE": "SHE IS ON THE FLOOR - WATCHING", "SUSPECT": "FALL SUSPECTED - WATCHING", "APPROACH": "FALL SUSPECTED - APPROACHING", "CHECK_IN": "CHECKING ON HER", "ALERT": "EMERGENCY - FAMILY ALERTED"}[comp.state]
    if getattr(comp, "purpose", "fall") == "reminder" and comp.state in ("APPROACH", "CHECK_IN"):
        banner = "MEDICINE REMINDER - GOING TO HER" if comp.state == "APPROACH" else "MEDICINE REMINDER - WAITING FOR HER OK"
    col = {"WATCH": (54, 224, 232), "FOLLOW": (54, 224, 232), "SEARCH": (255, 176, 0), "OBSERVE": (255, 176, 0), "SUSPECT": (255, 176, 0), "APPROACH": (255, 176, 0), "CHECK_IN": (255, 176, 0), "ALERT": (214, 69, 61)}[comp.state]
    d.rounded_rectangle([8, 8, 330, 52], radius=8, fill=(0, 0, 0, 200))
    d.text((16, 13), f"t = {t:5.1f} s", fill=(255, 255, 255), font=font(15, True))
    d.text((16, 31), banner, fill=col, font=font(13, True))
    # bottom panel: events (left), robot screen + alerts (right)
    y0 = H + 6
    d.text((10, y0), "What the robot does", fill=(150, 156, 166), font=font(11, True))
    ev = comp.events[-7:]
    for i, (te, text) in enumerate(ev):
        fnt = font(11)
        line = f"{te:5.1f}s  {text}"
        line = line if d.textlength(line, font=fnt) < 400 else line[:62] + "..."
        d.text((10, y0 + 16 + i * 18), line, fill=(225, 228, 233), font=fnt)
    robot_screen(d, 430, y0 + 2, 200, 70, comp.rb.mood, comp.screen_text)
    # alerts as phone-style cards
    kinds = {}
    for s in disp.sent:
        kinds.setdefault(s["kind"], []).append(s)
    cards = []
    if "heads_up" in kinds:
        cards.append(("heads_up", "Family: heads-up (text)", kinds["heads_up"][0]))
    if "emergency" in kinds:
        names = sorted({s["to"].split(" ")[0] for s in kinds["emergency"]})
        cards.append(("emergency", "URGENT to " + ", ".join(names), kinds["emergency"][0]))
    if "ambulance_call" in kinds:
        cards.append(("ambulance_call", "Ambulance call (108, simulated)", kinds["ambulance_call"][0]))
    if "reminder_missed" in kinds:
        cards.append(("reminder_missed", "Family: reminder missed (text)", kinds["reminder_missed"][0]))
    if "all_clear" in kinds:
        cards.append(("all_clear", "Family: all clear (text)", kinds["all_clear"][0]))
    cy = y0 + 78
    for kind, title, rec in cards[-3:]:
        c = KIND_COL[kind]
        d.rounded_rectangle([430, cy, 630, cy + 34], radius=6, fill=(38, 41, 48), outline=c, width=2)
        d.text((436, cy + 3), f"{rec['clock']}  {title}", fill=c, font=font(11, True))
        body = rec["text"][:46] + "..."
        d.text((436, cy + 18), body, fill=(205, 208, 214), font=font(9))
        cy += 38
    return canvas
