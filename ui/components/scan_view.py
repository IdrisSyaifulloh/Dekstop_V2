"""
Tampilan Pemindaian — Antarmuka untuk memindai file, folder, atau seluruh perangkat.

File ini mengelola halaman Scan pada MangoDefend yang terdiri dari:
- Header halaman dengan judul dan deskripsi
- Tiga kartu pilihan mode scan: Scan File, Scan Folder, Scan Perangkat
- Panel progres yang muncul saat scan sedang berjalan
- Bagian riwayat pemindaian yang menampilkan hasil-hasil scan sebelumnya

Ketika pengguna memilih file atau folder, sinyal dikirim ke komponen lain
yang bertanggung jawab menjalankan proses pemindaian sesungguhnya.
"""

import os
import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QFileDialog, QListWidget,
    QListWidgetItem, QScrollArea, QGridLayout, QProgressBar,
)
from PySide6.QtCore import Qt, Signal

# Widget kartu kustom dan sistem warna/gaya
from ui.widgets import SoftCard
from ui.styles.figma_theme import Colors, Typography, StyleHelper


class ScanView(QWidget):
    """
    Halaman pemindai malware dengan tiga pilihan mode scan.

    Mode yang tersedia:
    1. Scan File — memindai satu file yang dipilih pengguna
    2. Scan Folder — memindai semua file dalam folder yang dipilih
    3. Scan Perangkat — memindai seluruh file di komputer

    Sinyal yang dikirim ke luar ketika pengguna memilih aksi:
        scan_requested(str): Jalur file yang ingin dipindai (scan file tunggal).
        folder_scan_requested(str): Jalur folder yang ingin dipindai.
        device_scan_requested: Permintaan scan seluruh perangkat (tanpa parameter).
    """

    # Sinyal dikirim saat pengguna memilih satu file untuk dipindai
    scan_requested = Signal(str)

    # Sinyal dikirim saat pengguna memilih folder untuk dipindai
    folder_scan_requested = Signal(str)

    # Sinyal dikirim saat pengguna meminta scan seluruh perangkat
    device_scan_requested = Signal()

    def __init__(self, parent=None):
        """
        Menyiapkan daftar pelacak label dan membangun seluruh tampilan halaman.

        Args:
            parent: Widget induk (biasanya area konten utama jendela).
        """
        super().__init__(parent)

        # Tema awal: gelap
        self.is_dark = True

        # Referensi ke area gulir (disimpan agar bisa diakses nanti jika perlu)
        self._scroll_ref = None

        # Daftar label teks utama — warnanya diperbarui saat tema berubah
        self._primary_labels: list[QLabel] = []

        # Daftar label teks redup — warnanya diperbarui saat tema berubah
        self._muted_labels: list[QLabel] = []

        # Daftar semua kartu soft card — tema mereka diperbarui bersama-sama
        self._soft_cards: list[SoftCard] = []

        # Bangun seluruh tampilan halaman
        self.setup_ui()

    # ------------------------------------------------------------------
    # PEMBANTU WARNA TEMA
    # Fungsi pendek yang mengembalikan warna sesuai tema aktif.
    # ------------------------------------------------------------------

    def _tp(self) -> str:
        """Mengembalikan warna teks utama sesuai tema saat ini (gelap atau terang)."""
        return Colors.DARK_TEXT_PRIMARY if self.is_dark else Colors.LIGHT_TEXT_PRIMARY

    def _tm(self) -> str:
        """Mengembalikan warna teks redup (abu-abu, kurang mencolok) sesuai tema saat ini."""
        return Colors.DARK_TEXT_MUTED if self.is_dark else Colors.LIGHT_TEXT_MUTED

    def _card_bg(self) -> str:
        """Mengembalikan warna latar belakang kartu semi-transparan sesuai tema saat ini."""
        return "rgba(255,255,255,0.04)" if self.is_dark else "rgba(0,0,0,0.04)"

    def _card_border(self) -> str:
        """Mengembalikan warna garis tepi kartu semi-transparan sesuai tema saat ini."""
        return "rgba(255,255,255,0.08)" if self.is_dark else "rgba(0,0,0,0.08)"

    def _reg_p(self, lbl: QLabel) -> QLabel:
        """
        Mendaftarkan label ke daftar 'primary' dan mengembalikannya.

        Label yang terdaftar akan mendapat warna teks utama (_tp())
        saat fungsi _apply_theme() dipanggil.

        Args:
            lbl: Label yang ingin didaftarkan.

        Returns:
            Label yang sama — bisa langsung digunakan setelah didaftarkan.
        """
        self._primary_labels.append(lbl)
        return lbl

    def _reg_m(self, lbl: QLabel) -> QLabel:
        """
        Mendaftarkan label ke daftar 'muted' dan mengembalikannya.

        Label yang terdaftar akan mendapat warna teks redup (_tm())
        saat fungsi _apply_theme() dipanggil.

        Args:
            lbl: Label yang ingin didaftarkan.

        Returns:
            Label yang sama — bisa langsung digunakan setelah didaftarkan.
        """
        self._muted_labels.append(lbl)
        return lbl

    # ------------------------------------------------------------------
    # MEMBANGUN TAMPILAN
    # ------------------------------------------------------------------

    def setup_ui(self):
        """
        Membangun seluruh tata letak halaman scan di dalam area gulir.

        Urutan konten dari atas ke bawah:
        1. Kartu header dengan judul dan deskripsi halaman
        2. Grid tiga kartu pilihan mode scan (file / folder / perangkat)
        3. Panel progres scan (tersembunyi sampai scan dimulai)
        4. Bagian riwayat pemindaian
        5. Ruang kosong fleksibel di bawah
        """
        # Area gulir agar halaman bisa di-scroll jika konten melebihi tinggi layar
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)  # Konten mengikuti lebar area gulir
        scroll.setFrameShape(QFrame.Shape.NoFrame)  # Hapus batas kotak area gulir
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        # Sembunyikan scrollbar agar tampilan lebih bersih (masih bisa digulir dengan mouse)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_ref = scroll  # Simpan referensi

        # Widget konten yang ditempatkan di dalam area gulir
        content = QWidget()
        content.setStyleSheet("background:transparent;")

        # Tata letak vertikal untuk semua konten halaman
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 32)  # Margin tepi: kiri/kanan lebih lebar
        layout.setSpacing(24)  # Jarak antar bagian

        # --- 1. Kartu header ---
        # Menampilkan judul besar dan deskripsi singkat halaman scan
        header_card = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_500)
        self._soft_cards.append(header_card)
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(40, 36, 40, 36)  # Padding besar agar terlihat lapang
        header_layout.setSpacing(16)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Teks rata tengah

        # Judul halaman — didaftarkan sebagai label utama agar warnanya ikut tema
        title = self._reg_p(QLabel("Smart Malware Scanner"))
        title.setStyleSheet(f"""
            color:{self._tp()};font-size:26px;font-weight:bold;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)

        # Deskripsi singkat — didaftarkan sebagai label redup
        desc = self._reg_m(QLabel(
            "Pilih file, folder, atau scan seluruh perangkat\nuntuk mendeteksi malware menggunakan AI"
        ))
        desc.setWordWrap(True)   # Bungkus teks jika terlalu panjang
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet(f"""
            color:{self._tm()};font-size:13px;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        header_layout.addWidget(desc)

        layout.addWidget(header_card)

        # --- 2. Grid tiga kartu pilihan mode scan ---
        # Tiga kartu disusun dalam satu baris menggunakan QGridLayout
        options_grid = QGridLayout()
        options_grid.setSpacing(16)  # Jarak antar kartu

        # Kartu pertama: Scan File tunggal (warna aksen oranye)
        options_grid.addWidget(
            self._create_scan_option(
                icon="",                                        # Ikon emoji
                title="Scan File",
                desc="Pilih satu file untuk\ndipindai secara mendalam",
                btn_text="Pilih File",
                accent=Colors.ORANGE_500,                        # Aksen oranye
                callback=self._browse_file,                      # Fungsi dipanggil saat klik
            ),
            0, 0,  # Baris 0, kolom 0
        )

        # Kartu kedua: Scan seluruh folder (warna aksen oranye muda)
        options_grid.addWidget(
            self._create_scan_option(
                icon="",
                title="Folder Scanner",
                desc="Pindai semua file dalam\nfolder yang dipilih",
                btn_text="Pilih Folder",
                accent=Colors.ORANGE_300,                        # Aksen oranye lebih muda
                callback=self._browse_folder,
            ),
            0, 1,  # Baris 0, kolom 1
        )

        # Kartu ketiga: Full Device Scan (warna aksen merah karena lebih intens)
        options_grid.addWidget(
            self._create_scan_option(
                icon="",
                title="Scan Perangkat",
                desc="Scan seluruh file berbahaya\ndi seluruh perangkat Anda",
                btn_text="Mulai Full Scan",
                accent=Colors.RED_500,                           # Aksen merah = aksi kuat
                callback=self._start_device_scan,
            ),
            0, 2,  # Baris 0, kolom 2
        )

        layout.addLayout(options_grid)

        # --- 3. Panel progres scan ---
        # Panel ini disembunyikan dan baru muncul saat scan sedang berjalan
        self._progress_panel = self._create_progress_panel()
        self._progress_panel.hide()  # Sembunyikan dulu — akan ditampilkan saat scan dimulai
        layout.addWidget(self._progress_panel)

        # --- 4. Bagian riwayat scan ---
        # Kartu yang berisi daftar hasil pemindaian sebelumnya
        layout.addWidget(self._create_history_section())

        # Ruang kosong fleksibel agar konten tidak melekat ke bawah
        layout.addStretch()

        # Masukkan konten ke area gulir
        scroll.setWidget(content)

        # Tata letak akar: area gulir memenuhi seluruh halaman
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _create_scan_option(
        self, icon: str, title: str, desc: str,
        btn_text: str, accent: str, callback,
    ) -> SoftCard:
        """
        Membuat satu kartu pilihan scan dengan ikon, judul, deskripsi, dan tombol aksi.

        Kartu ini bisa diklik (seluruh area) atau hanya menekan tombolnya.
        Keduanya memanggil callback yang sama.

        Args:
            icon: Emoji atau karakter ikon yang ditampilkan besar di atas.
            title: Judul kartu, misalnya "Scan File".
            desc: Deskripsi singkat dua baris yang menjelaskan fungsi mode ini.
            btn_text: Teks pada tombol aksi, misalnya "Pilih File".
            accent: Warna aksen kartu (oranye atau merah).
            callback: Fungsi yang dipanggil saat kartu atau tombol diklik.

        Returns:
            Kartu pilihan scan yang siap ditambahkan ke tata letak.
        """
        # Buat kartu dengan efek hover untuk memberi umpan balik visual saat mouse di atas
        card = SoftCard(is_dark=self.is_dark, accent=accent)
        self._soft_cards.append(card)
        card.set_interactive(True)  # Aktifkan respons visual saat diklik

        # Ketika seluruh area kartu diklik, panggil callback
        card.clicked.connect(callback)
        card.setToolTip(f"Buka aksi: {title}")  # Teks bantuan saat mouse diam di kartu
        card.setMinimumHeight(220)  # Tinggi minimum agar kartu terlihat proporsional

        # Tata letak vertikal dalam kartu, semua elemen rata tengah
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Ikon besar di atas kartu
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size:36px;background:transparent;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(icon_lbl)

        # Judul kartu — didaftarkan sebagai label utama agar ikut tema
        title_lbl = self._reg_p(QLabel(title))
        title_lbl.setStyleSheet(f"""
            color:{self._tp()};font-size:16px;font-weight:bold;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_lbl)

        # Deskripsi dua baris — didaftarkan sebagai label redup
        desc_lbl = self._reg_m(QLabel(desc))
        desc_lbl.setWordWrap(True)  # Bungkus teks jika terlalu panjang
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setStyleSheet(f"""
            color:{self._tm()};font-size:11px;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        card_layout.addWidget(desc_lbl)

        # Sedikit ruang ekstra sebelum tombol
        card_layout.addSpacing(4)

        # Tombol aksi — kursor berubah jadi tangan saat hover
        btn = QPushButton(btn_text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumWidth(160)
        btn.setFixedHeight(42)
        btn.setStyleSheet(StyleHelper.pill_button_outline(42))  # Gaya tombol dengan tepi bulat

        # Ketika tombol diklik, panggil callback yang sama dengan klik kartu
        btn.clicked.connect(callback)

        # Pusatkan tombol secara horizontal dalam baris
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.addWidget(btn)
        card_layout.addLayout(btn_row)

        return card

    def _create_history_section(self) -> SoftCard:
        """
        Membuat kartu riwayat scan berisi daftar hasil pemindaian sebelumnya.

        Daftar ini bisa di-scroll jika jumlah entri banyak, dan menampilkan
        ikon, nama file, hasil deteksi, dan waktu scan untuk setiap entri.

        Returns:
            Kartu riwayat yang siap ditambahkan ke tata letak.
        """
        # Kartu pembungkus dengan warna aksen oranye muda
        card = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_400)
        self._soft_cards.append(card)

        # Tata letak vertikal dalam kartu
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(14)

        # Baris header: judul "Riwayat Pemindaian" di kiri
        header = QHBoxLayout()
        header.setSpacing(8)

        # Judul bagian — didaftarkan sebagai label utama
        ht = self._reg_p(QLabel("Riwayat Pemindaian"))
        ht.setStyleSheet(f"""
            color:{self._tp()};font-size:16px;font-weight:bold;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        header.addWidget(ht)
        header.addStretch()  # Ruang kosong agar judul tetap di kiri
        layout.addLayout(header)

        # Daftar gulir untuk menampilkan riwayat scan
        self.history_list = QListWidget()
        self._history_list_ref = self.history_list  # Simpan referensi tambahan
        self.history_list.setMinimumHeight(120)  # Tinggi minimum agar terlihat

        # Pesan awal ketika belum ada riwayat
        self.history_list.addItem("Belum ada riwayat pemindaian")

        layout.addWidget(self.history_list)

        # Terapkan gaya pada daftar riwayat
        self._apply_history_list_theme()

        return card

    def _create_progress_panel(self) -> SoftCard:
        """
        Membuat panel progres yang ditampilkan saat proses scan sedang berjalan.

        Panel ini berisi:
        - Baris atas: judul scan yang sedang berjalan + tombol "Batalkan"
        - Label status yang menampilkan file yang sedang dipindai
        - Progress bar yang menunjukkan persentase kemajuan

        Panel ini awalnya disembunyikan dan ditampilkan saat scan dimulai.

        Returns:
            Kartu panel progres yang siap digunakan.
        """
        # Kartu panel progres dengan warna aksen oranye
        card = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_500)
        self._soft_cards.append(card)

        # Tata letak vertikal dalam panel
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(12)

        # --- Baris atas: judul scan dan tombol batalkan ---
        header = QHBoxLayout()

        # Label judul yang menampilkan mode scan aktif (misal: "Memindai Folder...")
        self._scan_title_lbl = self._reg_p(QLabel("Memindai File..."))
        self._scan_title_lbl.setStyleSheet(f"""
            color:{self._tp()};font-size:15px;font-weight:bold;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        header.addWidget(self._scan_title_lbl)
        header.addStretch()  # Dorong tombol ke sisi kanan

        # Tombol untuk membatalkan scan yang sedang berjalan
        self._cancel_scan_btn = QPushButton("Batalkan")
        self._cancel_scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_scan_btn.setFixedHeight(34)
        self._cancel_scan_btn.setMinimumWidth(100)
        self._cancel_scan_btn.setStyleSheet(StyleHelper.pill_button_outline(34))
        # Ketika tombol diklik: panggil _on_cancel_scan_clicked
        self._cancel_scan_btn.clicked.connect(self._on_cancel_scan_clicked)
        header.addWidget(self._cancel_scan_btn)

        layout.addLayout(header)

        # Label status yang menampilkan nama file yang sedang dipindai
        self._scan_status_lbl = self._reg_m(QLabel("Menyiapkan..."))
        self._scan_status_lbl.setWordWrap(True)  # Bungkus jika nama file terlalu panjang
        self._scan_status_lbl.setStyleSheet(f"""
            color:{self._tm()};font-size:12px;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        layout.addWidget(self._scan_status_lbl)

        # Progress bar: menampilkan persentase kemajuan scan (0% - 100%)
        self._scan_progress_bar = QProgressBar()
        self._scan_progress_bar.setRange(0, 100)   # Nilai 0 sampai 100
        self._scan_progress_bar.setValue(0)         # Mulai dari 0%
        self._scan_progress_bar.setTextVisible(True)  # Tampilkan persentase dalam teks
        self._scan_progress_bar.setFixedHeight(20)
        # Terapkan gaya warna aksen pada progress bar
        self._apply_progress_bar_theme()
        layout.addWidget(self._scan_progress_bar)

        return card

    # ------------------------------------------------------------------
    # API PUBLIK PANEL PROGRES
    # Fungsi-fungsi ini dipanggil dari luar (misal dari jendela utama)
    # untuk mengendalikan panel progres scan.
    # ------------------------------------------------------------------

    # Fungsi callback yang dipanggil saat tombol batalkan ditekan (diisi dari luar)
    _cancel_scan_callback = None

    def set_cancel_scan_callback(self, callback):
        """
        Mendaftarkan fungsi yang akan dipanggil saat pengguna menekan tombol "Batalkan".

        Fungsi ini memungkinkan komponen luar (seperti jendela utama) untuk mengatur
        logika pembatalan scan tanpa mengubah kode ScanView.

        Args:
            callback: Fungsi tanpa parameter yang akan dijalankan saat tombol ditekan.
        """
        self._cancel_scan_callback = callback

    def _on_cancel_scan_clicked(self):
        """
        Dipanggil saat pengguna menekan tombol "Batalkan" di panel progres.

        Meneruskan aksi ke fungsi callback yang sudah didaftarkan via set_cancel_scan_callback().
        Jika belum ada callback yang didaftarkan, tidak ada yang terjadi.
        """
        if self._cancel_scan_callback:
            self._cancel_scan_callback()

    def show_scan_progress(self, title: str = "Memindai File..."):
        """
        Menampilkan panel progres dan mengatur ulang kondisinya ke keadaan awal.

        Dipanggil saat proses scan dimulai untuk memberi tahu pengguna bahwa
        scan sedang berjalan.

        Args:
            title: Judul yang ditampilkan di panel, menjelaskan jenis scan yang berjalan.
        """
        # Atur judul sesuai jenis scan
        self._scan_title_lbl.setText(title)

        # Reset progress bar ke 0%
        self._scan_progress_bar.setValue(0)

        # Reset label status ke pesan awal
        self._scan_status_lbl.setText("Menyiapkan...")

        # Tampilkan panel (dari kondisi tersembunyi)
        self._progress_panel.show()

    def update_scan_progress(self, value: int, message: str):
        """
        Memperbarui tampilan panel progres selama scan berlangsung.

        Dipanggil berulang kali selama proses scan untuk menampilkan kemajuan
        dan nama file yang sedang diproses.

        Args:
            value: Persentase kemajuan scan, dari 0 hingga 100.
            message: Pesan status, biasanya nama file yang sedang dipindai.
        """
        # Perbarui nilai progress bar (bilah hijau yang bergerak ke kanan)
        self._scan_progress_bar.setValue(value)

        # Perbarui teks status di bawah progress bar
        self._scan_status_lbl.setText(message)

    def hide_scan_progress(self):
        """
        Menyembunyikan panel progres ketika scan selesai atau dibatalkan.

        Panel akan hilang dari tampilan, tetapi kondisi internalnya tidak di-reset
        (reset dilakukan saat show_scan_progress() dipanggil lagi).
        """
        self._progress_panel.hide()

    def _apply_progress_bar_theme(self):
        """
        Menerapkan gaya warna aksen pada widget progress bar.

        Memastikan progress bar terlihat konsisten dengan warna oranye
        dan menyesuaikan latar belakang sesuai tema gelap/terang.
        """
        accent = Colors.ORANGE_500  # Warna utama progress bar

        # Latar belakang berbeda untuk tema gelap dan terang
        bg = "rgba(255,255,255,0.1)" if self.is_dark else "rgba(0,0,0,0.06)"

        # Warna teks persentase
        text_color = self._tp()

        self._scan_progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {accent};           /* Garis tepi oranye */
                border-radius: 10px;                  /* Sudut membulat */
                background: {bg};                     /* Latar belakang semi-transparan */
                color: {text_color};                  /* Warna teks "50%" */
                text-align: center;                   /* Teks di tengah */
                font-size: 11px;
                font-weight: 600;
            }}
            QProgressBar::chunk {{
                background: {accent};                 /* Warna isian oranye */
                border-radius: 8px;                   /* Sudut membulat pada isian */
            }}
        """)

    # ------------------------------------------------------------------
    # AKSI SCAN — Fungsi yang menangani dialog pilih file/folder
    # ------------------------------------------------------------------

    def _browse_file(self):
        """
        Membuka dialog pilih file (File Explorer) dan mengirim sinyal scan.

        Ketika pengguna memilih file dan menekan OK, jalur file dikirim
        melalui sinyal scan_requested ke komponen yang menjalankan scan.
        Jika pengguna menekan Cancel, tidak ada yang terjadi.
        """
        # Tampilkan dialog pemilihan file — bisa memilih semua jenis file
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Pilih File untuk Dipindai", "", "All Files (*.*)"
        )

        # Hanya proses jika pengguna benar-benar memilih file (bukan Cancel)
        if file_path:
            # Kirim jalur file ke komponen yang bertanggung jawab menjalankan scan
            self.scan_requested.emit(file_path)

    def _browse_folder(self):
        """
        Membuka dialog pilih folder dan mengirim sinyal scan folder.

        Ketika pengguna memilih folder dan menekan OK, jalur folder dikirim
        melalui sinyal folder_scan_requested.
        Jika pengguna menekan Cancel, tidak ada yang terjadi.
        """
        # Tampilkan dialog pemilihan folder
        folder_path = QFileDialog.getExistingDirectory(
            self, "Pilih Folder untuk Dipindai", ""
        )

        # Hanya proses jika pengguna benar-benar memilih folder
        if folder_path:
            # Kirim jalur folder ke komponen yang bertanggung jawab menjalankan scan
            self.folder_scan_requested.emit(folder_path)

    def _start_device_scan(self):
        """
        Mengirim sinyal untuk memulai scan seluruh perangkat.

        Tidak memerlukan dialog pilih file/folder karena scan akan mencakup
        seluruh drive dan partisi di komputer.
        """
        # Kirim sinyal — tidak ada parameter karena scan seluruh perangkat tidak perlu jalur
        self.device_scan_requested.emit()

    # ------------------------------------------------------------------
    # RIWAYAT SCAN
    # ------------------------------------------------------------------

    def add_to_history(self, filename: str, result: str, timestamp: str, file_path: str = ""):
        """
        Menambahkan satu entri hasil scan ke bagian atas daftar riwayat.

        Entri baru selalu muncul di atas (terbaru di atas).
        Jika sudah ada 20 entri, entri paling lama di bawah dihapus otomatis.

        Format entri yang ditampilkan:
        [ikon] nama_file
        hasil • waktu
        Path: /jalur/file (jika tersedia)

        Args:
            filename: Nama file yang dipindai (tanpa jalur lengkap).
            result: Hasil deteksi: "Benign" (aman) atau nama malware jika berbahaya.
            timestamp: Waktu scan dalam format string, misalnya "14:35:22".
            file_path: Jalur lengkap file (opsional, untuk tooltip dan tampilan).
        """
        # Hapus pesan placeholder "Belum ada riwayat" jika ini entri pertama
        if self.history_list.count() == 1:
            first = self.history_list.item(0)
            if first and first.text() == "Belum ada riwayat pemindaian":
                self.history_list.clear()

        # Tentukan ikon berdasarkan hasil deteksi:
        # ✅ (centang hijau) jika aman, ⚠️ (segitiga kuning) jika berbahaya
        icon = "" if result == "Benign" else ""

        # Tambahkan baris jalur file jika tersedia
        path_line = f"\nPath: {file_path}" if file_path else ""

        # Format teks lengkap entri riwayat
        item_text = f"{icon} {filename}\n{result} • {timestamp}{path_line}"

        # Buat item daftar dengan teks yang sudah diformat
        item = QListWidgetItem(item_text)

        # Tambahkan jalur sebagai tooltip agar pengguna bisa melihat jalur lengkap saat hover
        if file_path:
            item.setToolTip(file_path)

        # Sisipkan entri di posisi paling atas (indeks 0 = atas)
        self.history_list.insertItem(0, item)

        # Batasi riwayat maksimal 20 entri — hapus yang paling bawah jika lebih
        while self.history_list.count() > 20:
            self.history_list.takeItem(self.history_list.count() - 1)

    # ------------------------------------------------------------------
    # TEMA
    # ------------------------------------------------------------------

    def set_theme(self, is_dark: bool):
        """
        Mengganti tema antara gelap dan terang, lalu menggambar ulang semua widget.

        Dipanggil dari luar (misalnya tombol tema di Sidebar).

        Args:
            is_dark: True untuk tema gelap, False untuk tema terang.
        """
        self.is_dark = is_dark
        self._apply_theme()

    def _apply_theme(self):
        """
        Menerapkan warna tema saat ini ke semua label, kartu, dan widget yang terdaftar.

        Cara kerja:
        1. Ambil warna teks utama dan redup sesuai tema
        2. Perbarui semua label yang terdaftar di _primary_labels dan _muted_labels
           dengan mengganti properti CSS 'color:...' menggunakan regex
        3. Perbarui tema semua kartu soft card
        4. Perbarui gaya daftar riwayat dan progress bar
        """
        # Warna teks sesuai tema aktif
        tp = self._tp()  # Utama (lebih terang/gelap)
        tm = self._tm()  # Redup (abu-abu)

        # Perbarui semua label teks utama: ganti nilai 'color:...' di stylesheet-nya
        for lbl in self._primary_labels:
            lbl.setStyleSheet(re.sub(r"color:[^;]+;", f"color:{tp};", lbl.styleSheet(), count=1))

        # Perbarui semua label teks redup: ganti nilai 'color:...' di stylesheet-nya
        for lbl in self._muted_labels:
            lbl.setStyleSheet(re.sub(r"color:[^;]+;", f"color:{tm};", lbl.styleSheet(), count=1))

        # Perbarui tema semua kartu soft card
        for card in self._soft_cards:
            card.set_theme(self.is_dark)

        # Perbarui gaya daftar riwayat
        self._apply_history_list_theme()

        # Perbarui gaya progress bar jika sudah dibuat
        if hasattr(self, "_scan_progress_bar"):
            self._apply_progress_bar_theme()

    def _apply_history_list_theme(self):
        """
        Menerapkan warna tema pada widget daftar riwayat scan (QListWidget).

        Mengatur warna teks, latar belakang item, garis tepi, dan efek hover
        agar konsisten dengan tema aktif.
        """
        tp = self._tp()                  # Warna teks item daftar
        card_bg = self._card_bg()        # Latar belakang setiap item
        card_border = self._card_border()  # Garis tepi setiap item

        # Warna latar saat mouse hover di atas item
        hover_bg = "rgba(255,255,255,0.07)" if self.is_dark else "rgba(0,0,0,0.06)"

        if hasattr(self, "history_list"):
            self.history_list.setStyleSheet(f"""
                QListWidget{{
                    background:transparent;   /* Latar widget transparan */
                    border:none;
                    color:{tp};              /* Warna teks default item */
                    font-size:13px;
                }}
                QListWidget::item{{
                    background:{card_bg};    /* Latar setiap item */
                    border:1px solid {card_border};  /* Garis tepi tipis */
                    border-radius:10px;      /* Sudut membulat */
                    padding:12px;            /* Padding dalam item */
                    margin-bottom:6px;       /* Jarak antar item */
                }}
                QListWidget::item:hover{{
                    background:{hover_bg};              /* Warna hover berbeda */
                    border:1px solid rgba(255,165,0,0.3);  /* Garis tepi oranye saat hover */
                }}
            """)
