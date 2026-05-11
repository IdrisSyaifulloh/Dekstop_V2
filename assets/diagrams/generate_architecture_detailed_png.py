from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math


OUT = Path(__file__).resolve().parent / "architecture_mangodefend_detailed.png"
W, H = 3400, 2200

WHITE = (255, 255, 255)
BLACK = (24, 24, 27)
SLATE = (71, 85, 105)
LINE = (51, 65, 85)
BLUE = (219, 234, 254)
GREEN = (220, 252, 231)
ORANGE = (255, 237, 213)
PURPLE = (243, 232, 255)
YELLOW = (254, 249, 195)
RED = (254, 226, 226)
GRAY = (248, 250, 252)
MINT = (236, 253, 245)
PINK = (252, 231, 243)


def get_font(size=24, bold=False):
    candidates = []
    if bold:
        candidates += ["C:/Windows/Fonts/Inter-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]
    candidates += ["C:/Windows/Fonts/Inter-Regular.ttf", "C:/Windows/Fonts/arial.ttf"]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            continue
    return ImageFont.load_default()


F_TITLE = get_font(50, True)
F_GROUP = get_font(30, True)
F_HEAD = get_font(22, True)
F_TEXT = get_font(17)
F_SMALL = get_font(15)


def wrap_lines(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = []
    for word in words:
        candidate = " ".join(current + [word])
        box = draw.textbbox((0, 0), candidate, font=font)
        if box[2] - box[0] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines or [text]


def group_box(draw, xy, title, fill):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=22, outline=LINE, width=4, fill=fill)
    draw.text((x1 + 18, y1 + 12), title, fill=BLACK, font=F_GROUP)


def component_box(draw, xy, title, lines, fill=GRAY):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=16, outline=LINE, width=3, fill=fill)
    draw.text((x1 + 16, y1 + 12), title, fill=BLACK, font=F_HEAD)
    y = y1 + 48
    for line in lines:
        wrapped = wrap_lines(draw, f"- {line}", F_TEXT, x2 - x1 - 28)
        for segment in wrapped:
            draw.text((x1 + 16, y), segment, fill=BLACK, font=F_TEXT)
            y += 22
        y += 4


