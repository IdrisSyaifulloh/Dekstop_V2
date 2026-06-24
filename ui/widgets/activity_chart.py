"""
Widget Grafik Batang Aktivitas Scan — beranimasi mulus di semua perangkat.

Grafik ini menampilkan jumlah file yang dipindai per hari selama 7 hari terakhir.
Setiap batang tumbuh dari bawah saat pertama kali ditampilkan, dengan jeda kecil
antar batang (efek 'stagger') agar terlihat dinamis.

Fitur visual:
  - Batang 'ghost' (bayangan): menampilkan data periode sebelumnya sebagai perbandingan.
  - Batang 'live' (aktif): data hari-hari ini, tumbuh dari bawah saat pertama ditampilkan.
  - Batang terpilih berwarna oranye dengan cahaya berdenyut di belakangnya.
  - Hover menampilkan outline tipis oranye tanpa mengubah warna isian.
  - Garis rata-rata putus-putus sebagai referensi.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QBrush, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ui.styles.figma_theme import Colors      # Konstanta warna design system
from ui.core.anim_timer import AdaptiveTimer  # Timer berbasis delta waktu


class ActivityChart(QWidget):
    """
    Grafik batang beranimasi dengan lapisan backdrop (ghost) dan lapisan aktif.

    Cara kerja animasi:
      - 'animation_progress' bergerak dari 0.0 ke 1.0 dalam ~1.2 detik saat pertama tampil.
      - Setiap batang menggunakan 'local_progress' yang berbeda-beda berdasarkan indeksnya
        (batang pertama tumbuh duluan, batang terakhir tumbuh belakangan = efek stagger).
      - 'sweep_phase' berputar terus dari 0.0 ke 1.0 untuk cahaya denyut pada batang terpilih.

    Interaksi pengguna:
      - Klik batang mana saja → batang itu menjadi 'selected' (oranye + cahaya denyut).
      - Arahkan mouse ke batang → outline oranye tipis muncul.
      - Batang terakhir (hari ini) dipilih secara default.
    """

    def __init__(self, parent=None):
        """
        Siapkan grafik aktivitas 7 hari dengan animasi batang tumbuh dari bawah.
        """
        super().__init__(parent)
        self.setMinimumHeight(250)

        # Latar transparan agar warna kartu di bawah tetap terlihat
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Aktifkan pelacakan mouse agar hover bisa dideteksi tanpa klik
        self.setMouseTracking(True)

        # Status tema (gelap/terang) untuk menentukan palet warna
        self.is_dark = True

        # ── Data grafik ──
        # Label sumbu-X: tanggal 7 hari terakhir (format "DD")
        self.labels = self._default_labels()

        # Nilai batang utama (jumlah scan per hari)
        self.values = [0.0] * len(self.labels)

        # Nilai batang ghost/bayangan (data periode perbandingan, bisa 0 semua)
        self.ghost_values = [0.0] * len(self.labels)

        # Nilai tertinggi di antara semua batang (digunakan sebagai batas atas sumbu-Y)
        self.max_value = 1.0

        # Rata-rata nilai batang utama (ditampilkan sebagai garis putus-putus)
        self.avg_line = 0.0

        # ── Status interaksi ──
        self._hovered_index  = -1                    # Indeks batang yang sedang dihover (-1 = tidak ada)
        self._selected_index = len(self.values) - 1  # Batang terakhir dipilih saat awal

        # ── Status animasi ──
        self.animation_progress = 0.0  # 0.0→1.0: kemajuan animasi tumbuh batang
        self.sweep_phase        = 0.0  # 0.0→1.0: fase denyut cahaya pada batang terpilih

        # Timer adaptif yang menjalankan animasi ~60 kali per detik
        self._timer = AdaptiveTimer(target_fps=60, parent=self)
        self._timer.tick.connect(self._tick)
        self._timer.start()

    # ── API Publik ────────────────────────────────────────────────────────────

    def set_theme(self, is_dark: bool):
        """
        Ganti antara palet warna mode gelap dan mode terang.
        Dipanggil dari induk saat pengguna mengganti tema.
        """
        self.is_dark = is_dark
        self.update()  # Minta gambar ulang dengan palet baru

    def set_activity_data(self, labels: list[str], values: list[float],
                          ghost_values: list[float] | None = None):
        """
        Perbarui data grafik dengan data aktivitas scan terbaru.

        labels      : Daftar label sumbu-X (tanggal atau nama hari).
        values      : Jumlah scan per label (panjang harus sama dengan labels).
        ghost_values: Data bayangan/perbandingan (opsional). Jika None, semua nol.

        Data yang dimasukkan otomatis dibersihkan:
          - Label dikonversi ke string.
          - Nilai negatif diubah menjadi 0.
          - max_value dihitung ulang dengan margin 20% agar bar tidak menyentuh batas atas.
        """
        if not labels or not values:
            # Jika tidak ada data, gunakan label default dengan nilai nol
            labels = self._default_labels()
            values = [0.0] * len(labels)

        # Ambil data sebanyak jumlah label atau nilai, mana yang lebih kecil
        count = min(len(labels), len(values))
        self.labels = [str(label) for label in labels[:count]]
        self.values = [max(0.0, float(value)) for value in values[:count]]

        # Proses data ghost/bayangan
        if ghost_values:
            self.ghost_values = [max(0.0, float(value)) for value in ghost_values[:count]]
            # Isi kekurangan dengan nol jika data ghost lebih sedikit dari count
            if len(self.ghost_values) < count:
                self.ghost_values.extend([0.0] * (count - len(self.ghost_values)))
        else:
            self.ghost_values = [0.0] * count

        # Hitung nilai tertinggi dari semua batang (aktif + ghost), minimum 1.0
        # Tambah 20% di atas nilai tertinggi agar bar tidak menyentuh tepi atas grafik
        highest = max(self.values + self.ghost_values + [1.0])
        self.max_value = max(1.0, math.ceil(highest * 1.2))

        # Hitung rata-rata untuk garis referensi putus-putus
        self.avg_line = sum(self.values) / len(self.values) if self.values else 0.0

        # Pilih batang terakhir sebagai default saat data baru dimasukkan
        self._selected_index = max(0, len(self.values) - 1)

        self.update()

    @staticmethod
    def _default_labels() -> list[str]:
        """
        Buat label 7 hari terakhir dalam format tanggal dua digit ("01" hingga "31").
        Digunakan sebagai label sumbu-X default saat data belum diisi.
        """
        today = datetime.now().date()
        # Daftar dari 6 hari lalu hingga hari ini
        return [(today - timedelta(days=offset)).strftime("%d") for offset in range(6, -1, -1)]

    @staticmethod
    def _format_axis(value: float) -> str:
        """
        Format angka sumbu-Y secara rapi:
          - Jika bilangan bulat, tampilkan tanpa desimal (misal "10" bukan "10.0").
          - Jika tidak, tampilkan satu angka di belakang koma (misal "2.5").
        """
        return str(int(value)) if float(value).is_integer() else f"{value:.1f}"

    # ── Interaksi Mouse ───────────────────────────────────────────────────────

    def _bar_index_at(self, x_pos: float) -> int:
        """
        Temukan indeks batang yang berada di bawah posisi X mouse.

        Cara kerjanya:
          - Area plot dihitung dari ukuran widget dikurangi margin dan label.
          - Lebar setiap 'slot batang' = lebar area plot / jumlah batang.
          - Indeks = (posisi X - tepi kiri plot) / lebar slot.

        Mengembalikan -1 jika posisi X berada di luar area plot.
        """
        rect = self.rect().adjusted(12, 8, -12, -8)

        # Area plot aktual (di dalam margin label sumbu-X dan sumbu-Y)
        plot = QRectF(rect.left() + 12, rect.top() + 8, rect.width() - 58, rect.height() - 48)

        # Cek apakah posisi X berada di dalam area plot
        if not plot.contains(x_pos, plot.center().y()):
            return -1

        # Hitung slot tiap batang dan tentukan indeks
        bar_slot = plot.width() / max(1, len(self.values))
        index = int((x_pos - plot.left()) / bar_slot)
        return index if 0 <= index < len(self.values) else -1

    def mouseMoveEvent(self, event):
        """Perbarui highlight hover saat mouse bergerak di atas grafik."""
        index = self._bar_index_at(event.position().x())
        if index != self._hovered_index:
            self._hovered_index = index
            self.update()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """
        Pilih batang yang diklik (warna oranye tetap sampai batang lain diklik).
        Hanya merespons klik tombol kiri mouse.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            index = self._bar_index_at(event.position().x())
            if index >= 0:
                self._selected_index = index
                self.update()
        super().mousePressEvent(event)

    def leaveEvent(self, event):
        """Hapus highlight hover saat mouse meninggalkan widget."""
        self._hovered_index = -1
        self.update()
        super().leaveEvent(event)

    # ── Animasi ─────────────────────────────────────────────────────────────

    def _tick(self, dt: float):
        """
        Jalankan satu langkah animasi setiap tick timer.

        Dua animasi berjalan sekaligus:
          1. Tumbuh batang (animation_progress): 0→1 dalam ~1.2 detik.
             Setelah mencapai 1.0, tidak berubah lagi (hemat CPU).
          2. Denyut cahaya (sweep_phase): berputar terus 0→1→0→... setiap ~5 detik.
             Digunakan untuk efek kilau pada batang terpilih.

        dt : Waktu nyata yang berlalu (detik) — memastikan kecepatan sama di semua perangkat.
        """
        # Animasi tumbuh batang: tambah setiap frame sampai mencapai 1.0
        if self.animation_progress < 1.0:
            self.animation_progress = min(1.0, self.animation_progress + dt / 1.2)

        # Fase denyut cahaya: berputar terus-menerus (% 1.0 agar kembali ke 0)
        # dt / 5.0 berarti satu siklus penuh setiap 5 detik
        self.sweep_phase = (self.sweep_phase + dt / 5.0) % 1.0

        self.update()

    # ── Palet Warna ──────────────────────────────────────────────────────────

    def _palette(self) -> dict[str, QColor]:
        """
        Kembalikan palet warna yang sesuai dengan tema aktif.

        Setiap kunci adalah nama elemen grafik, nilainya adalah QColor.
        Palet berbeda antara mode gelap dan mode terang untuk keterbacaan optimal.
        """
        if self.is_dark:
            return {
                "grid":          QColor(255, 255, 255, 18),   # Garis grid: putih sangat samar
                "label":         QColor(107, 114, 128),        # Label sumbu: abu-abu sedang
                "axis":          QColor(204, 204, 204, 88),    # Teks sumbu-Y: putih transparan
                "avg":           QColor(255, 255, 255, 72),    # Garis rata-rata: putih semi-transparan
                "ghost_top":     QColor(255, 255, 255, 42),    # Batang ghost: atas putih transparan
                "ghost_bottom":  QColor(255, 255, 255, 10),    # Batang ghost: bawah hampir hilang
                "bar_top":       QColor(255, 255, 255, 210),   # Batang biasa: atas putih terang
                "bar_bottom":    QColor(214, 214, 214, 168),   # Batang biasa: bawah putih redup
                "accent_top":    QColor(255, 183, 50, 238),    # Batang terpilih: oranye kuning
                "accent_bottom": QColor(255, 165, 0,  188),    # Batang terpilih: oranye murni
                "glow":          QColor(255, 165, 0,  78),     # Cahaya denyut: oranye transparan
            }
        # Palet mode terang — warna lebih kontras dengan latar putih
        return {
            "grid":          QColor(31, 41, 55,  20),
            "label":         QColor(107, 114, 128),
            "axis":          QColor(68, 68, 68,  100),
            "avg":           QColor(68, 68, 68,  72),
            "ghost_top":     QColor(31, 41, 55,  28),
            "ghost_bottom":  QColor(31, 41, 55,  10),
            "bar_top":       QColor(255, 255, 255, 238),
            "bar_bottom":    QColor(229, 231, 235, 224),
            "accent_top":    QColor(255, 183, 50, 235),
            "accent_bottom": QColor(255, 165, 0,  180),
            "glow":          QColor(255, 165, 0,  56),
        }

    # ── Pembantu Menggambar ──────────────────────────────────────────────────

    def _draw_bar(self, painter: QPainter, rect: QRectF, radius: float,
                  top_color: QColor, bottom_color: QColor):
        """
        Gambar satu batang dengan sudut melengkung dan gradasi dari atas ke bawah.

        rect       : Posisi dan ukuran batang di canvas.
        radius     : Sudut melengkung batang dalam piksel.
        top_color  : Warna puncak batang (lebih terang).
        bottom_color: Warna dasar batang (lebih gelap).
        """
        # Gradasi vertikal: terang di atas, gelap di bawah
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0.0, top_color)
        gradient.setColorAt(1.0, bottom_color)

        painter.setPen(Qt.PenStyle.NoPen)  # Tidak ada border pada batang
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(rect, radius, radius)

    # ── Menggambar Utama ─────────────────────────────────────────────────────

    def paintEvent(self, event):
        """
        Gambar seluruh grafik setiap kali Qt meminta pembaruan tampilan.

        Urutan gambar:
          1. Grid garis horizontal + garis rata-rata putus-putus.
          2. Batang ghost (bayangan data lama) → batang aktif beranimasi.
          3. Label sumbu-X (tanggal) dan sumbu-Y (angka).
        """
        super().paintEvent(event)
        if not self.values:
            return  # Tidak ada yang digambar jika data kosong

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self._palette()

        # Area widget dikurangi margin 12px kiri-kanan dan 8px atas-bawah
        rect = self.rect().adjusted(12, 8, -12, -8)

        # Area plot aktual (di dalam margin untuk label sumbu)
        # Kiri +12: ruang untuk angka sumbu-Y tidak ada di sini, dihitung di _paint_labels
        # Kanan -58: ruang untuk label nilai sumbu-Y di sebelah kanan
        # Bawah -48: ruang untuk label tanggal sumbu-X
        plot = QRectF(rect.left() + 12, rect.top() + 8, rect.width() - 58, rect.height() - 48)

        self._paint_grid(painter, palette, plot)    # Langkah 1: grid
        self._paint_bars(painter, palette, plot)    # Langkah 2: batang
        self._paint_labels(painter, palette, plot)  # Langkah 3: label

        painter.end()

    def _paint_grid(self, painter: QPainter, palette: dict, plot: QRectF):
        """
        Gambar garis grid horizontal dan garis rata-rata putus-putus.

        Grid: 5 garis horizontal merata dari bawah ke atas area plot.
        Rata-rata: garis putus-putus di posisi vertikal yang sesuai nilai rata-rata.
        """
        # ── 5 garis grid horizontal ──
        painter.setPen(QPen(palette["grid"], 1))
        for step in range(5):
            # Posisi Y: dari bawah (step=0) ke atas (step=4)
            y = plot.bottom() - (plot.height() / 4.0) * step
            painter.drawLine(plot.left(), y, plot.right(), y)

        # ── Garis rata-rata putus-putus ──
        # Posisi Y dihitung dari rasio nilai rata-rata terhadap nilai maksimum
        avg_y   = plot.bottom() - (self.avg_line / self.max_value) * plot.height()
        avg_pen = QPen(palette["avg"], 1)
        avg_pen.setStyle(Qt.PenStyle.DashLine)  # Gaya garis putus-putus
        painter.setPen(avg_pen)
        painter.drawLine(plot.left(), avg_y, plot.right(), avg_y)

        # Simpan posisi Y rata-rata agar bisa digunakan kembali di _paint_labels
        self._avg_y = avg_y

    def _paint_bars(self, painter: QPainter, palette: dict, plot: QRectF):
        """
        Gambar semua batang grafik: ghost (bayangan) terlebih dahulu, lalu batang aktif.

        Urutan ini penting: ghost digambar dulu agar batang aktif menutupinya dari depan.

        Animasi tumbuh batang:
          - Setiap batang memiliki 'local_progress' yang berbeda (stagger).
          - Batang pertama (indeks 0) mulai tumbuh lebih awal dari batang terakhir.
          - Rumus: local_progress = animation_progress * 1.2 - index * 0.08
            → Semakin besar indeks, semakin terlambat mulai tumbuhnya.
          - Easing power 2.8: cepat di awal, melambat di akhir.
        """
        # Hitung lebar slot per batang (area plot dibagi jumlah batang)
        bar_slot = plot.width() / max(1, len(self.values))

        # Batang ghost sedikit lebih lebar agar kontras di belakang batang aktif
        ghost_width = min(42.0, bar_slot * 0.72)
        live_width  = min(42.0, bar_slot * 0.60)   # Batang aktif lebih sempit

        # ── Gambar batang ghost (data periode lama/perbandingan) ──
        for index, value in enumerate(self.ghost_values):
            x_center     = plot.left() + bar_slot * index + bar_slot * 0.5
            ghost_height = (value / max(1.0, self.max_value)) * plot.height()

            # Batang ghost tidak beranimasi — langsung tampilkan tinggi penuhnya
            ghost_rect = QRectF(
                x_center - ghost_width / 2.0,
                plot.bottom() - ghost_height,
                ghost_width, ghost_height,
            )
            self._draw_bar(painter, ghost_rect, 9.0, palette["ghost_top"], palette["ghost_bottom"])

        # ── Gambar batang aktif dengan animasi stagger ──
        for index, value in enumerate(self.values):
            # Kemajuan lokal batang ini: batang awal maju duluan
            local_progress = max(0.0, min(1.0, self.animation_progress * 1.2 - index * 0.08))

            # Easing: cepat di awal, lambat menjelang selesai (power 2.8)
            eased = 1.0 - math.pow(1.0 - local_progress, 2.8)

            # Tinggi batang saat ini = tinggi penuh × kemajuan easing
            live_height = (value / max(1.0, self.max_value)) * plot.height() * eased
            x_center    = plot.left() + bar_slot * index + bar_slot * 0.5

            live_rect = QRectF(
                x_center - live_width / 2.0,
                plot.bottom() - live_height,
                live_width, live_height,
            )

            is_selected = index == self._selected_index
            is_hovered  = index == self._hovered_index and not is_selected

            if is_selected:
                # ── Batang terpilih: oranye + cahaya denyut di belakangnya ──

                # Ukuran cahaya denyut berubah sesuai sweep_phase (pulsasi sine)
                # math.tau = 2π; sin berulang dari -1 ke 1 setiap siklus
                glow = 10.0 + 8.0 * (0.5 + 0.5 * math.sin(self.sweep_phase * math.tau))

                # Gambar kotak cahaya yang sedikit lebih besar dari batang
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(palette["glow"])
                painter.drawRoundedRect(
                    QRectF(
                        live_rect.left()   - glow * 0.4,  # Melebar ke kiri
                        live_rect.top()    - glow * 0.3,  # Melebar ke atas
                        live_rect.width()  + glow * 0.8,  # Melebar ke kanan
                        live_rect.height() + glow * 0.6,  # Melebar ke bawah
                    ),
                    14.0, 14.0,
                )

                # Gambar batang aktif dengan warna aksen oranye
                self._draw_bar(painter, live_rect, 8.0, palette["accent_top"], palette["accent_bottom"])
            else:
                # ── Batang biasa: warna putih/abu-abu ──
                self._draw_bar(painter, live_rect, 8.0, palette["bar_top"], palette["bar_bottom"])

            # ── Outline oranye tipis saat dihover (tanpa mengubah isian) ──
            if is_hovered:
                painter.setPen(QPen(palette["accent_top"], 1.5))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                # Gambar outline 2px lebih besar dari batang agar tidak menimpa isian
                painter.drawRoundedRect(live_rect.adjusted(-2, -2, 2, 2), 10.0, 10.0)

    def _paint_labels(self, painter: QPainter, palette: dict, plot: QRectF):
        """
        Gambar label teks pada sumbu-X (tanggal) dan sumbu-Y (angka).

        Sumbu-X: Label tanggal di bawah setiap batang.
        Sumbu-Y: Tiga nilai di sebelah kanan grafik — maksimum, rata-rata, nol.
        """
        bar_slot = plot.width() / max(1, len(self.values))

        # ── Label sumbu-X (tanggal) ──
        font = painter.font()
        font.setFamily("Inter")
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(palette["label"])

        for index, label in enumerate(self.labels):
            # Posisi X di tengah slot batang masing-masing
            x_center = plot.left() + bar_slot * index + bar_slot * 0.5
            painter.drawText(
                QRectF(x_center - 18, plot.bottom() + 8, 36, 18),
                Qt.AlignmentFlag.AlignCenter,
                label,
            )

        # ── Label sumbu-Y (nilai) ──
        axis_font = painter.font()
        axis_font.setPointSize(8)  # Sedikit lebih kecil dari label X
        painter.setFont(axis_font)
        painter.setPen(palette["axis"])

        # Ambil posisi Y rata-rata yang sudah dihitung di _paint_grid
        avg_y = getattr(self, "_avg_y", plot.center().y())

        # Tiga titik label: nilai maks di atas, rata-rata di tengah, nol di bawah
        axis_labels = [
            (self._format_axis(self.max_value), plot.top()),    # Label nilai tertinggi
            (self._format_axis(self.avg_line),  avg_y),         # Label nilai rata-rata
            ("0", plot.bottom() - 4),                            # Label nilai nol
        ]

        for text, y in axis_labels:
            # Gambar teks di sebelah kanan area plot (+10px dari tepi kanan)
            painter.drawText(
                QRectF(plot.right() + 10, y - 10, 24, 20),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                text,
            )
