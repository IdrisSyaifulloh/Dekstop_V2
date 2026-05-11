from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math

OUT = Path(__file__).resolve().parent / "architecture_mangodefend.png"
W, H = 2200, 1300

WHITE = (255, 255, 255)
BLACK = (30, 30, 30)
GRAY = (248, 250, 252)
BLUE = (219, 234, 254)
GREEN = (220, 252, 231)
ORANGE = (255, 237, 213)
PURPLE = (243, 232, 255)
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


F_TITLE = get_font(44, True)
F_HEAD = get_font(28, True)
F_TEXT = get_font(21)


def box(draw, xy, title, lines, fill=GRAY):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=18, fill=fill, outline=BLACK, width=3)
    draw.text((x1 + 18, y1 + 14), title, fill=BLACK, font=F_HEAD)
    y = y1 + 58
    for ln in lines:
        draw.text((x1 + 22, y), f"- {ln}", fill=BLACK, font=F_TEXT)
        y += 30


def arrow(draw, p1, p2, color=BLACK, width=4, label=None):
    x1, y1 = p1
    x2, y2 = p2
    draw.line((x1, y1, x2, y2), fill=color, width=width)
    ang = math.atan2(y2 - y1, x2 - x1)
    l = 16
    p3 = (x2 - int(l * math.cos(ang - 0.45)), y2 - int(l * math.sin(ang - 0.45)))
    p4 = (x2 - int(l * math.cos(ang + 0.45)), y2 - int(l * math.sin(ang + 0.45)))
    draw.polygon([p2, p3, p4], fill=color)
    if label:
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2
        draw.rectangle((mx - 90, my - 18, mx + 90, my + 18), fill=WHITE, outline=None)
        tb = draw.textbbox((0, 0), label, font=F_TEXT)
        tw = tb[2] - tb[0]
        th = tb[3] - tb[1]
        draw.text((mx - tw // 2, my - th // 2), label, fill=BLACK, font=F_TEXT)


img = Image.new("RGB", (W, H), WHITE)
d = ImageDraw.Draw(img)

d.text((40, 24), "Architecture Diagram - MangoDefend Desktop", fill=BLACK, font=F_TITLE)

d.rounded_rectangle((30, 90, 1670, 1240), radius=20, outline=BLACK, width=4)
d.text((52, 100), "Desktop Client", fill=BLACK, font=F_HEAD)

d.rounded_rectangle((1710, 90, 2160, 1240), radius=20, outline=BLACK, width=4)
d.text((1730, 100), "External / Optional", fill=BLACK, font=F_HEAD)

box(d, (70, 170, 640, 480), "UI Layer (PySide6)", [
    "ModernWindow + Sidebar",
    "ScanView / ProtectionView / UpdateView",
    "ResultDialog + MalwareAlertDialog",
    "User actions: scan, allow, kill+quarantine",
], fill=BLUE)

box(d, (700, 170, 1620, 480), "Core Orchestrator", [
    "ScanThread / BatchScanThread",
    "RealtimeProtection (watchdog + process monitor)",
    "SyncManager + ModelUpdater",
    "ConfigManager + NotificationManager",
], fill=ORANGE)

box(d, (70, 560, 760, 910), "Scanning Engine", [
    "core/scanner.py (MalwareScanner)",
    "Load ONNX model (Modelv3.onnx)",
    "File to image conversion (FileConverter)",
    "Preprocess 224x224 + ONNX inference",
], fill=GREEN)

box(d, (820, 560, 1620, 910), "Protection and Storage", [
    "File lock / suspend process before decision",
    "Kill process + move file to quarantine",
    "Local queue + logs + cache",
    "Quarantine folder in user home directory",
], fill=PURPLE)

box(d, (1740, 220, 2130, 520), "Embedded Backend", [
    "FastAPI local server",
    "Model update endpoint",
    "Sync endpoint (optional)",
], fill=(224, 242, 254))

box(d, (1740, 600, 2130, 900), "Remote Services", [
    "Cloud API (optional)",
    "Database / telemetry",
    "Subscription / auth server",
], fill=(254, 249, 195))

box(d, (1740, 980, 2130, 1180), "ONNX Model File", [
    "models/Modelv3.onnx",
    "Loaded by scanner runtime",
], fill=RED)

arrow(d, (640, 330), (700, 330), label="events")
arrow(d, (1160, 480), (420, 560), label="scan request")
arrow(d, (760, 720), (820, 720), label="prediction")
arrow(d, (1220, 560), (1220, 480), label="status")
arrow(d, (1620, 300), (1740, 300), label="HTTP")
arrow(d, (1620, 760), (1740, 760), label="sync")
arrow(d, (1935, 980), (560, 690), label="model used")
arrow(d, (380, 480), (380, 560), label="start scan")

d.rounded_rectangle((860, 980, 1360, 1180), radius=16, fill=(243, 244, 246), outline=BLACK, width=3)
d.text((885, 1004), "Data Artifacts", fill=BLACK, font=F_HEAD)
d.text((890, 1050), "- config.ini", fill=BLACK, font=F_TEXT)
d.text((890, 1082), "- local_queue.db", fill=BLACK, font=F_TEXT)
d.text((890, 1114), "- runtime logs", fill=BLACK, font=F_TEXT)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print(str(OUT))