def arrow(draw, start, end, label=None, color=LINE, width=4):
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill=color, width=width)
    angle = math.atan2(y2 - y1, x2 - x1)
    length = 16
    p3 = (x2 - int(length * math.cos(angle - 0.45)), y2 - int(length * math.sin(angle - 0.45)))
    p4 = (x2 - int(length * math.cos(angle + 0.45)), y2 - int(length * math.sin(angle + 0.45)))
    draw.polygon([end, p3, p4], fill=color)
    if label:
        mx = (x1 + x2) // 2
        my = (y1 + y2) // 2
        box = draw.textbbox((0, 0), label, font=F_SMALL)
        tw = box[2] - box[0]
        th = box[3] - box[1]
        draw.rounded_rectangle((mx - tw // 2 - 8, my - th // 2 - 4, mx + tw // 2 + 8, my + th // 2 + 4), radius=8, fill=WHITE)
        draw.text((mx - tw // 2, my - th // 2), label, fill=BLACK, font=F_SMALL)


def poly_arrow(draw, points, label=None, color=LINE, width=4):
    for index in range(len(points) - 1):
        draw.line((points[index][0], points[index][1], points[index + 1][0], points[index + 1][1]), fill=color, width=width)
    arrow(draw, points[-2], points[-1], label=label, color=color, width=width)


img = Image.new("RGB", (W, H), WHITE)
d = ImageDraw.Draw(img)

d.text((40, 24), "Architecture Diagram - MangoDefend Desktop (Detailed)", fill=BLACK, font=F_TITLE)

# Main groups
group_box(d, (30, 100, 2480, 2140), "Desktop Client / Windows Host", (250, 250, 252))
group_box(d, (2510, 100, 3370, 2140), "External / Optional Services", (252, 252, 254))

# Desktop host components
component_box(d, (70, 170, 520, 470), "Bootstrap & Entry", [
    "main.py checks Windows admin / UAC relaunch",
    "QApplication + app icon + logging initialization",
    "load config.ini via ConfigManager singleton",
    "instantiate ModernWindow and inject managers",
    "shutdown embedded backend, sync, and protection on exit",
], fill=BLUE)

component_box(d, (560, 170, 1040, 470), "UI Shell (PySide6)", [
    "ModernWindow + Sidebar + QStackedWidget",
    "DashboardView, ScanView, ProtectionView, UpdateView",
    "theme system and signal-slot wiring",
    "scan progress dialog + tab navigation",
], fill=BLUE)

component_box(d, (1080, 170, 1580, 470), "Dialogs & Alerts", [
    "ResultDialog for single scan results",
    "MalwareAlertDialog for realtime decisions",
    "QMessageBox for device limit and batch summary",
    "MalwareAlertBridge carries thread-safe UI alerts",
], fill=BLUE)

component_box(d, (1620, 170, 2420, 470), "Orchestration Services", [
    "ScanThread and BatchScanThread control scan jobs",
    "SyncManager handles background upload cycles",
    "ModelUpdater checks, downloads, verifies models",
    "NotificationManager shows desktop malware alerts",
    "EmbeddedBackend runs local FastAPI when enabled",
], fill=ORANGE)

component_box(d, (70, 540, 660, 920), "Scanning / ML Pipeline", [
    "MalwareScanner chooses direct image path or conversion path",
    "FileConverter performs binary visualization for non-image files only",
    "empty file becomes blank 32x32 image instead of crashing",
    "preprocess to 224x224 grayscale -> 3 channel tensor",
    "ONNX Runtime inference returns Benign / Malware logits",
    "result includes label, file hash, size, path, timestamp",
], fill=GREEN)

component_box(d, (700, 540, 1270, 920), "Binary Visualization", [
    "utils/file_converter.py reads raw file bytes",
    "calculate_width uses UCSB-style width by file size",
    "numpy frombuffer + pad + reshape to 2D matrix",
    "Pillow saves grayscale temp image in %TEMP%/mangodefend_temp",
    "bypassed completely for .png/.jpg/.jpeg input files",
], fill=MINT)

component_box(d, (1310, 540, 1910, 920), "Realtime Protection Core", [
    "Watchdog observer monitors Downloads/Desktop/Documents/TEMP",
    "Process monitor polls new PIDs and opened files",
    "FileLock uses CreateFileW FILE_SHARE_NONE",
    "scan queue, worker threads, cache cleanup, prescan existing files",
    "ask user -> allow or kill and quarantine",
], fill=PURPLE)

component_box(d, (1950, 540, 2420, 920), "Windows / OS Layer", [
    "CreateFileW exclusive lock blocks file access",
    "psutil suspend / resume / kill process",
    "watchdog filesystem events",
    "Toast notifications on Windows",
    "local filesystem, symlink/junction traversal",
], fill=PURPLE)

component_box(d, (70, 1000, 670, 1420), "Local Data & Persistence", [
    "config.ini stores backend, sync, update, protection settings",
    "local_queue.db stores pending sync records via LocalQueue",
    "models/Modelv3.onnx loaded by scanner",
    "models/version.json + models/backups for updater",
    "quarantine folder: ~/.Mangodefend/Karintina",
    "temp image cache: %TEMP%/mangodefend_temp",
    "embedded backend db: ~/.mangodefend/database.db",
], fill=YELLOW)

component_box(d, (710, 1000, 1290, 1420), "Sync Pipeline", [
    "SyncManager loop checks backend health",
    "LocalQueue fetches pending scans in batches",
    "BackendClient uploads filename / label / file_hash",
    "success -> mark synced, failure -> increment attempts",
    "manual sync_now and queue status available",
], fill=ORANGE)

component_box(d, (1330, 1000, 1910, 1420), "Model Update Pipeline", [
    "check /model/latest endpoint for new version",
    "stream download /model/download/{version}",
    "verify SHA256 against backend metadata",
    "backup current ONNX model before install",
    "write version.json after successful install",
], fill=ORANGE)

component_box(d, (1950, 1000, 2420, 1420), "Scan History / User Actions", [
    "ScanView history stores filename, status, timestamp, path",
    "batch scan can offer Karantina Semua",
    "realtime malware adds Malware (Realtime) entry",
    "user may delete manually using displayed path",
], fill=PINK)

component_box(d, (70, 1500, 1170, 2040), "Runtime Data Flows", [
    "Single scan: UI -> ScanThread -> MalwareScanner -> ResultDialog -> History",
    "Folder/device scan: UI -> BatchScanThread -> collect files -> per-file scan -> summary",
    "Realtime file flow: watchdog -> lock file -> scan -> allow/quarantine",
    "Realtime process flow: suspend PID -> scan exe/opened file -> resume/kill",
    "Batch and realtime malware can move files to quarantine",
], fill=GRAY)

component_box(d, (1210, 1500, 2420, 2040), "Important Architectural Notes", [
    "Binary visualization is not global: only scan paths for non-image files use it",
    "image files bypass FileConverter and go directly to preprocessing + ONNX",
    "startup, sync, model update, notifications, dialogs do not use binary visualization",
    "scanner supports CPU by default and CUDAExecutionProvider if available",
    "embedded backend is local-only; external server repo is a richer optional deployment",
], fill=RED)

# External services
component_box(d, (2550, 170, 3330, 560), "Embedded Backend (Local FastAPI)", [
    "core/embedded_backend.py runs uvicorn in background thread",
    "routes: /health, /scanning-file, /history-scan, /stats",
    "stores scan_results in local SQLite database",
    "used when Backend.use_embedded = true",
], fill=BLUE)

component_box(d, (2550, 620, 3330, 1210), "External Server Repo (mangodefend-server)", [
    "FastAPI app includes scans router and docs endpoints",
    "SQLAlchemy models: Device, ScanJob, ScanResult, User",
    "scan service validates HWID and rate limits guest scan requests",
    "Redis stores daily scan counters per hardware id",
    "Celery worker processes async full/custom scan jobs",
], fill=PURPLE)

component_box(d, (2550, 1270, 3330, 1770), "External Infrastructure", [
    "PostgreSQL / application database for server deployment",
    "Redis for rate limit and worker coordination",
    "Celery worker processes queued scan jobs",
    "optional cloud API / auth / subscription services",
    "remote model metadata and downloadable ONNX files",
], fill=YELLOW)

component_box(d, (2550, 1830, 3330, 2040), "ML Assets", [
    "Training notebook: maldebCNNMM.ipynb",
    "PyTorch / torchvision used for training only",
    "convert_to_onnx.py exports ResNet-18 based model to ONNX",
], fill=GREEN)

# Arrows - top layers
arrow(d, (520, 320), (560, 320), label="create UI")
arrow(d, (1040, 320), (1080, 320), label="dialogs")
arrow(d, (1580, 320), (1620, 320), label="signals / managers")

# To scan pipeline
arrow(d, (1310, 470), (400, 540), label="scan jobs")
arrow(d, (365, 920), (980, 920), label="non-image only")
arrow(d, (1270, 730), (1310, 730), label="image tensor")
arrow(d, (365, 1420), (365, 1000), label="model / temp / hashes")
arrow(d, (1910, 730), (1950, 730), label="lock / process ops")

# Realtime and history connections
arrow(d, (1610, 470), (1610, 540), label="realtime start")
arrow(d, (1910, 1210), (1950, 1210), label="history + path")
arrow(d, (2190, 920), (2190, 1000), label="alerts / decisions")
arrow(d, (1910, 730), (660, 730), label="scan target")

# Sync and update
arrow(d, (670, 1210), (710, 1210), label="queue")
arrow(d, (1290, 1210), (1330, 1210), label="version / download")
arrow(d, (1290, 1210), (2550, 360), label="HTTP local")
arrow(d, (1910, 1210), (2550, 900), label="HTTP remote")

# Backend/external relationships
arrow(d, (3330, 360), (2550, 900), label="optional replace")
arrow(d, (2940, 560), (2940, 620), label="deploy up")
arrow(d, (2940, 1210), (2940, 1270), label="db / worker / redis")
arrow(d, (2940, 1770), (2940, 1830), label="model source")
arrow(d, (2550, 1520), (1910, 1210), label="latest model")

# Local data interactions
arrow(d, (670, 1210), (2550, 1520), label="sync API")
arrow(d, (1000, 1420), (1000, 1500), label="runtime state")
arrow(d, (1790, 1420), (1790, 1500), label="notes")

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print(str(OUT))