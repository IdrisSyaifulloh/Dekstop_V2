"""
Scan Choice Dialog
Dialog pemilihan jenis pemindaian — pengguna memilih antara memindai satu file
atau melakukan pemindaian penuh seluruh perangkat.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class ScanChoiceDialog(QDialog):
    """
    Dialog modal yang meminta pengguna memilih jenis pemindaian:
    - "Pindai File"        : memilih satu file tertentu untuk dipindai
    - "Pindai Full Device" : memindai seluruh isi perangkat

    Sinyal yang dikirim setelah pengguna memilih:
    - file_scan_selected   : dikirim jika tombol "Pindai File" ditekan
    - device_scan_selected : dikirim jika tombol "Pindai Full Device" ditekan

    Pilihan pengguna bisa dibaca kembali lewat metode get_choice().
    """

    # Sinyal tanpa parameter — hanya memberi tahu bahwa pengguna memilih scan file
    file_scan_selected = Signal()

    # Sinyal tanpa parameter — hanya memberi tahu bahwa pengguna memilih scan perangkat
    device_scan_selected = Signal()

    def __init__(self, parent=None, is_dark_mode: bool = False):
        """
        Inisialisasi dialog dengan tema tampilan yang sesuai.

        Parameter:
            parent      — jendela induk (biasanya jendela utama aplikasi)
            is_dark_mode — True untuk tema gelap, False untuk tema terang
        """
        # Panggil konstruktor kelas induk QDialog
        super().__init__(parent)

        # Simpan mode tampilan agar bisa dirujuk nanti (misalnya saat apply_style dipanggil ulang)
        self.is_dark_mode = is_dark_mode

        # Inisialisasi pilihan ke None — akan diisi saat pengguna menekan salah satu tombol
        self.choice = None

        # Bangun tampilan dialog
        self.init_ui()

        # Terapkan style sesuai mode tampilan yang diberikan
        self.apply_style(is_dark_mode)

    # ──────────────────────────────────────────────────────────────────────────
    # BANGUN TAMPILAN (BUILD UI)
    # ──────────────────────────────────────────────────────────────────────────

    def init_ui(self):
        """
        Susun semua elemen tampilan dialog dari atas ke bawah:
        1. Ikon lup di bagian atas
        2. Judul dialog
        3. Keterangan singkat
        4. Tombol pilihan scan file dan scan perangkat
        5. Tombol Batal
        """
        # Judul dialog yang muncul di bilah atas jendela
        self.setWindowTitle("Pilih Jenis Pemindaian")

        # Jadikan dialog bersifat modal — pengguna tidak bisa klik jendela lain
        self.setModal(True)

        # Ukuran dialog dikunci agar tampilan konsisten di berbagai resolusi layar
        self.setFixedSize(500, 350)

        # Layout utama vertikal — semua elemen disusun dari atas ke bawah
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)  # padding dalam dialog
        layout.setSpacing(25)                       # jarak antar elemen

        # ── IKON LUP ─────────────────────────────────────────────────────────────
        # Ikon emoji kaca pembesar sebagai representasi visual "pemindaian"
        icon_label = QLabel("🔍")
        icon_label.setObjectName("dialogIcon")                        # nama untuk styling CSS
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)         # pusatkan ikon
        icon_label.setFixedHeight(80)                                 # tinggi tetap untuk konsistensi
        layout.addWidget(icon_label)

        # ── JUDUL DIALOG ─────────────────────────────────────────────────────────
        # Teks besar yang menjelaskan apa yang diminta dari pengguna
        title = QLabel("Pilih Jenis Pemindaian")
        title.setObjectName("dialogTitle")                            # nama untuk styling CSS
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)              # teks di tengah
        layout.addWidget(title)

        # ── DESKRIPSI ─────────────────────────────────────────────────────────────
        # Penjelasan singkat tentang dua pilihan yang tersedia
        desc = QLabel(
            "Pilih apakah Anda ingin memindai file tertentu\n"
            "atau melakukan pemindaian penuh pada device."
        )
        desc.setObjectName("dialogDesc")                              # nama untuk styling CSS
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)               # teks di tengah
        desc.setWordWrap(True)                                        # izinkan teks bungkus ke baris bawah
        layout.addWidget(desc)

        # Jarak kosong tambahan sebelum tombol agar tidak terlalu rapat
        layout.addSpacing(10)

        # ── TOMBOL-TOMBOL PILIHAN ─────────────────────────────────────────────────
        # Dibungkus dalam QWidget agar bisa dikelola sebagai satu blok
        buttons_widget = QWidget()
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(15)           # jarak antara tombol file dan tombol device
        buttons_widget.setLayout(buttons_layout)

        # Tombol "Pindai File" — memindai satu file yang dipilih pengguna
        self.file_btn = QPushButton("📄 Pindai File")
        self.file_btn.setObjectName("choiceButton")                   # nama untuk styling CSS
        self.file_btn.setFixedHeight(60)                              # tombol cukup tinggi agar mudah diklik
        self.file_btn.setCursor(Qt.CursorShape.PointingHandCursor)    # kursor berubah jadi tangan saat hover
        self.file_btn.clicked.connect(self.on_file_scan_clicked)      # hubungkan ke handler pilihan file
        buttons_layout.addWidget(self.file_btn)

        # Tombol "Pindai Full Device" — memindai seluruh isi perangkat
        self.device_btn = QPushButton("💻 Pindai Full Device")
        self.device_btn.setObjectName("choiceButton")                 # nama untuk styling CSS (sama agar style sama)
        self.device_btn.setFixedHeight(60)                            # tinggi sama dengan tombol file
        self.device_btn.setCursor(Qt.CursorShape.PointingHandCursor)  # kursor tangan saat hover
        self.device_btn.clicked.connect(self.on_device_scan_clicked)  # hubungkan ke handler pilihan device
        buttons_layout.addWidget(self.device_btn)

        # Tambahkan blok tombol ke layout utama
        layout.addWidget(buttons_widget)

        # Jarak kecil sebelum tombol batal
        layout.addSpacing(5)

        # ── TOMBOL BATAL ─────────────────────────────────────────────────────────
        # Tombol untuk menutup dialog tanpa memilih apa-apa
        # reject() adalah metode Qt standar yang menutup dialog dengan kode "dibatalkan"
        cancel_btn = QPushButton("Batal")
        cancel_btn.setObjectName("cancelButton")                      # nama untuk styling CSS terpisah
        cancel_btn.setFixedHeight(40)                                 # lebih kecil dari tombol pilihan
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)       # kursor tangan saat hover
        cancel_btn.clicked.connect(self.reject)                       # reject() = tutup dialog tanpa pilihan
        layout.addWidget(cancel_btn)

        # Terapkan layout ke dialog
        self.setLayout(layout)

    # ──────────────────────────────────────────────────────────────────────────
    # HANDLER TOMBOL (BUTTON HANDLERS)
    # ──────────────────────────────────────────────────────────────────────────

    def on_file_scan_clicked(self):
        """
        Dipanggil saat pengguna menekan tombol "Pindai File".

        Langkah yang dilakukan:
        1. Simpan pilihan sebagai string "file"
        2. Kirim sinyal file_scan_selected ke semua penerima yang terdaftar
        3. Tutup dialog dengan accept() — kode hasil QDialog.Accepted
        """
        # Catat bahwa pengguna memilih mode scan file
        self.choice = "file"

        # Kirim sinyal ke parent atau siapa pun yang mendengarkan sinyal ini
        self.file_scan_selected.emit()

        # Tutup dialog — pemanggil bisa cek hasilnya dengan dialog.result() == QDialog.Accepted
        self.accept()

    def on_device_scan_clicked(self):
        """
        Dipanggil saat pengguna menekan tombol "Pindai Full Device".

        Langkah yang dilakukan:
        1. Simpan pilihan sebagai string "device"
        2. Kirim sinyal device_scan_selected ke semua penerima yang terdaftar
        3. Tutup dialog dengan accept()
        """
        # Catat bahwa pengguna memilih mode scan perangkat penuh
        self.choice = "device"

        # Kirim sinyal ke parent atau siapa pun yang mendengarkan sinyal ini
        self.device_scan_selected.emit()

        # Tutup dialog
        self.accept()

    # ──────────────────────────────────────────────────────────────────────────
    # API PUBLIK (PUBLIC API)
    # ──────────────────────────────────────────────────────────────────────────

    def get_choice(self) -> str | None:
        """
        Kembalikan pilihan yang dibuat pengguna setelah dialog ditutup.

        Nilai yang mungkin dikembalikan:
            "file"   — pengguna memilih scan file
            "device" — pengguna memilih scan perangkat penuh
            None     — pengguna menekan Batal atau menutup dialog tanpa memilih
        """
        return self.choice

    def apply_style(self, is_dark_mode: bool):
        """
        Terapkan tema warna ke seluruh dialog berdasarkan mode tampilan.

        Perbedaan mode gelap dan terang:
        - Mode GELAP (is_dark_mode=True):
            * Dialog: latar gelap gradient (#1A1A1A → #252525)
            * Border dialog: oranye cerah (#FFA500)
            * Judul: putih
            * Deskripsi: abu muda (#CCCCCC)
            * Tombol pilihan: latar gelap dengan border oranye, teks oranye
              → saat hover: latar berubah oranye, teks putih
            * Tombol batal: transparan dengan border abu, teks abu muda

        - Mode TERANG (is_dark_mode=False):
            * Dialog: latar putih ke krem (#FFFFFF → #FFF5E6)
            * Border dialog: oranye lebih gelap (#FF8C00) agar kontras dengan latar terang
            * Judul: hampir hitam (#2C2C2C)
            * Deskripsi: abu gelap (#444444)
            * Tombol pilihan: latar putih/krem dengan border oranye, teks gelap
              → saat hover: sama dengan mode gelap (latar oranye, teks putih)
            * Tombol batal: transparan dengan border abu muda (#CCCCCC), teks abu

        Parameter:
            is_dark_mode — True untuk tema gelap, False untuk tema terang
        """
        # Perbarui atribut agar bisa dirujuk dari tempat lain
        self.is_dark_mode = is_dark_mode

        if is_dark_mode:
            # ── STYLE MODE GELAP ─────────────────────────────────────────────────
            self.setStyleSheet("""
                QDialog {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #1A1A1A, stop:1 #252525);
                    border: 2px solid #FFA500;
                    border-radius: 15px;
                }
                QLabel#dialogIcon {
                    font-size: 64px;
                    color: #FFA500;
                }
                QLabel#dialogTitle {
                    color: #FFFFFF;
                    font-size: 24px;
                    font-weight: bold;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QLabel#dialogDesc {
                    color: #CCCCCC;
                    font-size: 14px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    line-height: 1.6;
                }
                QPushButton#choiceButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(40, 40, 40, 0.95), stop:1 rgba(30, 30, 30, 0.95));
                    border: 3px solid #FFA500;
                    border-radius: 30px;
                    color: #FFA500;
                    font-size: 16px;
                    font-weight: 600;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QPushButton#choiceButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FFA500, stop:1 #FF8C00);
                    color: white;
                    border: 3px solid #FFB732;
                }
                QPushButton#choiceButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FF8C00, stop:1 #FF7F00);
                }
                QPushButton#cancelButton {
                    background: transparent;
                    border: 2px solid #666666;
                    border-radius: 20px;
                    color: #999999;
                    font-size: 14px;
                    font-weight: 600;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QPushButton#cancelButton:hover {
                    background: rgba(102, 102, 102, 0.2);
                    border: 2px solid #888888;
                    color: #CCCCCC;
                }
            """)
        else:
            # ── STYLE MODE TERANG ────────────────────────────────────────────────
            self.setStyleSheet("""
                QDialog {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #FFFFFF, stop:1 #FFF5E6);
                    border: 2px solid #FF8C00;
                    border-radius: 15px;
                }
                QLabel#dialogIcon {
                    font-size: 64px;
                    color: #FF8C00;
                }
                QLabel#dialogTitle {
                    color: #2C2C2C;
                    font-size: 24px;
                    font-weight: bold;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QLabel#dialogDesc {
                    color: #444444;
                    font-size: 14px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    line-height: 1.6;
                }
                QPushButton#choiceButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(255, 255, 255, 0.95), stop:1 rgba(255, 250, 240, 0.95));
                    border: 3px solid #FF8C00;
                    border-radius: 30px;
                    color: #2C2C2C;
                    font-size: 16px;
                    font-weight: 600;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QPushButton#choiceButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FFA500, stop:1 #FF8C00);
                    color: white;
                    border: 3px solid #FFB732;
                }
                QPushButton#choiceButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FF8C00, stop:1 #FF7F00);
                }
                QPushButton#cancelButton {
                    background: transparent;
                    border: 2px solid #CCCCCC;
                    border-radius: 20px;
                    color: #666666;
                    font-size: 14px;
                    font-weight: 600;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QPushButton#cancelButton:hover {
                    background: rgba(0, 0, 0, 0.05);
                    border: 2px solid #999999;
                    color: #333333;
                }
            """)
