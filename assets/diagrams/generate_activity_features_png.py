from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math

OUT = Path(__file__).resolve().parent / "activity_features_mangodefend.png"
W, H = 3000, 1900

WHITE = (255, 255, 255)
BLACK = (23, 23, 23)
GRAY = (248, 250, 252)
BLUE = (219, 234, 254)
GREEN = (220, 252, 231)
ORANGE = (255, 237, 213)
PURPLE = (243, 232, 255)
YELLOW = (254, 249, 195)
RED = (254, 226, 226)


def get_font(size=24, bold=False):
    candidates = []
    if bold:
        candidates += ["C:/Windows/Fonts/Inter-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]
    candidates += ["C:/Windows/Fonts/Inter-Regular.ttf", "C:/Windows/Fonts/arial.ttf"]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()


F_TITLE = get_font(46, True)
F_HEAD = get_font(26, True)
F_TEXT = get_font(19)
F_SMALL = get_font(17)


def wrapped_lines(draw, text, font, max_width):
    words = text.split()
    lines = []
    line = []
    for w in words:
        candidate = " ".join(line + [w])
        bb = draw.textbbox((0, 0), candidate, font=font)
        if bb[2] - bb[0] <= max_width:
            line.append(w)
        else:
            if line:
                lines.append(" ".join(line))
            line = [w]
    if line:
        lines.append(" ".join(line))
    return lines


def lane(draw, xy, title, fill):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=16, fill=fill, outline=BLACK, width=3)
    draw.text((x1 + 16, y1 + 10), title, fill=BLACK, font=F_HEAD)


