"""
MangoDefend — Layar Pembuka (Splash Screen)

Tampilan animasi logo yang muncul singkat saat aplikasi pertama kali dibuka.
Tidak ada bingkai jendela, latar transparan, selalu berada di atas semua jendela lain.

Alur animasi (total ~2.2 detik):
  0.0 – 0.4 detik  : Muncul perlahan dari transparan ke solid (fade in).
  0.4 – 1.6 detik  : Animasi cincin melebar + logo berdenyut + teks muncul.
  1.6 – 2.2 detik  : Menghilang perlahan (fade out), lalu sinyal 'finished' dikirim.
"""
import os
import sys
import math  # Digunakan untuk fungsi sin() pada animasi denyut logo

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QColor, QPainter, QPixmap, QBrush, QLinearGradient,
    QRadialGradient, QPen, QPainterPath
)
from PySide6.QtWidgets import QWidget, QApplication

from ui.styles.figma_theme import Colors, Typography


def _asset(relative: str) -> str:
    """
    Temukan path lengkap untuk sebuah file aset (gambar, ikon, dll).

    Fungsi ini bekerja dalam dua situasi:
      1. Saat pengembangan: file diambil dari folder project (direktori parent dari ui/).
      2. Setelah dikemas menjadi .exe (PyInstaller): file diambil dari folder _MEIPASS
         yang merupakan folder sementara yang dibuat PyInstaller saat exe dijalankan.

    relative : Path relatif dari root project, misalnya "assets/mango_icon.png".
    """
    if getattr(sys, "frozen", False):
        # Berjalan sebagai file .exe yang sudah dikemas oleh PyInstaller
        base = sys._MEIPASS
    else:
        # Berjalan normal saat pengembangan
        # __file__ = .../ui/splash_screen.py → dirname dua kali = root project
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


