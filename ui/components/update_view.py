"""
Tampilan Pembaruan — Pusat pembaruan model AI MangoDefend.

File ini mengelola halaman Update pada MangoDefend yang berfungsi untuk:
- Menampilkan versi model AI yang sedang digunakan (nomor versi besar)
- Menampilkan informasi teknis model (nama file, ukuran, engine, status)
- Menyediakan tombol untuk memeriksa dan mengunduh versi model terbaru
- Menampilkan riwayat versi-versi sebelumnya beserta perubahan yang dibuat

Model AI yang digunakan MangoDefend disimpan di folder /models/ dalam format ONNX.
"""

import os
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QProgressBar, QScrollArea, QGridLayout,
)
from PySide6.QtCore import Qt, Signal

# Widget kartu kustom dan sistem warna/gaya/ukuran
from ui.widgets import SoftCard
from ui.styles.figma_theme import Colors, Typography, StyleHelper, Sizes


class UpdateView(QWidget):
    """
    Halaman pusat pembaruan model AI MangoDefend.

    Ketika model AI diperbarui, akurasi deteksi malware meningkat karena
    model dilatih dengan data ancaman terbaru. Halaman ini memungkinkan
    pengguna untuk memeriksa dan mengunduh model terbaru dari server.

    Sinyal yang dikirim ke luar:
        check_update_requested: Dikirim saat pengguna menekan tombol "Periksa Pembaruan".
                                 Logika pengecekan dilakukan oleh komponen lain.
        download_update_requested: Dikirim saat pengguna menekan tombol "Unduh Pembaruan".
                                    Logika pengunduhan dilakukan oleh komponen lain.
    """

    # Sinyal permintaan periksa pembaruan — dikirim ke model_updater untuk cek ke server
    check_update_requested = Signal()

    # Sinyal permintaan unduh pembaruan — dikirim ke model_updater untuk mulai unduhan
    download_update_requested = Signal()

    def __init__(self, parent=None):
        """
        Menyiapkan data versi awal dan membangun tampilan halaman pembaruan.

        Args:
            parent: Widget induk (biasanya area konten utama jendela).
        """
        super().__init__(parent)

        # Tema awal: gelap
        self.is_dark = True

        # Versi model yang sedang digunakan saat ini
        self.current_version = "v3.0"

        # Versi terbaru yang tersedia di server (diperbarui setelah cek pembaruan)
        self.latest_version = "v3.0"

        # Status proses pemeriksaan pembaruan (True = sedang memeriksa)
        self.is_checking = False

        # Status proses pengunduhan (True = sedang mengunduh)
        self.is_downloading = False

        # Daftar kartu soft card untuk diperbarui saat tema berubah
        self._soft_cards: list[SoftCard] = []

        # Daftar pasangan (label, peran) untuk diperbarui warnanya saat tema berubah
        # Peran: 'section_header', 'primary', 'muted', 'muted_small', 'muted_tiny', 'primary_large'
        self._theme_labels: list[tuple[QLabel, str]] = []

        # Bangun seluruh tampilan halaman
        self.setup_ui()

    # ------------------------------------------------------------------
    # MEMBANGUN TAMPILAN
    # ------------------------------------------------------------------

    def setup_ui(self):
        """
        Membangun seluruh tata letak halaman pembaruan di dalam area gulir.

        Urutan konten dari atas ke bawah:
        1. Kartu versi model (nomor versi besar + badge status)
        2. Label "Informasi Model" + grid empat kartu info teknis
        3. Kartu pusat pembaruan (tombol cek + unduh + progress bar)
        4. Label "Riwayat Pembaruan" + daftar kartu riwayat versi
        5. Ruang kosong fleksibel di bawah
        """
        # Area gulir agar halaman bisa di-scroll jika konten terlalu panjang
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)  # Konten mengikuti lebar area gulir
        scroll.setFrameShape(QFrame.Shape.NoFrame)  # Hapus batas kotak
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        # Sembunyikan scrollbar agar tampilan lebih bersih
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Widget konten yang ditempatkan di dalam area gulir
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")

        # Tata letak vertikal untuk semua konten halaman
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(32, 24, 32, 32)  # Margin tepi
        layout.setSpacing(24)  # Jarak antar bagian

        # --- 1. Kartu versi model ---
        # Menampilkan nomor versi besar dan badge status (terbaru/ada pembaruan)
        layout.addWidget(self._create_version_card())

        # --- 2. Label judul bagian "Informasi Model" ---
        info_header = QLabel(" Informasi Model")
        # Daftarkan label ini dengan peran 'section_header' agar ikut perubahan tema
        self._theme_labels.append((info_header, "section_header"))
        layout.addWidget(info_header)

        # Grid 2 kolom x 2 baris untuk empat kartu informasi teknis
        info_grid = QGridLayout()
        info_grid.setSpacing(16)

        # Baca nama file dan ukuran model dari disk
        model_name, model_size = self._get_model_info()

        # Kartu info: nama file model (aksen oranye)
        self.info_model = self._create_info_card("Model", model_name, Colors.ORANGE_500)
        # Kartu info: ukuran file model (aksen hijau zamrud)
        self.info_size  = self._create_info_card("Ukuran", model_size, Colors.EMERALD_500)
        # Kartu info: engine yang digunakan untuk menjalankan model
        self.info_engine = self._create_info_card("Engine", "ONNX Runtime", Colors.ORANGE_300)
        # Kartu info: status pembaruan saat ini
        self.info_status = self._create_info_card("Status", "Terbaru", Colors.GREEN_500)

        # Tempatkan keempat kartu dalam grid 2x2
        info_grid.addWidget(self.info_model,  0, 0)  # Baris 0, kolom 0
        info_grid.addWidget(self.info_size,   0, 1)  # Baris 0, kolom 1
        info_grid.addWidget(self.info_engine, 1, 0)  # Baris 1, kolom 0
        info_grid.addWidget(self.info_status, 1, 1)  # Baris 1, kolom 1

        layout.addLayout(info_grid)

        # --- 3. Kartu pusat pembaruan ---
        # Berisi tombol cek, tombol unduh, dan progress bar pengunduhan
        layout.addWidget(self._create_update_card())

        # --- 4. Label judul bagian "Riwayat Pembaruan" ---
        history_header = QLabel("Riwayat Pembaruan")
        self._theme_labels.append((history_header, "section_header"))
        layout.addWidget(history_header)

        # Data riwayat versi: (nomor versi, tanggal rilis, judul perubahan, deskripsi)
        history_items = [
            ("v3.0", "Maret 2026",    "ONNX Runtime",        "Migrasi ke ONNX untuk performa lebih cepat dan ukuran lebih kecil"),
            ("v2.5", "Februari 2026", "Peningkatan Akurasi", "Perbaikan model dengan dataset lebih besar, akurasi naik 3%"),
            ("v2.0", "Januari 2026",  "Full Device Scan",    "Ditambahkan fitur scan seluruh perangkat dengan mode agresif"),
        ]

        # Buat satu kartu riwayat untuk setiap entri
        for version, date, title, desc in history_items:
            layout.addWidget(self._create_history_item(version, date, title, desc))

        # Ruang kosong fleksibel di bawah
        layout.addStretch()

        # Masukkan konten ke area gulir
        scroll.setWidget(scroll_content)

        # Tata letak akar: area gulir memenuhi seluruh halaman
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        # Terapkan warna tema ke semua label yang sudah didaftarkan
        self._apply_label_theme()

    def _create_version_card(self) -> SoftCard:
        """
        Membuat kartu header besar yang menampilkan nomor versi model saat ini.

        Kartu ini adalah elemen paling mencolok di halaman Update, dengan
        nomor versi ditampilkan dalam ukuran font 48px berwarna oranye.
        Di bawahnya terdapat badge yang menunjukkan apakah model sudah terbaru.

        Returns:
            Kartu versi yang siap ditambahkan ke tata letak.
        """
        # Kartu dengan padding besar dan semua konten rata tengah
        card = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_500)
        self._soft_cards.append(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(40, 36, 40, 36)  # Padding besar agar terlihat lapang
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Semua elemen rata tengah

        # Label kecil "Versi Model AI" di atas angka versi
        label = QLabel("Versi Model AI")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Daftarkan dengan peran 'muted' — akan tampil dengan warna abu-abu
        self._theme_labels.append((label, "muted"))
        layout.addWidget(label)

        # Nomor versi model — ukuran besar (48px) berwarna oranye mencolok
        self.version_display = QLabel(self.current_version)
        self.version_display.setStyleSheet(f"""
            color: {Colors.ORANGE_500};
            font-size: 48px;
            font-weight: bold;
            background: transparent;
            font-family: {Typography.FONT_FAMILY};
        """)
        self.version_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.version_display)

        # Badge status: "Model terbaru" (hijau) atau "Pembaruan tersedia" (oranye)
        self.version_status = QLabel("Model terbaru")
        self.version_status.setStyleSheet(StyleHelper.status_badge(Colors.GREEN_500))  # Badge hijau
        self.version_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Pusatkan badge secara horizontal
        badge_row = QHBoxLayout()
        badge_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_row.addWidget(self.version_status)
        layout.addLayout(badge_row)

        return card

    def _create_info_card(self, label: str, value: str, color: str) -> SoftCard:
        """
        Membuat kartu informasi kecil dengan label dan nilai berwarna aksen.

        Digunakan untuk menampilkan detail teknis model seperti nama file,
        ukuran, engine, dan status.

        Args:
            label: Nama properti yang ditampilkan (misalnya "Model", "Ukuran").
            value: Nilai properti (misalnya "Modelv3.onnx", "8.2 MB").
            color: Warna aksen untuk nilai dan kartu.

        Returns:
            Kartu informasi kecil.
        """
        # Buat kartu dengan warna aksen yang sesuai properti
        card = SoftCard(is_dark=self.is_dark, accent=color)
        self._soft_cards.append(card)
        card.setMinimumHeight(90)  # Tinggi minimum agar semua kartu seragam

        # Tata letak vertikal dalam kartu
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(6)

        # Baris atas: label properti di kiri
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Label nama properti — warna redup (abu-abu)
        label_lbl = QLabel(label)
        # Daftarkan dengan peran 'muted_tiny' — ukuran kecil, warna redup
        self._theme_labels.append((label_lbl, "muted_tiny"))
        top_row.addWidget(label_lbl)
        top_row.addStretch()  # Dorong konten ke kanan jika perlu

        card_layout.addLayout(top_row)

        # Nilai properti — ukuran lebih besar dan berwarna aksen
        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(f"""
            color: {color};
            font-size: 16px;
            font-weight: 700;
            background: transparent;
            font-family: {Typography.FONT_FAMILY};
        """)
        card_layout.addWidget(value_lbl)

        return card

    def _create_update_card(self) -> SoftCard:
        """
        Membuat kartu pusat pembaruan yang berisi kontrol untuk cek dan unduh model.

        Kartu ini berisi:
        - Judul "Pusat Pembaruan"
        - Pesan status yang berubah sesuai proses (idle/memeriksa/mengunduh/selesai)
        - Progress bar pengunduhan (tersembunyi sampai unduhan dimulai)
        - Tombol "Periksa Pembaruan" (selalu terlihat)
        - Tombol "Unduh Pembaruan" (hanya muncul jika ada versi baru)

        Returns:
            Kartu pusat pembaruan.
        """
        # Kartu dengan warna aksen oranye muda
        card = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_400)
        self._soft_cards.append(card)

        # Tata letak vertikal dalam kartu
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Baris header: judul "Pusat Pembaruan" di kiri
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        # Judul kartu — daftarkan dengan peran 'primary_large'
        header = QLabel("Pusat Pembaruan")
        self._theme_labels.append((header, "primary_large"))
        header_row.addWidget(header)
        header_row.addStretch()
        layout.addLayout(header_row)

        # Pesan status yang berubah sesuai kondisi
        # Awal: "Periksa apakah tersedia pembaruan model AI terbaru"
        # Saat memeriksa: "Memeriksa pembaruan yang tersedia..."
        # Saat ada pembaruan: "Versi baru tersedia: v3.1"
        # Setelah selesai: "Pembaruan berhasil diinstal!"
        self.status_message = QLabel("Periksa apakah tersedia pembaruan model AI terbaru")
        self.status_message.setWordWrap(True)  # Bungkus jika teks terlalu panjang
        # Daftarkan dengan peran 'muted'
        self._theme_labels.append((self.status_message, "muted"))
        layout.addWidget(self.status_message)

        # Progress bar pengunduhan — disembunyikan sampai proses unduh dimulai
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)    # Nilai 0 hingga 100 persen
        self.progress_bar.setValue(0)          # Mulai dari 0%
        self.progress_bar.setTextVisible(True) # Tampilkan persentase dalam teks
        self.progress_bar.setFixedHeight(28)
        self.progress_bar.hide()  # Tersembunyi dulu — ditampilkan saat unduhan dimulai
        layout.addWidget(self.progress_bar)

        # Baris tombol: disusun secara horizontal di tengah
        button_row = QHBoxLayout()
        button_row.setSpacing(12)
        button_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Tombol "Periksa Pembaruan" — selalu terlihat, gaya primer (solid/terisi)
        self.check_btn = QPushButton("Periksa Pembaruan")
        self.check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_btn.setFixedHeight(48)
        self.check_btn.setFixedWidth(220)
        self.check_btn.setStyleSheet(StyleHelper.pill_button_primary(Sizes.BTN_HEIGHT_MD))
        # Ketika diklik: panggil _check_for_updates untuk memulai proses pengecekan
        self.check_btn.clicked.connect(self._check_for_updates)
        button_row.addWidget(self.check_btn)

        # Tombol "Unduh Pembaruan" — tersembunyi dulu, hanya muncul jika ada versi baru
        self.download_btn = QPushButton("Unduh Pembaruan")
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.setFixedHeight(48)
        self.download_btn.setFixedWidth(220)
        self.download_btn.setStyleSheet(StyleHelper.pill_button_outline(Sizes.BTN_HEIGHT_MD))
        # Ketika diklik: panggil _download_update untuk memulai pengunduhan
        self.download_btn.clicked.connect(self._download_update)
        self.download_btn.hide()  # Tersembunyi dulu — muncul setelah cek menemukan versi baru
        button_row.addWidget(self.download_btn)

        layout.addLayout(button_row)

        return card

    def _create_history_item(self, version: str, date: str, title: str, desc: str) -> SoftCard:
        """
        Membuat satu kartu entri riwayat versi.

        Setiap kartu menampilkan:
        - Badge nomor versi di sisi kiri
        - Judul perubahan dan tanggal rilis di kanan atas
        - Deskripsi perubahan di kanan bawah

        Args:
            version: Nomor versi, misalnya "v3.0".
            date: Tanggal rilis, misalnya "Maret 2026".
            title: Judul perubahan utama, misalnya "ONNX Runtime".
            desc: Deskripsi lengkap perubahan yang dilakukan.

        Returns:
            Kartu riwayat satu versi.
        """
        # Kartu dengan layout horizontal: badge versi | konten teks
        card = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_300)
        self._soft_cards.append(card)

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(24, 18, 24, 18)
        card_layout.setSpacing(16)

        # --- Badge nomor versi di sisi kiri ---
        # Kotak kecil dengan latar oranye transparan dan garis tepi oranye
        ver_frame = QFrame()
        ver_frame.setFixedSize(56, 56)  # Ukuran tetap 56x56 piksel
        ver_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 165, 0, 0.12);   /* Latar oranye sangat transparan */
                border: 1px solid rgba(255, 165, 0, 0.25);  /* Garis tepi oranye tipis */
                border-radius: 14px;                    /* Sudut membulat */
            }
        """)

        # Tata letak dalam badge versi
        ver_inner = QVBoxLayout(ver_frame)
        ver_inner.setContentsMargins(0, 0, 0, 0)

        # Teks nomor versi dalam badge (misalnya "v3.0")
        ver_lbl = QLabel(version)
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_lbl.setStyleSheet(f"""
            color: {Colors.ORANGE_400};
            font-size: 13px;
            font-weight: 700;
            background: transparent;
            font-family: {Typography.FONT_FAMILY};
        """)
        ver_inner.addWidget(ver_lbl)
        card_layout.addWidget(ver_frame)

        # --- Area teks konten riwayat di sisi kanan ---
        text_widget = QWidget()
        text_widget.setStyleSheet("background: transparent;")
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)

        # Baris judul: nama fitur dan tanggal rilis
        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        # Judul perubahan (misalnya "ONNX Runtime")
        title_lbl = QLabel(title)
        # Daftarkan dengan peran 'primary' — warna teks utama
        self._theme_labels.append((title_lbl, "primary"))
        title_row.addWidget(title_lbl)

        # Tanggal rilis (misalnya "Maret 2026") — warna redup, lebih kecil
        date_lbl = QLabel(date)
        # Daftarkan dengan peran 'muted_tiny' — warna abu-abu, ukuran sangat kecil
        self._theme_labels.append((date_lbl, "muted_tiny"))
        title_row.addWidget(date_lbl)
        title_row.addStretch()  # Sisa ruang kosong di kanan

        text_layout.addLayout(title_row)

        # Deskripsi lengkap perubahan — bisa dibungkus ke baris baru
        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        # Daftarkan dengan peran 'muted_small' — warna redup, ukuran kecil
        self._theme_labels.append((desc_lbl, "muted_small"))
        text_layout.addWidget(desc_lbl)

        # Tambahkan area teks ke tata letak kartu dengan bobot 1 (melebar mengisi sisa ruang)
        card_layout.addWidget(text_widget, 1)

        return card

    # ------------------------------------------------------------------
    # PEMBANTU
    # ------------------------------------------------------------------

    def _get_model_info(self) -> tuple:
        """
        Membaca nama file dan ukuran model ONNX dari folder models.

        Mencari file Modelv3.onnx di folder /models/ relatif dari
        lokasi file ini (3 level ke atas ke root proyek).

        Returns:
            Tuple (nama_file, ukuran_string):
            - nama_file: nama file model, misalnya "Modelv3.onnx"
            - ukuran_string: ukuran dalam MB, misalnya "8.2 MB" atau "N/A" jika tidak ditemukan
        """
        # Hitung jalur ke file model: naik 3 level dari ui/components/ ke root, lalu ke models/
        model_path = Path(__file__).resolve().parent.parent.parent / "models" / "Modelv3.onnx"

        if model_path.exists():
            # Konversi ukuran file dari byte ke megabyte
            size_mb = model_path.stat().st_size / (1024 * 1024)
            return "Modelv3.onnx", f"{size_mb:.1f} MB"

        # Jika file tidak ditemukan, kembalikan nama dengan ukuran "N/A"
        return "Modelv3.onnx", "N/A"

    # ------------------------------------------------------------------
    # AKSI PEMBARUAN — Dipanggil oleh tombol di kartu pusat pembaruan
    # ------------------------------------------------------------------

    def _check_for_updates(self):
        """
        Dipanggil saat pengguna menekan tombol "Periksa Pembaruan".

        Mencegah pemeriksaan ganda (jika sudah dalam proses, tidak mulai lagi),
        mengubah tampilan tombol, dan mengirim sinyal check_update_requested
        ke komponen yang menangani komunikasi dengan server pembaruan.
        """
        # Hanya mulai jika belum dalam proses pemeriksaan
        if not self.is_checking:
            self.is_checking = True  # Tandai bahwa pemeriksaan sedang berjalan

            # Nonaktifkan tombol agar tidak bisa diklik ganda
            self.check_btn.setEnabled(False)

            # Ubah teks tombol menjadi indikator loading
            self.check_btn.setText(" Memeriksa...")

            # Perbarui pesan status
            self.status_message.setText("Memeriksa pembaruan yang tersedia...")

            # Kirim sinyal ke komponen yang bertugas memeriksa server
            self.check_update_requested.emit()

    def _download_update(self):
        """
        Dipanggil saat pengguna menekan tombol "Unduh Pembaruan".

        Mencegah pengunduhan ganda, menampilkan progress bar, mengubah
        tampilan tombol, dan mengirim sinyal download_update_requested
        ke komponen yang menangani pengunduhan file.
        """
        # Hanya mulai jika belum dalam proses pengunduhan
        if not self.is_downloading:
            self.is_downloading = True  # Tandai bahwa pengunduhan sedang berjalan

            # Nonaktifkan tombol agar tidak bisa diklik ganda
            self.download_btn.setEnabled(False)

            # Tampilkan progress bar yang sebelumnya tersembunyi
            self.progress_bar.show()

            # Perbarui pesan status
            self.status_message.setText("Mengunduh pembaruan...")

            # Kirim sinyal ke komponen yang bertugas mengunduh file model
            self.download_update_requested.emit()

    # ------------------------------------------------------------------
    # API PUBLIK — Dipanggil dari komponen luar untuk memperbarui tampilan
    # ------------------------------------------------------------------

    def set_check_result(self, has_update: bool, latest_version: str = None):
        """
        Menampilkan hasil pemeriksaan pembaruan di halaman ini.

        Dipanggil oleh komponen model_updater setelah selesai berkomunikasi
        dengan server dan mengetahui apakah ada versi baru atau tidak.

        Args:
            has_update: True jika ada versi baru yang tersedia, False jika tidak.
            latest_version: Nomor versi terbaru (hanya diisi jika has_update=True).
        """
        # Tandai bahwa proses pemeriksaan sudah selesai
        self.is_checking = False

        # Aktifkan kembali tombol periksa
        self.check_btn.setEnabled(True)
        self.check_btn.setText("Periksa Pembaruan")

        if has_update:
            # Ada versi baru — simpan nomor versi terbaru
            self.latest_version = latest_version

            # Perbarui pesan status dengan nomor versi baru
            self.status_message.setText(f"Versi baru tersedia: {latest_version}")

            # Ubah badge versi menjadi peringatan (oranye)
            self.version_status.setText(f"⚠  Pembaruan tersedia → {latest_version}")
            self.version_status.setStyleSheet(StyleHelper.status_badge(Colors.ORANGE_500))

            # Tampilkan tombol unduh agar pengguna bisa mulai mengunduh
            self.download_btn.show()

            # Perbarui kartu info status (cari QLabel di dalamnya)
            self.info_status.findChild(QLabel, "").setText("Tersedia Update")
        else:
            # Sudah menggunakan versi terbaru
            self.status_message.setText("Anda sudah menggunakan versi terbaru")

            # Sembunyikan tombol unduh karena tidak diperlukan
            self.download_btn.hide()

    def set_download_progress(self, progress: int):
        """
        Memperbarui nilai progress bar pengunduhan model.

        Dipanggil berulang kali selama proses pengunduhan berlangsung
        untuk menampilkan kemajuan secara visual.
        Ketika progress mencapai 100, tampilan direset ke kondisi selesai.

        Args:
            progress: Persentase kemajuan unduhan, dari 0 hingga 100.
        """
        # Perbarui nilai progress bar
        self.progress_bar.setValue(progress)

        # Jika sudah 100% (selesai)
        if progress >= 100:
            # Tandai bahwa pengunduhan sudah selesai
            self.is_downloading = False

            # Sembunyikan progress bar kembali
            self.progress_bar.hide()

            # Tampilkan pesan sukses
            self.status_message.setText("Pembaruan berhasil diinstal!")

            # Perbarui versi yang ditampilkan ke versi terbaru yang baru diunduh
            self.current_version = self.latest_version
            self.version_display.setText(self.current_version)

            # Reset badge status ke "Model terbaru" (hijau)
            self.version_status.setText("Model terbaru")
            self.version_status.setStyleSheet(StyleHelper.status_badge(Colors.GREEN_500))

            # Sembunyikan tombol unduh — tidak lagi diperlukan
            self.download_btn.hide()

            # Aktifkan kembali tombol unduh untuk penggunaan berikutnya
            self.download_btn.setEnabled(True)

    def set_theme(self, is_dark: bool):
        """
        Mengganti tema dan memperbarui tampilan semua elemen halaman.

        Dipanggil dari luar (misalnya tombol tema di Sidebar) untuk
        menyinkronkan tampilan halaman pembaruan dengan pilihan tema pengguna.

        Args:
            is_dark: True untuk tema gelap, False untuk tema terang.
        """
        # Simpan pilihan tema baru
        self.is_dark = is_dark

        # Perbarui tema semua kartu soft card
        for card in self._soft_cards:
            card.set_theme(self.is_dark)

        # Perbarui warna semua label yang terdaftar
        self._apply_label_theme()

    def _apply_label_theme(self):
        """
        Menerapkan warna tema yang sesuai pada setiap label berdasarkan perannya.

        Setiap label yang didaftarkan di _theme_labels memiliki peran (role)
        yang menentukan ukuran font dan warna teks yang tepat.

        Peta peran → gaya:
        - 'section_header': judul bagian besar, warna teks utama
        - 'primary_large': teks penting besar, warna teks utama
        - 'primary': teks penting normal, warna teks utama
        - 'muted': teks keterangan, warna abu-abu
        - 'muted_small': teks keterangan kecil, warna abu-abu
        - 'muted_tiny': teks sangat kecil, warna abu-abu
        """
        # Pilih warna teks berdasarkan tema aktif
        tp = Colors.DARK_TEXT_PRIMARY if self.is_dark else Colors.LIGHT_TEXT_PRIMARY   # Teks utama
        tm = Colors.DARK_TEXT_MUTED   if self.is_dark else Colors.LIGHT_TEXT_MUTED    # Teks redup

        # Singkatan untuk nama font agar kode lebih pendek
        f = Typography.FONT_FAMILY

        # Kamus peta peran → stylesheet CSS
        styles = {
            # Judul bagian besar (misalnya "Informasi Model")
            "section_header": f"color:{tp};font-size:18px;font-weight:bold;font-family:{f};background:transparent;",
            # Teks utama berukuran besar (misalnya judul "Pusat Pembaruan")
            "primary_large":  f"color:{tp};font-size:18px;font-weight:bold;font-family:{f};background:transparent;",
            # Teks utama normal (misalnya judul perubahan di riwayat)
            "primary":        f"color:{tp};font-size:14px;font-weight:600;font-family:{f};background:transparent;",
            # Teks keterangan normal — warna abu-abu
            "muted":          f"color:{tm};font-size:13px;font-family:{f};background:transparent;",
            # Teks keterangan kecil — warna abu-abu, ukuran lebih kecil
            "muted_small":    f"color:{tm};font-size:12px;font-family:{f};background:transparent;",
            # Teks sangat kecil — warna abu-abu, untuk label dan tanggal
            "muted_tiny":     f"color:{tm};font-size:11px;font-family:{f};background:transparent;",
        }

        # Terapkan stylesheet yang sesuai ke setiap label berdasarkan perannya
        for lbl, role in self._theme_labels:
            if role in styles:
                lbl.setStyleSheet(styles[role])
