"""
Widget Cincin Kemajuan (Progress Ring) — berbasis delta waktu untuk semua perangkat.

Progress ring adalah lingkaran dengan busur berwarna yang panjangnya mencerminkan
persentase kemajuan suatu proses (misalnya: proses scan 75% = busur sepanjang 75%).

Keunggulan:
  - Nilai progres bergerak mulus (tidak langsung meloncat) menggunakan easing eksponensial.
  - Kecepatan animasi konsisten di semua perangkat berkat delta-time.
  - Mendukung mode gelap dan terang untuk warna teks tengah.
"""
from PySide6.QtWidgets import QWidget         # Kelas dasar widget tampilan
from PySide6.QtCore import Qt                 # Konstanta penyelarasan
from PySide6.QtGui import QPainter, QPen, QColor, QConicalGradient  # Alat menggambar

from ui.core.anim_timer import AdaptiveTimer  # Timer berbasis delta waktu


class ProgressRing(QWidget):
    """
    Indikator kemajuan berbentuk cincin lingkaran dengan animasi halus.

    Cara kerjanya:
      - Ada nilai 'target_progress' (tujuan) dan 'progress' (posisi saat ini).
      - Setiap tick timer, nilai 'progress' mendekati 'target_progress' secara eksponensial.
        Artinya: cepat di awal, makin lambat saat mendekati target (efek ease-out).
      - Saat 'progress' sudah sangat dekat dengan target, timer dihentikan otomatis.
      - Persentase ditampilkan sebagai teks di tengah cincin.
    """

    def __init__(self, diameter=120, line_width=12, parent=None):
        """
        Siapkan cincin kemajuan dengan ukuran dan ketebalan yang bisa diatur.

        diameter   : Lebar dan tinggi widget dalam piksel (default 120px).
        line_width : Ketebalan cincin dalam piksel (default 12px).
        parent     : Widget induk; ring ikut terhapus saat induk ditutup.
        """
        super().__init__(parent)
        self.diameter = diameter
        self.line_width = line_width

        # Nilai kemajuan yang sedang ditampilkan (0.0 = 0%, 1.0 = 100%)
        # Ini bergerak perlahan menuju target_progress
        self.progress = 0.0

        # Nilai kemajuan yang ingin dicapai — diatur dari luar via set_progress()
        self.target_progress = 1.0

        # Status tema: True = mode gelap (teks putih), False = mode terang (teks gelap)
        self.is_dark = True

        # Paksa ukuran widget tepat sesuai diameter
        self.setFixedSize(diameter, diameter)

        # Latar belakang transparan agar kartu di baliknya tetap terlihat
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Timer adaptif ~60 tick/detik untuk menggerakkan animasi
        self._timer = AdaptiveTimer(target_fps=60, parent=self)
        self._timer.tick.connect(self._on_tick)
        # Timer TIDAK langsung dimulai — hanya berjalan saat set_progress(animate=True) dipanggil

    def set_progress(self, value: float, animate: bool = True):
        """
        Atur nilai kemajuan yang ingin ditampilkan.

        value   : Nilai antara 0.0 (0%) hingga 1.0 (100%). Otomatis dibatasi.
        animate : Jika True, nilai bergerak mulus ke target. Jika False, langsung loncat.

        Contoh penggunaan:
            ring.set_progress(0.75)        # Animasi ke 75%
            ring.set_progress(0.75, False) # Langsung tampilkan 75% tanpa animasi
        """
        # Batasi nilai antara 0.0 dan 1.0 agar tidak keluar batas
        self.target_progress = max(0.0, min(1.0, value))

        if animate:
            # Mulai timer animasi jika belum berjalan
            if not self._timer.is_active():
                self._timer.start()
        else:
            # Langsung set nilai tanpa animasi, lalu hentikan timer
            self.progress = self.target_progress
            self._timer.stop()
            self.update()  # Minta gambar ulang segera

    def _on_tick(self, dt: float):
        """
        Jalankan satu langkah animasi setiap tick.

        Menggunakan rumus easing eksponensial:
          progress += selisih × (1 - 0.05^dt)

        Efeknya: semakin dekat ke target, semakin lambat gerakannya (seperti rem halus).
        Saat selisih sudah sangat kecil (<0.2%), anggap sudah sampai dan hentikan timer.

        dt : Waktu nyata yang berlalu sejak tick sebelumnya (dalam detik).
        """
        diff = self.target_progress - self.progress  # Hitung jarak ke target

        if abs(diff) < 0.002:
            # Sudah sangat dekat — langsung paskan ke target dan hentikan timer
            self.progress = self.target_progress
            self._timer.stop()
        else:
            # Geser progress sebagian kecil dari selisih yang tersisa
            # pow(0.05, dt) → semakin besar dt, semakin besar langkah yang diambil
            # Hasilnya: ~95% dari selisih tertutup setiap detik
            self.progress += diff * (1.0 - pow(0.05, dt))

        # Minta Qt untuk menggambar ulang widget dengan nilai progress terbaru
        self.update()

    def paintEvent(self, event):
        """
        Gambar cincin kemajuan setiap kali Qt meminta pembaruan tampilan.

        Terdiri dari tiga bagian:
          1. Cincin latar (track) abu-abu samar — menunjukkan batas 100%.
          2. Busur kemajuan hijau dengan gradasi warna — panjangnya sesuai progress.
          3. Teks persentase di tengah cincin.
        """
        painter = QPainter(self)

        # Anti-aliasing membuat tepi cincin terlihat mulus
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()              # Area gambar seluruh widget
        cx = rect.width() / 2          # Koordinat X pusat cincin
        cy = rect.height() / 2         # Koordinat Y pusat cincin

        # Hitung jari-jari cincin (dikurangi setengah ketebalan garis agar tidak terpotong)
        radius = (min(rect.width(), rect.height()) - self.line_width) / 2

        # ── Bagian 1: Cincin latar belakang (track) ──
        # Warna putih sangat transparan (alpha 20/255 ≈ 8%) sebagai rel/track
        bg_pen = QPen(QColor(255, 255, 255, 20), self.line_width)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)  # Ujung garis melengkung
        painter.setPen(bg_pen)

        # Gambar lingkaran penuh dari sudut 90° (atas) searah jarum jam
        # Qt: sudut dinyatakan dalam 1/16 derajat, positif = berlawanan jarum jam
        painter.drawArc(
            int(cx - radius), int(cy - radius),  # Pojok kiri atas kotak pembatas
            int(radius * 2), int(radius * 2),    # Lebar dan tinggi kotak pembatas
            90 * 16,                             # Mulai dari atas (90°)
            -360 * 16,                           # Gambar penuh (negatif = searah jarum jam)
        )

        # ── Bagian 2: Busur kemajuan dengan gradasi hijau ──
        if self.progress > 0:
            # Gradasi kerucut (conical) dari hijau cerah ke hijau emerald
            # Dimulai dari sudut 90° (posisi "12 jam") searah putaran jam
            gradient = QConicalGradient(cx, cy, 90)
            gradient.setColorAt(0.0, QColor(34, 197, 94))    # Hijau segar di titik mulai
            gradient.setColorAt(1.0, QColor(16, 185, 129))   # Hijau emerald di titik akhir

            arc_pen = QPen(gradient, self.line_width)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)

            # Panjang busur = -360° × progress (negatif = searah jarum jam)
            # Contoh: progress=0.75 → busur sepanjang 270° (3/4 lingkaran)
            painter.drawArc(
                int(cx - radius), int(cy - radius),
                int(radius * 2), int(radius * 2),
                90 * 16,                                  # Mulai dari atas
                int(-360 * 16 * self.progress),           # Panjang busur sesuai kemajuan
            )

        # ── Bagian 3: Teks persentase di tengah ──
        # Warna teks berbeda untuk mode gelap (putih) dan mode terang (gelap)
        text_color = QColor(255, 255, 255) if self.is_dark else QColor(31, 41, 55)
        painter.setPen(text_color)

        # Atur font tebal dan besar agar angka mudah dibaca
        font = painter.font()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)

        # Tampilkan persentase sebagai bilangan bulat (contoh: "75%")
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter,
                         f"{int(self.progress * 100)}%")

        # Akhiri sesi menggambar
        painter.end()
