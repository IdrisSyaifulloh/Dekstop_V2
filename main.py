"""
MangoDefend - Aplikasi Perlindungan Malware berbasis AI
Titik masuk utama aplikasi desktop.

File ini adalah "pintu gerbang" pertama yang dijalankan saat pengguna
membuka MangoDefend. Tugasnya adalah:
1. Meminta hak Administrator (diperlukan untuk memantau file sistem)
2. Membuat jendela aplikasi Qt
3. Menampilkan splash screen saat aplikasi sedang memuat
4. Menginisialisasi semua layanan latar belakang
5. Menjaga aplikasi tetap berjalan di system tray saat jendela ditutup
"""
import sys
import os
import logging

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt
from ui.modern_window import ModernWindow
from core.config_manager import get_config
from build_info import BUILD_TAG

# Logger untuk mencatat semua kejadian penting di modul utama ini
logger = logging.getLogger(__name__)


def _is_windows_admin() -> bool:
    """
    Periksa apakah aplikasi saat ini berjalan dengan hak Administrator di Windows.

    Hak Administrator diperlukan agar aplikasi bisa memantau perubahan file
    di folder sistem seperti System32, Program Files, dan AppData.
    Tanpa hak ini, proteksi real-time tidak bisa bekerja penuh.

    Mengembalikan True jika:
    - Sistem operasinya bukan Windows (Linux/macOS tidak perlu cek ini), ATAU
    - Aplikasi sudah berjalan sebagai Administrator
    """
    if sys.platform != "win32":
        # Di Linux dan macOS, anggap selalu punya izin yang cukup
        return True

    try:
        import ctypes
        # IsUserAnAdmin() adalah fungsi Windows API yang mengembalikan 1 jika admin
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        # Jika pemeriksaan gagal karena alasan apapun, anggap bukan admin (aman)
        return False


def ensure_windows_admin() -> bool:
    """
    Minta izin Administrator jika aplikasi belum dijalankan sebagai admin.

    Cara kerjanya menggunakan ShellExecuteW dengan verb "runas":
    - "runas" adalah perintah Windows untuk "jalankan sebagai pengguna lain"
    - Kata kunci ini memicu Windows untuk menampilkan dialog UAC (User Account Control)
      — kotak dialog abu-abu yang muncul dan bertanya "Izinkan aplikasi ini?"
    - Jika pengguna klik "Ya", Windows meluncurkan proses baru dengan hak Administrator
    - Proses lama (tanpa admin) ini kemudian perlu ditutup agar tidak dobel

    Mengembalikan:
    - True  : aplikasi sudah/tidak perlu menjadi admin, lanjutkan eksekusi normal
    - False : proses anak berhasil diluncurkan, proses ini harus segera keluar

    Melempar RuntimeError jika:
    - Pengguna menolak dialog UAC (kode error 1223)
    - ShellExecuteW gagal karena alasan lain
    """
    # Jika bukan Windows atau sudah admin, tidak perlu melakukan apapun
    if sys.platform != "win32" or _is_windows_admin():
        return True

    import ctypes

    # Tentukan apa yang akan dijalankan:
    # - Jika dikompilasi sebagai .exe (frozen=True): jalankan .exe itu sendiri
    # - Jika dijalankan sebagai skrip .py: jalankan interpreter Python dengan skrip ini
    script = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)

    # Siapkan argumen tambahan yang perlu diteruskan ke proses baru
    # (hanya relevan jika bukan .exe, karena argumen diteruskan terpisah dari skrip)
    params = ""
    if not getattr(sys, "frozen", False):
        # Gabungkan semua argumen baris perintah dengan tanda kutip di sekitar setiap argumen
        params = " ".join(f'"{arg}"' for arg in sys.argv[1:])

    # Panggil ShellExecuteW — fungsi Windows API untuk membuka file/program
    # Parameter:
    # - None       : tidak ada jendela induk
    # - "runas"    : verb yang meminta UAC / hak Administrator
    # - sys.executable : program yang dijalankan (python.exe atau .exe aplikasi)
    # - f'"{script}" {params}' : argumen baris perintah untuk program tersebut
    # - os.path.dirname(script) : folder kerja awal untuk proses baru
    # - 1          : tampilkan jendela proses baru secara normal (SW_SHOWNORMAL)
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        f'"{script}" {params}'.strip(),
        os.path.dirname(script) or None,
        1,
    )

    # ShellExecuteW mengembalikan nilai > 32 jika berhasil meluncurkan proses baru
    # Nilai <= 32 menunjukkan kode error tertentu
    if result <= 32:
        if result == 1223:
            # Kode 1223 = ERROR_CANCELLED: pengguna mengklik "Tidak" di dialog UAC
            raise RuntimeError(
                "Startup dibatalkan karena izin Administrator tidak diberikan."
            )
        # Error lain yang tidak diketahui — sertakan kode error untuk diagnosis
        raise RuntimeError(
            f"Gagal menjalankan MangoDefend sebagai Administrator (kode: {result})."
        )

    # Proses baru berhasil diluncurkan dengan hak admin
    # Kembalikan False agar pemanggil tahu proses ini harus segera keluar
    return False