class SplashScreen(QWidget):
    """
    Layar pembuka tanpa bingkai dengan animasi logo dan efek fade masuk/keluar.

    Cara kerja teknis:
      - Widget tanpa bingkai (FramelessWindowHint) agar tidak ada title bar.
      - Latar transparan (TranslucentBackground) agar sudut melengkung kartu terlihat.
      - Timer 60fps (setiap 16ms) memperbarui nilai animasi dan memicu paint ulang.
      - Semua gambar dilakukan secara manual di paintEvent (bukan CSS).

    Sinyal:
      finished : Dikirim tepat setelah animasi selesai dan widget ditutup.
                 main.py menunggu sinyal ini untuk menampilkan jendela utama.
    """

    # Sinyal yang dikirim ke main.py setelah animasi selesai
    finished = Signal()

    # ── Konstanta waktu animasi ──
    _TOTAL          = 2.2   # Total durasi animasi dalam detik
    _FADE_IN        = 0.4   # Akhir fase fade-in (animasi mulai muncul)
    _FADE_OUT_START = 1.6   # Awal fase fade-out (animasi mulai menghilang)

    # Ukuran widget splash screen dalam piksel (kotak sempurna)
    _SIZE = 320

    def __init__(self):
        """
        Siapkan splash screen: atur properti jendela, muat logo, dan mulai timer animasi.
        """
        super().__init__(None)  # None = tidak ada parent, jendela mandiri

        # ── Pengaturan jendela ──
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |        # Tanpa bingkai/title bar
            Qt.WindowType.WindowStaysOnTopHint |       # Selalu di atas jendela lain
            Qt.WindowType.BypassWindowManagerHint      # Bypass window manager (lebih bersih di beberapa OS)
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # Latar transparan
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)          # Hapus dari memori saat ditutup
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)  # Tampil tanpa mengambil fokus

        # ── Status animasi ──
        self._t       = 0.0   # Waktu yang sudah berjalan sejak awal (detik)
        self._opacity = 0.0   # Tingkat keopakan: 0.0 = bening total, 1.0 = penuh solid
        self._ring_t  = 0.0   # Kemajuan animasi cincin: 0.0 = belum mulai, 1.0 = selesai

        # ── Muat logo aplikasi ──
        logo_path = _asset(os.path.join("assets", "mango_icon.png"))
        # Jika file logo tidak ditemukan, QPixmap() kosong digunakan (fallback ke huruf "M")
        self._logo = QPixmap(logo_path) if os.path.exists(logo_path) else QPixmap()

        # Paksa ukuran widget tepat 320×320 piksel
        self.setFixedSize(self._SIZE, self._SIZE)

        # Posisikan di tengah layar
        self._center()

        # ── Timer animasi 60fps ──
        # Interval 16ms ≈ 1/60 detik → ~60 frame per detik
        self._tick_ms = 16
        self._timer = QTimer(self)
        self._timer.setInterval(self._tick_ms)
        self._timer.timeout.connect(self._tick)  # Setiap 16ms panggil _tick()
        self._timer.start()

    def _center(self):
        """
        Pindahkan splash screen ke tengah-tengah layar utama (monitor pertama).
        Dihitung berdasarkan ukuran layar dikurangi ukuran widget.
        """
        screen = QApplication.primaryScreen().geometry()
        self.move(
            screen.x() + (screen.width()  - self._SIZE) // 2,  # Tengah horizontal
            screen.y() + (screen.height() - self._SIZE) // 2,  # Tengah vertikal
        )

    def showEvent(self, event):
        """
        Dipanggil otomatis Qt setiap kali widget akan ditampilkan.
        Posisikan ulang ke tengah layar untuk mengantisipasi resolusi layar yang berubah.
        """
        self._center()
        super().showEvent(event)

    def _tick(self):
        """
        Jalankan satu langkah animasi setiap 16ms.

        Tugasnya:
          1. Tambah waktu berjalan (self._t) sebesar 0.016 detik.
          2. Hitung tingkat keopakan (self._opacity) berdasarkan fase animasi:
               - Fase masuk  (0.0 – 0.4 dtk): opacity naik dari 0 ke 1.
               - Fase tahan  (0.4 – 1.6 dtk): opacity tetap di 1.
               - Fase keluar (1.6 – 2.2 dtk): opacity turun dari 1 ke 0.
          3. Hitung kemajuan cincin (self._ring_t) selama fase tahan.
          4. Jika waktu habis: hentikan timer, tutup widget, kirim sinyal finished.
          5. Minta gambar ulang via self.update().
        """
        dt = self._tick_ms / 1000.0  # Konversi 16ms ke detik (0.016)
        self._t += dt
        t = self._t

        # ── Hitung keopakan berdasarkan fase ──
        if t < self._FADE_IN:
            # Fase masuk: opacity naik dari 0 ke 1 secara linear
            self._opacity = t / self._FADE_IN

        elif t < self._FADE_OUT_START:
            # Fase tahan: opacity penuh, animasi logo dan cincin berjalan
            self._opacity = 1.0

        elif t < self._TOTAL:
            # Fase keluar: opacity turun dari 1 ke 0 secara linear
            self._opacity = 1.0 - (t - self._FADE_OUT_START) / (self._TOTAL - self._FADE_OUT_START)

        else:
            # Animasi selesai — tutup dan beritahu parent bahwa splash sudah selesai
            self._timer.stop()
            self.close()
            self.finished.emit()  # main.py menunggu sinyal ini untuk menampilkan jendela utama
            return

        # ── Hitung kemajuan animasi cincin (hanya setelah fase masuk) ──
        if t > self._FADE_IN:
            # ring_t bergerak dari 0 ke 1 sepanjang fase tahan (0.4 – 1.6 dtk)
            self._ring_t = min(1.0, (t - self._FADE_IN) / (self._FADE_OUT_START - self._FADE_IN))

        # Minta Qt untuk menggambar ulang dengan nilai animasi terbaru
        self.update()

    def paintEvent(self, event):
        """
        Gambar semua elemen visual splash screen setiap frame.

        Urutan gambar (penting untuk layering yang benar):
          1. Kartu latar belakang gelap dengan sudut melengkung.
          2. Cincin berputar dan melebar di sekitar logo.
          3. Logo aplikasi dengan denyutan kecil.
          4. Nama "MANGO DEFEND" dan tagline "AI Malware Protection".

        Seluruh gambar dipengaruhi oleh self._opacity (fade in/out).
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)  # Tepi mulus

        # Terapkan keopakan global — mengontrol fade in/out seluruh widget
        # Dibatasi antara 0.0 dan 1.0 untuk keamanan
        painter.setOpacity(max(0.0, min(1.0, self._opacity)))

        w, h   = self.width(), self.height()   # Ukuran widget (320 × 320 piksel)
        cx, cy = w / 2.0, h / 2.0             # Titik tengah widget

        # Gambar setiap lapisan secara berurutan
        self._draw_card(painter, w, h)       # Lapisan 1: kartu latar
        self._draw_ring(painter, cx, cy)     # Lapisan 2: cincin animasi
        self._draw_logo(painter, cx, cy, w)  # Lapisan 3: logo
        self._draw_text(painter, cx, cy, w)  # Lapisan 4: teks nama + tagline

        painter.end()

    def _draw_card(self, painter: QPainter, w: float, h: float):
        """
        Gambar kotak latar belakang gelap dengan sudut melengkung.

        Terdiri dari tiga lapisan:
          1. Gradasi gelap dari kiri-atas ke kanan-bawah (latar utama).
          2. Kilau oranye samar di sudut kiri-atas (radial gradient).
          3. Garis tepi tipis oranye (border).

        Ukuran kartu: widget dikurangi 48px di setiap sisi (24px margin di tiap sisi).
        """
        card_r = 48.0                    # Sudut melengkung kartu dalam piksel
        card_w = w - 48                  # Lebar kartu (320 - 48 = 272 piksel)
        card_h = h - 48                  # Tinggi kartu (320 - 48 = 272 piksel)
        card_x = (w - card_w) / 2.0     # Posisi X kiri kartu (24 piksel dari tepi)
        card_y = (h - card_h) / 2.0     # Posisi Y atas kartu

        # Buat path bentuk kartu dengan sudut melengkung
        path = QPainterPath()
        path.addRoundedRect(card_x, card_y, card_w, card_h, card_r, card_r)

        # ── Lapisan 1: Gradasi latar gelap ──
        # Dari hitam kebiruan di kiri-atas ke hitam pekat di kanan-bawah
        bg_grad = QLinearGradient(QPointF(card_x, card_y), QPointF(card_x + card_w, card_y + card_h))
        bg_grad.setColorAt(0.0, QColor(18, 18, 26, 245))   # Biru-hitam, hampir buram
        bg_grad.setColorAt(1.0, QColor(12, 12, 20, 245))   # Hitam, hampir buram
        painter.fillPath(path, QBrush(bg_grad))

        # ── Lapisan 2: Kilau oranye samar di sudut kiri-atas ──
        # Efek cahaya radial: paling terang di tengah, memudar ke tepi
        tint = QRadialGradient(
            QPointF(card_x + card_w * 0.25, card_y + card_h * 0.25),  # Pusat kilau (1/4 dari kiri-atas)
            card_w * 0.7   # Radius kilau cukup besar agar halus
        )
        tint.setColorAt(0.0, QColor(255, 165, 0, 28))  # Oranye sangat transparan di pusat
        tint.setColorAt(1.0, QColor(255, 165, 0, 0))   # Benar-benar transparan di tepi
        painter.fillPath(path, QBrush(tint))

        # ── Lapisan 3: Garis tepi tipis oranye ──
        # Alpha 55/255 ≈ 22% — cukup terlihat tapi tidak mendominasi
        painter.setPen(QPen(QColor(255, 165, 0, 55), 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Offset 0.6px agar border berada tepat di dalam path dan tidak terpotong
        painter.drawRoundedRect(
            QRectF(card_x + 0.6, card_y + 0.6, card_w - 1.2, card_h - 1.2),
            card_r, card_r
        )

    def _draw_ring(self, painter: QPainter, cx: float, cy: float):
        """
        Gambar efek cincin yang melebar dan busur yang berputar di sekitar logo.

        Animasi cincin:
          - Radius bertambah dari 52px (saat ring_t=0) ke 80px (saat ring_t=1).
          - Alpha (keopakan) berkurang seiring radius bertambah — efek menghilang saat melebar.

        Komponen gambar:
          1. Cahaya luar (glow) di luar cincin — lingkaran besar sangat transparan.
          2. Cincin utama — lingkaran dengan ketebalan garis.
          3. Busur terang yang berputar — busur pendek yang berotasi.
        """
        ring_t = self._ring_t

        # Radius cincin: membesar dari 52 ke 80 piksel sesuai kemajuan animasi
        ring_r = 52.0 + (80.0 - 52.0) * ring_t

        # Alpha semakin kecil seiring cincin melebar (efek menghilang saat mengembang)
        ring_alpha = int(180 * (1.0 - ring_t))  # 180 → 0

        # ── Cahaya luar (glow) — lingkaran besar tipis di luar cincin ──
        # Menggunakan ketebalan garis yang proporsional dengan radius untuk efek kabut
        painter.setPen(QPen(QColor(255, 165, 0, ring_alpha // 3), ring_r * 0.18))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), ring_r + 6, ring_r + 6)

        # ── Cincin utama ──
        painter.setPen(QPen(QColor(255, 183, 50, ring_alpha), 2.5))
        painter.drawEllipse(QPointF(cx, cy), ring_r, ring_r)

        # ── Busur terang yang berputar ──
        # Sudut mulai busur berputar: ring_t * 720 derajat → berputar dua kali penuh
        # % 360 memastikan nilainya selalu dalam range 0–360
        arc_angle = int(ring_t * 720) % 360

        # Kotak pembatas lingkaran busur (posisi dan ukuran area gambar arc)
        arc_rect = QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)

        # Qt menggunakan 1/16 derajat dalam drawArc
        # Busur panjang 90 derajat (1/4 lingkaran), dimulai dari arc_angle
        painter.setPen(QPen(QColor(255, 220, 100, min(255, ring_alpha + 60)), 3.0))
        painter.drawArc(arc_rect, arc_angle * 16, 90 * 16)

    def _draw_logo(self, painter: QPainter, cx: float, cy: float, w: float):
        """
        Gambar logo aplikasi di tengah layar dengan efek denyutan kecil.

        Efek denyut:
          - Skala logo berubah dari 1.0 → 1.04 → 1.0 menggunakan fungsi sinus.
          - math.sin(ring_t * pi) menghasilkan puncak denyutan di tengah animasi.

        Fallback:
          - Jika file logo tidak ditemukan, tampilkan huruf "M" besar berwarna oranye.
        """
        logo_size = 96  # Ukuran dasar logo dalam piksel

        if not self._logo.isNull():
            # ── Hitung skala denyut ──
            # sin(ring_t * π): naik dari 0 ke 1 lalu turun kembali ke 0 seiring ring_t 0→1
            # 0.04 = amplitudo: logo membesar maksimum 4% di puncak denyut
            pulse = 1.0 + 0.04 * math.sin(self._ring_t * math.pi)
            scaled_size = int(logo_size * pulse)

            # Skala logo dengan kualitas smooth (tidak pecah-pecah)
            logo_scaled = self._logo.scaled(
                scaled_size, scaled_size,
                Qt.AspectRatioMode.KeepAspectRatio,         # Jaga proporsi asli
                Qt.TransformationMode.SmoothTransformation,  # Penskalaan mulus
            )

            # Posisikan logo di tengah-tengah widget, sedikit ke atas dari center
            lx = int(cx - logo_scaled.width()  / 2)
            ly = int(cy - logo_scaled.height() / 2) - 16  # 16px di atas center
            painter.drawPixmap(lx, ly, logo_scaled)

        else:
            # ── Fallback: tampilkan huruf "M" jika logo tidak ada ──
            painter.setPen(QColor(255, 165, 0))
            f = painter.font()
            f.setPointSize(42)
            f.setBold(True)
            painter.setFont(f)
            # Gambar di tengah widget, sedikit di atas center
            painter.drawText(QRectF(0, cy - 60, w, 80), Qt.AlignmentFlag.AlignCenter, "M")

    def _draw_text(self, painter: QPainter, cx: float, cy: float, w: float):
        """
        Gambar nama aplikasi "MANGO DEFEND" dan tagline "AI Malware Protection".

        Efek muncul perlahan:
          - name_alpha dihitung dari ring_t × 2.5, dibatasi maksimum 255 (penuh).
          - ring_t=0 → nama tidak terlihat, ring_t=0.4 → nama mulai terlihat jelas.

        Teks tagline menggunakan alpha 2/3 dari alpha nama agar lebih redup
        sebagai hierarki visual (nama lebih menonjol dari tagline).
        """
        # Alpha teks: muncul perlahan seiring ring_t naik
        # × 2.5: alpha penuh tercapai di ring_t = 0.4 (tidak perlu menunggu animasi selesai)
        name_alpha = int(255 * min(1.0, self._ring_t * 2.5))

        # ── Nama Aplikasi "MANGO DEFEND" ──
        painter.setPen(QColor(255, 255, 255, name_alpha))  # Putih dengan alpha animasi
        f = painter.font()
        f.setFamily(Typography.FONT_FAMILY)
        f.setPointSize(15)
        f.setBold(True)
        f.setLetterSpacing(f.SpacingType.AbsoluteSpacing, 2.5)  # Jarak antar huruf untuk tampilan premium
        painter.setFont(f)

        # Gambar nama di bawah logo (cy + 52 piksel)
        painter.drawText(QRectF(0, cy + 52, w, 30), Qt.AlignmentFlag.AlignCenter, "MANGO DEFEND")

        # ── Tagline "AI Malware Protection" ──
        # Alpha 2/3 dari nama agar lebih redup → hierarki visual yang jelas
        painter.setPen(QColor(255, 165, 0, name_alpha * 2 // 3))  # Oranye semi-transparan
        f2 = painter.font()
        f2.setFamily(Typography.FONT_FAMILY)
        f2.setPointSize(9)
        f2.setBold(False)
        f2.setLetterSpacing(f2.SpacingType.AbsoluteSpacing, 1.5)  # Jarak huruf lebih kecil dari nama
        painter.setFont(f2)

        # Gambar tagline di bawah nama (cy + 82 piksel)
        painter.drawText(QRectF(0, cy + 82, w, 20), Qt.AlignmentFlag.AlignCenter, "AI Malware Protection")
