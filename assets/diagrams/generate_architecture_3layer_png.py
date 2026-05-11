from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math


OUT = Path(__file__).resolve().parent / "architecture_mangodefend_3layer.png"
W, H = 2200, 1300

WHITE = (255, 255, 255)
BLACK = (17, 24, 39)
LINE = (55, 65, 81)
BLUE = (219, 234, 254)
ORANGE = (255, 237, 213)
PURPLE = (237, 233, 254)


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
F_HEAD = get_font(30, True)
F_TEXT = get_font(20)
F_SMALL = get_font(18)


def wrap_lines(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = []
    for word in words:
        candidate = " ".join(current + [word])
        width = draw.textbbox((0, 0), candidate, font=font)[2]
        if width <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def layer_box(draw, xy, title, bullets, fill):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=24, fill=fill, outline=LINE, width=4)
    draw.text((x1 + 22, y1 + 16), title, fill=BLACK, font=F_HEAD)
    y = y1 + 70
    for item in bullets:
        for row in wrap_lines(draw, f"- {item}", F_TEXT, x2 - x1 - 40):
            draw.text((x1 + 22, y), row, fill=BLACK, font=F_TEXT)
            y += 28
        y += 4


def arrow(draw, start, end, label=None):
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill=LINE, width=5)
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 15
    p1 = (x2 - int(size * math.cos(angle - 0.5)), y2 - int(size * math.sin(angle - 0.5)))
    p2 = (x2 - int(size * math.cos(angle + 0.5)), y2 - int(size * math.sin(angle + 0.5)))
    draw.polygon([end, p1, p2], fill=LINE)
    if label:
        tw = draw.textbbox((0, 0), label, font=F_SMALL)[2]
        th = draw.textbbox((0, 0), label, font=F_SMALL)[3]
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2
        draw.rounded_rectangle((mx - tw // 2 - 8, my - th // 2 - 6, mx + tw // 2 + 8, my + th // 2 + 6), radius=8, fill=WHITE)
        draw.text((mx - tw // 2, my - th // 2), label, fill=BLACK, font=F_SMALL)


img = Image.new("RGB", (W, H), WHITE)
draw = ImageDraw.Draw(img)

draw.text((40, 24), "Architecture Diagram - MangoDefend (3 Layer)", fill=BLACK, font=F_TITLE)

frontend_xy = (80, 180, 700, 1080)
core_xy = (790, 180, 1410, 1080)
backend_xy = (1500, 180, 2120, 1080)

layer_box(
    draw,
    frontend_xy,
    "Frontend (UI)",
    [
        "PySide6 ModernWindow + Sidebar + Views",
        "ScanView, DashboardView, ProtectionView, UpdateView",
        "Result dialog, malware alert dialog, scan history",
        "User action: scan file/folder/device dan karantina",
    ],
    BLUE,
)

layer_box(
    draw,
    core_xy,
    "Core (Engine)",
    [
        "ScanThread / BatchScanThread orchestration",
        "MalwareScanner + FileConverter + ONNX Runtime inference",
        "RealtimeProtection (watchdog, process monitor, lock file)",
        "ConfigManager, ModelUpdater, SyncManager",
        "Local queue/database/temp/quarantine handling",
    ],
    ORANGE,
)

layer_box(
    draw,
    backend_xy,
    "Backend (Service)",
    [
        "Embedded backend lokal (FastAPI + SQLite)",
        "External backend (FastAPI API server)",
        "Database + Redis + Celery worker",
        "Model metadata/download endpoint + sync endpoint",
    ],
    PURPLE,
)

arrow(draw, (700, 620), (790, 620), "request scan")
arrow(draw, (1410, 620), (1500, 620), "sync / update")
arrow(draw, (1500, 700), (1410, 700), "response")
arrow(draw, (790, 700), (700, 700), "result")

draw.text((80, 1140), "Flow ringkas: Frontend -> Core -> Backend -> Core -> Frontend", fill=BLACK, font=F_SMALL)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print(str(OUT))