def _on_malware_detected(file_path: str, scan_result: dict):
    """
    Tangani kejadian ketika malware terdeteksi oleh proteksi real-time.

    Fungsi ini dipanggil oleh RealtimeProtection setiap kali sebuah file
    baru yang masuk ke komputer terdeteksi sebagai malware.

    Alur notifikasi:
    1. Catat peringatan ke file log (untuk arsip dan investigasi)
    2. Impor NotificationManager (diimpor di sini agar startup lebih cepat)
    3. Tampilkan pop-up peringatan di layar pengguna

    Kesalahan dalam menampilkan notifikasi sengaja tidak dihentikan
    agar deteksi malware tetap tercatat di log meski pop-up gagal.
    """
    # Catat ke log sebagai peringatan (level WARNING agar mudah ditemukan)
    logger.warning(
        "MALWARE DETECTED: %s — result: %s",
        file_path,
        scan_result.get('result')
    )

    try:
        # Impor di sini (bukan di atas) agar modul tidak dimuat saat startup
        # — teknik "lazy import" untuk mempercepat waktu muat awal aplikasi
        from core.notification_manager import NotificationManager
        notif = NotificationManager()

        # Tampilkan notifikasi pop-up di sudut layar dengan detail file berbahaya
        notif.show_malware_alert(
            file_path=file_path,
            file_name=os.path.basename(file_path),  # Hanya nama file, tanpa folder
            threat_level="High"                      # Selalu anggap ancaman tinggi
        )
    except Exception as e:
        # Catat error tapi jangan hentikan aplikasi — deteksi sudah tercatat di log
        logger.error("Failed to show malware notification: %s", e)


