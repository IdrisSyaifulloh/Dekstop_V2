from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

OUT_DIR = Path(__file__).resolve().parent
PAGE_W = 2200
HEADER_H = 120
LANE_H = 70
MARGIN = 36
COLORS = {
    "bg": (255, 255, 255),
    "text": (24, 24, 27),
    "border": (30, 41, 59),
    "grid": (148, 163, 184),
    "user": (239, 246, 255),
    "app": (255, 247, 237),
    "ml": (240, 253, 244),
    "backend": (250, 245, 255),
    "step": (255, 255, 255),
    "io": (237, 233, 254),
    "start": (15, 23, 42),
    "decision": (254, 249, 195),
    "accent": (124, 58, 237),
}


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


F_TITLE = get_font(34, True)
F_COL = get_font(22, True)
F_TEXT = get_font(18)
F_SMALL = get_font(16)


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = []
    for word in words:
        trial = " ".join(current + [word])
        box = draw.textbbox((0, 0), trial, font=font)
        if box[2] - box[0] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines or [text]


def draw_step(draw, x1, y1, x2, y2, text, fill, kind="process"):
    if kind == "decision":
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        pts = [(cx, y1), (x2, cy), (cx, y2), (x1, cy)]
        draw.polygon(pts, fill=fill, outline=COLORS["border"])
        pad = 28
    elif kind == "io":
        skew = 24
        pts = [(x1 + skew, y1), (x2, y1), (x2 - skew, y2), (x1, y2)]
        draw.polygon(pts, fill=fill, outline=COLORS["border"])
        pad = 20
    elif kind == "start":
        radius = min(x2 - x1, y2 - y1) // 2 - 8
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=COLORS["start"], outline=COLORS["border"])
        return
    elif kind == "end":
        radius = min(x2 - x1, y2 - y1) // 2 - 8
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=COLORS["bg"], outline=COLORS["border"], width=3)
        inner = max(8, radius - 8)
        draw.ellipse((cx - inner, cy - inner, cx + inner, cy + inner), fill=COLORS["start"], outline=COLORS["start"])
        return
    else:
        draw.rounded_rectangle((x1, y1, x2, y2), radius=14, fill=fill, outline=COLORS["border"], width=2)
        pad = 16

    lines = wrap_text(draw, text, F_TEXT, x2 - x1 - pad * 2)
    total_h = len(lines) * 24
    text_y = y1 + ((y2 - y1 - total_h) // 2)
    for line in lines:
        box = draw.textbbox((0, 0), line, font=F_TEXT)
        text_w = box[2] - box[0]
        draw.text((x1 + (x2 - x1 - text_w) // 2, text_y), line, fill=COLORS["text"], font=F_TEXT)
        text_y += 24


def draw_legend(draw, x, y):
    items = [
        ("start", "Mulai"),
        ("process", "Proses / fungsi aplikasi"),
        ("io", "Aksi input/output user"),
        ("decision", "Keputusan / percabangan"),
        ("end", "Selesai"),
    ]
    box_w = 500
    box_h = 34 + len(items) * 42
    draw.rounded_rectangle((x, y, x + box_w, y + box_h), radius=12, fill=(250, 250, 252), outline=COLORS["border"], width=2)
    draw.text((x + 14, y + 10), "Legend Simbol", fill=COLORS["text"], font=F_SMALL)
    for idx, (kind, label) in enumerate(items):
        row_y = y + 42 + idx * 40
        draw_step(draw, x + 14, row_y, x + 84, row_y + 26, "", COLORS["decision"] if kind == "decision" else COLORS["io"] if kind == "io" else COLORS["step"], kind=kind)
        draw.text((x + 100, row_y + 2), label, fill=COLORS["text"], font=F_SMALL)


def draw_arrow(draw, start, end, label=None):
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill=COLORS["border"], width=3)
    angle = math.atan2(y2 - y1, x2 - x1)
    length = 14
    p3 = (x2 - int(length * math.cos(angle - 0.45)), y2 - int(length * math.sin(angle - 0.45)))
    p4 = (x2 - int(length * math.cos(angle + 0.45)), y2 - int(length * math.sin(angle + 0.45)))
    draw.polygon([end, p3, p4], fill=COLORS["border"])
    if label:
        mx = (x1 + x2) // 2
        my = (y1 + y2) // 2
        box = draw.textbbox((0, 0), label, font=F_SMALL)
        tw = box[2] - box[0]
        th = box[3] - box[1]
        draw.rectangle((mx - tw // 2 - 8, my - th // 2 - 4, mx + tw // 2 + 8, my + th // 2 + 4), fill=COLORS["bg"])
        draw.text((mx - tw // 2, my - th // 2), label, fill=COLORS["text"], font=F_SMALL)


def draw_poly_arrow(draw, points, label=None):
    for index in range(len(points) - 1):
        draw.line((points[index][0], points[index][1], points[index + 1][0], points[index + 1][1]), fill=COLORS["border"], width=3)

    x1, y1 = points[-2]
    x2, y2 = points[-1]
    angle = math.atan2(y2 - y1, x2 - x1)
    length = 14
    p3 = (x2 - int(length * math.cos(angle - 0.45)), y2 - int(length * math.sin(angle - 0.45)))
    p4 = (x2 - int(length * math.cos(angle + 0.45)), y2 - int(length * math.sin(angle + 0.45)))
    draw.polygon([points[-1], p3, p4], fill=COLORS["border"])

    if label and len(points) >= 2:
        mx = (points[1][0] + points[2][0]) // 2 if len(points) > 2 else (points[0][0] + points[1][0]) // 2
        my = (points[1][1] + points[2][1]) // 2 if len(points) > 2 else (points[0][1] + points[1][1]) // 2
        box = draw.textbbox((0, 0), label, font=F_SMALL)
        tw = box[2] - box[0]
        th = box[3] - box[1]
        draw.rectangle((mx - tw // 2 - 8, my - th // 2 - 4, mx + tw // 2 + 8, my + th // 2 + 4), fill=COLORS["bg"])
        draw.text((mx - tw // 2, my - th // 2), label, fill=COLORS["text"], font=F_SMALL)


def render_diagram(spec):
    filename = spec["filename"]
    title = spec["title"]
    columns = spec["columns"]
    steps = spec["steps"]
    col_count = len(columns)
    col_w = (PAGE_W - (MARGIN * 2)) // col_count
    row_gap = 46
    step_h = 84
    content_h = HEADER_H + LANE_H + MARGIN + len(steps) * (step_h + row_gap) + 80
    page_h = max(1300, content_h)

    img = Image.new("RGB", (PAGE_W, page_h), COLORS["bg"])
    draw = ImageDraw.Draw(img)

    draw.line((0, 18, PAGE_W, 18), fill=COLORS["accent"], width=6)
    draw.text((MARGIN, 36), title, fill=COLORS["text"], font=F_TITLE)
    draw_legend(draw, PAGE_W - 560, 28)

    top = HEADER_H
    bottom = page_h - MARGIN
    left = MARGIN
    right = PAGE_W - MARGIN

    draw.rectangle((left, top, right, bottom), outline=COLORS["border"], width=3)

    lane_fills = [COLORS["user"], COLORS["app"], COLORS["ml"], COLORS["backend"]]
    for index, name in enumerate(columns):
        x1 = left + index * col_w
        x2 = right if index == col_count - 1 else x1 + col_w
        draw.rectangle((x1, top, x2, top + LANE_H), fill=lane_fills[index % len(lane_fills)], outline=COLORS["border"], width=2)
        box = draw.textbbox((0, 0), name, font=F_COL)
        tw = box[2] - box[0]
        draw.text((x1 + (x2 - x1 - tw) // 2, top + 20), name, fill=COLORS["text"], font=F_COL)
        if index < col_count - 1:
            draw.line((x2, top, x2, bottom), fill=COLORS["border"], width=3)

    centers = []
    for index in range(col_count):
        x1 = left + index * col_w
        x2 = right if index == col_count - 1 else x1 + col_w
        centers.append((x1 + x2) // 2)

    rects = []
    for row_index, step in enumerate(steps):
        lane = step["lane"]
        kind = step.get("kind", "process")
        y1 = top + LANE_H + MARGIN + row_index * (step_h + row_gap)
        y2 = y1 + step_h
        cx = centers[lane]
        width = 84 if kind in {"start", "end"} else col_w - 60
        x1 = cx - width // 2
        x2 = cx + width // 2
        fill = COLORS["decision"] if kind == "decision" else COLORS["io"] if kind == "io" else COLORS["step"]
        draw_step(draw, x1, y1, x2, y2, step["text"], fill, kind=kind)
        rects.append((x1, y1, x2, y2, kind))

    if spec.get("arrows"):
        for arrow in spec["arrows"]:
            src = rects[arrow["from"]]
            dst = rects[arrow["to"]]
            start = ((src[0] + src[2]) // 2, src[3])
            end = ((dst[0] + dst[2]) // 2, dst[1])

            style = arrow.get("style")
            if style == "branch-left":
                mid_x = min(start[0], end[0]) - 70
                points = [
                    start,
                    (start[0], start[1] + 18),
                    (mid_x, start[1] + 18),
                    (mid_x, end[1] - 18),
                    (end[0], end[1] - 18),
                    end,
                ]
                draw_poly_arrow(draw, points, arrow.get("label"))
            elif style == "branch-right":
                mid_x = max(start[0], end[0]) + 70
                points = [
                    start,
                    (start[0], start[1] + 18),
                    (mid_x, start[1] + 18),
                    (mid_x, end[1] - 18),
                    (end[0], end[1] - 18),
                    end,
                ]
                draw_poly_arrow(draw, points, arrow.get("label"))
            else:
                draw_arrow(draw, start, end, arrow.get("label"))
    else:
        for index, step in enumerate(steps[:-1]):
            x1, y1, x2, y2, _kind = rects[index]
            nx1, ny1, nx2, ny2, _next_kind = rects[index + 1]
            draw_arrow(draw, ((x1 + x2) // 2, y2), ((nx1 + nx2) // 2, ny1))

    img.save(OUT_DIR / filename)


DIAGRAMS = [
    {
        "filename": "activity_feature_startup_swimlane.png",
        "title": "Activity Diagram - Startup Aplikasi",
        "columns": ["Users", "Application", "Services / Backend"],
        "steps": [
            {"lane": 0, "kind": "start", "text": ""},
            {"lane": 0, "kind": "io", "text": "Jalankan MangoDefend"},
            {"lane": 1, "text": "Cek admin Windows dan minta UAC jika perlu"},
            {"lane": 1, "text": "Init logging, QApplication, icon aplikasi"},
            {"lane": 1, "text": "Load config.ini dan parameter startup"},
            {"lane": 2, "text": "Start embedded backend jika diaktifkan"},
            {"lane": 2, "text": "Init sync manager, realtime protection, model updater"},
            {"lane": 1, "text": "Buat ModernWindow, inject managers, connect signals"},
            {"lane": 0, "kind": "io", "text": "Lihat dashboard dan pilih fitur"},
            {"lane": 0, "kind": "end", "text": ""},
        ],
    },
    {
        "filename": "activity_feature_single_scan_swimlane.png",
        "title": "Activity Diagram - Fitur Single File Scan (Detail)",
        "columns": ["Users", "Application", "Binary Visualization", "Machine Learning"],
        "steps": [
            {"lane": 0, "kind": "start", "text": ""},
            {"lane": 0, "kind": "io", "text": "Klik Scan File dan pilih target"},
            {"lane": 1, "text": "Tampilkan ScanningDialog dan buat ScanThread"},
            {"lane": 1, "text": "Kirim progress scan ke UI"},
            {"lane": 1, "kind": "decision", "text": "File target sudah image?"},
            {"lane": 2, "text": "Jika bukan image: baca bytes file"},
            {"lane": 2, "kind": "decision", "text": "File 0-byte?"},
            {"lane": 2, "text": "Jika kosong: pad jadi citra blank 32x32"},
            {"lane": 2, "text": "Hitung width berdasarkan ukuran file"},
            {"lane": 2, "text": "Ubah bytes ke matriks grayscale dan simpan image temp"},
            {"lane": 3, "text": "Load model ONNX jika belum aktif"},
            {"lane": 3, "text": "Resize 224x224, normalisasi, ubah ke 3 channel"},
            {"lane": 3, "text": "Jalankan inferensi ONNX dan tentukan Benign atau Malware"},
            {"lane": 1, "text": "Bangun result: label, hash, size, path, output model"},
            {"lane": 1, "text": "Simpan ke riwayat pemindaian dengan path lengkap"},
            {"lane": 1, "text": "Tampilkan ResultDialog dan update counter ancaman"},
            {"lane": 0, "kind": "io", "text": "Lihat hasil scan"},
            {"lane": 0, "kind": "end", "text": ""},
        ],
    },
    {
        "filename": "activity_feature_folder_scan_swimlane.png",
        "title": "Activity Diagram - Fitur Folder Scan (Detail)",
        "columns": ["Users", "Application", "Binary Visualization", "Machine Learning"],
        "steps": [
            {"lane": 0, "kind": "start", "text": ""},
            {"lane": 0, "kind": "io", "text": "Klik Pilih Folder dan tentukan folder target"},
            {"lane": 1, "text": "Buat BatchScanThread mode folder"},
            {"lane": 1, "text": "Kumpulkan semua file secara rekursif"},
            {"lane": 1, "text": "Ikuti hidden folder, symlink, junction, dan cegah cycle loop"},
            {"lane": 1, "text": "Kirim progress jumlah file yang sedang dipindai"},
            {"lane": 1, "kind": "decision", "text": "Untuk tiap file, target sudah image?"},
            {"lane": 2, "text": "Jika non-image: lakukan binary visualization ke image temp"},
            {"lane": 3, "text": "Scan tiap file memakai pipeline model ONNX yang sama"},
            {"lane": 1, "text": "Tambahkan setiap hasil ke riwayat pemindaian + path"},
            {"lane": 1, "text": "Hitung clean, malware, dan error"},
            {"lane": 1, "text": "Tampilkan ringkasan hasil scan"},
            {"lane": 1, "kind": "decision", "text": "Ada malware?"},
            {"lane": 0, "kind": "io", "text": "Pilih Karantina Semua atau Abaikan"},
            {"lane": 1, "text": "Jika dipilih, pindahkan semua malware ke folder karantina"},
            {"lane": 0, "kind": "end", "text": ""},
        ],
    },
    {
        "filename": "activity_feature_device_scan_swimlane.png",
        "title": "Activity Diagram - Fitur Device Scan (Detail)",
        "columns": ["Users", "Application", "Binary Visualization", "Machine Learning"],
        "steps": [
            {"lane": 0, "kind": "start", "text": ""},
            {"lane": 0, "kind": "io", "text": "Klik Mulai Full Scan dan konfirmasi"},
            {"lane": 1, "text": "Buat BatchScanThread mode full device"},
            {"lane": 1, "text": "Kumpulkan file dari Downloads, Desktop, Documents, AppData, dan drive lain"},
            {"lane": 1, "text": "Ikuti hidden folder, symlink, junction, tanpa filter format dan ukuran"},
            {"lane": 1, "kind": "decision", "text": "Jumlah file mencapai 2000?"},
            {"lane": 0, "kind": "io", "text": "Jika ya, pilih lanjut scan semua file atau berhenti di batas default"},
            {"lane": 1, "text": "Terapkan keputusan user dan lanjutkan enumerasi / scanning"},
            {"lane": 1, "kind": "decision", "text": "Untuk tiap file, target sudah image?"},
            {"lane": 2, "text": "Jika non-image: lakukan binary visualization ke image temp"},
            {"lane": 3, "text": "Scan semua file yang terkumpul dengan model ONNX"},
            {"lane": 1, "text": "Update progress, history, counter, dan summary"},
            {"lane": 1, "kind": "decision", "text": "Ada malware?"},
            {"lane": 0, "kind": "io", "text": "Pilih Karantina Semua atau Abaikan"},
            {"lane": 1, "text": "Jika dipilih, karantina massal dilakukan"},
            {"lane": 0, "kind": "end", "text": ""},
        ],
    },
    {
        "filename": "activity_feature_realtime_protection_swimlane.png",
        "title": "Activity Diagram - Fitur Realtime Protection (Detail)",
        "columns": ["Users", "Application", "Binary Visualization", "Machine Learning"],
        "steps": [
            {"lane": 0, "kind": "start", "text": ""},
            {"lane": 0, "kind": "io", "text": "Aktifkan toggle realtime protection"},
            {"lane": 1, "text": "Start watchdog, process monitor, prescan, dan worker queue"},
            {"lane": 1, "text": "Deteksi file baru atau proses baru"},
            {"lane": 1, "text": "Lock file dengan CreateFileW atau suspend process"},
            {"lane": 1, "kind": "decision", "text": "Target sudah image?"},
            {"lane": 2, "text": "Jika non-image: binary visualization ke image temp"},
            {"lane": 3, "text": "Scan target dengan pipeline model ONNX"},
            {"lane": 1, "kind": "decision", "text": "Hasil malware?"},
            {"lane": 1, "text": "Jika clean, release lock atau resume process dan cache hasil"},
            {"lane": 1, "text": "Jika malware, kirim alert ke UI bridge"},
            {"lane": 1, "text": "Tambahkan Malware Realtime ke riwayat pemindaian + path"},
            {"lane": 0, "kind": "io", "text": "Pilih Lanjutkan atau Kill dan Karantina"},
            {"lane": 1, "text": "Terapkan keputusan: allow atau kill plus quarantine"},
            {"lane": 0, "kind": "end", "text": ""},
        ],
    },
    {
        "filename": "activity_feature_model_update_swimlane.png",
        "title": "Activity Diagram - Fitur Model Update",
        "columns": ["Users", "Application", "Backend / Storage"],
        "steps": [
            {"lane": 0, "kind": "start", "text": ""},
            {"lane": 0, "kind": "io", "text": "Buka tab Update dan klik Check Update"},
            {"lane": 1, "text": "Baca versi model lokal saat ini"},
            {"lane": 2, "text": "Ambil metadata model terbaru dari backend"},
            {"lane": 1, "kind": "decision", "text": "Ada versi model yang lebih baru?"},
            {"lane": 0, "kind": "io", "text": "Jika ada, klik Download Update"},
            {"lane": 2, "text": "Unduh file model terbaru"},
            {"lane": 1, "text": "Verifikasi SHA256, backup model lama, install model baru"},
            {"lane": 2, "text": "Simpan version.json dan backup model"},
            {"lane": 0, "kind": "io", "text": "Lihat status update selesai"},
            {"lane": 0, "kind": "end", "text": ""},
        ],
    },
    {
        "filename": "activity_feature_sync_swimlane.png",
        "title": "Activity Diagram - Fitur Sinkronisasi Backend",
        "columns": ["Users", "Application", "Backend / Storage"],
        "steps": [
            {"lane": 1, "kind": "start", "text": ""},
            {"lane": 1, "text": "SyncManager berjalan periodik di background"},
            {"lane": 2, "text": "Cek health backend"},
            {"lane": 1, "kind": "decision", "text": "Backend online?"},
            {"lane": 1, "text": "Jika offline, lewati siklus sync saat ini"},
            {"lane": 1, "text": "Jika online, baca pending records dari SQLite queue lokal"},
            {"lane": 2, "text": "Upload record satu per satu ke API backend"},
            {"lane": 1, "text": "Tandai sukses sebagai synced atau tambah attempt saat gagal"},
            {"lane": 0, "kind": "io", "text": "User dapat tetap memakai aplikasi selama sync berjalan"},
            {"lane": 1, "kind": "end", "text": ""},
        ],
    },
]


DIAGRAMS[1]["arrows"] = [
    {"from": 0, "to": 1},
    {"from": 1, "to": 2},
    {"from": 2, "to": 3},
    {"from": 3, "to": 4},
    {"from": 4, "to": 10, "label": "Ya"},
    {"from": 4, "to": 5, "label": "Tidak", "style": "branch-left"},
    {"from": 5, "to": 6},
    {"from": 6, "to": 7, "label": "Ya", "style": "branch-left"},
    {"from": 6, "to": 8, "label": "Tidak"},
    {"from": 7, "to": 8},
    {"from": 8, "to": 9},
    {"from": 9, "to": 10},
    {"from": 10, "to": 11},
    {"from": 11, "to": 12},
    {"from": 12, "to": 13},
    {"from": 13, "to": 14},
    {"from": 14, "to": 15},
    {"from": 15, "to": 16},
    {"from": 16, "to": 17},
]

DIAGRAMS[2]["arrows"] = [
    {"from": 0, "to": 1},
    {"from": 1, "to": 2},
    {"from": 2, "to": 3},
    {"from": 3, "to": 4},
    {"from": 4, "to": 5},
    {"from": 5, "to": 6},
    {"from": 6, "to": 8, "label": "Ya"},
    {"from": 6, "to": 7, "label": "Tidak", "style": "branch-left"},
    {"from": 7, "to": 8},
    {"from": 8, "to": 9},
    {"from": 9, "to": 10},
    {"from": 10, "to": 11},
    {"from": 11, "to": 12},
    {"from": 12, "to": 13, "label": "Ya", "style": "branch-left"},
    {"from": 12, "to": 15, "label": "Tidak"},
    {"from": 13, "to": 14},
    {"from": 14, "to": 15},
]

DIAGRAMS[3]["arrows"] = [
    {"from": 0, "to": 1},
    {"from": 1, "to": 2},
    {"from": 2, "to": 3},
    {"from": 3, "to": 4},
    {"from": 4, "to": 5},
    {"from": 5, "to": 7, "label": "Ya"},
    {"from": 5, "to": 6, "label": "Tidak", "style": "branch-left"},
    {"from": 6, "to": 7},
    {"from": 7, "to": 8},
    {"from": 8, "to": 9},
    {"from": 9, "to": 10},
    {"from": 10, "to": 11},
    {"from": 11, "to": 12, "label": "Ya", "style": "branch-left"},
    {"from": 11, "to": 14, "label": "Tidak"},
    {"from": 12, "to": 13},
    {"from": 13, "to": 14},
]

DIAGRAMS[4]["arrows"] = [
    {"from": 0, "to": 1},
    {"from": 1, "to": 2},
    {"from": 2, "to": 3},
    {"from": 3, "to": 4},
    {"from": 4, "to": 5},
    {"from": 5, "to": 7, "label": "Ya"},
    {"from": 5, "to": 6, "label": "Tidak", "style": "branch-left"},
    {"from": 6, "to": 7},
    {"from": 7, "to": 8},
    {"from": 8, "to": 10, "label": "Tidak", "style": "branch-left"},
    {"from": 8, "to": 9, "label": "Ya"},
    {"from": 9, "to": 10},
    {"from": 10, "to": 11},
    {"from": 11, "to": 12},
    {"from": 12, "to": 13},
    {"from": 13, "to": 14},
]

DIAGRAMS[5]["arrows"] = [
    {"from": 0, "to": 1},
    {"from": 1, "to": 2},
    {"from": 2, "to": 3},
    {"from": 3, "to": 4, "label": "Ya", "style": "branch-left"},
    {"from": 3, "to": 7, "label": "Tidak"},
    {"from": 4, "to": 5},
    {"from": 5, "to": 6},
    {"from": 6, "to": 7},
    {"from": 7, "to": 8},
    {"from": 8, "to": 9},
    {"from": 9, "to": 10},
]

DIAGRAMS[6]["arrows"] = [
    {"from": 0, "to": 1},
    {"from": 1, "to": 2},
    {"from": 2, "to": 3},
    {"from": 3, "to": 4, "label": "Tidak", "style": "branch-left"},
    {"from": 3, "to": 5, "label": "Ya"},
    {"from": 4, "to": 8},
    {"from": 5, "to": 6},
    {"from": 6, "to": 7},
    {"from": 7, "to": 8},
    {"from": 8, "to": 9},
]

for spec in DIAGRAMS:
    render_diagram(spec)

print(str(OUT_DIR))