def step_box(draw, xy, title, fill=GRAY):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=12, fill=fill, outline=BLACK, width=2)
    w = x2 - x1 - 20
    lines = wrapped_lines(draw, title, F_TEXT, w)
    total_h = len(lines) * 26
    y = y1 + ((y2 - y1 - total_h) // 2)
    for ln in lines:
        bb = draw.textbbox((0, 0), ln, font=F_TEXT)
        tw = bb[2] - bb[0]
        draw.text((x1 + (x2 - x1 - tw) // 2, y), ln, fill=BLACK, font=F_TEXT)
        y += 26


def decision(draw, center, size, text):
    cx, cy = center
    w, h = size
    pts = [(cx, cy - h // 2), (cx + w // 2, cy), (cx, cy + h // 2), (cx - w // 2, cy)]
    draw.polygon(pts, fill=YELLOW, outline=BLACK)
    lines = wrapped_lines(draw, text, F_SMALL, w - 30)
    y = cy - (len(lines) * 22) // 2
    for ln in lines:
        bb = draw.textbbox((0, 0), ln, font=F_SMALL)
        tw = bb[2] - bb[0]
        draw.text((cx - tw // 2, y), ln, fill=BLACK, font=F_SMALL)
        y += 22


def arrow(draw, p1, p2, label=None):
    x1, y1 = p1
    x2, y2 = p2
    draw.line((x1, y1, x2, y2), fill=BLACK, width=3)
    ang = math.atan2(y2 - y1, x2 - x1)
    l = 14
    p3 = (x2 - int(l * math.cos(ang - 0.45)), y2 - int(l * math.sin(ang - 0.45)))
    p4 = (x2 - int(l * math.cos(ang + 0.45)), y2 - int(l * math.sin(ang + 0.45)))
    draw.polygon([p2, p3, p4], fill=BLACK)
    if label:
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2
        bb = draw.textbbox((0, 0), label, font=F_SMALL)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        draw.rectangle((mx - tw // 2 - 8, my - th // 2 - 4, mx + tw // 2 + 8, my + th // 2 + 4), fill=WHITE)
        draw.text((mx - tw // 2, my - th // 2), label, fill=BLACK, font=F_SMALL)


img = Image.new("RGB", (W, H), WHITE)
d = ImageDraw.Draw(img)

# Title
d.text((40, 24), "Activity Diagram - MangoDefend Features (End-to-End)", fill=BLACK, font=F_TITLE)

# Lanes
lane(d, (30, 100, 720, 1830), "User & UI (PySide6)", BLUE)
lane(d, (750, 100, 1480, 1830), "Scan Engine", GREEN)
lane(d, (1510, 100, 2240, 1830), "Realtime Protection", ORANGE)
lane(d, (2270, 100, 2970, 1830), "Data / Backend / Model", PURPLE)

# Global startup flow
step_box(d, (80, 160, 670, 250), "Start App (main.py)", fill=GRAY)
step_box(d, (80, 280, 670, 370), "Init Config + Window + Signals")
step_box(d, (80, 400, 670, 490), "User chooses feature: Scan / Protection / Update")
decision(d, (375, 565), (420, 120), "Feature path?")

# Manual Single Scan (left + engine)
step_box(d, (80, 650, 670, 730), "Single Scan: choose one file")
step_box(d, (800, 650, 1430, 730), "ScanThread -> scanner.scan_file(file)")
step_box(d, (800, 760, 1430, 840), "Convert to image (if non-image) + ONNX inference")
step_box(d, (800, 870, 1430, 950), "Result: Benign / Malware + file hash + path")
step_box(d, (80, 870, 670, 960), "Show ResultDialog + add to scan history")

# Folder / Device Scan path
step_box(d, (80, 1020, 670, 1100), "Batch Scan: choose folder or device")
step_box(d, (800, 1020, 1430, 1100), "Collect files (including hidden + followlinks)")
decision(d, (1115, 1180), (430, 120), "Device scan limit reached (2000)?")
step_box(d, (80, 1230, 670, 1310), "Prompt user: continue all or stop at limit")
step_box(d, (800, 1325, 1430, 1405), "Scan each file -> emit progress + emit per-result")
step_box(d, (80, 1425, 670, 1510), "Summary shown: total, clean, malware, errors")
decision(d, (375, 1585), (420, 120), "Malware found?")
step_box(d, (80, 1660, 670, 1745), "Option: Karantina Semua / Abaikan")

# Realtime protection path
step_box(d, (1560, 650, 2190, 730), "Toggle protection ON")
step_box(d, (1560, 760, 2190, 840), "Watchdog + Process Monitor running")
step_box(d, (1560, 870, 2190, 950), "New file/process detected -> lock or suspend")
step_box(d, (1560, 980, 2190, 1060), "Scan in worker (same scanner pipeline)")
decision(d, (1875, 1140), (430, 120), "Realtime malware?")
step_box(d, (1560, 1210, 2190, 1290), "Show MalwareAlertDialog (allow / kill+quarantine)")
step_box(d, (1560, 1320, 2190, 1400), "Apply action + add 'Malware (Realtime)' to history")

# Data/backend/model path
step_box(d, (2320, 650, 2920, 730), "Embedded backend starts (optional)")
step_box(d, (2320, 760, 2920, 840), "Sync manager loop checks backend health")
step_box(d, (2320, 870, 2920, 950), "Upload pending scan queue when online")
step_box(d, (2320, 1020, 2920, 1100), "Update tab: check latest model version")
step_box(d, (2320, 1130, 2920, 1210), "If update: download -> verify SHA256 -> install")
step_box(d, (2320, 1240, 2920, 1320), "ONNX model used by scanner on next sessions")

# Arrows startup
arrow(d, (375, 250), (375, 280))
arrow(d, (375, 370), (375, 400))
arrow(d, (375, 490), (375, 505))

# Branch from feature decision
arrow(d, (375, 625), (375, 650), "single")
arrow(d, (520, 605), (780, 1025), "batch")
arrow(d, (560, 560), (1560, 690), "realtime")
arrow(d, (580, 545), (2320, 690), "update/sync")

# Single scan arrows
arrow(d, (670, 690), (800, 690))
arrow(d, (1115, 730), (1115, 760))
arrow(d, (1115, 840), (1115, 870))
arrow(d, (800, 910), (670, 910))

# Batch arrows
arrow(d, (670, 1060), (800, 1060))
arrow(d, (1115, 1100), (1115, 1120))
arrow(d, (900, 1180), (670, 1265), "yes")
arrow(d, (1115, 1240), (1115, 1325), "continue/no limit")
arrow(d, (670, 1265), (800, 1365), "decision returned")
arrow(d, (800, 1460), (670, 1460))
arrow(d, (375, 1510), (375, 1525))
arrow(d, (375, 1645), (375, 1660), "yes")

# Realtime arrows
arrow(d, (1875, 730), (1875, 760))
arrow(d, (1875, 840), (1875, 870))
arrow(d, (1875, 950), (1875, 980))
arrow(d, (1875, 1060), (1875, 1080))
arrow(d, (1875, 1200), (1875, 1210), "yes")
arrow(d, (1875, 1290), (1875, 1320))
arrow(d, (1660, 1140), (1430, 910), "no -> clean")

# Backend/model arrows
arrow(d, (2620, 730), (2620, 760))
arrow(d, (2620, 840), (2620, 870))
arrow(d, (2620, 980), (2620, 1020))
arrow(d, (2620, 1100), (2620, 1130), "update available")
arrow(d, (2620, 1210), (2620, 1240))
arrow(d, (2320, 1280), (1430, 800), "model for inference")

# Cross links to history/quarantine
arrow(d, (670, 1700), (1510, 1360), "quarantine all")
arrow(d, (2190, 1360), (670, 920), "history entry")

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print(str(OUT))