def _init_services(window, config):
    """
    Jalankan semua layanan latar belakang di thread terpisah.

    Mengapa di thread terpisah?
    - Inisialisasi layanan (memuat model, membuka koneksi, dll.) bisa memakan
      waktu beberapa detik
    - Jika dijalankan di thread utama, jendela aplikasi tidak akan muncul
      hingga semua layanan selesai diinisialisasi
    - Dengan thread terpisah, splash screen muncul lebih dulu, lalu layanan
      disiapkan di belakang layar tanpa pengguna menunggu

    Layanan yang diinisialisasi:
    - Proteksi real-time: memantau file baru di folder Downloads, Desktop, dll.
    - Pembaruan model: siap memeriksa dan mengunduh model AI terbaru
    """
    import threading

    def _run():
        """
        Fungsi yang dijalankan di thread terpisah untuk menginisialisasi semua layanan.

        Setiap layanan diinisialisasi dalam blok try/except tersendiri sehingga
        jika satu layanan gagal, layanan lainnya tetap bisa berjalan normal.
        """
        # Variabel untuk menyimpan referensi layanan yang berhasil dibuat
        realtime_protection = None
        model_updater = None

        # ─── LAYANAN 1: PROTEKSI REAL-TIME ───────────────────────────────────
        # Proteksi real-time memantau file secara langsung saat masuk ke komputer
        try:
            from core.realtime_protection import RealtimeProtection

            # Baca konfigurasi proteksi real-time dari file config.ini
            # scan_delay: berapa detik menunggu sebelum memindai file baru
            # (memberi waktu agar file selesai ditulis ke disk sebelum dipindai)
            scan_delay = config.get_int('RealtimeProtection', 'scan_delay', 5)

            # max_queue: maksimal file yang mengantre untuk dipindai
            max_queue = config.get_int('RealtimeProtection', 'max_queue_size', 5000)

            import os as _os
            import ctypes as _ctypes

            # Deteksi semua drive lokal yang tersedia (C:\, D:\, dst.)
            # GetLogicalDrives mengembalikan bitmask: bit ke-2 = C:, bit ke-3 = D:, dst.
            _drives = []
            if _os.name == "nt":
                _bitmask = _ctypes.windll.kernel32.GetLogicalDrives()
                for _i in range(26):
                    if _bitmask & (1 << _i):
                        _drive = f"{chr(65 + _i)}:\\"
                        # Tipe 3 = fixed (HDD/SSD), tipe 2 = removable (flashdisk)
                        _dtype = _ctypes.windll.kernel32.GetDriveTypeW(_drive)
                        if _dtype in (2, 3) and _os.path.exists(_drive):
                            _drives.append(_drive)
            else:
                _drives = ["/"]  # Linux/Mac: pantau dari root

            # Pantau seluruh drive — watchdog pakai recursive=True jadi semua subfolder ikut terpantau
            # _get_default_paths() di RealtimeProtection juga melakukan hal sama sebagai fallback
            _monitored = _drives

            # Buat objek proteksi real-time dengan semua pengaturan yang sudah disiapkan
            realtime_protection = RealtimeProtection(
                monitored_paths=_monitored,
                scan_delay=scan_delay,
                max_queue_size=max_queue,
                # Callback yang dipanggil ketika malware ditemukan
                on_malware_detected=_on_malware_detected
            )

            # Baca ekstensi file yang dikecualikan dari pemindaian (whitelist)
            # Misalnya: .txt, .log, .md adalah file teks yang tidak berbahaya
            whitelist_ext = config.get(
                'RealtimeProtection',
                'whitelist_extensions',
                '.txt,.log,.md'
            )
            # Pisahkan string koma menjadi daftar ekstensi dan tambahkan satu per satu
            for ext in whitelist_ext.split(','):
                realtime_protection.whitelist_extensions.add(ext.strip())

            # Hubungkan jembatan sinyal malware ke jendela utama aplikasi
            # agar peringatan bisa ditampilkan di dalam UI (bukan hanya pop-up)
            realtime_protection.malware_bridge = window.malware_bridge

            # Mulai atau hanya siapkan proteksi sesuai pengaturan
            if config.get_bool('RealtimeProtection', 'enabled', False):
                # Langsung mulai memantau jika diaktifkan di konfigurasi
                realtime_protection.start()
                logger.info("Real-time protection auto-started")
                # Jangan rescan semua file lama saat startup.
                # Realtime harus fokus pada file baru/copy/rename agar alert tidak tertahan
                # oleh antrean dan dialog dari file lama di seluruh drive.
            else:
                # Siapkan saja tapi jangan mulai — pengguna bisa aktifkan manual
                logger.info("Real-time protection ready (disabled)")
        except Exception as e:
            logger.error("Real-time protection error: %s", e)

        # ─── LAYANAN 2: PEMBARUAN MODEL AI ────────────────────────────────────
        # ModelUpdater memeriksa apakah ada versi model yang lebih baru di server
        try:
            if config.get_bool('ModelUpdate', 'enabled', True):
                from core.model_updater import ModelUpdater

                # Baca URL server tempat model AI tersedia untuk diunduh
                model_api_url = config.get(
                    'ModelUpdate',
                    'model_api_url',
                    'http://localhost:8000'
                )

                # Buat objek pembaruan model (belum memeriksa pembaruan, hanya siap)
                model_updater = ModelUpdater(backend_url=model_api_url)
                logger.info("Model updater initialized")
        except Exception as e:
            logger.error("Model updater error: %s", e)

        # ─── HUBUNGKAN SEMUA LAYANAN KE JENDELA UTAMA ─────────────────────────
        # Setelah semua layanan berhasil dibuat, hubungkan ke jendela utama
        # agar UI bisa mengontrol dan memantau layanan-layanan tersebut
        if realtime_protection:
            window.realtime_protection = realtime_protection
            # Panggil metode inisialisasi di jendela agar tombol dan status diperbarui
            window.initialize_protection()

        if model_updater:
            window.model_updater = model_updater

        # Simpan referensi ke proteksi real-time di window agar tidak dihapus
        # oleh garbage collector Python ketika variabel lokal di sini hilang
        window._realtime_protection_ref = realtime_protection

        logger.info("All services initialized")

    # Buat dan mulai thread daemon untuk menjalankan _run() di latar belakang
    # daemon=True berarti thread ini otomatis berhenti ketika aplikasi utama ditutup
    t = threading.Thread(target=_run, daemon=True, name="ServiceInit")
    t.start()
    return t


