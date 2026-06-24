"""
Widget Spinner Loading — Berputar Mulus di Semua Perangkat.

Spinner adalah animasi busur (setengah lingkaran) yang berputar terus-menerus,
menandakan bahwa ada proses yang sedang berjalan di latar belakang.

Keunggulan:
  - Menggunakan delta-time sehingga kecepatan putar SAMA persis
    di komputer lambat (30 fps) maupun komputer cepat (144 fps).
  - Sudut putar dihitung dalam 'derajat per detik', bukan 'derajat per tick'.
"""
from PySide6.QtWidgets import QWidget       # Kelas dasar semua widget tampilan
from PySide6.QtCore import Qt               # Konstanta Qt seperti transparansi
from PySide6.QtGui import QPainter, QPen, QColor  # Alat menggambar

from ui.core.anim_timer import AdaptiveTimer  # Timer berbasis delta waktu


class AnimatedSpinner(QWidget):
    """
    Spinner lingkaran yang berputar dengan kecepatan tetap di semua perangkat.

    Cara kerjanya:
      - Ada dua lingkaran: latar belakang (abu-abu samar) dan busur berputar (oranye).
      - Setiap tick timer, sudut mulai busur digeser sebesar (kecepatan × dt) derajat.
      - Karena dt adalah waktu nyata yang berlalu, kecepatan visually selalu sama.
    """

    # Kecepatan putar spinner dalam derajat per detik
    # 300 derajat/detik berarti satu putaran penuh selesai dalam 1.2 detik
    _SPEED_DEG_S = 300.0

    def __init__(self, diameter=80, line_width=6, parent=None):
        """
        Siapkan spinner dengan ukuran dan ketebalan garis yang bisa diatur.

        diameter   : Lebar dan tinggi widget dalam piksel (default 80px).
        line_width : Ketebalan cincin/busur dalam piksel (default 6px).
        parent     : Widget induk; spinner ikut terhapus saat induk ditutup.
        """
        super().__init__(parent)
        self.diameter = diameter
        self.line_width = line_width

        # Sudut awal busur spinner (dalam derajat, akan terus bertambah)
        self._angle = 0.0

        # Paksa ukuran widget tepat sesuai diameter yang diminta
        self.setFixedSize(diameter, diameter)

        # Latar belakang widget transparan agar kartu di bawahnya tetap terlihat
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Buat timer adaptif yang akan memanggil _on_tick ~60 kali per detik
        self._timer = AdaptiveTimer(target_fps=60, parent=self)

        # Hubungkan sinyal tick ke fungsi penggerak animasi
        self._timer.tick.connect(self._on_tick)

        # Langsung mulai berputar saat spinner dibuat
        self._timer.start()

    def _on_tick(self, dt: float):
        """
        Jalankan satu langkah animasi setiap kali timer berbunyi.

        dt adalah waktu nyata (detik) sejak tick terakhir.
        Mengalikan kecepatan dengan dt memastikan spinner berputar
        dengan kecepatan yang sama di semua perangkat.

        Setelah menggeser sudut, minta Qt untuk menggambar ulang widget.
        """
        # Geser sudut busur sesuai kecepatan × waktu nyata yang berlalu
        # % 360 memastikan sudut tidak melampaui 360 derajat (kembali ke 0)
        self._angle = (self._angle + self._SPEED_DEG_S * dt) % 360.0

        # Minta Qt untuk memanggil paintEvent agar tampilan diperbarui
        self.update()

    def paintEvent(self, event):
        """
        Gambar spinner setiap kali Qt meminta pembaruan tampilan.

        Terdiri dari dua lapisan:
          1. Lingkaran latar (abu-abu samar) — selalu penuh, tidak berputar.
          2. Busur oranye sepanjang 120 derajat — berputar mengikuti self._angle.
        """
        painter = QPainter(self)

        # Aktifkan anti-aliasing agar tepi lingkaran terlihat mulus, bukan bergerigi
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()  # Area gambar seluruh widget

        # Kecilkan area gambar agar garis tepi cincin tidak terpotong di tepi widget
        margin = self.line_width
        draw_rect = rect.adjusted(margin, margin, -margin, -margin)

        # ── Lapisan 1: Lingkaran latar belakang abu-abu samar ──
        # Warna abu-abu dengan transparansi tinggi (60/255 ≈ 24%)
        back_pen = QPen(QColor(100, 100, 100, 60), self.line_width)
        back_pen.setCapStyle(Qt.PenCapStyle.RoundCap)  # Ujung garis melengkung
        painter.setPen(back_pen)

        # Gambar lingkaran penuh (360 × 16 = satuan Qt untuk sudut dalam drawArc)
        painter.drawArc(draw_rect, 0, 360 * 16)

        # ── Lapisan 2: Busur oranye berputar ──
        # Warna oranye solid — inilah bagian yang terlihat "berputar"
        arc_pen = QPen(QColor(255, 140, 0), self.line_width)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)  # Ujung busur membulat
        painter.setPen(arc_pen)

        # Qt menggunakan satuan 1/16 derajat untuk drawArc:
        #   - Argumen ke-3: sudut mulai busur (self._angle × 16)
        #   - Argumen ke-4: panjang busur (120 derajat × 16 = busur 1/3 lingkaran)
        painter.drawArc(draw_rect, int(self._angle * 16), 120 * 16)

        # Akhiri sesi menggambar dan lepaskan sumber daya painter
        painter.end()
