"""
Scanning Dialog
Overlay dialog untuk menampilkan progress scanning
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from ui.components.spinner import AnimatedSpinner
import time


class ScanningDialog(QWidget):
    """
    Overlay pemindaian yang menutupi seluruh layar saat scanning berlangsung.
    Menampilkan spinner animasi, pesan status, waktu berjalan, dan progress bar.
    Pengguna bisa menekan tombol "Batalkan" untuk menghentikan proses scanning.
    """

    def __init__(self, parent=None):
        """
        Inisialisasi overlay scanning dengan semua atribut yang dibutuhkan.

        Atribut yang disiapkan di sini:
        - objectName   : nama unik widget agar bisa ditarget oleh stylesheet CSS
        - WA_StyledBackground : izinkan warna latar dari stylesheet diterapkan ke widget ini
        - _cancel_callback   : fungsi yang akan dipanggil saat tombol Batalkan ditekan (awalnya None)
        - _start_time        : waktu mulai scanning (diisi saat start() dipanggil)
        - _elapsed_seconds   : total detik yang sudah berlalu sejak scanning dimulai
        - _timer             : timer Qt yang berdetak setiap 1000ms (1 detik) untuk update tampilan
        """
        # Panggil konstruktor kelas induk QWidget
        super().__init__(parent)

        # Beri nama unik agar stylesheet bisa menarget widget ini secara spesifik
        self.setObjectName("scanningOverlay")

        # Aktifkan dukungan warna latar dari stylesheet — tanpa ini, QWidget biasanya transparan
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Tempat menyimpan fungsi callback untuk tombol Batalkan.
        # Awalnya None karena pemanggil (parent) yang akan mengisi fungsi ini nanti.
        self._cancel_callback = None

        # Waktu mulai scanning — akan diisi oleh time.perf_counter() saat start() dipanggil.
        # Diinisialisasi None agar bisa dicek apakah scanning sudah dimulai atau belum.
        self._start_time = None

        # Hitungan total detik yang sudah berlalu — direset ke 0 setiap kali start() dipanggil
        self._elapsed_seconds = 0

        # Timer Qt yang berdetak setiap 1 detik (1000 ms).
        # Setiap detak memanggil _tick() yang memperbarui tampilan waktu.
        # QTimer lebih andal dari loop manual karena terintegrasi dengan event loop Qt
        # dan otomatis berhenti ketika tidak dibutuhkan.
        self._timer = QTimer(self)
        self._timer.setInterval(1000)        # interval detak: 1000 ms = 1 detik
        self._timer.timeout.connect(self._tick)  # setiap detak panggil _tick()

        # Bangun tampilan visual overlay
        self.setup_ui()

    def setup_ui(self):
        """
        Susun semua widget di dalam kartu overlay:
        1. Spinner animasi berputar
        2. Judul "Memindai File"
        3. Label status (pesan aktif)
        4. Label timer (waktu berjalan)
        5. Progress bar (persentase)
        6. Tombol Batalkan
        """
        # Layout utama overlay — tanpa margin, konten di tengah secara vertikal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)           # overlay memenuhi seluruh layar tanpa margin
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # pusatkan kartu di tengah layar

        # ── KARTU TENGAH ──────────────────────────────────────────────────────────
        # Kartu ini yang benar-benar terlihat pengguna — latar belakang overlay hanya bayangan gelap
        card = QFrame()
        card.setObjectName("spinnerContainer")  # nama untuk ditarget stylesheet
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)    # padding dalam kartu agar tidak sempit
        card_layout.setSpacing(20)                         # jarak antar widget dalam kartu
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── SPINNER ANIMASI ───────────────────────────────────────────────────────
        # Lingkaran berputar yang menunjukkan proses sedang berjalan
        self.spinner = AnimatedSpinner()
        card_layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignCenter)

        # ── JUDUL ─────────────────────────────────────────────────────────────────
        # Teks besar di bawah spinner
        self.title_label = QLabel("Memindai File")
        self.title_label.setObjectName("spinnerTitle")     # nama untuk ditarget stylesheet
        self.title_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.title_label)

        # ── LABEL STATUS ──────────────────────────────────────────────────────────
        # Pesan dinamis yang berubah sesuai file yang sedang dipindai
        # Contoh: "Memindai dokumen.pdf..." atau "Menganalisis data..."
        self.status_label = QLabel("Menyiapkan...")
        self.status_label.setObjectName("statusText")      # nama untuk ditarget stylesheet
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)               # izinkan teks panjang ke baris bawah
        card_layout.addWidget(self.status_label)

        # ── LABEL TIMER ───────────────────────────────────────────────────────────
        # Menampilkan berapa detik scanning sudah berjalan (diperbarui setiap 1 detik)
        self.timer_label = QLabel("⏱ 0 detik")
        self.timer_label.setObjectName("timerText")        # nama untuk ditarget stylesheet
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setFont(QFont("Segoe UI", 11))
        card_layout.addWidget(self.timer_label)

        # ── PROGRESS BAR ──────────────────────────────────────────────────────────
        # Batang kemajuan dari 0% hingga 100%
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)          # skala 0 sampai 100 persen
        self.progress_bar.setValue(0)               # mulai dari 0%
        self.progress_bar.setTextVisible(True)      # tampilkan angka persentase di dalam bar
        self.progress_bar.setFixedHeight(24)        # tinggi bar agar terlihat jelas
        card_layout.addWidget(self.progress_bar)

        # ── TOMBOL BATALKAN ───────────────────────────────────────────────────────
        # Tombol untuk menghentikan proses scanning di tengah jalan
        self.cancel_btn = QPushButton("Batalkan")
        self.cancel_btn.setObjectName("cancelScanButton")  # nama untuk ditarget stylesheet
        self.cancel_btn.clicked.connect(self._handle_cancel)

        # Bungkus tombol dalam layout horizontal agar bisa dipusatkan
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(self.cancel_btn)
        card_layout.addLayout(btn_layout)

        # Masukkan kartu ke layout utama overlay
        layout.addWidget(card)

        # Terapkan style default (mode terang)
        self.apply_style()

    def apply_style(self, is_dark=False):
        """
        Terapkan tema warna ke overlay berdasarkan mode tampilan.

        Perbedaan mode gelap dan terang:
        - Mode GELAP (is_dark=True):
            * Overlay: bayangan hitam lebih pekat (opacity 180/255)
            * Kartu: latar gelap (#252525 → #1A1A1A gradient)
            * Teks: putih dan abu terang (#CCCCCC)
            * Aksen warna: oranye cerah (#FFA500, #FF8C00)

        - Mode TERANG (is_dark=False):
            * Overlay: bayangan hitam lebih transparan (opacity 150/255)
            * Kartu: latar putih ke krem (gradient putih → #FFE4B5)
            * Teks: abu gelap (#2C2C2C, #444444)
            * Aksen warna: oranye gelap (#FF8C00) agar kontras dengan latar terang

        Parameter:
            is_dark — True untuk mode gelap, False untuk mode terang (default)
        """
        if is_dark:
            # ── STYLE MODE GELAP ─────────────────────────────────────────────────
            self.setStyleSheet("""
                QWidget#scanningOverlay {
                    background: rgba(0, 0, 0, 180);
                }
                QFrame#spinnerContainer {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #252525, stop:0.5 #1F1F1F, stop:1 #1A1A1A);
                    border: 4px solid #FFA500;
                    border-radius: 35px;
                    padding: 10px;
                }
                QLabel#spinnerTitle {
                    color: #FFA500;
                    font-weight: 700;
                    font-size: 22px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QLabel#statusText {
                    color: #CCCCCC;
                    font-size: 15px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QLabel#timerText {
                    color: #FFA500;
                    font-size: 13px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QProgressBar {
                    border: 3px solid #FFA500;
                    border-radius: 14px;
                    color: #FFA500;
                    text-align: center;
                    font-weight: 600;
                    font-size: 13px;
                    background: rgba(30, 30, 30, 0.8);
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #FFA500, stop:0.5 #FF8C00, stop:1 #FF7F00);
                    border-radius: 11px;
                }
                QPushButton#cancelScanButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FF6B35, stop:1 #E64A19);
                    color: white;
                    border: 2px solid #FF8C00;
                    padding: 12px 28px;
                    border-radius: 22px;
                    font-weight: 600;
                    font-size: 14px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QPushButton#cancelScanButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #E64A19, stop:1 #D84315);
                    border: 2px solid #FFA500;
                }
            """)
        else:
            # ── STYLE MODE TERANG ────────────────────────────────────────────────
            self.setStyleSheet("""
                QWidget#scanningOverlay {
                    background: rgba(0, 0, 0, 150);
                }
                QFrame#spinnerContainer {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #FFFFFF, stop:0.5 #FFF5E6, stop:1 #FFE4B5);
                    border: 4px solid #FF8C00;
                    border-radius: 35px;
                    padding: 10px;
                }
                QLabel#spinnerTitle {
                    color: #2C2C2C;
                    font-weight: 700;
                    font-size: 22px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QLabel#statusText {
                    color: #444444;
                    font-size: 15px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QLabel#timerText {
                    color: #FF8C00;
                    font-size: 13px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QProgressBar {
                    border: 3px solid #FF8C00;
                    border-radius: 14px;
                    color: #2C2C2C;
                    text-align: center;
                    font-weight: 600;
                    font-size: 13px;
                    background: rgba(255, 255, 255, 0.8);
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #FFA500, stop:0.5 #FF8C00, stop:1 #FF7F00);
                    border-radius: 11px;
                }
                QPushButton#cancelScanButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FF6B35, stop:1 #E64A19);
                    color: white;
                    border: 2px solid #FF8C00;
                    padding: 12px 28px;
                    border-radius: 22px;
                    font-weight: 600;
                    font-size: 14px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QPushButton#cancelScanButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #E64A19, stop:1 #D84315);
                    border: 2px solid #FFA500;
                }
            """)

    def set_cancel_callback(self, callback):
        """
        Daftarkan fungsi yang akan dijalankan ketika pengguna menekan tombol "Batalkan".

        Cara pakai:
            overlay.set_cancel_callback(self.hentikan_scanning)

        Parameter:
            callback — fungsi tanpa argumen yang akan dipanggil saat pembatalan diminta
        """
        self._cancel_callback = callback

    def _handle_cancel(self):
        """
        Dipanggil oleh Qt saat tombol "Batalkan" ditekan.
        Jika callback sudah didaftarkan oleh parent, jalankan callback tersebut.
        Jika callback belum didaftarkan (None), tidak ada yang terjadi.
        """
        if self._cancel_callback:
            self._cancel_callback()  # jalankan fungsi pembatalan dari parent

    def update_progress(self, value, message):
        """
        Perbarui tampilan progress bar dan pesan status.
        Dipanggil oleh thread scanner setiap kali ada kemajuan baru.

        Parameter:
            value   — angka persentase kemajuan (0 sampai 100)
            message — pesan status terbaru (contoh: "Memindai file ke-23 dari 100")
        """
        self.progress_bar.setValue(value)       # perbarui angka di progress bar
        self.status_label.setText(message)      # perbarui pesan status

    def _tick(self):
        """
        Dipanggil secara otomatis setiap 1 detik oleh QTimer.
        Menghitung ulang waktu yang sudah berlalu dan memperbarui label timer.

        Kenapa pakai time.perf_counter() bukan time.time()?
        - time.time() mengukur waktu kalender (UTC) yang bisa berubah jika pengguna
          mengubah jam sistem atau saat pergantian jam musim panas — ini bisa menyebabkan
          timer loncat atau mundur.
        - time.perf_counter() mengukur waktu dari jam internal prosesor (monotonic clock)
          yang hanya bisa maju, tidak pernah mundur, dan sangat presisi (resolusi nanosecond).
        - Untuk mengukur durasi, perf_counter adalah pilihan yang benar karena hasilnya
          selalu akurat dan tidak terpengaruh perubahan jam sistem.
        """
        # Hitung selisih antara waktu sekarang dan waktu mulai scanning
        self._elapsed_seconds = int(time.perf_counter() - self._start_time)

        # Perbarui teks timer di layar
        self.timer_label.setText(f"⏱ {self._elapsed_seconds} detik")

    def start(self):
        """
        Tampilkan overlay dan mulai menghitung waktu scanning.
        Urutan langkah:
        1. Sesuaikan ukuran overlay agar sama persis dengan ukuran jendela parent
        2. Catat waktu mulai menggunakan perf_counter (jam presisi)
        3. Reset hitungan detik ke 0
        4. Reset tampilan timer ke "0 detik"
        5. Jalankan timer Qt agar _tick() dipanggil setiap 1 detik
        6. Tampilkan overlay (show())
        7. Pindahkan overlay ke paling depan (raise_()) agar tidak tertutup widget lain
        """
        # Langkah 1: perluas ukuran overlay agar pas dengan jendela parent
        if self.parent():
            self.setGeometry(self.parent().rect())

        # Langkah 2: catat waktu mulai dengan jam presisi prosesor
        self._start_time = time.perf_counter()

        # Langkah 3: reset hitungan detik
        self._elapsed_seconds = 0

        # Langkah 4: reset tampilan timer
        self.timer_label.setText("⏱ 0 detik")

        # Langkah 5: mulai timer Qt (berdetak setiap 1 detik)
        self._timer.start()

        # Langkah 6: tampilkan overlay
        self.show()

        # Langkah 7: pastikan overlay ada di atas semua widget lain
        self.raise_()

    def finish(self):
        """
        Hentikan timer dan sembunyikan overlay setelah scanning selesai.
        Urutan langkah:
        1. Hentikan timer Qt agar _tick() tidak dipanggil lagi
        2. Hitung total waktu scanning dan tampilkan di label timer
        3. Sembunyikan overlay dari layar
        """
        # Langkah 1: hentikan timer — tidak perlu update tampilan lagi
        self._timer.stop()

        # Langkah 2: hitung dan tampilkan total waktu jika scanning pernah dimulai
        if self._start_time is not None:
            total = int(time.perf_counter() - self._start_time)
            self.timer_label.setText(f"⏱ Selesai dalam {total} detik")

        # Langkah 3: sembunyikan overlay dari layar
        self.hide()
