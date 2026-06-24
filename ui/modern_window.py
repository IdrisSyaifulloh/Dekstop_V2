"""
MangoDefend — Jendela Utama Aplikasi

File ini adalah pusat kendali tampilan aplikasi. Ia memuat:
  - Sidebar navigasi di sisi kiri
  - Area konten di sisi kanan yang bisa berpindah halaman
  - Logika untuk menjalankan scan file, scan folder, scan perangkat penuh
  - Pengelolaan proteksi realtime (nyalakan/matikan)
  - Pengelolaan pembaruan model AI
  - Respons terhadap peringatan malware dari thread latar belakang
  - Dukungan tema gelap dan terang (mengikuti tema OS secara otomatis)
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
import os
import logging
from datetime import datetime

# Impor komponen sidebar dan halaman dashboard yang selalu dibutuhkan saat startup.
# Halaman lain (ScanView, ProtectionView, dll.) diimpor secara lokal di dalam
# _get_or_create_view() karena dibuat hanya saat pertama kali dikunjungi (lazy loading).
from ui.components import Sidebar, DashboardView

# Impor dialog hasil scan tunggal dan scan batch
from ui.dialogs import ResultDialog, BatchResultDialog

# Impor dialog peringatan malware untuk proteksi realtime
from ui.dialogs.malware_alert import MalwareAlertDialog, MalwareAlertBridge

# Impor fungsi pengambil stylesheet tema
from ui.styles.figma_theme import get_theme_stylesheet

# Impor thread scan di latar belakang
from ui.threads import ScanThread, BatchScanThread

# Logger untuk mencatat peristiwa penting (bisa dibaca di file log aplikasi)
logger = logging.getLogger(__name__)


class ModernWindow(QMainWindow):
    """
    Jendela utama aplikasi MangoDefend.

    Berisi sidebar navigasi di kiri dan area konten di kanan yang bisa
    berpindah halaman (Dashboard, Scan, Protection, Karantina, Update).

    Fitur:
      - Tema gelap dan terang, mengikuti pengaturan tema OS secara otomatis.
      - Halaman dibuat saat pertama kali dikunjungi (lazy loading) untuk hemat memori.
      - Merespons peringatan malware dari thread latar belakang melalui jembatan sinyal.
      - Saat jendela ditutup, aplikasi disembunyikan ke system tray (tidak benar-benar keluar).
    """

    @staticmethod
    def _detect_system_dark_mode() -> bool:
        """
        Periksa apakah sistem operasi saat ini menggunakan mode gelap.

        Mengembalikan True jika mode gelap, False jika mode terang.
        Dipanggil sekali saat inisialisasi untuk menentukan tema awal.
        """
        hints  = QGuiApplication.styleHints()
        scheme = hints.colorScheme()
        # Jika scheme bukan Light (terang), berarti gelap atau tidak diketahui → anggap gelap
        return scheme != Qt.ColorScheme.Light

    def __init__(self):
        """
        Siapkan jendela utama: atur status awal, bangun tampilan, dan terapkan tema.
        """
        super().__init__()

        # ── Status awal — mengikuti tema OS yang terdeteksi ──
        self.is_dark_mode = self._detect_system_dark_mode()

        # Halaman yang sedang aktif (ID string)
        self.current_tab = "dashboard"

        # Penghitung ancaman yang ditemukan sepanjang sesi aplikasi
        self.threats_detected = 0

        # Waktu scan terakhir (digunakan untuk menampilkan "Scan terakhir: xx menit lalu")
        self.last_scan = datetime.now()

        # ── Objek proses scan ──
        # scan_worker: thread scan file tunggal yang sedang berjalan (jika ada)
        self.scan_worker = None

        # result_dialog: dialog hasil scan yang terakhir dibuka (simpan referensi agar tidak terhapus)
        self.result_dialog = None

        # ── Referensi ke pengelola eksternal (diisi oleh main.py setelah window dibuat) ──
        self.realtime_protection = None  # Objek engine proteksi realtime
        self.model_updater       = None  # Objek pengelola pembaruan model AI

        # ── Jembatan peringatan malware ──
        # Engine proteksi berjalan di thread berbeda. MalwareAlertBridge adalah
        # perantara yang mengirim sinyal ke thread UI agar dialog bisa ditampilkan
        # (Qt hanya mengizinkan operasi UI dari thread utama).
        self.malware_bridge = MalwareAlertBridge()
        self.malware_bridge.malware_detected.connect(self._on_malware_alert)

        # Bangun tampilan jendela
        self.init_ui()

        # Terapkan stylesheet tema pertama kali
        self.apply_theme()

        # ── Ikuti perubahan tema OS secara otomatis ──
        # Saat pengguna mengganti tema Windows (Gelap↔Terang), aplikasi otomatis ikut berganti
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._on_os_theme_changed)

    def init_ui(self):
        """
        Bangun tata letak jendela utama: sidebar di kiri, area konten di kanan.

        Tata letak menggunakan QHBoxLayout (horizontal) sehingga sidebar dan
        area konten berdampingan secara horizontal.
        """
        from build_info import BUILD_TAG
        self.setWindowTitle(f"MangoDefend - AI Malware Protection [{BUILD_TAG}]")
        self.setGeometry(100, 100, 1400, 900)  # Posisi dan ukuran awal jendela
        self.setMinimumSize(1200, 800)          # Ukuran minimum agar tampilan tidak rusak

        # Widget tengah sebagai wadah utama semua elemen
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout horizontal: sidebar | area konten
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)  # Tanpa margin di tepi jendela
        main_layout.setSpacing(0)                    # Tanpa celah antara sidebar dan konten

        # ── Sidebar Navigasi Kiri ──
        # Sidebar berisi tombol navigasi (Dashboard, Scan, dll), status perlindungan,
        # tombol ganti tema, dan penghitung ancaman
        self.sidebar = Sidebar(is_dark=self.is_dark_mode)

        # Saat pengguna mengklik menu di sidebar, ganti halaman konten
        self.sidebar.tab_changed.connect(self._on_tab_changed)

        # Saat pengguna menekan tombol ganti tema di sidebar, terapkan tema baru
        self.sidebar.theme_toggled.connect(self._on_theme_toggled)

        main_layout.addWidget(self.sidebar)

        # ── Area Konten Kanan ──
        # QStackedWidget memungkinkan banyak halaman "ditumpuk" dan satu yang ditampilkan
        self.content_stack = QStackedWidget()

        # Cache halaman yang sudah dibuat: {tab_id: widget_halaman}
        # Halaman TIDAK dibuat sekaligus saat startup — hanya dibuat saat pertama kali dibuka
        # Teknik ini disebut "lazy initialization" — menghemat memori dan mempercepat startup
        self._view_cache: dict[str, QWidget] = {}

        # ── Dashboard: satu-satunya halaman yang dibuat langsung ──
        # Karena dashboard adalah halaman awal, harus siap sebelum jendela ditampilkan
        self.dashboard_view = DashboardView()
        self.content_stack.addWidget(self.dashboard_view)

        # Halaman lain diinisialisasi sebagai None — akan dibuat saat pertama dikunjungi
        self.scan_view       = None
        self.protection_view = None
        self.quarantine_view = None
        self.update_view     = None

        # Sambungkan sinyal navigasi dari kartu pintasan dashboard
        self.dashboard_view.navigate_requested.connect(self._navigate_from_dashboard)
        self._connect_view_signals()

        # Tambahkan area konten ke layout dan beri bobot 1 (mengisi semua sisa ruang)
        main_layout.addWidget(self.content_stack, 1)

        # Tampilkan halaman awal (dashboard, indeks 0)
        self.content_stack.setCurrentIndex(0)

    def _connect_view_signals(self):
        """
        Hubungkan sinyal navigasi dari halaman yang sudah dibuat.

        Catatan: hanya dashboard yang terhubung di sini karena halaman lain
        belum dibuat (lazy). Halaman lain terhubung saat dibuat di _get_or_create_view().
        """
        # Sambungkan sekali lagi untuk memastikan koneksi terdaftar
        self.dashboard_view.navigate_requested.connect(self._navigate_from_dashboard)

    def _get_or_create_view(self, tab_id: str) -> QWidget:
        """
        Ambil halaman dari cache, atau buat baru jika belum pernah dibuka.

        Cara kerja lazy initialization:
          1. Cek apakah halaman sudah pernah dibuat (ada di _view_cache).
          2. Jika sudah: kembalikan langsung dari cache (cepat, tidak buat ulang).
          3. Jika belum: buat halaman, sambungkan sinyal-sinyalnya, simpan ke cache.

        tab_id : Identifier halaman, salah satu dari: "scan", "protection",
                 "quarantine", "update".
        """
        # Jika halaman sudah ada di cache, kembalikan langsung
        if tab_id in self._view_cache:
            return self._view_cache[tab_id]

        # ── Buat halaman baru sesuai tab_id ──

        if tab_id == "scan":
            # Halaman Scan: impor lokal menghindari sirkular impor
            from ui.components import ScanView
            view = ScanView()

            # Saat pengguna klik "Scan File Tunggal" di halaman scan
            view.scan_requested.connect(self.run_scanner)

            # Saat pengguna klik "Scan Folder"
            view.folder_scan_requested.connect(self._run_folder_scan)

            # Saat pengguna klik "Scan Seluruh Perangkat"
            view.device_scan_requested.connect(self._run_device_scan)

            # Berikan fungsi pembatalan scan ke tombol "Batalkan" di halaman scan
            view.set_cancel_scan_callback(self._cancel_scan)
            self.scan_view = view

        elif tab_id == "protection":
            from ui.components import ProtectionView
            view = ProtectionView()

            # Saat pengguna menekan tombol aktifkan/nonaktifkan di halaman protection
            view.protection_toggled.connect(self._toggle_realtime_protection)
            self.protection_view = view

        elif tab_id == "quarantine":
            from ui.components import QuarantineView
            view = QuarantineView()
            self.quarantine_view = view
            # QuarantineView tidak memiliki aksi khusus — data dimuat saat halaman dibuka

        elif tab_id == "update":
            from ui.components import UpdateView
            view = UpdateView()

            # Saat pengguna klik "Periksa Pembaruan"
            view.check_update_requested.connect(self._check_for_updates)

            # Saat pengguna klik "Unduh Pembaruan"
            view.download_update_requested.connect(self._download_update)
            self.update_view = view

        else:
            # tab_id tidak dikenal — kembalikan dashboard sebagai fallback
            return self.dashboard_view

        # Terapkan tema aktif saat ini ke halaman yang baru dibuat
        view.set_theme(self.is_dark_mode)

        # Tambahkan halaman ke QStackedWidget agar bisa ditampilkan
        self.content_stack.addWidget(view)

        # Simpan ke cache agar tidak dibuat ulang di kunjungan berikutnya
        self._view_cache[tab_id] = view
        return view

    def _on_tab_changed(self, tab_id: str):
        """
        Ganti halaman konten yang ditampilkan saat pengguna mengklik menu di sidebar.

        Dipanggil oleh sinyal Sidebar.tab_changed.

        tab_id : Identifier halaman yang ingin ditampilkan (contoh: "scan", "dashboard").
        """
        self.current_tab = tab_id

        if tab_id == "dashboard":
            # Dashboard sudah selalu ada, langsung tampilkan
            self.content_stack.setCurrentWidget(self.dashboard_view)
            return

        # Untuk halaman lain: buat jika belum ada, lalu tampilkan
        view = self._get_or_create_view(tab_id)
        self.content_stack.setCurrentWidget(view)

        # Khusus halaman karantina: muat ulang daftar item setiap kali halaman dibuka
        # agar data selalu terkini (file karantina bisa bertambah dari mana saja)
        if tab_id == "quarantine":
            self.quarantine_view.load_quarantine_items()

    def _navigate_from_dashboard(self, tab_id: str):
        """
        Pindah ke halaman lain saat pengguna mengklik kartu pintasan di dashboard.

        Berbeda dari _on_tab_changed, fungsi ini juga menyinkronkan state tombol
        sidebar agar tombol yang sesuai tampak aktif/tercentang.

        tab_id : Identifier halaman tujuan.
        """
        # Aktifkan tombol navigasi yang sesuai di sidebar
        self.sidebar.set_active_tab(tab_id)

        # Ganti halaman konten
        self._on_tab_changed(tab_id)

    def _on_theme_toggled(self, is_dark: bool):
        """
        Terapkan tema baru saat pengguna menekan tombol ganti tema di sidebar.

        Dipanggil oleh sinyal Sidebar.theme_toggled.

        is_dark : True = pengguna memilih mode gelap, False = mode terang.
        """
        self.is_dark_mode = is_dark
        self.apply_theme()

    def _on_os_theme_changed(self, scheme):
        """
        Ikuti perubahan tema OS secara otomatis.

        Dipanggil saat pengguna mengganti tema di pengaturan Windows/macOS/Linux
        tanpa perlu pengguna menekan tombol apapun di dalam aplikasi.

        scheme : Nilai Qt.ColorScheme dari colorSchemeChanged signal.
        """
        is_dark = (scheme != Qt.ColorScheme.Light)

        # Abaikan jika tema tidak berubah (mencegah gambar ulang yang tidak perlu)
        if is_dark == self.is_dark_mode:
            return

        self.is_dark_mode = is_dark

        # Perbarui status internal sidebar dan label tombolnya
        self.sidebar.is_dark = is_dark
        self.sidebar.theme_btn.setText(" Dark Mode" if is_dark else " Light Mode")

        # Perbarui kartu hitungan ancaman di sidebar
        self.sidebar.threats_card.set_theme(is_dark)
        self.sidebar._apply_threats_card_theme()

        # Terapkan tema ke seluruh jendela
        self.apply_theme()

    def apply_theme(self):
        """
        Terapkan ulang stylesheet ke seluruh jendela dan semua halaman sesuai tema aktif.

        Fungsi ini dipanggil setiap kali tema berubah — baik dari tombol sidebar
        maupun dari perubahan tema OS.

        Urutan operasi:
          1. Ambil string CSS dari figma_theme.py sesuai mode gelap/terang.
          2. Terapkan ke jendela utama (mewariskan ke semua widget turunan).
          3. Panggil set_theme() pada tiap halaman yang sudah dibuat untuk
             mengupdate elemen yang digambar manual (bukan CSS).
        """
        stylesheet = get_theme_stylesheet(self.is_dark_mode)
        self.setStyleSheet(stylesheet)

        # Perbarui halaman dashboard (selalu ada)
        self.dashboard_view.set_theme(self.is_dark_mode)

        # Perbarui semua halaman lain yang sudah pernah dibuka
        for view in self._view_cache.values():
            view.set_theme(self.is_dark_mode)

    def _ensure_scan_view(self):
        """
        Pastikan halaman scan sudah dibuat sebelum digunakan.
        Dipanggil sebelum menampilkan progress scan agar tidak error.
        """
        if self.scan_view is None:
            self._get_or_create_view("scan")

    # =================================================================
    # FITUR SCAN FILE TUNGGAL
    # =================================================================

    def run_scanner(self, file_path: str = None):
        """
        Jalankan scan satu file.

        Jika file_path tidak diberikan (misalnya pengguna klik tombol scan tanpa
        memilih file terlebih dahulu), tampilkan dialog pemilihan file.

        Alur:
          1. Jika belum ada file_path, buka dialog pilih file.
          2. Tampilkan panel progress di halaman scan.
          3. Buat thread scan di latar belakang dan sambungkan sinyalnya.
          4. Jalankan thread.

        file_path : Path file yang akan dipindai (opsional).
        """
        if not file_path:
            # Buka dialog pemilihan file jika path belum ada
            from PySide6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Pilih File untuk Dipindai", "", "All Files (*.*)"
            )

        # Pengguna membatalkan dialog pemilihan file — tidak lakukan apapun
        if not file_path:
            return

        # Pastikan halaman scan sudah ada, lalu tampilkan panel progress
        self._ensure_scan_view()
        self.scan_view.show_scan_progress("Memindai File...")

        # Buat thread scan dan sambungkan semua sinyalnya
        self.scan_worker = ScanThread(file_path)
        self.scan_worker.progress.connect(self._on_scan_progress)   # Update progress bar
        self.scan_worker.finished.connect(self._on_scan_finished)   # Hasil scan selesai
        self.scan_worker.error.connect(self._on_scan_error)          # Terjadi error
        self.scan_worker.start()  # Mulai thread scan di latar belakang

    def _on_scan_progress(self, value: int, message: str):
        """
        Teruskan pembaruan kemajuan scan ke panel progress di halaman scan.

        Dipanggil oleh sinyal ScanThread.progress secara berkala selama scan.

        value   : Persentase kemajuan (0–100).
        message : Teks status saat ini (misalnya "Mengekstrak fitur...").
        """
        if self.scan_view:
            self.scan_view.update_scan_progress(value, message)

    def _on_scan_finished(self, result: dict):
        """
        Tangani hasil scan file tunggal yang telah selesai.

        Tugas:
          1. Sembunyikan panel progress.
          2. Perbarui waktu scan terakhir di dashboard.
          3. Tambahkan entri ke riwayat scan di halaman scan.
          4. Jika malware ditemukan, tambah hitungan ancaman.
          5. Tampilkan dialog hasil scan kepada pengguna.

        result : Dict hasil scan dari ScanThread, berisi 'result', 'file', dll.
        """
        # Sembunyikan panel progress di halaman scan
        if self.scan_view:
            self.scan_view.hide_scan_progress()

        # Perbarui waktu scan terakhir di dashboard
        self.last_scan = datetime.now()
        self.dashboard_view.update_last_scan(self.last_scan)

        # Catat aktivitas scan di grafik dashboard (tambah 1 scan hari ini)
        self.dashboard_view.record_scan_activity(1, self.last_scan)

        # Jika hasilnya malware, tambah hitungan ancaman di sidebar dan dashboard
        if result.get('result') == 'Malware':
            self.threats_detected += 1
            self.sidebar.update_threats_count(self.threats_detected)
            self.dashboard_view.update_threats_count(self.threats_detected)

        # Ambil informasi file dari hasil scan untuk riwayat
        file_info  = result.get('file', {})
        file_name  = file_info.get('file_name', 'Unknown')
        file_path  = file_info.get('file_path', '')
        scan_result = result.get('result', 'Unknown')
        timestamp  = datetime.now().strftime("%H:%M")

        # Tambahkan ke riwayat scan di halaman scan
        if self.scan_view:
            self.scan_view.add_to_history(file_name, scan_result, timestamp, file_path)

        # Tampilkan dialog hasil scan — simpan referensi agar tidak dihapus GC
        self.result_dialog = ResultDialog(result, self)
        self.result_dialog.show_dialog()

    def _on_scan_error(self, error_msg: str):
        """
        Sembunyikan panel progress dan tampilkan pesan kesalahan kepada pengguna.

        Dipanggil oleh sinyal ScanThread.error jika terjadi exception saat scan.

        error_msg : Pesan kesalahan dari exception yang terjadi.
        """
        if self.scan_view:
            self.scan_view.hide_scan_progress()

        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Scan Error", f"Terjadi kesalahan: {error_msg}")

    def _cancel_scan(self):
        """
        Hentikan proses scan yang sedang berjalan.

        Dapat menghentikan dua jenis scan:
          - scan_worker : Thread scan file tunggal.
          - batch_worker: Thread scan banyak file (folder/perangkat).

        Setelah dihentikan, panel progress disembunyikan.
        """
        # Hentikan scan file tunggal jika sedang berjalan
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.cancel()  # Kirim sinyal pembatalan ke thread
            self.scan_worker.wait()    # Tunggu thread benar-benar selesai

        # Hentikan scan batch jika sedang berjalan
        if hasattr(self, 'batch_worker') and self.batch_worker and self.batch_worker.isRunning():
            self.batch_worker.cancel()
            self.batch_worker.wait()

        # Sembunyikan panel progress
        if self.scan_view:
            self.scan_view.hide_scan_progress()

    # =================================================================
    # SCAN FOLDER DAN SCAN SELURUH PERANGKAT
    # =================================================================

    def _run_folder_scan(self, folder_path: str):
        """
        Mulai scan semua file di dalam folder yang dipilih pengguna.

        Jika scan batch sudah berjalan, tampilkan peringatan dan batalkan.

        folder_path : Path folder yang akan dipindai.
        """
        # Cegah menjalankan dua scan batch sekaligus
        if hasattr(self, 'batch_worker') and self.batch_worker and self.batch_worker.isRunning():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Scan Berjalan", "Scan batch sedang berjalan. Tunggu hingga selesai.")
            return
        self._start_batch_scan(folder_path=folder_path)

    def _run_device_scan(self):
        """
        Minta konfirmasi pengguna, lalu mulai scan seluruh file di perangkat.

        Scan perangkat penuh bisa memakan waktu lama, sehingga konfirmasi
        diperlukan agar pengguna tidak menjalankannya secara tidak sengaja.
        """
        # Cegah menjalankan dua scan batch sekaligus
        if hasattr(self, 'batch_worker') and self.batch_worker and self.batch_worker.isRunning():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Scan Berjalan", "Scan batch sedang berjalan. Tunggu hingga selesai.")
            return

        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Scan Seluruh Perangkat",
            "Scan akan memeriksa seluruh file berbahaya di perangkat Anda.\n"
            "Proses ini mungkin memakan waktu beberapa menit.\n\nLanjutkan?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._start_batch_scan(full_device=True)

    def _start_batch_scan(self, folder_path: str = None, full_device: bool = False):
        """
        Buat dan jalankan proses scan banyak file di thread latar belakang.

        Dua mode:
          - folder_path diisi: scan hanya folder tertentu.
          - full_device=True : scan seluruh perangkat.

        Mencatat waktu mulai scan untuk menghitung total durasi di akhir.

        folder_path : Path folder yang dipindai (None jika full device scan).
        full_device : True jika ingin scan seluruh perangkat.
        """
        import time
        title = "Scan Seluruh Perangkat..." if full_device else "Scan Folder..."

        # Pastikan halaman scan ada dan tampilkan panel progress
        self._ensure_scan_view()
        self.scan_view.show_scan_progress(title)

        # Simpan waktu mulai scan untuk menghitung durasi total
        self._batch_scan_start_time = time.perf_counter()

        # Buat dan jalankan thread scan batch
        self.batch_worker = BatchScanThread(
            folder_path=folder_path,
            full_device=full_device
        )

        # Sambungkan semua sinyal dari batch worker
        self.batch_worker.progress.connect(self._on_scan_progress)          # Update progress bar
        self.batch_worker.limit_reached.connect(self._on_batch_limit_reached)  # Batas file tercapai
        self.batch_worker.file_scanned.connect(self._on_batch_file_scanned)    # Satu file selesai
        self.batch_worker.batch_finished.connect(self._on_batch_finished)      # Semua file selesai
        self.batch_worker.error.connect(self._on_scan_error)                   # Terjadi error

        self.batch_worker.start()

    def _on_batch_limit_reached(self, info: dict):
        """
        Tanya pengguna apakah ingin melanjutkan scan melewati batas jumlah file.

        Konteks:
          Scan perangkat penuh membatasi jumlah file default untuk menjaga kecepatan.
          Jika file terlalu banyak, pengguna ditanya apakah ingin melampaui batas.

        Keputusan pengguna diteruskan ke batch_worker yang sedang menunggu.

        info : Dict berisi 'limit' (batas default) dan 'file_count' (file yang ditemukan).
        """
        if not hasattr(self, 'batch_worker') or not self.batch_worker:
            return

        from PySide6.QtWidgets import QMessageBox

        limit      = info.get('limit', 2000)
        file_count = info.get('file_count', limit)

        reply = QMessageBox.question(
            self,
            "Lanjutkan Scan Semua File?",
            "Batas aman scan perangkat telah tercapai.\n\n"
            f"File yang sudah terkumpul: {file_count}\n"
            f"Batas default: {limit} file\n\n"
            "Pilih 'Yes' untuk lanjut scan semua file yang ditemukan.\n"
            "Pilih 'No' untuk berhenti di batas default agar proses tetap lebih cepat.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,  # Pilihan default: No (lebih aman)
        )

        # Teruskan keputusan pengguna ke thread yang sedang menunggu jawaban
        self.batch_worker.set_limit_decision(
            reply == QMessageBox.StandardButton.Yes
        )

    def _on_batch_file_scanned(self, result: dict):
        """
        Perbarui riwayat scan dan hitungan ancaman untuk setiap file yang selesai dipindai.

        Dipanggil oleh sinyal BatchScanThread.file_scanned untuk setiap file.

        result : Dict hasil scan satu file, format sama seperti scan tunggal.
        """
        file_info   = result.get('file', {})
        file_name   = file_info.get('file_name', 'Unknown')
        file_path   = file_info.get('file_path', '')
        scan_result = result.get('result', 'Unknown')
        timestamp   = datetime.now().strftime('%H:%M')

        # Tambahkan ke riwayat scan di halaman scan
        if self.scan_view:
            self.scan_view.add_to_history(file_name, scan_result, timestamp, file_path)

        # Catat aktivitas scan di grafik dashboard
        self.dashboard_view.record_scan_activity(1)

        # Jika ditemukan malware, tambah hitungan ancaman
        if scan_result == 'Malware':
            self.threats_detected += 1
            self.sidebar.update_threats_count(self.threats_detected)
            self.dashboard_view.update_threats_count(self.threats_detected)

    def _on_batch_finished(self, summary: dict):
        """
        Tangani penyelesaian scan batch: sembunyikan progress, perbarui waktu scan,
        hitung durasi, dan tampilkan ringkasan hasil.

        summary : Dict berisi statistik hasil scan (total file, malware, dll).
        """
        import time
        if self.scan_view:
            self.scan_view.hide_scan_progress()

        # Perbarui waktu scan terakhir di dashboard
        self.last_scan = datetime.now()
        self.dashboard_view.update_last_scan(self.last_scan)

        # Hitung total durasi scan (dari saat dimulai sampai sekarang)
        scan_duration = None
        if hasattr(self, '_batch_scan_start_time'):
            scan_duration = time.perf_counter() - self._batch_scan_start_time

        # Tampilkan dialog ringkasan hasil batch scan
        dialog = BatchResultDialog(summary, self, scan_duration=scan_duration)

        # Sambungkan tombol "Karantina Semua" di dialog ke fungsi karantina
        dialog.quarantine_requested.connect(self._quarantine_batch_results)
        dialog.show_dialog()

    def _quarantine_batch_results(self, malware_results: list):
        """
        Pindahkan semua file malware yang terdeteksi ke folder karantina,
        lalu laporkan hasilnya kepada pengguna.

        File dikarantina dengan cara dipindah (bukan disalin) ke folder
        ~/.Mangodefend/Karintina/ dengan nama baru yang berisi timestamp.
        Nama file asli tetap tersimpan di dalam nama baru agar bisa diidentifikasi.

        malware_results : Daftar dict hasil scan yang hasilnya 'Malware'.
        """
        import shutil
        import time
        from pathlib import Path as _Path

        # Tentukan folder karantina di direktori home pengguna
        quarantine_dir = _Path.home() / ".Mangodefend" / "Karintina"

        # Buat folder karantina jika belum ada (parents=True: buat semua folder induk)
        quarantine_dir.mkdir(parents=True, exist_ok=True)

        success, failed = 0, 0  # Hitung berhasil dan gagal dikarantina

        for result in malware_results:
            file_path = result.get("file", {}).get("file_path", "")

            # Lewati jika path kosong atau file sudah tidak ada
            if not file_path or not _Path(file_path).exists():
                failed += 1
                continue

            try:
                src  = _Path(file_path)
                # Nama file baru: timestamp_namaasli.quarantined
                # Timestamp mencegah konflik nama jika ada file dengan nama sama
                dest = quarantine_dir / f"{int(time.time())}_{src.name}.quarantined"
                shutil.move(str(src), str(dest))  # Pindahkan file (bukan salin)
                success += 1
            except Exception:
                # Catat kegagalan tapi lanjutkan ke file berikutnya
                failed += 1

        # Tampilkan laporan hasil karantina ke pengguna
        from PySide6.QtWidgets import QMessageBox
        info = f"Karantina selesai!\n\n Berhasil: {success} file"
        if failed:
            info += f"\n Gagal: {failed} file"
        QMessageBox.information(self, "Karantina Selesai", info)

    # =================================================================
    # PROTEKSI REALTIME
    # =================================================================

    def _toggle_realtime_protection(self, enabled: bool):
        """
        Nyalakan atau matikan proteksi realtime berdasarkan permintaan dari ProtectionView.

        Jika nyalakan:
          - Panggil realtime_protection.start().
          - Perbarui status "Protected" di sidebar dan dashboard.

        Jika matikan:
          - Jalankan stop() di thread terpisah agar UI tidak membeku
            (stop() bisa memakan beberapa detik untuk menghentikan watcher file/proses).
          - Perbarui status "Unprotected" di sidebar dan dashboard.

        enabled : True = pengguna ingin mengaktifkan, False = ingin menonaktifkan.
        """
        if self.realtime_protection:
            if enabled:
                try:
                    self.realtime_protection.start()
                    self.sidebar.update_status("Protected", True)
                    self.dashboard_view.set_realtime_state(True)
                except Exception as e:
                    print(f"Failed to start protection: {e}")
                    # Jika gagal, kembalikan tampilan ke status tidak aktif
                    self.protection_view.set_protection_state(False)
                    self.dashboard_view.set_realtime_state(False)
            else:
                # ── Hentikan di thread terpisah ──
                # stop() memanggil OS API yang bisa blocking beberapa detik.
                # Jika dipanggil di thread UI, aplikasi akan terlihat "frozen" (tidak responsif).
                import threading as _threading

                def _do_stop():
                    """Hentikan proteksi realtime di thread terpisah agar UI tetap responsif."""
                    try:
                        self.realtime_protection.stop()
                    except Exception as e:
                        print(f"Failed to stop protection: {e}")

                _threading.Thread(target=_do_stop, daemon=True, name="StopProtection").start()

                # Langsung perbarui tampilan tanpa menunggu thread selesai
                self.sidebar.update_status("Unprotected", False)
                self.dashboard_view.set_realtime_state(False)
        else:
            # Engine proteksi belum diinisialisasi (main.py belum menyuntikkannya)
            self.protection_view.set_protection_state(False)
            self.dashboard_view.set_realtime_state(False)

    def _on_malware_alert(self, alert_data: dict):
        """
        Tampilkan dialog peringatan malware saat engine proteksi mendeteksi ancaman.

        Konteks:
          Engine proteksi berjalan di thread latar belakang. Ia tidak bisa langsung
          menampilkan dialog UI (Qt tidak mengizinkan). Sebagai gantinya, engine memanggil
          malware_bridge.show_alert() yang mengirim sinyal 'malware_detected' ke thread UI.
          Sinyal tersambung ke fungsi ini (_on_malware_alert) di thread UI.

        Alur:
          1. Ambil data dari alert_data.
          2. Catat ke riwayat scan di halaman scan.
          3. Tampilkan dialog peringatan dan tunggu keputusan pengguna.
          4. Kirim keputusan (karantina/izinkan) kembali ke thread background via event.
          5. Perbarui hitungan ancaman jika file dikuarantina.

        alert_data : Dict berisi info file, hasil scan, event threading, dan info proses.
        """
        file_path       = alert_data.get("file_path", "Unknown")
        scan_result     = alert_data.get("scan_result", {})

        # event dan response_holder adalah mekanisme komunikasi dua arah antar thread:
        # - response_holder: list tempat keputusan pengguna disimpan
        # - response_event : threading.Event yang di-set setelah keputusan diambil
        #   agar thread background tahu bahwa pengguna sudah merespons
        response_event  = alert_data.get("response_event")
        response_holder = alert_data.get("response_holder")

        process_pid     = alert_data.get("process_pid")
        process_name    = alert_data.get("process_name", "")

        # Ambil nama file saja dari path lengkap untuk ditampilkan di riwayat
        file_name = os.path.basename(file_path) if file_path and file_path != "Unknown" else "Unknown"

        now       = datetime.now()
        timestamp = now.strftime('%H:%M')

        # Tambahkan ke riwayat scan di halaman scan
        if self.scan_view:
            self.scan_view.add_to_history(file_name, "Malware (Realtime)", timestamp, file_path)

        # Perbarui waktu scan terakhir dan grafik aktivitas di dashboard
        self.last_scan = now
        self.dashboard_view.update_last_scan(now)
        self.dashboard_view.record_scan_activity(1, now)

        # ── Tampilkan dialog peringatan malware ──
        dialog = MalwareAlertDialog(
            file_path, scan_result, self,
            process_pid=process_pid,
            process_name=process_name,
        )

        # Tampilkan dialog dan tunggu pengguna memilih aksi (blocking di thread UI)
        result_code = dialog.exec()

        # Ambil aksi yang dipilih pengguna dari dialog
        action = dialog.get_action()

        # Ganti action jika kode hasil adalah salah satu aksi yang valid
        if result_code in (MalwareAlertDialog.ACTION_CONTINUE, MalwareAlertDialog.ACTION_KILL):
            action = result_code

        # Catat aksi pengguna ke log untuk keperluan audit
        logger.warning(
            "Realtime malware dialog action=%s for %s process=%s pid=%s",
            action,
            file_path,
            process_name,
            process_pid,
        )

        # ── Kirim keputusan kembali ke thread background ──
        # Thread background sedang menunggu keputusan ini via response_event.wait()
        if response_holder is not None:
            response_holder.append(action)  # Simpan keputusan di list bersama
        if response_event is not None:
            response_event.set()            # Beritahu thread background bahwa keputusan sudah ada

        # ── Jika pengguna memilih karantina (KILL) ──
        if action == MalwareAlertDialog.ACTION_KILL:
            # Tambah hitungan ancaman di dashboard
            self.threats_detected += 1
            self.dashboard_view.update_threats(self.threats_detected)

            # Navigasi ke halaman karantina dan muat ulang daftarnya
            def _goto_quarantine():
                self.sidebar.set_active_tab("quarantine")
                self._on_tab_changed("quarantine")
                if self.quarantine_view:
                    self.quarantine_view.load_quarantine_items()

            QTimer.singleShot(1500, _goto_quarantine)
            QTimer.singleShot(3500, lambda: self.quarantine_view.load_quarantine_items() if self.quarantine_view else None)

    # =================================================================
    # PEMBARUAN MODEL AI
    # =================================================================

    def _check_for_updates(self):
        """
        Periksa apakah ada versi model AI yang lebih baru di server.

        Menampilkan hasilnya langsung di halaman update.
        Jika model_updater belum tersedia (belum diinisialisasi), tampilkan pesan tidak tersedia.
        """
        if self.model_updater:
            try:
                has_update, latest_version = self.model_updater.check_for_updates()

                # Kirim hasil ke halaman update untuk ditampilkan ke pengguna
                self.update_view.set_check_result(has_update, latest_version)

                if has_update:
                    print(f"Update available: {latest_version}")
                else:
                    print("Already up to date")
            except Exception as e:
                print(f"Failed to check updates: {e}")
                # Tampilkan hasil "tidak ada update" jika terjadi error
                self.update_view.set_check_result(False)
        else:
            print("Model updater not available")
            self.update_view.set_check_result(False)

    def _download_update(self):
        """
        Unduh dan pasang pembaruan model AI terbaru.

        Saat ini menggunakan simulasi progress (0–100% dalam iterasi).
        TODO: Ganti dengan unduhan nyata dari server model.
        """
        if self.model_updater:
            try:
                # Simulasi unduhan: tambah 10% setiap 0.1 detik
                for progress in range(0, 101, 10):
                    self.update_view.set_download_progress(progress)
                    import time
                    time.sleep(0.1)

                print("Update installed successfully")
            except Exception as e:
                print(f"Failed to download update: {e}")
        else:
            print("Model updater not available")

    # =================================================================
    # INISIALISASI DARI MAIN.PY
    # =================================================================

    def initialize_protection(self):
        """
        Sinkronkan tampilan tombol proteksi di UI dengan status proteksi realtime
        yang sebenarnya saat aplikasi pertama dibuka.

        Masalah yang diselesaikan:
          Engine proteksi dimulai di main.py sebelum jendela ditampilkan.
          Tanpa fungsi ini, status tombol di UI mungkin tidak mencerminkan
          status engine yang sebenarnya.

        Dipanggil oleh main.py setelah mengisi self.realtime_protection.
        """
        if self.realtime_protection:
            # Tanya engine apakah sedang aktif
            is_enabled = self.realtime_protection.is_running()

            # Perbarui tampilan halaman protection jika sudah dibuat
            if self.protection_view:
                self.protection_view.set_protection_state(is_enabled)

            # Perbarui status di sidebar
            if is_enabled:
                self.sidebar.update_status("Protected", True)
            else:
                self.sidebar.update_status("Unprotected", False)

            # Perbarui status di dashboard
            self.dashboard_view.set_realtime_state(is_enabled)

    def closeEvent(self, event):
        """
        Dipanggil saat pengguna menekan tombol X (tutup) jendela.

        Perilaku: TIDAK benar-benar menutup aplikasi.
        Sebagai gantinya, batalkan event penutupan dan sembunyikan jendela ke system tray.
        Aplikasi tetap berjalan di latar belakang untuk proteksi realtime.

        Ini adalah pola umum untuk aplikasi antivirus/antimalware yang perlu
        terus berjalan di latar belakang meskipun jendela ditutup.
        """
        self._cancel_scan()  # Hentikan scan yang sedang berjalan (jika ada)
        event.ignore()       # Batalkan event penutupan (tidak benar-benar tutup)
        self.hide()          # Sembunyikan jendela ke system tray
