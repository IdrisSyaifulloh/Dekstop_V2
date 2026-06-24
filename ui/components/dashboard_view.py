"""
Tampilan Dashboard — Ringkasan keamanan sistem secara keseluruhan.

File ini menampilkan halaman utama MangoDefend yang berisi:
- Kartu identitas aplikasi (logo, versi model, status)
- Empat kartu statistik: ancaman diblokir, scan terakhir, penggunaan memori, dan beban CPU
- Tiga kartu ringkasan: total ancaman, lapisan proteksi, dan waktu scan
- Grafik batang aktivitas scan selama 7 hari terakhir

Data CPU dan memori diperbarui secara otomatis setiap 3 detik menggunakan timer.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

# psutil adalah library untuk membaca data sistem (CPU, memori, proses)
import psutil
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Sistem warna, tipografi, widget grafik, dan kartu kustom
from ui.styles.figma_theme import Colors, Typography
from ui.widgets import ActivityChart, SoftCard


def _asset(relative: str) -> str:
    """
    Mencari lokasi file aset (gambar, ikon) yang benar.

    Ketika aplikasi dikemas menjadi .exe, aset ada di folder sementara PyInstaller.
    Ketika sedang dikembangkan, aset dicari dari folder root proyek.

    Args:
        relative: Jalur file relatif dari root proyek, misalnya 'assets/mango_icon.png'.

    Returns:
        Jalur file lengkap (absolut) menuju file aset.
    """
    # Jika aplikasi sudah dikemas sebagai .exe, gunakan folder sementara PyInstaller
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        # Naik dua level dari ui/components/ ke root proyek
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, relative)


# Jalur lengkap ke file ikon aplikasi — disiapkan sekali saat modul pertama kali dimuat
_LOGO_PATH = _asset(os.path.join("assets", "mango_icon.png"))


class DashboardView(QWidget):
    """
    Halaman utama MangoDefend yang menampilkan ringkasan kondisi keamanan komputer.

    Berisi kartu statistik, data penggunaan CPU dan memori secara langsung,
    serta grafik aktivitas pemindaian 7 hari terakhir.

    Sinyal:
        navigate_requested(str): Dikirim ketika pengguna mengklik kartu yang
                                  mengarah ke halaman lain (misalnya klik kartu
                                  ancaman akan membuka halaman Quarantine).
    """

    # Sinyal untuk meminta navigasi ke halaman lain dari dalam dashboard
    navigate_requested = Signal(str)

    def __init__(self, parent=None):
        """
        Menyiapkan data awal dashboard dan membangun seluruh tampilan.

        Args:
            parent: Widget induk (biasanya area konten utama jendela).
        """
        super().__init__(parent)

        # Tema awal: gelap
        self.is_dark = True

        # Status proteksi realtime (True = aktif, False = standby)
        self.realtime_enabled = True

        # Waktu scan terakhir — diawali dengan waktu saat aplikasi dibuka
        self.last_scan = datetime.now()

        # Jumlah ancaman yang berhasil dideteksi dalam sesi ini
        self.threats_detected = 0

        # Kamus yang menyimpan jumlah scan per hari: {tanggal: jumlah_scan}
        self.scan_activity_by_day: dict = {}

        # Daftar semua kartu soft card untuk diperbarui saat tema berubah
        self._soft_cards: list[SoftCard] = []

        # Kamus kartu metrik (threats, last_scan, memory, cpu) untuk diakses per kunci
        self._metric_cards: dict[str, SoftCard] = {}

        # Daftar kartu ringkasan di bawah (blocked, layers, latest)
        self._summary_cards: list[SoftCard] = []

        # Referensi ke widget grafik aktivitas (akan diisi saat setup_ui)
        self.activity_chart: ActivityChart | None = None

        # --- Timer otomatis: memperbarui data CPU dan memori setiap 3 detik ---
        # Timer ini terus berjalan selama aplikasi aktif
        self._resource_timer = QTimer(self)
        # Ketika timer berbunyi (timeout), panggil fungsi _update_resources
        self._resource_timer.timeout.connect(self._update_resources)
        # Interval 3000 milidetik = 3 detik
        self._resource_timer.setInterval(3000)
        # Mulai timer segera
        self._resource_timer.start()

        # Bangun seluruh tampilan dashboard
        self.setup_ui()

    # ------------------------------------------------------------------
    # PEMBANTU WARNA TEMA
    # Fungsi-fungsi kecil ini mengembalikan warna yang tepat
    # berdasarkan tema aktif (gelap atau terang).
    # ------------------------------------------------------------------

    def _tp(self) -> str:
        """Mengembalikan warna teks utama sesuai tema saat ini (gelap atau terang)."""
        return Colors.DARK_TEXT_PRIMARY if self.is_dark else Colors.LIGHT_TEXT_PRIMARY

    def _ts(self) -> str:
        """Mengembalikan warna teks sekunder sesuai tema saat ini."""
        return Colors.DARK_TEXT_SECONDARY if self.is_dark else Colors.LIGHT_TEXT_SECONDARY

    def _tm(self) -> str:
        """Mengembalikan warna teks redup (kurang menonjol) sesuai tema saat ini."""
        return Colors.DARK_TEXT_MUTED if self.is_dark else Colors.LIGHT_TEXT_MUTED

    def _badge_bg(self, color: str, dark_alpha: int = 22, light_alpha: int = 18) -> str:
        """
        Menghasilkan warna latar belakang transparan dari warna aksen yang diberikan.

        Digunakan untuk membuat chip/badge dengan latar belakang semi-transparan
        yang cocok untuk kedua tema tanpa terlihat terlalu mencolok.

        Args:
            color: Warna dasar dalam format hex, misalnya '#FF6B00'.
            dark_alpha: Tingkat kegelapan (0-255) untuk tema gelap.
            light_alpha: Tingkat kegelapan (0-255) untuk tema terang.

        Returns:
            String warna CSS rgba, misalnya 'rgba(255, 107, 0, 0.086)'.
        """
        # Hapus karakter '#' di awal lalu pisahkan komponen R, G, B
        q = color.lstrip("#")
        r, g, b = int(q[0:2], 16), int(q[2:4], 16), int(q[4:6], 16)
        # Pilih tingkat transparansi berdasarkan tema aktif
        alpha = dark_alpha if self.is_dark else light_alpha
        # Konversi alpha dari 0-255 ke 0.0-1.0 untuk format rgba CSS
        return f"rgba({r}, {g}, {b}, {alpha / 255:.3f})"

    # ------------------------------------------------------------------
    # MEMBANGUN TAMPILAN
    # ------------------------------------------------------------------

    def setup_ui(self):
        """
        Membangun seluruh tata letak dashboard di dalam area gulir.

        Dashboard dibungkus dalam QScrollArea agar pengguna bisa menggulir
        ke bawah jika layar tidak cukup tinggi untuk menampilkan semua konten.

        Urutan konten dari atas ke bawah:
        1. Header panel (chip mode, judul, cap waktu)
        2. Grid 3 kolom: kartu identitas | kartu threats & scan | kartu memori & CPU
        3. Garis pemisah
        4. Label "Protection stats" + tiga kartu ringkasan
        5. Header grafik + grafik aktivitas 7 hari
        """
        # Area gulir agar konten bisa di-scroll jika layar tidak cukup tinggi
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)  # Konten mengikuti lebar area gulir
        scroll.setFrameShape(QFrame.Shape.NoFrame)  # Hapus batas kotak area gulir
        # Sembunyikan scrollbar horizontal dan vertikal (tetap bisa digulir dengan mouse)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        # Widget konten yang ditaruh di dalam area gulir
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        scroll.setWidget(content)

        # Tata letak vertikal untuk konten
        outer = QVBoxLayout(content)
        outer.setContentsMargins(18, 18, 18, 18)  # Margin tepi konten
        outer.setSpacing(14)

        # Panel utama: kartu besar yang membungkus seluruh konten dashboard
        self.main_panel = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_500, hover_effect=False)
        self._soft_cards.append(self.main_panel)
        self.main_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Tata letak dalam panel utama
        panel_layout = QVBoxLayout(self.main_panel)
        panel_layout.setContentsMargins(20, 18, 20, 20)
        panel_layout.setSpacing(14)

        # Baris header panel (chip mode, judul, cap waktu)
        panel_layout.addLayout(self._create_panel_header())

        # Grid tiga kolom untuk kartu-kartu statistik utama
        top_grid = QGridLayout()
        top_grid.setHorizontalSpacing(10)
        top_grid.setVerticalSpacing(10)

        # Kolom pertama (kiri): kartu identitas — memanjang dua baris
        top_grid.addWidget(self._create_identity_card(), 0, 0, 2, 1)

        # Baris atas kolom tengah: kartu ancaman yang diblokir
        top_grid.addWidget(
            self._create_metric_card(
                key="threats",
                title="Threats blocked",        # Judul kartu
                stamp=self._panel_stamp(),       # Cap waktu
                value="0",                       # Nilai awal
                subtitle="Realtime neutralization active",  # Keterangan bawah
                accent=Colors.ORANGE_500,        # Warna aksen oranye
                footer_glyph="▂▃▅▇▆",           # Simbol mini grafik dekoratif
                value_color=Colors.ORANGE_500,   # Warna angka = oranye
            ),
            0, 1,  # Baris 0, kolom 1
        )

        # Baris atas kolom kanan: kartu waktu scan terakhir
        top_grid.addWidget(
            self._create_metric_card(
                key="last_scan",
                title="Last scan",
                stamp=self.last_scan.strftime("%H:%M"),   # Jam dan menit scan terakhir
                value=self.last_scan.strftime("%H:%M"),
                subtitle="No threats found",
                accent=Colors.GREEN_500,
                footer_glyph="◦─◦─◦",
                value_color=self._tp(),  # Warna angka = warna teks utama
            ),
            0, 2,  # Baris 0, kolom 2
        )

        # Baris bawah kolom tengah: kartu penggunaan memori (diperbarui tiap 3 detik)
        top_grid.addWidget(
            self._create_metric_card(
                key="memory",
                title="Memory usage",
                stamp="Live",         # Menunjukkan data ini diperbarui secara langsung
                value="128 MB",       # Nilai awal sementara
                subtitle="Runtime footprint",
                accent=Colors.EMERALD_500,
                footer_glyph="▁▂▂▃▂",
                value_color=self._tp(),
            ),
            1, 1,  # Baris 1, kolom 1
        )

        # Baris bawah kolom kanan: kartu beban CPU (diperbarui tiap 3 detik)
        top_grid.addWidget(
            self._create_metric_card(
                key="cpu",
                title="CPU load",
                stamp="Live",         # Menunjukkan data ini diperbarui secara langsung
                value="2.3%",         # Nilai awal sementara
                subtitle="Background processing",
                accent=Colors.ORANGE_400,
                footer_glyph="▁▄▂▅▃",
                value_color=self._tp(),
            ),
            1, 2,  # Baris 1, kolom 2
        )

        # Atur bobot kolom agar ketiga kolom lebarnya sama rata
        top_grid.setColumnStretch(0, 1)
        top_grid.setColumnStretch(1, 1)
        top_grid.setColumnStretch(2, 1)
        panel_layout.addLayout(top_grid)

        # Garis pemisah horizontal tipis antar bagian
        divider = QFrame()
        divider.setFixedHeight(1)  # Garis setipis 1 piksel
        self.divider = divider
        panel_layout.addWidget(divider)

        # Label judul bagian "Protection stats"
        panel_layout.addWidget(self._create_section_label("Protection stats"))

        # Tiga kartu ringkasan di bawah label
        panel_layout.addLayout(self._create_summary_row())

        # --- Header grafik aktivitas ---
        chart_header = QHBoxLayout()
        chart_header.setSpacing(10)

        # Judul "Recent activity" di sisi kiri
        self.chart_title = QLabel("Recent activity")
        chart_header.addWidget(self.chart_title)
        chart_header.addStretch()  # Dorong badge "7D" ke kanan

        # Badge kecil "7D" yang menjelaskan rentang waktu grafik (7 hari)
        self.chart_badge = QLabel("7D")
        self.chart_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_badge.setFixedHeight(28)
        self.chart_badge.setMinimumWidth(44)
        chart_header.addWidget(self.chart_badge)
        panel_layout.addLayout(chart_header)

        # Widget grafik batang untuk menampilkan aktivitas scan harian
        self.activity_chart = ActivityChart()
        self.activity_chart.set_theme(self.is_dark)  # Atur tema awal grafik
        self.activity_chart.setToolTip("Hover bar untuk lihat detail aktivitas")
        panel_layout.addWidget(self.activity_chart)

        # Isi grafik dengan data awal (semua nol jika belum ada data)
        self._refresh_activity_chart()

        # Masukkan panel utama ke tata letak konten gulir
        outer.addWidget(self.main_panel)

        # Tata letak akar: area gulir memenuhi seluruh halaman
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        # Terapkan tema dan ambil data resource awal
        self._apply_theme()
        self._update_resources()

        # Sambungkan kartu-kartu ke aksi navigasi
        self._wire_interactions()

    def _create_panel_header(self) -> QHBoxLayout:
        """
        Membuat baris header di bagian paling atas panel utama.

        Berisi tiga elemen yang disusun secara horizontal:
        - Chip "Security pulse" di sisi kiri
        - Judul "MangoDefend Overview" di tengah
        - Cap tanggal dan waktu di sisi kanan

        Returns:
            Tata letak horizontal berisi tiga elemen header.
        """
        layout = QHBoxLayout()
        layout.setSpacing(12)

        # Chip/badge di kiri yang menunjukkan mode pemantauan
        self.mode_chip = QLabel("Security pulse")
        self.mode_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_chip.setFixedHeight(34)
        self.mode_chip.setMinimumWidth(118)
        layout.addWidget(self.mode_chip)

        # Ruang fleksibel yang mendorong judul ke tengah
        layout.addStretch()

        # Judul halaman di tengah
        self.header_title = QLabel("MangoDefend Overview")
        self.header_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.header_title)

        # Ruang fleksibel yang mendorong cap waktu ke kanan
        layout.addStretch()

        # Cap tanggal dan waktu scan terakhir di kanan
        self.header_stamp = QLabel(self._panel_stamp())
        self.header_stamp.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.header_stamp)

        return layout

    def _create_identity_card(self) -> SoftCard:
        """
        Membuat kartu identitas besar di kolom kiri dashboard.

        Kartu ini menampilkan:
        - Logo aplikasi + chip status realtime
        - Nama aplikasi "MangoDefend"
        - Subtitle dan keterangan status proteksi
        - Tabel mini: nama model, mode operasi, jenis window

        Kartu ini bisa diklik dan akan mengarahkan ke halaman Update.

        Returns:
            Kartu identitas yang sudah terhubung ke aksi navigasi.
        """
        # Buat kartu dengan efek hover agar terlihat interaktif
        card = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_500, hover_effect=True)
        self._soft_cards.append(card)
        card.set_interactive(True)       # Aktifkan respons visual saat diklik
        card.setToolTip("Buka halaman Update")  # Teks bantuan saat mouse diam di atas kartu
        self.identity_card = card        # Simpan referensi untuk dihubungkan ke sinyal nanti
        card.setMinimumHeight(284)       # Tinggi minimum agar proporsional dengan kolom lain
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        # Tata letak vertikal dalam kartu
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # --- Baris atas: logo + chip status ---
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Frame persegi untuk logo — diberi latar dan border melingkar
        logo_frame = QFrame()
        logo_frame.setFixedSize(54, 54)
        self.logo_frame = logo_frame  # Disimpan agar bisa digaya ulang saat tema berubah
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(7, 7, 7, 7)
        logo_layout.setSpacing(0)

        # Label yang menampilkan gambar logo
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = QPixmap(_LOGO_PATH)  # Muat gambar dari jalur yang sudah disiapkan
        if not pix.isNull():
            # Skalakan gambar ke 38x38 piksel dengan kualitas halus
            self.logo_label.setPixmap(
                pix.scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
        else:
            # Fallback: tampilkan teks "MD" jika gambar tidak ditemukan
            self.logo_label.setText("MD")
        logo_layout.addWidget(self.logo_label)
        top_row.addWidget(logo_frame)

        # Dorong chip status ke sisi kanan baris atas
        top_row.addStretch()

        # Chip status realtime di sudut kanan atas kartu
        self.state_chip = QLabel("Realtime ready")
        self.state_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_chip.setFixedHeight(28)
        self.state_chip.setMinimumWidth(112)
        top_row.addWidget(self.state_chip)
        layout.addLayout(top_row)

        # --- Nama aplikasi ---
        self.identity_title = QLabel("MangoDefend")
        layout.addWidget(self.identity_title)

        # --- Subtitle berwarna oranye ---
        self.identity_subtitle = QLabel("Desktop threat telemetry")
        layout.addWidget(self.identity_subtitle)

        # --- Label status lapisan proteksi ---
        self.identity_status = QLabel("Layered protection status")
        layout.addWidget(self.identity_status)

        # --- Nilai mode scan saat ini ---
        self.identity_value = QLabel("Public scan lane")
        layout.addWidget(self.identity_value)

        # --- Tabel mini dua kolom: label dan nilai ---
        info_grid = QGridLayout()
        info_grid.setHorizontalSpacing(8)
        info_grid.setVerticalSpacing(10)

        # Simpan referensi label kiri (kunci) dan kanan (nilai)
        self.identity_keys: list[QLabel] = []
        self.identity_vals: list[QLabel] = []

        # Data yang ditampilkan dalam tabel mini
        rows = [
            ("Model", "CNN v3 ONNX"),  # Nama model AI yang digunakan
            ("Mode", "Local core"),    # Mode operasi (lokal, tanpa server)
            ("Window", "Desktop"),     # Jenis platform
        ]

        for row, (key_text, value_text) in enumerate(rows):
            # Label kolom kiri (kunci) — rata kiri
            key = QLabel(key_text)
            # Label kolom kanan (nilai) — rata kanan
            val = QLabel(value_text)
            key.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.identity_keys.append(key)
            self.identity_vals.append(val)
            info_grid.addWidget(key, row, 0)  # Kolom 0 (kiri)
            info_grid.addWidget(val, row, 1)  # Kolom 1 (kanan)

        layout.addLayout(info_grid)
        return card

    def _create_metric_card(
        self,
        *,
        key: str,
        title: str,
        stamp: str,
        value: str,
        subtitle: str,
        accent: str,
        footer_glyph: str,
        value_color: str,
    ) -> SoftCard:
        """
        Membuat satu kartu statistik kecil (metrik) di grid atas dashboard.

        Setiap kartu menampilkan:
        - Baris atas: judul (kiri) dan cap waktu (bawah judul)
        - Nilai besar di tengah
        - Baris bawah: subtitle dan simbol grafik dekoratif

        Referensi setiap label disimpan sebagai atribut kelas menggunakan nama dinamis,
        misalnya self.threats_value_label untuk kartu dengan key='threats'.

        Args:
            key: ID unik kartu, digunakan sebagai awalan nama atribut label.
            title: Judul kartu yang ditampilkan.
            stamp: Cap waktu atau status singkat di bawah judul.
            value: Nilai utama yang ditampilkan besar.
            subtitle: Keterangan di bagian bawah kartu.
            accent: Warna aksen untuk ikon dan elemen dekoratif.
            footer_glyph: Simbol mini sebagai grafik dekoratif (contoh: '▂▃▅▇▆').
            value_color: Warna teks nilai utama.

        Returns:
            Kartu metrik yang sudah dibuat dan ditambahkan ke daftar _soft_cards.
        """
        # Buat kartu dengan warna aksen yang sesuai dan efek hover
        card = SoftCard(is_dark=self.is_dark, accent=accent, hover_effect=True)
        self._soft_cards.append(card)
        self._metric_cards[key] = card  # Simpan referensi berdasarkan kunci
        card.set_interactive(True)
        card.setMinimumHeight(138)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # Tata letak vertikal dalam kartu
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Baris header: kolom kiri berisi judul dan cap waktu
        header = QHBoxLayout()
        header.setSpacing(4)

        title_stamp_col = QVBoxLayout()
        title_stamp_col.setSpacing(2)
        title_stamp_col.setContentsMargins(0, 0, 0, 0)

        # Label judul kartu
        title_label = QLabel(title)
        # Label cap waktu di bawah judul
        stamp_label = QLabel(stamp)
        title_stamp_col.addWidget(title_label)
        title_stamp_col.addWidget(stamp_label)
        header.addLayout(title_stamp_col)
        header.addStretch()
        layout.addLayout(header)

        # Nilai besar di tengah kartu (misalnya "0", "14:35", "128 MB")
        value_label = QLabel(value)
        layout.addWidget(value_label)

        # Baris footer: subtitle di kiri, simbol grafik di kanan
        footer = QHBoxLayout()
        footer.setSpacing(8)
        subtitle_label = QLabel(subtitle)
        footer.addWidget(subtitle_label)
        footer.addStretch()
        glyph_label = QLabel(footer_glyph)  # Simbol dekoratif seperti '▂▃▅▇▆'
        footer.addWidget(glyph_label)
        layout.addLayout(footer)

        # Simpan referensi semua label sebagai atribut kelas dengan nama dinamis
        # Contoh: key='threats' → self.threats_title_label, self.threats_value_label, dll.
        setattr(self, f"{key}_title_label", title_label)
        setattr(self, f"{key}_stamp_label", stamp_label)
        setattr(self, f"{key}_value_label", value_label)
        setattr(self, f"{key}_subtitle_label", subtitle_label)
        setattr(self, f"{key}_glyph_label", glyph_label)
        setattr(self, f"{key}_accent", accent)
        setattr(self, f"{key}_value_color", value_color)

        return card

    def _create_section_label(self, text: str) -> QLabel:
        """
        Membuat label judul bagian (section header) dengan teks yang diberikan.

        Digunakan sebagai pemisah visual antara grid atas dan baris ringkasan.

        Args:
            text: Teks yang akan ditampilkan sebagai judul bagian.

        Returns:
            Label judul yang siap ditambahkan ke tata letak.
        """
        label = QLabel(text)
        label.setText(text)
        # Simpan referensi agar bisa diperbarui saat tema berubah
        self.summary_header = label
        return label

    def _create_summary_row(self) -> QHBoxLayout:
        """
        Membuat tiga kartu ringkasan yang disusun secara horizontal.

        Kartu-kartu ini:
        1. "Threats neutralized" — total ancaman yang diblokir dalam sesi ini
        2. "Layers online" — jumlah lapisan proteksi yang aktif (misalnya 3/3)
        3. "Latest scan" — jam scan terakhir

        Setiap kartu bisa diklik dan akan mengarahkan ke halaman yang relevan.

        Returns:
            Tata letak horizontal berisi tiga kartu ringkasan.
        """
        layout = QHBoxLayout()
        layout.setSpacing(8)

        # Kamus untuk menyimpan referensi label per kartu: {key: (title, value, caption)}
        self.summary_items: dict[str, tuple[QLabel, QLabel, QLabel]] = {}

        # Data tiga kartu ringkasan: (kunci, judul, nilai, warna aksen, keterangan)
        items = [
            ("blocked", "Threats neutralized", "0",                          Colors.ORANGE_500, "Session total"),
            ("layers",  "Layers online",        "3 / 3",                     Colors.GREEN_500,  "Monitor state"),
            ("latest",  "Latest scan",           self.last_scan.strftime("%H:%M"), self._tp(),  "Updated just now"),
        ]

        for key, title_text, value_text, accent, caption_text in items:
            # Buat kartu kecil dengan warna aksen yang sesuai
            card = SoftCard(is_dark=self.is_dark, accent=accent, hover_effect=True)
            card.setMinimumHeight(92)
            self._soft_cards.append(card)
            self._summary_cards.append(card)
            card.set_interactive(True)  # Aktifkan respons visual saat diklik

            # Tata letak vertikal dalam kartu dengan tiga baris teks (semua rata tengah)
            col = QVBoxLayout(card)
            col.setContentsMargins(14, 12, 14, 12)
            col.setSpacing(2)

            title   = QLabel(title_text)   # Label judul kecil di atas
            value   = QLabel(value_text)   # Angka/teks utama di tengah
            caption = QLabel(caption_text) # Keterangan kecil di bawah

            col.addWidget(title,   alignment=Qt.AlignmentFlag.AlignCenter)
            col.addWidget(value,   alignment=Qt.AlignmentFlag.AlignCenter)
            col.addWidget(caption, alignment=Qt.AlignmentFlag.AlignCenter)

            # Tambahkan kartu ke tata letak dengan bobot 1 (lebar sama rata)
            layout.addWidget(card, 1)

            # Simpan referensi label agar bisa diperbarui nanti
            self.summary_items[key] = (title, value, caption)

        return layout

    def _panel_stamp(self) -> str:
        """
        Memformat waktu scan terakhir menjadi teks yang mudah dibaca.

        Contoh hasil: "21 Jun 2026  14:35"

        Returns:
            String tanggal dan waktu scan terakhir.
        """
        return self.last_scan.strftime("%d %b %Y  %H:%M")

    def _wire_interactions(self):
        """
        Menghubungkan klik pada setiap kartu interaktif ke aksi navigasi yang sesuai.

        Ketika pengguna mengklik kartu tertentu, sinyal navigate_requested dikirim
        dengan ID halaman tujuan, sehingga tampilan utama bisa berpindah halaman.

        Koneksi:
        - Kartu identitas → halaman Update
        - Kartu ancaman → halaman Quarantine
        - Kartu scan terakhir → halaman Scan
        - Kartu memori → halaman Protection
        - Kartu CPU → halaman Protection
        - Kartu ringkasan blocked → halaman Quarantine
        - Kartu ringkasan layers → halaman Protection
        - Kartu ringkasan latest scan → halaman Scan
        """
        # Kartu identitas: klik → buka halaman Update
        self.identity_card.clicked.connect(lambda: self.navigate_requested.emit("update"))

        # Kartu ancaman: klik → buka halaman Quarantine (lihat file yang diblokir)
        self._metric_cards["threats"].clicked.connect(lambda: self.navigate_requested.emit("quarantine"))

        # Kartu scan terakhir: klik → buka halaman Scan
        self._metric_cards["last_scan"].clicked.connect(lambda: self.navigate_requested.emit("scan"))

        # Kartu memori: klik → buka halaman Protection
        self._metric_cards["memory"].clicked.connect(lambda: self.navigate_requested.emit("protection"))

        # Kartu CPU: klik → buka halaman Protection
        self._metric_cards["cpu"].clicked.connect(lambda: self.navigate_requested.emit("protection"))

        # Kartu ringkasan "blocked": klik → buka Quarantine
        self._summary_cards[0].clicked.connect(lambda: self.navigate_requested.emit("quarantine"))

        # Kartu ringkasan "layers": klik → buka Protection
        self._summary_cards[1].clicked.connect(lambda: self.navigate_requested.emit("protection"))

        # Kartu ringkasan "latest scan": klik → buka Scan
        self._summary_cards[2].clicked.connect(lambda: self.navigate_requested.emit("scan"))

        # Tambahkan tooltip (teks bantuan) pada setiap kartu
        self._metric_cards["threats"].setToolTip("Buka halaman Quarantine")
        self._metric_cards["last_scan"].setToolTip("Buka halaman Scan")
        self._metric_cards["memory"].setToolTip("Buka halaman Protection")
        self._metric_cards["cpu"].setToolTip("Buka halaman Protection")
        self._summary_cards[0].setToolTip("Lihat file yang diblokir")
        self._summary_cards[1].setToolTip("Lihat lapisan proteksi")
        self._summary_cards[2].setToolTip("Buka riwayat scan")
        self.main_panel.setToolTip("Ringkasan proteksi MangoDefend")

    # ------------------------------------------------------------------
    # PENERAPAN TEMA
    # ------------------------------------------------------------------

    def _apply_theme(self):
        """
        Menerapkan warna tema saat ini ke semua widget di dashboard.

        Dipanggil setelah setup_ui() dan setiap kali tema berubah.
        Mengatur warna teks, latar belakang, garis pemisah, chip, dan grafik.
        """
        # Perbarui tema semua kartu soft card
        for card in self._soft_cards:
            card.set_theme(self.is_dark)

        # Ambil warna-warna yang sesuai tema saat ini
        tp = self._tp()   # Warna teks utama
        ts = self._ts()   # Warna teks sekunder
        tm = self._tm()   # Warna teks redup
        success = Colors.GREEN_500 if self.is_dark else Colors.EMERALD_500  # Warna "berhasil"

        # Perbarui warna aksen panel utama
        self.main_panel.set_accent(Colors.ORANGE_500 if self.is_dark else Colors.ORANGE_400)

        # Garis pemisah: warna berbeda untuk tema gelap dan terang
        self.divider.setStyleSheet(
            f"background: {'rgba(255,255,255,0.08)' if self.is_dark else 'rgba(31,41,55,0.10)'}; border: none;"
        )

        # Chip "Security pulse" di header panel
        self.mode_chip.setStyleSheet(
            f"""
            background: {self._badge_bg(Colors.ORANGE_500, 30, 22)};
            color: {Colors.ORANGE_500};
            border: 1px solid {self._badge_bg(Colors.ORANGE_500, 80, 50)};
            border-radius: 17px;
            font-size: 11px;
            font-weight: 600;
            font-family: {Typography.FONT_FAMILY};
            padding: 0 12px;
            """
        )

        # Judul "MangoDefend Overview" di header panel
        self.header_title.setStyleSheet(
            f"color: {tp}; font-size: 22px; font-weight: 600; background: transparent;"
            f" font-family: {Typography.FONT_FAMILY};"
        )

        # Cap tanggal dan waktu di kanan header
        self.header_stamp.setStyleSheet(
            f"color: {tm}; font-size: 12px; background: transparent; font-family: {Typography.FONT_FAMILY};"
        )

        # Frame pembungkus logo: latar belakang dan border semi-transparan
        self.logo_frame.setStyleSheet(
            f"""
            background: {self._badge_bg(Colors.ORANGE_500, 26, 18)};
            border: 1px solid {self._badge_bg(Colors.ORANGE_500, 72, 46)};
            border-radius: 16px;
            """
        )

        # Label logo (teks fallback "MD" jika gambar tidak ada)
        self.logo_label.setStyleSheet(
            f"color: {Colors.ORANGE_500}; background: transparent; font-size: 16px; font-weight: 700;"
        )

        # Chip status realtime di sudut kanan atas kartu identitas
        self.state_chip.setStyleSheet(
            f"""
            background: {self._badge_bg(success, 24, 18)};
            color: {success};
            border: 1px solid {self._badge_bg(success, 84, 48)};
            border-radius: 14px;
            font-size: 11px;
            font-weight: 600;
            padding: 0 10px;
            """
        )

        # Nama aplikasi "MangoDefend" (teks besar)
        self.identity_title.setStyleSheet(
            f"color: {tp}; font-size: 28px; font-weight: 600; background: transparent;"
            f" font-family: {Typography.FONT_FAMILY};"
        )

        # Subtitle berwarna oranye
        self.identity_subtitle.setStyleSheet(
            f"color: {Colors.ORANGE_500}; font-size: 13px; font-weight: 500; background: transparent;"
            f" font-family: {Typography.FONT_FAMILY};"
        )

        # Label status proteksi (teks redup)
        self.identity_status.setStyleSheet(
            f"color: {tm}; font-size: 11px; letter-spacing: 0.4px; background: transparent;"
            f" font-family: {Typography.FONT_FAMILY};"
        )

        # Nilai mode scan (teks utama, ukuran sedang)
        self.identity_value.setStyleSheet(
            f"color: {tp}; font-size: 18px; font-weight: 500; background: transparent;"
            f" font-family: {Typography.FONT_FAMILY};"
        )

        # Label kunci di tabel mini (warna redup)
        for key in self.identity_keys:
            key.setStyleSheet(
                f"color: {tm}; font-size: 11px; background: transparent; font-family: {Typography.FONT_FAMILY};"
            )

        # Label nilai di tabel mini (warna sekunder)
        for val in self.identity_vals:
            val.setStyleSheet(
                f"color: {ts}; font-size: 11px; font-weight: 500; background: transparent;"
                f" font-family: {Typography.FONT_FAMILY};"
            )

        # Perbarui gaya semua label di keempat kartu metrik
        for key in ("threats", "last_scan", "memory", "cpu"):
            # Ambil referensi label yang disimpan secara dinamis saat pembuatan
            title_label    = getattr(self, f"{key}_title_label")
            stamp_label    = getattr(self, f"{key}_stamp_label")
            value_label    = getattr(self, f"{key}_value_label")
            subtitle_label = getattr(self, f"{key}_subtitle_label")
            glyph_label    = getattr(self, f"{key}_glyph_label")
            accent         = getattr(self, f"{key}_accent")
            value_color    = getattr(self, f"{key}_value_color")

            # Judul kartu — warna sekunder, ukuran kecil
            title_label.setStyleSheet(
                f"color: {ts}; font-size: 11px; font-weight: 500; background: transparent;"
                f" font-family: {Typography.FONT_FAMILY};"
            )

            # Cap waktu di bawah judul — warna redup
            stamp_label.setStyleSheet(
                f"color: {tm}; font-size: 11px; background: transparent; font-family: {Typography.FONT_FAMILY};"
            )

            # Nilai besar di tengah — warna sesuai kartu
            value_label.setStyleSheet(
                f"color: {value_color}; font-size: 21px; font-weight: 600; background: transparent;"
                f" font-family: {Typography.FONT_FAMILY};"
            )

            # Subtitle di bawah — warna hijau untuk kartu scan, redup untuk lainnya
            subtitle_label.setStyleSheet(
                f"color: {success if key == 'last_scan' else tm}; font-size: 12px; background: transparent;"
                f" font-family: {Typography.FONT_FAMILY};"
            )

            # Simbol grafik dekoratif — warna aksen, font monospace
            glyph_label.setStyleSheet(
                f"color: {accent}; font-size: 18px; background: transparent;"
                f" font-family: {Typography.FONT_FAMILY_MONO};"
            )

        # Label judul bagian "Protection stats"
        self.summary_header.setStyleSheet(
            f"color: {tp}; font-size: 20px; font-weight: 500; background: transparent;"
            f" font-family: {Typography.FONT_FAMILY};"
        )

        # Perbarui gaya label di tiga kartu ringkasan
        for key, (title, value, caption) in self.summary_items.items():
            # Tentukan warna nilai berdasarkan jenis kartu
            value_color = tp  # Default: warna teks utama

            if key == "blocked":
                value_color = Colors.ORANGE_500    # Ancaman: oranye
            elif key == "layers":
                value_color = success              # Lapisan aktif: hijau

            # Judul kecil di atas nilai
            title.setStyleSheet(
                f"color: {tm}; font-size: 11px; font-weight: 500; background: transparent;"
                f" font-family: {Typography.FONT_FAMILY};"
            )

            # Nilai utama yang besar
            value.setStyleSheet(
                f"color: {value_color}; font-size: 22px; font-weight: 600; background: transparent;"
                f" font-family: {Typography.FONT_FAMILY};"
            )

            # Keterangan kecil di bawah nilai
            caption.setStyleSheet(
                f"color: {tm}; font-size: 11px; background: transparent; font-family: {Typography.FONT_FAMILY};"
            )

        # Judul grafik "Recent activity"
        self.chart_title.setStyleSheet(
            f"color: {tp}; font-size: 18px; font-weight: 500; background: transparent;"
            f" font-family: {Typography.FONT_FAMILY};"
        )

        # Badge "7D" di sebelah judul grafik
        self.chart_badge.setStyleSheet(
            f"""
            background: {self._badge_bg(Colors.ORANGE_400, 24, 16)};
            color: {Colors.ORANGE_500};
            border: 1px solid {self._badge_bg(Colors.ORANGE_400, 74, 42)};
            border-radius: 14px;
            font-size: 11px;
            font-weight: 600;
            padding: 0 10px;
            """
        )

        # Perbarui tema grafik aktivitas jika sudah dibuat
        if self.activity_chart:
            self.activity_chart.set_theme(self.is_dark)

    # ------------------------------------------------------------------
    # PEMBARUAN DATA LANGSUNG
    # ------------------------------------------------------------------

    def _update_resources(self):
        """
        Mengambil data penggunaan CPU dan memori secara langsung dari sistem,
        lalu memperbarui label di kartu metrik CPU dan memori.

        Fungsi ini dipanggil otomatis setiap 3 detik oleh _resource_timer.
        Menggunakan library psutil untuk membaca data sistem.
        """
        try:
            # Baca persentase beban CPU saat ini (interval=0 berarti baca langsung tanpa jeda)
            cpu = psutil.cpu_percent(interval=0)

            # Baca penggunaan memori proses aplikasi ini sendiri (bukan seluruh sistem)
            proc = psutil.Process()  # Objek proses untuk aplikasi yang sedang berjalan
            mem_mb = proc.memory_info().rss / (1024 * 1024)  # Konversi byte ke MB

            # Perbarui label di kartu CPU (contoh: "4.2%")
            self.cpu_value_label.setText(f"{cpu:.1f}%")

            # Perbarui label di kartu memori (contoh: "132 MB")
            self.memory_value_label.setText(f"{mem_mb:.0f} MB")

        except Exception:
            # Abaikan error — mungkin terjadi jika psutil tidak tersedia atau proses berakhir
            pass

    def update_threats(self, count: int):
        """
        Memperbarui jumlah ancaman yang ditampilkan di kartu metrik dan kartu ringkasan.

        Dipanggil oleh mesin deteksi setiap kali ancaman baru ditemukan.

        Args:
            count: Jumlah total ancaman yang sudah diblokir dalam sesi ini.
        """
        # Simpan nilai terbaru
        self.threats_detected = count

        # Perbarui angka besar di kartu metrik "Threats blocked"
        self.threats_value_label.setText(str(count))

        # Perbarui angka di kartu ringkasan "Threats neutralized"
        self.summary_items["blocked"][1].setText(str(count))

    def update_threats_count(self, count: int):
        """
        Alias untuk fungsi update_threats() — dipertahankan agar kode lama tetap berjalan.

        Args:
            count: Jumlah total ancaman yang sudah diblokir.
        """
        self.update_threats(count)

    def update_last_scan(self, scan_time: datetime):
        """
        Memperbarui semua label waktu dengan timestamp scan terbaru.

        Dipanggil setelah proses scan selesai untuk mencerminkan waktu scan yang baru.

        Args:
            scan_time: Objek datetime yang merepresentasikan waktu scan selesai.
        """
        # Simpan waktu scan terbaru
        self.last_scan = scan_time

        # Format: jam dan menit saja (misalnya "14:35")
        stamp = scan_time.strftime("%H:%M")

        # Perbarui cap waktu di kartu metrik "Last scan"
        self.last_scan_stamp_label.setText(stamp)
        self.last_scan_value_label.setText(stamp)

        # Perbarui nilai di kartu ringkasan "Latest scan"
        self.summary_items["latest"][1].setText(stamp)
        self.summary_items["latest"][2].setText("Updated just now")

        # Perbarui cap tanggal dan waktu di header panel
        self.header_stamp.setText(self._panel_stamp())

    def record_scan_activity(self, count: int = 1, scan_time: datetime | None = None):
        """
        Mencatat bahwa ada aktivitas scan terjadi hari ini untuk ditampilkan di grafik.

        Setiap kali scan dilakukan, fungsi ini dipanggil untuk menambah hitungan
        aktivitas pada hari tersebut. Grafik kemudian diperbarui secara otomatis.

        Args:
            count: Jumlah file yang dipindai dalam satu sesi scan (default 1).
            scan_time: Waktu scan terjadi. Jika None, gunakan waktu saat ini.
        """
        # Jangan catat jika jumlahnya nol atau negatif
        if count <= 0:
            return

        # Gunakan waktu saat ini jika tidak ada waktu yang diberikan
        when = scan_time or datetime.now()
        day = when.date()  # Ambil hanya bagian tanggal (tanpa jam)

        # Tambahkan ke hitungan hari ini (jika sudah ada, tambahkan; jika belum, mulai dari 0)
        self.scan_activity_by_day[day] = self.scan_activity_by_day.get(day, 0) + count

        # Hapus data yang lebih dari 7 hari lalu
        self._trim_activity_days()

        # Perbarui tampilan grafik
        self._refresh_activity_chart()

    def _trim_activity_days(self):
        """
        Menghapus entri data aktivitas yang lebih dari 7 hari lalu.

        Dilakukan agar kamus scan_activity_by_day tidak terus bertambah besar
        dan grafik hanya menampilkan data 7 hari terakhir yang relevan.
        """
        # Hitung batas tanggal paling awal yang masih ditampilkan (6 hari lalu)
        start_day = datetime.now().date() - timedelta(days=6)

        # Buat kamus baru hanya dengan entri yang masih dalam rentang 7 hari
        self.scan_activity_by_day = {
            day: count
            for day, count in self.scan_activity_by_day.items()
            if day >= start_day
        }

    def _refresh_activity_chart(self):
        """
        Mengirimkan data aktivitas scan 7 hari terakhir ke widget grafik untuk dirender.

        Membangun dua daftar paralel:
        - labels: tanggal dalam format "DD" (misalnya "21")
        - values: jumlah aktivitas scan pada masing-masing tanggal

        Hari tanpa data akan menampilkan nilai 0 di grafik.
        """
        # Jangan lakukan apa-apa jika grafik belum dibuat
        if not self.activity_chart:
            return

        today = datetime.now().date()

        # Buat daftar 7 tanggal: dari 6 hari lalu hingga hari ini (urutan kronologis)
        days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]

        # Buat label untuk sumbu X (hanya hari dalam bulan, misalnya "15", "16", ...)
        labels = [day.strftime("%d") for day in days]

        # Ambil jumlah aktivitas untuk setiap hari (0 jika tidak ada data)
        values = [self.scan_activity_by_day.get(day, 0) for day in days]

        # Kirim data ke widget grafik
        self.activity_chart.set_activity_data(labels, values)

    def set_realtime_state(self, enabled: bool):
        """
        Memperbarui tampilan dashboard berdasarkan status proteksi realtime.

        Ketika proteksi aktif, menampilkan status hijau dan lapisan penuh (3/3).
        Ketika proteksi dimatikan, menampilkan status standby dan lapisan nol (0/3).

        Args:
            enabled: True jika proteksi realtime sedang aktif, False jika tidak.
        """
        # Simpan status baru
        self.realtime_enabled = enabled

        # Perbarui chip status di kartu identitas
        self.state_chip.setText("Realtime active" if enabled else "Realtime standby")

        # Perbarui teks mode di bawah nama aplikasi
        self.identity_value.setText("Public scan lane" if enabled else "Protection paused")

        # Perbarui kartu ringkasan lapisan proteksi
        self.summary_items["layers"][1].setText("3 / 3" if enabled else "0 / 3")
        self.summary_items["layers"][2].setText("Monitor state" if enabled else "Protection paused")

        # Terapkan ulang tema untuk memperbarui warna sesuai kondisi baru
        self._apply_theme()

    def set_theme(self, is_dark: bool):
        """
        Mengganti tema antara gelap dan terang, lalu menggambar ulang semua widget.

        Dipanggil dari luar (misalnya tombol tema di Sidebar) untuk menyinkronkan
        tampilan dashboard dengan tema yang dipilih pengguna.

        Args:
            is_dark: True untuk tema gelap, False untuk tema terang.
        """
        # Simpan pilihan tema baru
        self.is_dark = is_dark

        # Terapkan ulang semua warna dan gaya
        self._apply_theme()