def main():
    """
    Titik masuk utama aplikasi — fungsi pertama yang dijalankan saat program dibuka.

    Urutan eksekusi:
    1. Siapkan logging (pencatatan kejadian ke file)
    2. Minta hak Administrator jika belum punya
    3. Buat objek aplikasi Qt
    4. Tampilkan splash screen
    5. Buat jendela utama
    6. Buat ikon system tray
    7. Tunggu splash selesai, lalu tampilkan jendela dan mulai layanan
    8. Masuk ke event loop Qt (aplikasi "hidup" di sini)
    9. Saat aplikasi ditutup, hentikan semua layanan dengan rapi
    """
    # ─── LANGKAH 1: SETUP LOGGING ─────────────────────────────────────────────
    # Buat folder log di folder home pengguna (~/.Mangodefend/)
    log_dir  = os.path.join(os.path.expanduser("~"), ".Mangodefend")
    os.makedirs(log_dir, exist_ok=True)  # Buat folder jika belum ada

    # Tentukan lokasi file log
    log_file = os.path.join(log_dir, "mangodefend.log")

    # Konfigurasi logging: catat ke file DAN tampilkan di konsol sekaligus
    logging.basicConfig(
        level=logging.INFO,  # Catat semua pesan level INFO ke atas
        # Format: waktu [level] nama_modul: pesan
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            # Handler 1: Tulis log ke file (utf-8 agar mendukung karakter Indonesia)
            logging.FileHandler(log_file, encoding="utf-8"),
            # Handler 2: Tampilkan log di konsol (berguna saat pengembangan)
            logging.StreamHandler(),
        ]
    )
    logger.info("MangoDefend build tag: %s", BUILD_TAG)

    # ─── LANGKAH 2: MINTA HAK ADMINISTRATOR ──────────────────────────────────
    try:
        if not ensure_windows_admin():
            # ensure_windows_admin() mengembalikan False berarti proses baru (dengan
            # hak admin) sudah diluncurkan — proses ini (tanpa admin) harus keluar
            return 0
    except RuntimeError as exc:
        # Pengguna menolak UAC atau terjadi error saat meminta admin
        logger.error("%s", exc)
        if sys.platform == "win32":
            try:
                import ctypes
                # Tampilkan kotak dialog error Windows agar pengguna tahu ada masalah
                # Parameter: jendela induk=None, pesan, judul, ikon error=0x10
                ctypes.windll.user32.MessageBoxW(None, str(exc), "MangoDefend", 0x10)
            except Exception:
                pass
        return 1  # Keluar dengan kode error 1

    # ─── LANGKAH 3: BUAT OBJEK APLIKASI QT ──────────────────────────────────
    # Atur kebijakan penskalaan DPI agar tampilan tajam di layar HiDPI/4K
    # PassThrough berarti Qt mengikuti faktor skala OS secara presisi
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Buat objek utama aplikasi Qt — harus ada sebelum membuat widget apapun
    app = QApplication(sys.argv)
    app.setApplicationName("MangoDefend - RMAV Desktop")
    app.setOrganizationName("MangoDefend")

    # Pasang ikon aplikasi jika file ikon tersedia
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "mango_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # ─── MUAT KONFIGURASI ─────────────────────────────────────────────────────
    # Muat konfigurasi aplikasi dari file config.ini (atau buat jika belum ada)
    config = get_config()

    # ─── LANGKAH 4: TAMPILKAN SPLASH SCREEN ──────────────────────────────────
    # Splash screen ditampilkan segera agar pengguna tahu aplikasi sedang dimuat
    # (bukan karena hang/tidak merespons)
    from ui.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()  # Tampilkan splash screen secepatnya

    # ─── LANGKAH 5: SIAPKAN JENDELA UTAMA ────────────────────────────────────
    # Buat jendela utama tapi belum ditampilkan — akan muncul setelah splash selesai
    window = ModernWindow()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))

    # ─── LANGKAH 6: BUAT IKON SYSTEM TRAY ────────────────────────────────────
    # Agar aplikasi tetap berjalan di latar belakang saat jendela ditutup,
    # kita buat ikon di system tray (pojok kanan bawah taskbar Windows)
    # setQuitOnLastWindowClosed(False) mencegah aplikasi mati saat jendela ditutup
    app.setQuitOnLastWindowClosed(False)

    # Buat objek ikon tray
    tray = QSystemTrayIcon(app)
    tray_icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
    tray.setIcon(tray_icon)
    # Tooltip muncul saat kursor diarahkan ke ikon tray
    tray.setToolTip("MangoDefend - AI Malware Protection")

    # Buat menu klik-kanan untuk ikon tray
    tray_menu = QMenu()
    act_show = QAction("Buka MangoDefend", tray_menu)  # Tombol buka jendela
    act_quit = QAction("Keluar", tray_menu)             # Tombol tutup aplikasi
    tray_menu.addAction(act_show)
    tray_menu.addSeparator()  # Garis pemisah antar menu
    tray_menu.addAction(act_quit)
    tray.setContextMenu(tray_menu)

    def _tray_activated(reason):
        """
        Buka kembali jendela utama ketika pengguna double-klik ikon tray.

        ActivationReason.DoubleClick berarti pengguna klik dua kali — ini
        cara paling umum yang diharapkan pengguna untuk membuka kembali aplikasi
        yang tersembunyi di tray.
        """
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            window.show()         # Tampilkan jendela yang tersembunyi
            window.raise_()       # Angkat jendela ke depan semua jendela lain
            window.activateWindow()  # Berikan fokus keyboard ke jendela ini

    # Hubungkan aksi tombol tray ke fungsi yang sesuai
    # Lambda digunakan untuk memanggil beberapa metode dalam satu baris
    act_show.triggered.connect(
        lambda: (window.show(), window.raise_(), window.activateWindow())
    )
    act_quit.triggered.connect(app.quit)       # Tombol "Keluar" menutup aplikasi
    tray.activated.connect(_tray_activated)    # Double-klik ikon tray membuka jendela
    tray.show()  # Tampilkan ikon di system tray

    # ─── LANGKAH 6.5: DAFTARKAN AUTO-START KE REGISTRY WINDOWS ─────────────────
    # Jika config mengizinkan, daftarkan MangoDefend agar otomatis jalan saat Windows menyala
    try:
        from utils.startup_manager import enable_startup, disable_startup, is_startup_enabled
        _startup_on_boot = config.get_bool("App", "startup_on_boot", True)
        _currently_registered = is_startup_enabled()

        if _startup_on_boot and not _currently_registered:
            # Belum terdaftar padahal config minta aktif — daftarkan sekarang
            enable_startup()
        elif not _startup_on_boot and _currently_registered:
            # Sudah terdaftar tapi config minta nonaktif — hapus dari registry
            disable_startup()
    except Exception as _e:
        logger.warning(f"Tidak bisa mengatur auto-start: {_e}")

    # ─── LANGKAH 7: HUBUNGKAN SPLASH KE INISIALISASI LAYANAN ─────────────────
    def _on_splash_finished():
        """
        Tampilkan jendela utama dan mulai inisialisasi layanan latar belakang.

        Dipanggil oleh splash screen melalui sinyal 'finished' setelah
        animasi splash selesai. Dengan cara ini, jendela utama tidak muncul
        sebelum splash selesai ditampilkan.
        """
        window.show()                   # Tampilkan jendela utama
        _init_services(window, config)  # Mulai semua layanan di thread terpisah

    # Hubungkan sinyal selesainya splash ke fungsi di atas
    splash.finished.connect(_on_splash_finished)

    # ─── LANGKAH 8: MASUK KE EVENT LOOP QT ──────────────────────────────────
    # app.exec() adalah "jantung" aplikasi — program tidak keluar dari sini
    # hingga pengguna menutup aplikasi. Semua klik tombol, sinyal, dan timer
    # diproses di dalam event loop ini.
    exit_code = app.exec()

    # ─── LANGKAH 9: BERSIHKAN LAYANAN SAAT APLIKASI DITUTUP ─────────────────
    logger.info("Shutting down services...")

    # Hentikan proteksi real-time agar tidak ada thread yang tertinggal
    if getattr(window, '_realtime_protection_ref', None):
        window._realtime_protection_ref.stop()

    # Kembalikan kode keluar ke sistem operasi (0 = sukses, non-0 = error)
    return exit_code


# ─── TITIK MASUK PROGRAM ─────────────────────────────────────────────────────
# Blok ini hanya berjalan jika file ini dijalankan langsung (python main.py)
# Tidak berjalan jika file ini diimpor oleh file lain
if __name__ == "__main__":
    # sys.exit() memastikan kode keluar dari main() diteruskan ke sistem operasi
    sys.exit(main())
