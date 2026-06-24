"""
Modul Perlindungan Real-Time MangoDefend.

Modul ini menjaga komputer secara aktif: setiap file baru yang muncul
atau proses baru yang mau dijalankan langsung diperiksa oleh model AI.
Jika terdeteksi sebagai malware, file/proses tersebut diblokir sebelum
sempat membahayakan sistem.
"""

# ================================================================
# Import pustaka standar Python yang dibutuhkan
# ================================================================
import os           # Untuk operasi file dan folder (cek ada/tidak, baca path, dll.)
import sys          # Untuk cek sistem operasi (Windows atau bukan)
import time         # Untuk fungsi waktu: jeda, hitung durasi, timestamp
import ctypes       # Untuk memanggil fungsi Windows secara langsung (level rendah)
import threading    # Untuk menjalankan banyak pekerjaan secara bersamaan (multi-thread)
import logging      # Untuk mencatat log/pesan debug ke file atau konsol
import shutil       # Untuk memindahkan atau menyalin file (dipakai saat karantina)
from pathlib import Path            # Cara modern Python untuk bekerja dengan path file/folder
from typing import Set, Callable, Optional, List  # Tipe data untuk type hints (petunjuk tipe)
from queue import PriorityQueue, Empty  # Antrean prioritas thread-safe untuk file scan

from .scanner import MalwareScanner  # Import scanner AI dari modul scanner di folder yang sama

# Buat logger khusus untuk modul ini agar pesannya bisa dibedakan dari modul lain
logger = logging.getLogger(__name__)

# ================================================================
# Persiapan Windows API
# Bagian ini hanya berjalan di Windows — mengambil fungsi dari DLL sistem
# ================================================================

if sys.platform == "win32":
    # Import tipe data khusus Windows
    import ctypes.wintypes

    # kernel32 = DLL inti Windows untuk operasi file, proses, memori
    kernel32 = ctypes.windll.kernel32
    # ntdll = DLL level sangat rendah Windows, berisi fungsi suspend/resume proses
    ntdll    = ctypes.windll.ntdll

    # Konstanta untuk membuka file — artinya: buka untuk dibaca saja
    GENERIC_READ             = 0x80000000
    # Konstanta untuk cara membuka file — artinya: file harus sudah ada
    OPEN_EXISTING            = 3
    # Atribut file biasa (bukan hidden, bukan system)
    FILE_ATTRIBUTE_NORMAL    = 0x00000080
    # Flag khusus agar bisa membuka folder sebagai file (untuk backup)
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    # Nilai penanda jika gagal membuka file (handle tidak valid)
    INVALID_HANDLE_VALUE     = ctypes.wintypes.HANDLE(-1).value

    # Mode berbagi file: tidak berbagi sama sekali (kunci eksklusif)
    FILE_SHARE_NONE          = 0x00000000
    # Mode berbagi file: izinkan proses lain membaca, tapi tidak menulis
    FILE_SHARE_READ          = 0x00000001

    # Izin untuk suspend dan resume proses
    PROCESS_SUSPEND_RESUME    = 0x0800
    # Izin untuk membaca informasi proses (nama exe, dll.)
    PROCESS_QUERY_INFORMATION = 0x0400
    # Izin untuk membaca memori proses
    PROCESS_VM_READ           = 0x0010
    # Gabungan izin: suspend + baca info + baca memori — dipakai saat menangkap proses baru
    PROCESS_SUSPEND_AND_QUERY = 0x0800 | 0x0400 | 0x0010
    # Kode sukses dari Windows API — jika fungsi berhasil, nilainya 0
    STATUS_SUCCESS            = 0


# ================================================================
# Kunci File Windows (FileLock)
# Digunakan untuk "memblokir" file agar tidak bisa dibuka/dijalankan
# selama proses pemindaian berlangsung
# ================================================================

class FileLock:
    """
    Mengunci sebuah file agar tidak bisa dibuka atau dijalankan
    oleh program lain selama proses pemindaian berlangsung.

    Selama kunci aktif, file tersebut "diblokir" — tidak ada yang
    bisa mengaksesnya sampai kunci dilepas.
    """

    def __init__(self, file_path: str):
        # Simpan path file yang akan dikunci
        self.file_path = file_path
        # Handle = "pegangan" ke file yang dibuka oleh Windows API, awalnya kosong
        self._handle = None
        # Status apakah file sedang terkunci atau tidak
        self._locked = False

    def acquire(self, max_retries: int = 5, retry_delay: float = 0.3) -> bool:
        """
        Mengunci file. Jika file sedang dipakai program lain,
        akan mencoba beberapa kali sebelum menyerah.

        Mengembalikan True jika berhasil dikunci, False jika gagal.
        """
        # Kunci file hanya bisa dilakukan di Windows
        if sys.platform != "win32":
            return False  # Di sistem selain Windows, langsung gagal

        # Coba kunci file sebanyak max_retries kali
        for attempt in range(max_retries):
            try:
                # Kunci file: izinkan proses lain membaca (termasuk scanner sendiri),
                # tapi blokir eksekusi dan penulisan
                handle = kernel32.CreateFileW(
                    self.file_path,         # Path file yang akan dikunci
                    GENERIC_READ,           # Hanya perlu izin baca
                    FILE_SHARE_READ,        # Proses lain boleh membaca, tidak boleh write/execute
                    None,                   # Security attributes (pakai default)
                    OPEN_EXISTING,          # File harus sudah ada
                    FILE_ATTRIBUTE_NORMAL,  # Atribut file biasa
                    None                    # Template file (tidak dipakai)
                )

                # Jika handle valid (bukan -1), berarti file berhasil dikunci
                if handle != INVALID_HANDLE_VALUE:
                    self._handle = handle   # Simpan handle untuk dipakai saat melepas kunci
                    self._locked = True     # Tandai bahwa file sudah terkunci
                    return True             # Laporkan sukses

                # Jika gagal, cek kode error dari Windows
                error_code = kernel32.GetLastError()
                if error_code == 32:  # Error 32 = ERROR_SHARING_VIOLATION (file sedang dipakai)
                    time.sleep(retry_delay)  # Tunggu sebentar lalu coba lagi
                    continue
                else:
                    # Error lain (mis. file tidak ada) — tidak perlu dicoba lagi
                    return False

            except Exception as e:
                # Jika ada error tak terduga, catat dan coba lagi
                logger.debug(f"Lock attempt {attempt + 1} failed for {self.file_path}: {e}")
                time.sleep(retry_delay)  # Tunggu sebelum percobaan berikutnya

        # Semua percobaan habis, gagal mengunci
        return False

    def release(self):
        """
        Melepas kunci file sehingga file bisa diakses kembali secara normal.
        """
        # Hanya lepas kunci jika handle ada dan file memang sedang terkunci
        if self._handle and self._locked:
            try:
                kernel32.CloseHandle(self._handle)  # Tutup handle = lepas kunci di Windows
            except Exception:
                pass  # Abaikan error saat menutup handle
            finally:
                # Bersihkan status meski terjadi error
                self._handle = None    # Kosongkan handle
                self._locked = False   # Tandai sudah tidak terkunci

    @property
    def is_locked(self) -> bool:
        """Mengembalikan True jika file sedang dalam kondisi terkunci."""
        return self._locked

    def __enter__(self):
        # Dipakai saat menggunakan sintaks "with FileLock(...) as lock:"
        # Otomatis mengunci saat masuk blok with
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Otomatis melepas kunci saat keluar dari blok with (meski terjadi error)
        self.release()
        return False  # False = tidak menelan exception, tetap disebarkan ke atas


# ================================================================
# Daftar Ekstensi File
# ================================================================

# Ekstensi yang TIDAK perlu dipindai — file media, teks, konfigurasi, dll.
# File-file ini sangat jarang (hampir tidak pernah) mengandung malware
SKIP_EXTENSIONS = {
    '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',   # Video
    '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma',            # Audio
    '.txt', '.md', '.csv', '.json', '.xml', '.yaml', '.yml', '.ini', '.cfg',  # Teks/konfigurasi
    '.log', '.html', '.css',                                     # Log dan web
    '.ttf', '.otf', '.woff', '.woff2',                          # Font
    '.tmp', '.temp', '.lock', '.gitignore', '.gitattributes',   # File sementara/git
    '.svg', '.ico',                                              # Ikon/gambar vektor
}

# Ekstensi yang WAJIB dipindai — bisa mengandung kode berbahaya
# Ini adalah ekstensi yang paling sering digunakan oleh malware
DANGEROUS_EXTENSIONS = {
    '.exe', '.dll', '.scr', '.bat', '.cmd',   # Program dan skrip Windows
    '.ps1', '.vbs', '.js', '.jar', '.msi',    # Skrip (PowerShell, VBScript, JavaScript, Java, Installer)
    '.com', '.pif', '.wsf', '.hta', '.cpl', '.sys',  # Tipe program Windows lainnya
    '.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp',  # Gambar (bisa menyembunyikan malware)
    '.zip', '.rar', '.7z',                    # Arsip terkompresi
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',  # Dokumen Office
    '.bin', '.dat', '.iso',                   # File biner/image disk
    '.file',                                  # Ekstensi generik
}

# Nama folder yang DILEWATI saat memindai — folder sistem Windows yang tidak boleh diganggu
# Huruf kecil semua karena pengecekan dilakukan case-insensitive
EXCLUDED_DIR_NAMES = {
    '$recycle.bin', '$windows.~bt', '$windows.~ws',      # Folder tersembunyi Windows
    'system volume information', 'windows',               # Folder sistem inti
    'program files', 'program files (x86)', 'programdata',  # Folder program yang sudah terpercaya
    'recovery', 'appdata',                                # Recovery dan data aplikasi
    '__pycache__', 'venv', '.venv', '.git', 'node_modules',  # Folder pengembangan
}

# Prioritas antrean scan. Angka lebih kecil diproses lebih dulu oleh PriorityQueue.
SCAN_PRIORITY_REALTIME = -10  # File baru/copy/rename/ubah dari watchdog selalu paling depan.
SCAN_PRIORITY_PRESCAN = 5     # File lama dari prescan/rescan diproses belakangan.


# ================================================================
# KELAS UTAMA — RealtimeProtection
# ================================================================

class RealtimeProtection:
    """
    Sistem perlindungan real-time MangoDefend.

    Kelas ini bertugas memantau komputer secara terus-menerus:
    - Setiap file baru yang muncul di folder yang dipantau langsung dikunci
      dan dipindai oleh model AI sebelum bisa dibuka.
    - Setiap program baru yang coba dijalankan langsung dibekukan dan
      dipindai sebelum sempat mengeksekusi kodenya.

    Jika terdeteksi sebagai malware, pengguna akan ditanya apakah
    file/proses tersebut harus dikarantina atau diizinkan.
    """

    def __init__(
        self,
        monitored_paths: Optional[List[str]] = None,  # Folder yang akan dipantau
        scan_delay: int = 1,                           # Jeda minimal sebelum scan (detik)
        max_queue_size: int = 10000,                   # Maks file dalam antrean scan
        on_malware_detected: Optional[Callable] = None,  # Fungsi callback saat malware ditemukan
        quarantine_dir: Optional[str] = None,          # Folder karantina
    ):
        """
        Menyiapkan semua komponen perlindungan real-time.
        """
        # Simpan daftar folder yang akan dipantau (jika kosong, semua drive dipantau)
        self.monitored_paths    = monitored_paths
        # Pastikan jeda scan minimal 1 detik agar tidak membebani CPU
        self.scan_delay         = max(scan_delay, 1)
        # Batasi ukuran antrean maksimal 10.000 agar tidak habis memori
        self.max_queue_size     = min(max_queue_size, 10000)
        # Fungsi yang dipanggil saat malware ditemukan (opsional, untuk notifikasi)
        self.on_malware_detected = on_malware_detected
        # Jembatan ke UI untuk menampilkan dialog peringatan malware
        self.malware_bridge     = None

        # Tentukan folder karantina: pakai yang diberikan, atau buat default di home user
        if quarantine_dir:
            self.quarantine_dir = Path(quarantine_dir)
        else:
            # Default: C:\Users\NamaUser\.Mangodefend\Karintina
            self.quarantine_dir = Path.home() / ".Mangodefend" / "Karintina"

        # Buat instance scanner AI untuk memindai file
        self.scanner = MalwareScanner()

        # Status apakah perlindungan sedang aktif
        self.running  = False
        # Mode perlindungan yang sedang berjalan ("none", "pseudo-blocking", dll.)
        self.mode     = "none"
        # Daftar semua thread yang sedang berjalan (scan worker, prescan, dll.)
        self._scan_threads: List[threading.Thread] = []
        # Observer watchdog yang memantau perubahan file
        self._observer      = None
        # Antrean file yang menunggu untuk dipindai
        self._scan_queue    = None
        # Kamus file yang sedang dikunci: {path_file: objek_FileLock}
        self._active_locks: dict = {}
        # Kunci mutex untuk mengakses _active_locks secara aman dari banyak thread
        self._lock_mutex    = threading.Lock()

        # Statistik perlindungan yang ditampilkan di dashboard UI
        self.stats = {
            "files_scanned": 0,        # Total file yang sudah dipindai
            "malware_detected": 0,     # Total malware yang ditemukan
            "files_blocked": 0,        # Total file yang berhasil dikunci
            "files_quarantined": 0,    # Total file yang dikarantina
            "processes_suspended": 0,  # Total proses yang dibekukan untuk diperiksa
            "processes_killed": 0,     # Total proses malware yang dimatikan
            "start_time": None,        # Waktu perlindungan mulai aktif
            "mode": "none"             # Mode perlindungan saat ini
        }

        # Event untuk menghentikan semua thread dengan rapi saat proteksi dimatikan
        self._shutdown_event    = threading.Event()
        # Cache file yang sudah dipindai dan dinyatakan aman — agar tidak dipindai berulang
        self.scan_cache: Set[str] = set()
        # Berapa lama (detik) entri cache dianggap valid sebelum dibersihkan
        self.cache_ttl          = 300
        # Ekstensi file yang masuk daftar putih (tidak perlu dipindai)
        self.whitelist_extensions: Set[str] = set()
        # Set PID proses yang sudah diketahui (untuk mendeteksi proses baru)
        self._known_pids: Set[int] = set()
        # PID yang sudah ditangani oleh WMI/polling agar tidak diproses dua kali.
        self._handled_pids: Set[int] = set()
        self._handled_pids_lock = threading.Lock()

        logger.info("RealtimeProtection initialized")

    def _cache_key(self, file_path: str) -> str:
        """Buat kunci cache yang konsisten untuk Windows agar path beda kapital tetap dianggap sama."""
        try:
            return os.path.normcase(os.path.abspath(file_path))
        except Exception:
            return os.path.normcase(str(file_path))

    def _cache_contains(self, file_path: str) -> bool:
        """Cek apakah file sudah ada di cache aman."""
        return self._cache_key(file_path) in self.scan_cache

    def _cache_add(self, file_path: str):
        """Masukkan file ke cache aman dengan path yang sudah dinormalisasi."""
        self.scan_cache.add(self._cache_key(file_path))

    def _cache_discard(self, file_path: str):
        """Hapus file dari cache aman dengan path yang sudah dinormalisasi."""
        self.scan_cache.discard(self._cache_key(file_path))

    # ================================================================
    # MULAI / BERHENTI
    # ================================================================

    def start(self):
        """
        Mengaktifkan perlindungan real-time.

        Memulai pemantauan file sistem dan proses secara bersamaan.
        Folder karantina dibuat otomatis jika belum ada.
        """
        # Cek apakah perlindungan sudah berjalan — hindari double-start
        if self.running:
            logger.warning("Protection already running")
            return

        # Tandai bahwa perlindungan sedang aktif
        self.running = True
        # Catat waktu mulai untuk menghitung uptime di dashboard
        self.stats["start_time"] = time.time()
        # Buat folder karantina jika belum ada (parents=True = buat folder induk juga)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        # Mulai pemantauan file baru (watchdog + kunci file)
        self._start_watchdog_mode()
        # Mulai pemantauan proses baru (WMI atau polling)
        self._start_process_monitor()

    def stop(self):
        """
        Mematikan perlindungan real-time secara aman.

        Menghentikan semua pemantauan, menunggu thread selesai,
        dan melepas semua kunci file yang masih aktif.
        """
        # Jika memang tidak sedang berjalan, tidak perlu melakukan apapun
        if not self.running:
            return

        logger.info("Stopping real-time protection...")
        # Tandai bahwa perlindungan harus berhenti
        self.running = False
        # Kirim sinyal ke semua thread agar segera berhenti
        self._shutdown_event.set()

        # Hentikan watchdog observer (pemantau perubahan file)
        if self._observer:
            self._observer.stop()              # Minta observer berhenti
            self._observer.join(timeout=2)     # Tunggu maksimal 2 detik hingga benar-benar berhenti
            self._observer = None              # Hapus referensi agar bisa di-garbage-collect

        # Tunggu semua thread pekerja selesai (maks 3 detik per thread)
        for t in self._scan_threads:
            t.join(timeout=3)
        self._scan_threads.clear()  # Kosongkan daftar thread

        # Reset event shutdown agar bisa dipakai lagi jika proteksi dinyalakan ulang
        self._shutdown_event.clear()

        # Lepas semua kunci file yang masih aktif saat proteksi dihentikan
        with self._lock_mutex:  # Kunci mutex agar aman dari race condition
            for file_path, lock in self._active_locks.items():
                lock.release()  # Lepas kunci sehingga file bisa diakses normal
                logger.debug(f"Released remaining lock: {file_path}")
            self._active_locks.clear()  # Kosongkan kamus kunci

        # Reset mode ke "none" karena proteksi sudah mati
        self.mode = "none"
        self.stats["mode"] = "none"
        logger.info("Real-time protection stopped")

    # ================================================================
    # WATCHDOG + PSEUDO-BLOCKING
    # Bagian ini memantau folder dan mengunci file baru secara otomatis
    # ================================================================

    def _start_watchdog_mode(self):
        """
        Mengaktifkan pemantauan folder secara otomatis.

        Setiap kali ada file baru muncul atau file berubah di folder
        yang dipantau, file tersebut langsung dikunci dan dimasukkan
        ke antrean pemindaian. Empat pekerja pemindai berjalan serentak
        agar proses tidak lambat.
        """
        # Coba import watchdog — pustaka pemantau perubahan file
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            # Jika watchdog tidak terinstall, proteksi file tidak bisa berjalan
            logger.error("watchdog not installed! Run: pip install watchdog")
            self.running = False
            return

        # Jika tidak ada folder yang ditentukan, pakai semua drive lokal
        if not self.monitored_paths:
            self.monitored_paths = self._get_default_paths()

        # Buat antrean untuk menampung file yang menunggu dipindai
        self._scan_queue = PriorityQueue(maxsize=self.max_queue_size)

        # Simpan referensi ke self agar bisa diakses dari dalam kelas handler
        protection = self

        # Kelas handler yang dipanggil watchdog saat ada perubahan file
        class PseudoBlockHandler(FileSystemEventHandler):
            def _is_realtime_candidate(self, file_path: str) -> bool:
                """Cek cepat agar watchdog tidak memenuhi antrean dengan file noise non-target."""
                ext = Path(file_path).suffix.lower()
                return ext in DANGEROUS_EXTENSIONS

            def on_created(self, event):
                if event.is_directory:
                    return
                logger.info(f"[WATCHDOG] on_created: {event.src_path}")
                if protection._should_ignore_path(event.src_path):
                    logger.info(f"[WATCHDOG] IGNORED (skip rule): {event.src_path}")
                    return
                if not self._is_realtime_candidate(event.src_path):
                    logger.info(f"[WATCHDOG] IGNORED (not realtime target): {event.src_path}")
                    return
                # File baru dengan path yang sama harus discan ulang, meski sebelumnya pernah di-allow.
                protection._cache_discard(event.src_path)
                # File baru/copy tidak memakai cache agar selalu discan ulang.
                protection._on_new_file(
                    event.src_path,
                    priority=SCAN_PRIORITY_REALTIME,
                    bypass_cache=True,
                )

            def on_moved(self, event):
                if event.is_directory:
                    return
                dest_path = event.dest_path
                logger.info(f"[WATCHDOG] on_moved/renamed: {event.src_path} -> {dest_path}")
                if protection._should_ignore_path(dest_path):
                    logger.info(f"[WATCHDOG] IGNORED (skip rule): {dest_path}")
                    return
                if not self._is_realtime_candidate(dest_path):
                    logger.info(f"[WATCHDOG] IGNORED (not realtime target): {dest_path}")
                    return
                protection._cache_discard(event.src_path)
                # Rename/copy bisa menghasilkan path lama yang sudah ada di cache.
                # Buang cache tujuan agar file hasil rename tetap discan.
                protection._cache_discard(dest_path)
                # Rename/move dianggap file baru dan tidak memakai cache.
                protection._on_new_file(
                    dest_path,
                    priority=SCAN_PRIORITY_REALTIME,
                    bypass_cache=True,
                )

            def on_modified(self, event):
                if event.is_directory:
                    return
                file_path = event.src_path
                logger.info(f"[WATCHDOG] on_modified: {file_path}")
                if protection._should_ignore_path(file_path):
                    logger.info(f"[WATCHDOG] IGNORED (skip rule): {file_path}")
                    return
                if not self._is_realtime_candidate(file_path):
                    logger.info(f"[WATCHDOG] IGNORED (not realtime target): {file_path}")
                    return
                # Jika file berbahaya berubah isinya, hasil scan lama tidak boleh dipercaya.
                if Path(file_path).suffix.lower() in DANGEROUS_EXTENSIONS:
                    protection._cache_discard(file_path)
                with protection._lock_mutex:
                    if file_path not in protection._active_locks:
                        # File modified tidak memakai cache karena isi file sudah berubah.
                        protection._on_new_file(
                            file_path,
                            priority=SCAN_PRIORITY_REALTIME,
                            bypass_cache=True,
                        )

        # Buat observer watchdog yang akan memantau folder
        self._observer = Observer()
        handler = PseudoBlockHandler()  # Handler yang akan menangani event perubahan file

        # Daftarkan setiap folder yang akan dipantau ke observer
        for path in self.monitored_paths:
            try:
                if os.path.exists(path):  # Pastikan folder benar-benar ada
                    # recursive=True = pantau juga sub-folder di dalamnya
                    self._observer.schedule(handler, path, recursive=True)
                    logger.info(f"📂 Monitoring: {path}")
            except Exception as e:
                logger.error(f"Failed to monitor {path}: {e}")

        # Mulai observer — mulai memantau perubahan file
        self._observer.start()

        # Jalankan 4 thread pekerja scan secara paralel agar pemindaian cepat
        for i in range(4):
            t = threading.Thread(
                target=self._scan_worker,   # Fungsi yang dijalankan oleh thread ini
                daemon=True,                # Daemon = otomatis mati saat program utama ditutup
                name=f"ScanWorker-{i}"      # Nama thread untuk memudahkan debugging
            )
            t.start()                       # Mulai jalankan thread
            self._scan_threads.append(t)    # Simpan referensi agar bisa di-join saat stop

        # Thread pembersih cache — hapus entri cache yang sudah terlalu banyak
        t_cache = threading.Thread(
            target=self._cache_cleanup_worker,
            daemon=True,
            name="CacheCleanup"
        )
        t_cache.start()
        self._scan_threads.append(t_cache)

        # Prescan otomatis dimatikan agar file lama di seluruh drive tidak memenuhi antrean
        # dan tidak menahan worker dengan banyak dialog palsu. Realtime tetap memantau
        # semua folder untuk file baru/copy/rename lewat watchdog.

        # Update mode dan statistik
        self.mode = "pseudo-blocking"
        self.stats["mode"] = "pseudo-blocking"
        logger.info("✅ Real-time protection started (PSEUDO-BLOCKING MODE)")

    # Pengaturan prescan — seberapa agresif memindai file yang sudah ada
    _PRESCAN_BATCH_SIZE   = 20    # Jumlah file per gelombang sebelum jeda (agar CPU tidak penuh)
    _PRESCAN_BATCH_DELAY  = 2.0   # Jeda antar gelombang dalam detik
    _PRESCAN_PRIORITY_DIRS = {    # Folder yang dipindai lebih dulu karena berisiko tinggi
        "downloads", "temp", "tmp", "desktop",
        "appdata\\local\\temp", "users",
    }

    def _get_priority_existing_file_dirs(self) -> List[str]:
        """Ambil folder prioritas untuk scan cepat saat realtime baru dinyalakan."""
        candidates = [
            Path.home() / "Downloads",
            Path.home() / "Desktop",
            Path(os.environ.get("TEMP", "")),
            Path(os.environ.get("TMP", "")),
        ]
        result = []
        seen = set()
        for path in candidates:
            try:
                if not path or not path.exists() or not path.is_dir():
                    continue
                resolved = str(path.resolve())
                key = resolved.lower()
                if key in seen:
                    continue
                seen.add(key)
                result.append(resolved)
            except Exception:
                continue
        return result

    def _prescan_priority_existing_files(self):
        """
        Scan ringan untuk file berbahaya yang sudah ada sebelum realtime ON.

        Fokus ke Downloads, Desktop, dan Temp agar alert muncul untuk file uji
        tanpa menyapu seluruh drive.
        """
        if not self.running:
            return

        self._shutdown_event.wait(timeout=0.5)
        if not self.running:
            return

        queued = 0
        logger.info("Priority prescan: scanning existing files in Downloads/Desktop/Temp")

        for base_path in self._get_priority_existing_file_dirs():
            if not self.running:
                break
            try:
                for root, dirs, filenames in os.walk(base_path):
                    if not self.running:
                        break

                    dirs[:] = [
                        d for d in dirs
                        if not self._should_ignore_path(os.path.join(root, d))
                    ]

                    for fname in filenames:
                        if not self.running:
                            break

                        ext = Path(fname).suffix.lower()
                        if ext not in DANGEROUS_EXTENSIONS:
                            continue

                        fpath = os.path.join(root, fname)
                        if self._should_ignore_path(fpath):
                            continue
                        if self._cache_contains(fpath):
                            continue
                        with self._lock_mutex:
                            if fpath in self._active_locks:
                                continue

                        # Jangan skip file 0 byte. Model tetap bisa memberi keputusan.
                        self._on_new_file(fpath, priority=SCAN_PRIORITY_PRESCAN)
                        queued += 1

                        if queued % self._PRESCAN_BATCH_SIZE == 0:
                            self._shutdown_event.wait(timeout=0.5)

            except (OSError, PermissionError):
                continue

        logger.info("Priority prescan complete - %d existing dangerous files queued", queued)

    def _prescan_existing_files(self):
        """
        Memindai file-file berbahaya yang sudah ada di komputer SEBELUM
        perlindungan diaktifkan.

        Pemindaian dilakukan bertahap agar UI tetap responsif:
        folder Downloads, Temp, dan Desktop diprioritaskan terlebih dahulu.
        Setiap 20 file, program berhenti sejenak selama 2 detik
        agar CPU tidak kewalahan.
        """
        # Jika tidak ada folder yang dipantau, tidak ada yang perlu dipindai
        if not self.monitored_paths:
            return

        # Tunggu 3 detik agar UI selesai dimuat sebelum memulai pemindaian berat
        # Jika shutdown dipanggil dalam 3 detik ini, langsung keluar
        self._shutdown_event.wait(timeout=3.0)
        if not self.running:
            return  # Proteksi sudah dimatikan, hentikan prescan

        logger.info("🔍 Pre-scanning existing files in batches of %d (2s pause between batches)...",
                    self._PRESCAN_BATCH_SIZE)

        queued = 0  # Hitung total file yang sudah dimasukkan ke antrean

        def _walk_path(base_path: str):
            """Fungsi dalam fungsi: berjalan melalui semua file di base_path dan antrean yang berbahaya."""
            nonlocal queued  # Akses variabel 'queued' dari fungsi luar
            try:
                # Jalan rekursif melalui semua folder dan sub-folder
                for root, dirs, filenames in os.walk(base_path):
                    if not self.running:
                        return  # Hentikan jika proteksi dimatikan di tengah jalan

                    # Hapus folder yang dikecualikan dari daftar penelusuran
                    # dirs[:] = modifikasi in-place agar os.walk tidak masuk ke folder yang dikecualikan
                    dirs[:] = [
                        d for d in dirs
                        if not self._should_ignore_path(os.path.join(root, d))
                    ]

                    # Urutkan folder: folder berisiko tinggi (Downloads, Temp, dll.) dipindai dulu
                    root_lower = root.lower()
                    dirs.sort(key=lambda d: (
                        # Nilai 0 = prioritas tinggi (scan dulu), 1 = prioritas biasa
                        0 if any(p in os.path.join(root_lower, d.lower())
                                 for p in self._PRESCAN_PRIORITY_DIRS) else 1
                    ))

                    # Periksa setiap file dalam folder ini
                    for fname in filenames:
                        if not self.running:
                            return  # Hentikan jika proteksi dimatikan

                        # Cek ekstensi file — hanya proses file yang berpotensi berbahaya
                        ext = Path(fname).suffix.lower()
                        if ext not in DANGEROUS_EXTENSIONS:
                            continue  # Lewati file yang aman (video, audio, teks, dll.)

                        fpath = os.path.join(root, fname)  # Gabungkan folder + nama file

                        if self._should_ignore_path(fpath):
                            continue  # Lewati file di folder sistem atau dikecualikan
                        if self._cache_contains(fpath):
                            continue  # Lewati file yang sudah pernah dipindai dan aman
                        with self._lock_mutex:
                            if fpath in self._active_locks:
                                continue  # Lewati file yang sedang dikunci (sedang dipindai)

                        # Masukkan file ke antrean untuk dipindai
                        self._on_new_file(fpath, priority=SCAN_PRIORITY_PRESCAN)
                        queued += 1  # Tambah hitungan file yang diantrean

                        # Setiap 20 file, jeda sebentar agar CPU bisa istirahat
                        if queued % self._PRESCAN_BATCH_SIZE == 0:
                            logger.debug("Prescan batch %d files queued, pausing %ss...",
                                         queued, self._PRESCAN_BATCH_DELAY)
                            # Tunggu atau sampai shutdown dipanggil
                            self._shutdown_event.wait(timeout=self._PRESCAN_BATCH_DELAY)

            except (OSError, PermissionError):
                pass  # Abaikan error akses folder yang tidak bisa dibaca

        # Tahap 1: Pindai folder prioritas tinggi dulu (Downloads, Temp, Desktop)
        for base_path in self.monitored_paths:
            if not self.running:
                break  # Hentikan jika proteksi dimatikan
            for pdir in self._PRESCAN_PRIORITY_DIRS:
                candidate = os.path.join(base_path, pdir)  # Coba path: base_path/downloads, dst.
                if os.path.isdir(candidate):
                    _walk_path(candidate)  # Pindai jika folder ini ada

        # Tahap 2: Pindai sisa folder (file yang sudah di-cache dari tahap 1 akan dilewati)
        for base_path in self.monitored_paths:
            if not self.running:
                break
            _walk_path(base_path)

        logger.info("✅ Pre-scan complete — %d existing dangerous files queued", queued)

    def rescan_all(self):
        """
        Memindai ulang SEMUA file yang sudah ada di semua folder yang dipantau.

        Berbeda dengan prescan yang hanya berjalan sekali saat proteksi diaktifkan,
        metode ini bisa dipanggil kapan saja — misalnya saat user menekan tombol
        "Scan Sekarang" atau saat bridge UI baru tersambung.

        File yang sudah ada di scan_cache (sudah terbukti aman) akan dilewati,
        kecuali file yang sebelumnya terdeteksi malware tapi bridge belum siap
        (file tersebut tidak ada di cache, jadi akan di-scan ulang).
        """
        if not self.running or not self.monitored_paths:
            return  # Tidak ada yang perlu dipindai jika proteksi tidak aktif

        def _do_rescan():
            # Tunggu sebentar agar UI sepenuhnya siap
            self._shutdown_event.wait(timeout=1.0)
            if not self.running:
                return

            logger.info("🔄 Rescan all: memindai ulang semua folder yang dipantau...")
            queued = 0  # Hitung total file yang diantrean

            for base_path in self.monitored_paths:
                if not self.running:
                    break
                try:
                    for root, dirs, filenames in os.walk(base_path):
                        if not self.running:
                            break

                        # Hapus folder yang dikecualikan
                        dirs[:] = [
                            d for d in dirs
                            if not self._should_ignore_path(os.path.join(root, d))
                        ]

                        for fname in filenames:
                            if not self.running:
                                break

                            # Hanya proses ekstensi berbahaya
                            ext = Path(fname).suffix.lower()
                            if ext not in DANGEROUS_EXTENSIONS:
                                continue

                            fpath = os.path.join(root, fname)

                            if self._should_ignore_path(fpath):
                                continue  # Lewati folder sistem
                            if self._cache_contains(fpath):
                                continue  # Sudah terbukti aman, lewati
                            with self._lock_mutex:
                                if fpath in self._active_locks:
                                    continue  # Sedang dipindai, lewati

                            # Antrean untuk dipindai
                            self._on_new_file(fpath, priority=SCAN_PRIORITY_PRESCAN)
                            queued += 1

                            # Jeda tiap 20 file agar CPU tidak penuh
                            if queued % self._PRESCAN_BATCH_SIZE == 0:
                                self._shutdown_event.wait(timeout=self._PRESCAN_BATCH_DELAY)

                except (OSError, PermissionError):
                    pass  # Abaikan folder yang tidak bisa diakses

            logger.info("✅ Rescan selesai — %d file diantrean", queued)

        # Jalankan di thread terpisah agar UI tidak freeze
        t = threading.Thread(target=_do_rescan, daemon=True, name="RescanAll")
        t.start()
        self._scan_threads.append(t)

    def _on_new_file(self, file_path: str, priority: int = 0, bypass_cache: bool = False):
        """
        Menangani file baru yang terdeteksi oleh watchdog atau prescan.

        File langsung dikunci agar tidak bisa dibuka oleh siapapun,
        lalu dimasukkan ke antrean pemindaian.
        """
        # Cache hanya dipakai untuk rescan/pemanggilan biasa.
        # Event realtime dari watchdog memakai bypass_cache=True agar file baru/copy/rename
        # selalu discan walaupun path-nya pernah di-allow sebelumnya.
        if not bypass_cache and self._cache_contains(file_path):
            logger.debug(f"[QUEUE] SKIP (cached): {file_path}")
            return

        logger.info(f"[QUEUE] Queuing for scan: {file_path}")

        # Coba kunci file segera, tetapi jangan mengunci file yang masih 0 byte.
        # FIXED: saat copy/rename, Windows sering membuat file kosong dulu.
        # Kalau file kosong langsung dikunci, proses copy bisa tertahan dan watchdog
        # tidak pernah sampai scan isi file final.
        try:
            initial_size = os.path.getsize(file_path)
        except OSError:
            initial_size = -1

        lock = None
        got_lock = False
        if initial_size > 0:
            lock = FileLock(file_path)
            got_lock = lock.acquire(max_retries=5, retry_delay=0.1)
        else:
            logger.info(f"[LOCK] Delaying lock until file has content: {file_path}")

        if got_lock:
            with self._lock_mutex:
                self._active_locks[file_path] = lock
            self.stats["files_blocked"] += 1
            logger.info(f"[LOCK] LOCKED: {file_path}")
        else:
            logger.warning(f"[LOCK] Failed to lock (will scan without lock): {file_path}")

        # Masukkan file ke antrean scan
        try:
            self._scan_queue.put((priority, time.monotonic(), file_path), block=False)
            logger.info(f"[QUEUE] Added to scan queue: {os.path.basename(file_path)} priority={priority}")
        except Exception:
            logger.warning(f"[QUEUE] Queue full, dropping: {file_path}")
            if got_lock and lock:
                lock.release()
                with self._lock_mutex:
                    self._active_locks.pop(file_path, None)

    def _wait_for_stable_file(self, file_path: str, stable_secs: float = 0.5,
                               max_wait: float = 30.0, require_nonzero: bool = False) -> bool:
        """
        Menunggu hingga file selesai ditulis sepenuhnya ke disk.

        Memeriksa apakah ukuran file berhenti berubah selama 0,5 detik.
        Berguna untuk file yang sedang diunduh agar tidak dipindai
        sebelum proses unduhan selesai.

        Mengembalikan True jika file sudah stabil, False jika habis batas waktu.
        """
        # Hitung batas waktu maksimum menunggu
        deadline = time.monotonic() + max_wait
        last_size = -1        # Ukuran file pada pengecekan sebelumnya (-1 = belum pernah dicek)
        unchanged_for = 0.0   # Berapa lama ukuran file tidak berubah (dalam detik)
        poll = 0.2            # Interval pengecekan: setiap 0.2 detik

        # Terus cek sampai batas waktu habis
        while time.monotonic() < deadline:
            # Hentikan jika proteksi dimatikan
            if self._shutdown_event.is_set() or not self.running:
                return False
            try:
                size = os.path.getsize(file_path)  # Baca ukuran file saat ini
            except OSError:
                return False  # File tidak bisa dibaca — anggap gagal

            if require_nonzero and size <= 0:
                last_size = size
                unchanged_for = 0.0
            elif size == last_size:
                # Ukuran sama seperti sebelumnya — file mungkin sudah selesai ditulis
                unchanged_for += poll  # Tambah durasi tidak berubah
                if unchanged_for >= stable_secs:
                    return True  # File stabil selama stable_secs detik — aman untuk dipindai
            else:
                # Ukuran berubah — file masih sedang ditulis, reset penghitung
                last_size = size
                unchanged_for = 0.0
            time.sleep(poll)  # Tunggu sebelum cek lagi

        return False  # Habis waktu, file tidak stabil

    def _ensure_locked(self, file_path: str) -> bool:
        """
        Memastikan file sudah terkunci sebelum dipindai.

        Jika kunci belum terpasang, menunggu file selesai ditulis
        lalu mencoba mengunci kembali.

        Mengembalikan True jika file berhasil dikunci.
        """
        # Cek apakah file sudah terkunci dari sebelumnya
        with self._lock_mutex:
            existing_lock = self._active_locks.get(file_path)
            if existing_lock:
                try:
                    current_size = os.path.getsize(file_path)
                except OSError:
                    current_size = -1

                if current_size > 0:
                    return True  # Sudah terkunci dan file sudah berisi, aman untuk scan

                self._active_locks.pop(file_path, None)
                existing_lock.release()
                logger.info(f"[LOCK] Released early 0-byte lock, scanning once stable: {file_path}")

        # File belum terkunci — tunggu dulu sampai file stabil (selesai ditulis)
        if not self._wait_for_stable_file(file_path, require_nonzero=False):
            return False  # File tidak stabil dalam batas waktu, lewati

        # Coba kunci file sekarang (setelah stabil)
        lock = FileLock(file_path)
        if lock.acquire(max_retries=10, retry_delay=0.2):
            # Berhasil dikunci
            with self._lock_mutex:
                self._active_locks[file_path] = lock  # Daftarkan kunci
            self.stats["files_blocked"] += 1
            logger.info(f"🔒 LOCKED (after stabilise): {file_path}")
            return True

        # Tetap gagal dikunci meski sudah menunggu
        logger.warning(f"Could not acquire lock even after stabilise: {file_path}")
        return False

    def _scan_worker(self):
        """
        Pekerja pemindaian yang berjalan terus di background.

        Terus mengambil file dari antrean, memastikan file terkunci,
        lalu memindainya dengan model AI. Jika terdeteksi malware,
        pengguna dimintai keputusan. Jika bersih, kunci dilepas.
        """
        logger.info(f"Scan worker started: {threading.current_thread().name}")

        # Loop terus selama proteksi aktif
        while self.running:
            try:
                # Ambil satu file dari antrean (tunggu maksimal 1 detik)
                try:
                    queue_item = self._scan_queue.get(timeout=1)
                except Empty:
                    # Antrean kosong, coba lagi di iterasi berikutnya
                    continue

                if isinstance(queue_item, tuple) and len(queue_item) == 3:
                    _, _, file_path = queue_item
                else:
                    file_path = queue_item

                # Jika file sudah tidak ada (dihapus/dipindah), lewati
                if not os.path.exists(file_path):
                    self._release_lock(file_path)  # Pastikan kuncinya juga dilepas
                    continue

                # Pastikan file terkunci sebelum dipindai
                locked = self._ensure_locked(file_path)
                if not locked:
                    # Tidak bisa dikunci, tapi tetap pindai (tanpa blokir akses).
                    # FIXED: file 0 byte tetap masuk scanner agar realtime tidak diam.
                    logger.warning(f"Scanning without lock (access not blocked): {file_path}")

                # Variabel untuk menyimpan hasil scan
                is_malware = False
                scan_result = None
                t_rt_start = time.perf_counter()  # Catat waktu mulai scan untuk hitung durasi

                try:
                    # Pindai file menggunakan model AI
                    logger.info(f"[SCAN START] Realtime scanning: {file_path}")
                    scan_result = self.scanner.scan_file(file_path)
                    self.stats["files_scanned"] += 1  # Tambah hitungan file yang dipindai
                    logger.warning(
                        "[SCAN RESULT] %s -> result=%s confidence=%s raw=%s",
                        file_path,
                        scan_result.get("result") if scan_result else None,
                        scan_result.get("confidence") if scan_result else None,
                        scan_result,
                    )

                    # Cek apakah hasilnya malware
                    if scan_result and scan_result.get('result') == 'Malware':
                        is_malware = True
                        self.stats["malware_detected"] += 1  # Tambah hitungan malware ditemukan

                except Exception as e:
                    # Scan gagal (mis. file rusak, model error) — catat dan lewati file ini
                    logger.error(f"Scan error for {file_path}: {e}")
                    self._release_lock(file_path)  # Lepas kunci agar file bisa diakses
                    continue

                if is_malware:
                    # Hitung durasi dari scan selesai sampai siap tampilkan alert
                    rt_duration = time.perf_counter() - t_rt_start
                    logger.warning(f"🚨 MALWARE BLOCKED: {file_path} (waktu deteksi→alert: {rt_duration:.3f}s)")

                    if self.malware_bridge:
                        # Bridge sudah tersambung — tampilkan dialog ke user
                        action = self._ask_user_decision(file_path, scan_result)
                        if action == 1:
                            logger.warning(f"[ACTION] User chose QUARANTINE: {file_path}")
                            # FIXED: Jalur watchdog menangani file baru/berubah, bukan proses yang
                            # sedang aktif. Jangan panggil _kill_processes_for_file() di sini karena
                            # fungsi itu menyapu open_files() semua proses Windows dan bisa nyangkut.
                            killed_count = self._kill_all_instances(file_path)
                            if killed_count == 0:
                                self._taskkill_by_image_name(file_path)
                            logger.warning(f"[ACTION] Kill instance result: {killed_count} process(es) killed")
                            logger.warning(f"[ACTION] Releasing MangoDefend lock before quarantine")
                            self._release_lock(file_path)
                            time.sleep(0.3)
                            logger.warning(f"[ACTION] Moving to quarantine: {file_path}")
                            quarantined = self._quarantine_file(file_path)
                            logger.warning(f"[ACTION] Quarantine result={quarantined}: {file_path}")
                        else:
                            # User memilih "Izinkan" — lepas kunci dan masukkan ke cache aman
                            logger.info(f"▶️ User allowed: {os.path.basename(file_path)}")
                            self._release_lock(file_path)
                            self._cache_add(file_path)  # Tambahkan ke cache agar tidak dipindai lagi
                    else:
                        # Bridge belum tersambung (UI belum siap) — JANGAN masukkan ke cache
                        # Tujuan: agar file ini bisa di-scan ulang nanti saat user membukanya
                        logger.warning(f"🚨 Malware found but bridge not ready, will re-scan on access: {file_path}")
                        self._release_lock(file_path)  # Lepas kunci saja, cache tidak diisi
                else:
                    # File bersih — lepas kunci dan masukkan ke cache agar tidak dipindai lagi
                    self._release_lock(file_path)
                    self._cache_add(file_path)  # Tambahkan ke cache "aman"
                    logger.info(f"✅ Clean: {os.path.basename(file_path)}")

            except Exception as e:
                # Error tak terduga di level worker — catat dan jeda sebentar
                logger.error(f"Scan worker error: {e}")
                time.sleep(1)  # Jeda 1 detik sebelum mencoba lagi

        logger.info(f"Scan worker stopped: {threading.current_thread().name}")

    def _release_lock(self, file_path: str):
        """
        Melepas kunci file agar bisa diakses kembali secara normal.
        """
        with self._lock_mutex:  # Kunci mutex agar aman dari race condition antar thread
            # Ambil dan hapus kunci dari kamus kunci aktif
            lock = self._active_locks.pop(file_path, None)
            if lock:
                lock.release()  # Lepas kunci Windows API
                logger.debug(f"🔓 Unlocked: {file_path}")

    def _cache_cleanup_worker(self):
        """
        Membersihkan cache pemindaian secara berkala.

        Jika cache sudah berisi lebih dari 1000 entri, seluruh cache
        dikosongkan agar tidak memakan terlalu banyak memori.
        Berjalan setiap 60 detik di background.
        """
        while self.running:
            time.sleep(60)  # Tunggu 60 detik sebelum cek berikutnya
            if len(self.scan_cache) > 1000:
                # Cache terlalu besar — kosongkan semua agar memori tidak habis
                self.scan_cache.clear()
                logger.debug("Scan cache cleared")

    # ================================================================
    # PEMANTAU PROSES — Mendeteksi program baru yang dijalankan
    # Menggunakan WMI (lebih cepat) atau polling (cadangan)
    # ================================================================

    def _start_process_monitor(self):
        """
        Mengaktifkan pemantauan proses baru yang dijalankan.

        Mencoba menggunakan WMI terlebih dahulu karena lebih cepat
        mendeteksi proses baru. Jika WMI tidak tersedia, beralih ke
        mode polling (pengecekan berkala setiap 500ms).
        """
        try:
            import psutil  # Pustaka untuk membaca info proses
            # Ambil semua PID proses yang sudah berjalan saat ini
            # Ini jadi "baseline" untuk mendeteksi proses BARU nantinya
            self._known_pids = set(psutil.pids())
        except ImportError:
            # psutil tidak terinstall — pemantauan proses tidak bisa berjalan
            logger.warning("psutil not installed, process monitor disabled. Run: pip install psutil")
            return

        # Coba gunakan WMI untuk pemantauan real-time yang lebih cepat
        wmi_started = self._start_wmi_monitor()
        if wmi_started:
            # Backup polling tetap hidup karena WMI di VM kadang start tetapi miss event.
            t = threading.Thread(
                target=self._process_monitor_worker_polling,
                daemon=True,
                name="ProcessMonitor-Polling"
            )
            t.start()
            self._scan_threads.append(t)
            logger.info("Process monitor polling backup started (100ms interval)")
        if not wmi_started:
            # WMI gagal — gunakan polling sebagai cadangan
            t = threading.Thread(
                target=self._process_monitor_worker_polling,
                daemon=True,
                name="ProcessMonitor-Polling"
            )
            t.start()
            self._scan_threads.append(t)
            logger.info("Process monitor started (polling fallback, 100ms interval)")

    def _start_wmi_monitor(self) -> bool:
        """
        Memulai pemantauan proses menggunakan WMI Windows.

        WMI memberi notifikasi sangat awal saat proses baru dibuat —
        jauh sebelum proses sempat menjalankan kodenya.
        Membutuhkan paket: pip install wmi pywin32.

        Mengembalikan True jika WMI berhasil diaktifkan.
        """
        # WMI hanya tersedia di Windows
        if sys.platform != "win32":
            return False

        # Cek apakah paket wmi dan pythoncom sudah terinstall
        try:
            import wmi        # noqa: F401 (import hanya untuk cek ketersediaan)
            import pythoncom  # noqa: F401
        except ImportError:
            logger.warning(
                "wmi/pywin32 not installed — using polling fallback. "
                "For better protection run: pip install wmi pywin32"
            )
            return False  # WMI tidak tersedia, pakai polling

        def wmi_worker():
            """Thread yang berjalan terus untuk mendengarkan event proses baru via WMI."""
            import pythoncom as _com
            # Inisialisasi COM — diperlukan untuk WMI di thread yang berbeda
            _com.CoInitialize()
            try:
                import wmi as _wmi
                c = _wmi.WMI()  # Buat koneksi ke WMI
                # Daftarkan watcher untuk event "pembuatan proses baru"
                watcher = c.Win32_ProcessStartTrace.watch_for("creation")
                logger.info("✅ WMI process monitor started (early notification mode)")

                while self.running:
                    try:
                        # Tunggu event proses baru (timeout 100ms agar deteksi lebih cepat)
                        event = watcher(TimeoutMs=100)
                        if event and self.running:
                            pid = event.ProcessId  # Ambil PID proses yang baru dibuat
                            logger.info(f"[PROCESS EVENT] WMI detected PID={pid}")
                            # Tangani setiap proses di thread terpisah agar WMI tidak terblokir
                            t = threading.Thread(
                                target=self._handle_new_pid,
                                args=(pid,),
                                daemon=True
                            )
                            t.start()
                    except Exception as e:
                        err_str = str(e)
                        # Abaikan error timeout (normal, bukan masalah)
                        if "timed out" not in err_str.lower():
                            logger.debug(f"WMI event error: {e}")
                        continue
            except Exception as e:
                logger.error(f"WMI monitor fatal error: {e}")
                # WMI gagal di runtime (mis. di VirtualBox) — aktifkan polling sebagai fallback
                if self.running:
                    logger.info("Switching to polling fallback after WMI failure")
                    self._process_monitor_worker_polling()
            finally:
                _com.CoUninitialize()  # Lepas COM saat thread selesai
                logger.info("WMI monitor stopped")

        # Jalankan WMI worker di thread terpisah
        t = threading.Thread(target=wmi_worker, daemon=True, name="WMIMonitor")
        t.start()
        self._scan_threads.append(t)
        return True  # WMI berhasil diaktifkan

    def _nt_suspend(self, pid: int) -> bool:
        """
        Membekukan semua thread proses menggunakan NtSuspendProcess Windows.

        Proses yang dibekukan tidak bisa melakukan apapun — semua threadnya
        dihentikan secara bersamaan sebelum sempat menjalankan kode berbahaya.

        Mengembalikan True jika berhasil.
        """
        # NtSuspendProcess hanya ada di Windows
        if sys.platform != "win32":
            return False

        # Buka handle ke proses yang akan dibekukan
        handle = kernel32.OpenProcess(PROCESS_SUSPEND_AND_QUERY, False, pid)
        if not handle:
            # Coba dengan izin minimal jika izin penuh gagal
            handle = kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
        if not handle:
            return False  # Tidak bisa membuka proses sama sekali
        try:
            # Panggil NtSuspendProcess untuk membekukan semua thread proses
            ret = ntdll.NtSuspendProcess(handle)
            return ret == STATUS_SUCCESS  # True jika sukses (ret == 0)
        except Exception as e:
            logger.debug(f"NtSuspendProcess failed for PID={pid}: {e}")
            return False
        finally:
            kernel32.CloseHandle(handle)  # Selalu tutup handle setelah selesai

    def _suspend_and_get_exe(self, pid: int) -> tuple[bool, str]:
        """
        Membekukan proses dan membaca lokasi file eksekutabelnya
        dalam SATU langkah atomik tanpa jeda.

        Dengan cara ini tidak ada celah waktu antara pembekuan dan
        pembacaan path — proses tidak sempat "lari" sebelum kita tahu
        file mana yang sedang dijalankan.

        Mengembalikan tuple (berhasil_dibekukan, path_file_exe).
        """
        # Fungsi ini hanya bisa dijalankan di Windows
        if sys.platform != "win32":
            return False, ""

        import ctypes  # Import lagi untuk memastikan tersedia di scope ini

        # Buka handle ke proses dengan izin suspend + baca info + baca memori
        handle = kernel32.OpenProcess(PROCESS_SUSPEND_AND_QUERY, False, pid)
        if not handle:
            # Jika gagal dengan izin penuh, coba dengan izin minimal
            handle = kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
            if not handle:
                return False, ""  # Tidak bisa membuka proses sama sekali
            try:
                # Bekukan dengan izin minimal (tanpa bisa baca path)
                ret = ntdll.NtSuspendProcess(handle)
                suspended = (ret == STATUS_SUCCESS)
            except Exception:
                suspended = False
            finally:
                kernel32.CloseHandle(handle)
            return suspended, ""  # Tidak bisa baca path, kembalikan string kosong

        # Variabel hasil
        suspended = False
        exe_path  = ""
        try:
            # Langkah 1: Bekukan proses DULU sebelum melakukan apapun
            ret = ntdll.NtSuspendProcess(handle)
            suspended = (ret == STATUS_SUCCESS)

            # Langkah 2: Baca path file exe SETELAH proses beku (tidak bisa lari)
            buf  = ctypes.create_unicode_buffer(32768)   # Buffer untuk menyimpan path (max 32KB)
            size = ctypes.wintypes.DWORD(32768)           # Ukuran buffer
            ok = kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
            if ok and size.value > 0:
                exe_path = buf.value  # Ambil path dari buffer

        except Exception as e:
            logger.debug(f"_suspend_and_get_exe failed PID={pid}: {e}")
        finally:
            kernel32.CloseHandle(handle)  # Selalu tutup handle

        return suspended, exe_path  # Kembalikan status bekukan dan path file

    def _nt_resume(self, pid: int) -> bool:
        """
        Melanjutkan kembali proses yang sebelumnya dibekukan.

        Dipanggil setelah pemindaian selesai dan hasilnya bersih,
        agar proses bisa berjalan normal.

        Mengembalikan True jika berhasil.
        """
        if sys.platform != "win32":
            return False

        # Buka handle ke proses yang akan di-resume
        handle = kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
        if not handle:
            return False  # Proses mungkin sudah mati
        try:
            # Panggil NtResumeProcess untuk melanjutkan semua thread yang dibekukan
            ret = ntdll.NtResumeProcess(handle)
            return ret == STATUS_SUCCESS
        except Exception as e:
            logger.debug(f"NtResumeProcess failed for PID={pid}: {e}")
            return False
        finally:
            kernel32.CloseHandle(handle)  # Selalu tutup handle

    # Daftar proses UWP (aplikasi Windows Store) yang tidak bisa dibekukan
    # Membekukan proses ini akan menyebabkan Windows crash atau tidak responsif
    _UWP_HOSTS = {
        "applicationframehost.exe", "runtimebroker.exe",
        "wwahost.exe", "sihost.exe", "backgroundtaskhost.exe",
        "windows.internal.shellcommon.dll",
    }

    def _is_uwp_process(self, exe_path: str, proc_name: str) -> bool:
        """
        Memeriksa apakah proses ini adalah aplikasi UWP (aplikasi Windows Store).

        Proses UWP tidak bisa dibekukan karena dilindungi oleh Windows.
        Jika terdeteksi sebagai UWP, proses tetap dipindai tapi tidak dibekukan.

        Mengembalikan True jika ini adalah proses UWP.
        """
        name_lower = proc_name.lower()
        if name_lower in self._UWP_HOSTS:
            return True  # Nama proses cocok dengan daftar UWP

        exe_lower = exe_path.lower()
        # Proses UWP biasanya ada di folder WindowsApps atau Packages
        if "windowsapps" in exe_lower or "packages" in exe_lower:
            return True

        return False  # Bukan UWP

    def _handle_new_pid(self, pid: int):
        """
        Menangani proses baru yang baru saja terdeteksi berjalan.

        Urutan penanganan:
        1. Bekukan proses dan baca path filenya secara atomik.
        2. Jika path tidak terbaca, gunakan psutil sebagai cadangan.
        3. Lewati proses UWP dan proses sistem — langsung jalankan kembali.
        4. Pindai file eksekutabelnya dengan model AI.
        5. Jika bersih, jalankan kembali. Jika malware, minta keputusan pengguna.
        """
        import psutil  # Pustaka untuk membaca info proses

        # Jangan pindai proses MangoDefend sendiri — ini kita!
        if pid == os.getpid():
            return

        # WMI dan polling backup bisa menangkap PID yang sama.
        # Bagian ini mencegah proses yang sama discan dua kali.
        with self._handled_pids_lock:
            if pid in self._handled_pids:
                return
            self._handled_pids.add(pid)
            if len(self._handled_pids) > 5000:
                self._handled_pids.clear()
                self._handled_pids.add(pid)

        # Coba dapatkan objek proses dari PID
        try:
            proc = psutil.Process(pid)
        except psutil.NoSuchProcess:
            return  # Proses sudah mati sebelum sempat ditangani

        # Langkah 1: Bekukan proses DAN baca path exe secara bersamaan (atomik)
        suspended, exe_path = self._suspend_and_get_exe(pid)

        if suspended:
            self.stats["processes_suspended"] += 1  # Catat statistik
            logger.debug(f"⏸️ Suspended PID={pid}")

        # Langkah 2: Jika path exe tidak berhasil dibaca, coba via psutil
        if not exe_path:
            try:
                exe_path = proc.exe()  # Baca path exe menggunakan psutil
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Tidak bisa baca path dan proses sudah mati atau tidak ada izin
                if suspended:
                    self._nt_resume(pid)  # Jangan biarkan proses beku selamanya
                return

        # Jika path masih kosong setelah dicoba dua cara, lepas pembekuan dan keluar
        if not exe_path:
            if suspended:
                self._nt_resume(pid)
            return

        # Baca nama proses untuk pemeriksaan UWP
        try:
            proc_name = proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            proc_name = ""  # Tidak bisa baca nama, pakai string kosong

        # Langkah 3a: Cek apakah ini proses UWP (aplikasi Windows Store)
        is_uwp = self._is_uwp_process(exe_path, proc_name)
        if is_uwp:
            if suspended:
                self._nt_resume(pid)  # Resume proses UWP — jangan dibekukan
                suspended = False
            logger.debug(f"UWP process, no freeze: {proc_name} PID={pid}")

        if not suspended:
            # Proses tidak dibekukan (UWP atau gagal freeze) — scan tanpa blokir
            logger.warning(f"Scanning without freeze: {proc_name} PID={pid}")

        # Langkah 3b: Cek apakah ini proses sistem Windows yang tidak perlu dipindai
        is_system = self._is_system_process(exe_path)

        if is_system:
            logger.debug(f"System process skipped: {exe_path} PID={pid}")
            # Proses sistem: periksa argumen baris perintahnya (mungkin membuka file berbahaya)
            handled = self._check_opened_file_args(proc, pid, suspended)
            if not handled and suspended:
                self._nt_resume(pid)  # Resume jika tidak ada file berbahaya ditemukan
            return

        # Langkah 4: Pindai file exe proses ini.
        # Process monitor tidak memakai cache agar double-click file yang sama tetap discan ulang.
        logger.info(f"🔍 Scanning new process: {exe_path} PID={pid}")
        self._scan_and_handle_process(proc, pid, exe_path, already_suspended=suspended)

    def _check_opened_file_args(self, proc, pid: int, already_suspended: bool) -> bool:
        """
        Memeriksa argumen baris perintah untuk menemukan file berbahaya
        yang dibuka oleh proses yang sudah berjalan.

        Contoh: Adobe Acrobat membuka file PDF berbahaya yang dikirim lewat email.
        Dalam kasus ini yang dipindai adalah file PDF-nya, bukan Acrobat-nya.

        Mengembalikan True jika file berbahaya ditemukan dan sudah ditangani.
        """
        import psutil

        # Baca argumen baris perintah proses (mis: ["acrobat.exe", "dokumen.pdf"])
        try:
            cmdline = proc.cmdline()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False  # Tidak bisa baca argumen

        # Jika hanya ada nama program tanpa argumen, tidak ada file yang dibuka
        if len(cmdline) <= 1:
            return False

        # Periksa setiap argumen (mulai dari indeks 1, karena 0 adalah nama program)
        for arg in cmdline[1:]:
            # Bersihkan argumen dari karakter kutip di awal/akhir
            clean_arg = arg.strip().strip('"').strip("'")
            # Lewati flag/opsi (biasanya diawali - atau /)
            if clean_arg.startswith('-') or clean_arg.startswith('/'):
                continue
            try:
                # Normalisasi path agar bisa dibandingkan dengan benar
                clean_arg = os.path.normpath(clean_arg)
            except Exception:
                continue  # Lewati jika normalisasi gagal

            # Pastikan argumen ini menunjuk ke file yang benar-benar ada
            if not os.path.isfile(clean_arg):
                continue
            # Cek ekstensi file yang dibuka
            arg_ext = Path(clean_arg).suffix.lower()
            if arg_ext in SKIP_EXTENSIONS:
                continue  # Lewati file yang pasti aman (video, audio, dll.)

            # File ini berpotensi berbahaya — pindai segera!
            try:
                opener_name = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                opener_name = f"PID {pid}"
            logger.info(f"Dangerous file opened as arg: {os.path.basename(clean_arg)} by {opener_name}")
            self._scan_opened_file(proc, pid, clean_arg, already_suspended=already_suspended)
            return True  # Ditemukan dan ditangani

        return False  # Tidak ada file berbahaya di argumen

    # ── Fallback polling — digunakan jika WMI tidak tersedia ──────────

    def _process_monitor_worker_polling(self):
        """
        Memantau proses baru dengan cara mengecek daftar proses secara berkala.

        Digunakan sebagai cadangan jika WMI tidak tersedia.
        Pengecekan dilakukan setiap 500ms — cukup cepat untuk menangkap
        proses baru sebelum sempat berbuat banyak.
        """
        import psutil

        logger.info("Process monitor worker started (polling mode, 100ms interval)")

        _POLL_INTERVAL = 0.1  # Cek setiap 100 milidetik (0.1 detik)

        while self.running:
            try:
                # Ambil semua PID proses yang sedang berjalan saat ini
                current_pids = set(psutil.pids())
                # Proses baru = PID yang ada sekarang tapi tidak ada sebelumnya
                new_pids     = current_pids - self._known_pids
                # Update daftar PID yang diketahui untuk perbandingan berikutnya
                self._known_pids = current_pids

                # Tangani setiap proses baru
                for pid in new_pids:
                    if not self.running:
                        break  # Hentikan jika proteksi dimatikan
                    logger.info(f"[PROCESS EVENT] Polling detected PID={pid}")
                    # Buat thread baru untuk menangani setiap PID agar tidak saling menunggu
                    t = threading.Thread(
                        target=self._handle_new_pid,
                        args=(pid,),
                        daemon=True
                    )
                    t.start()

                # Tunggu sebelum cek berikutnya, atau sampai shutdown dipanggil
                self._shutdown_event.wait(timeout=_POLL_INTERVAL)

            except Exception as e:
                logger.error(f"Process monitor polling error: {e}")
                self._shutdown_event.wait(timeout=1.0)  # Jeda lebih lama jika error

        logger.info("Process monitor worker stopped")

    # ================================================================
    # PEMINDAIAN & PENGAMBILAN KEPUTUSAN
    # ================================================================

    def _scan_and_handle_process(self, proc, pid: int, exe_path: str,
                                  already_suspended: bool = False):
        """
        Memindai file eksekutabel proses yang (idealnya) sudah dibekukan,
        lalu mengambil tindakan: karantina jika malware, lanjutkan jika bersih.
        """
        import psutil

        # FIXED: Nama proses dibaca aman agar kegagalan proc.name() tidak membatalkan alert.
        try:
            proc_name = proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            proc_name = Path(exe_path).name or f"PID {pid}"
        # Jika proses belum dibekukan (dari mode polling), coba bekukan sekarang
        if not already_suspended:
            try:
                proc.suspend()              # Bekukan via psutil (metode alternatif)
                already_suspended = True
                self.stats["processes_suspended"] += 1
                logger.info(f"⏸️ Suspended (psutil fallback): {proc_name} PID={pid}")
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                # Tidak bisa dibekukan — mungkin proses terlindungi atau sudah mati
                logger.warning(f"Could not suspend PID={pid}: {e}")
        else:
            logger.info(f"⏸️ Already suspended: {proc_name} PID={pid}")

        try:
            t_proc_start = time.perf_counter()          # Catat waktu mulai scan
            result = self.scanner.scan_file(exe_path)   # Pindai file exe dengan AI
            self.stats["files_scanned"] += 1             # Tambah hitungan file dipindai
            logger.warning(
                "[PROCESS SCAN RESULT] %s PID=%s -> result=%s confidence=%s raw=%s",
                exe_path,
                pid,
                result.get("result") if result else None,
                result.get("confidence") if result else None,
                result,
            )

            if result and result.get('result') == 'Malware':
                # Malware terdeteksi!
                proc_duration = time.perf_counter() - t_proc_start
                logger.warning(f"🚨 MALWARE PROCESS: {exe_path} (waktu deteksi→alert: {proc_duration:.3f}s)")

                # Tampilkan dialog ke user dan tunggu keputusannya
                action = self._ask_user_decision(
                    exe_path, result,
                    process_pid=pid,
                    process_name=proc_name,  # FIXED: pakai nama aman agar alert tidak batal
                )

                if action == 1:
                    # User memilih "Karantina & Hapus"
                    logger.warning(f"🚨 KILLED malware process: {proc_name} PID={pid}")
                    self._kill_process_tree(proc)           # Matikan proses beserta child-nya
                    self._kill_all_instances(exe_path)      # Matikan semua instance file yang sama
                    killed_count = self._kill_processes_for_file(exe_path)  # Sweep tambahan
                    logger.warning(f"Kill sweep matched {killed_count} extra process(es)")
                    time.sleep(1.0)                         # Tunggu 1 detik agar proses benar-benar mati
                    self._kill_all_instances(exe_path)      # Sapu kedua untuk proses yang respawn
                    self.stats["malware_detected"] += 1
                    self.stats["processes_killed"] += 1
                    quarantined = self._quarantine_file(exe_path)         # Pindahkan exe ke karantina
                    logger.warning(f"[ACTION] Process quarantine result={quarantined}: {exe_path}")
                else:
                    # User memilih "Izinkan" — resume proses tanpa cache agar double-click berikutnya tetap discan.
                    logger.info(f"▶️ User allowed: {proc_name} PID={pid}")
                    if already_suspended:
                        self._nt_resume(pid)    # Lanjutkan proses yang dibekukan
            else:
                # File bersih — resume proses tanpa cache agar eksekusi berikutnya tetap dicek.
                if already_suspended:
                    self._nt_resume(pid)
                logger.info(f"▶️ Clean, resumed: {proc_name} PID={pid}")

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Proses sudah mati atau akses ditolak — tidak ada yang perlu dilakukan
            pass
        except Exception as e:
            logger.error(f"Scan error for PID={pid}: {e}")
            if already_suspended:
                self._nt_resume(pid)  # Jangan biarkan proses beku jika terjadi error

    def _scan_opened_file(self, proc, pid: int, file_path: str,
                           already_suspended: bool = False):
        """
        Memindai file yang sedang dibuka oleh suatu proses.

        Proses yang membuka file tersebut dibekukan terlebih dahulu,
        lalu file yang dibuka dipindai. Jika malware, proses pembukanya
        juga ikut dihentikan.
        """
        import psutil

        # FIXED: Nama proses pembuka dibaca aman agar alert tidak batal jika proses hilang/AccessDenied.
        try:
            proc_name = proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            proc_name = f"PID {pid}"
        suspended  = already_suspended  # Status apakah proses pembuka sudah dibekukan
        opener_exe = ""                 # Path exe proses pembuka (untuk kill nanti)

        try:
            logger.info(
                f"🔍 Scanning opened file: {os.path.basename(file_path)} "
                f"(by {proc_name}, PID={pid})"
            )

            # Bekukan proses pembuka jika belum dibekukan
            if not already_suspended:
                if self._nt_suspend(pid):
                    # Berhasil dibekukan via NtSuspendProcess
                    suspended = True
                    self.stats["processes_suspended"] += 1
                    logger.info(f"⏸️ Suspended opener: {proc_name} PID={pid}")
                else:
                    try:
                        # Gagal via NtSuspend — coba via psutil sebagai cadangan
                        proc.suspend()
                        suspended = True
                        self.stats["processes_suspended"] += 1
                        logger.info(f"⏸️ Suspended opener (psutil fallback): {proc_name} PID={pid}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        logger.warning(f"Could not suspend opener PID={pid}: {e}")
            else:
                logger.info(f"⏸️ Opener already suspended: {proc_name} PID={pid}")

            # Pindai file yang dibuka (bukan proses pembukanya)
            result = self.scanner.scan_file(file_path)
            self.stats["files_scanned"] += 1
            logger.warning(
                "[OPENED FILE SCAN RESULT] %s opened_by_pid=%s -> result=%s confidence=%s raw=%s",
                file_path,
                pid,
                result.get("result") if result else None,
                result.get("confidence") if result else None,
                result,
            )

            if result and result.get('result') == 'Malware':
                # File yang dibuka adalah malware! Tampilkan dialog ke user
                action = self._ask_user_decision(
                    file_path, result,
                    process_pid=pid,
                    process_name=proc_name,
                )

                if action == 1:
                    # User memilih karantina
                    logger.warning(f"🚨 MALWARE: {file_path}")
                    logger.warning(f"🚨 KILLING opener: {proc_name} PID={pid}")

                    # Baca path exe pembuka untuk proses kill
                    try:
                        opener_exe = proc.exe()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                    # Tentukan target yang akan di-kill:
                    # - Jika file malware adalah dokumen (pdf, doc), kill aplikasi pembukanya
                    # - Jika file malware adalah exe, kill file itu sendiri
                    target_exe = file_path
                    if Path(file_path).suffix.lower() not in {".exe", ".scr", ".com"}:
                        target_exe = opener_exe or file_path

                    # Matikan proses pembuka beserta semua child-nya
                    killed = self._kill_process_tree(proc)
                    if killed:
                        suspended = False  # Proses sudah mati, tidak perlu di-resume
                    else:
                        logger.warning(f"Opener still alive after kill: PID={pid}")

                    self._kill_all_instances(target_exe)    # Matikan semua instance
                    killed_count = self._kill_processes_for_file(file_path)  # Sweep tambahan
                    logger.warning(f"Kill sweep matched {killed_count} extra process(es)")
                    time.sleep(1.0)                         # Tunggu 1 detik
                    self._kill_all_instances(target_exe)    # Sapu kedua untuk yang respawn
                    self.stats["malware_detected"] += 1
                    self.stats["processes_killed"] += 1
                    quarantined = self._quarantine_file(file_path)        # Karantina file malware
                    logger.warning(f"[ACTION] Opened-file quarantine result={quarantined}: {file_path}")
                else:
                    # User memilih izinkan — resume proses pembuka tanpa cache.
                    logger.info(f"▶️ User allowed: {os.path.basename(file_path)}")
                    if suspended:
                        self._nt_resume(pid)
                        suspended = False
            else:
                # File bersih — resume proses pembuka tanpa cache.
                logger.info(f"✅ Clean file: {os.path.basename(file_path)}")
                if suspended:
                    self._nt_resume(pid)
                    suspended = False

        except Exception as e:
            logger.error(f"Error scanning opened file {file_path}: {e}")
            if suspended:
                self._nt_resume(pid)  # Selalu resume jika terjadi error agar tidak beku selamanya

    def _ask_user_decision(
        self,
        file_path: str,
        scan_result: dict,
        process_pid: int = None,
        process_name: str = "",
    ) -> int:
        """
        Menampilkan dialog peringatan ke pengguna dan menunggu keputusan mereka.

        Mengirim informasi malware ke jembatan UI, lalu menunggu
        hingga pengguna memilih tindakan.

        Mengembalikan:
        - 0 = izinkan file/proses berjalan
        - 1 = hapus dan karantina
        """
        if self.malware_bridge:
            # Bridge tersambung — tampilkan dialog ke user melalui UI thread
            import threading as _threading
            response_event  = _threading.Event()   # Event untuk menunggu jawaban user
            response_holder = []                   # Daftar untuk menyimpan jawaban user

            # Kemas semua data yang diperlukan untuk menampilkan dialog
            alert_data = {
                "file_path":     file_path,        # Path file yang berbahaya
                "scan_result":   scan_result,       # Hasil scan (label, confidence, dll.)
                "process_pid":   process_pid,       # PID proses (jika dari process monitor)
                "process_name":  process_name,      # Nama proses (untuk ditampilkan di dialog)
                "response_event":  response_event,  # Event untuk sinkronisasi antar thread
                "response_holder": response_holder, # Wadah untuk menampung keputusan user
            }

            # Kirim sinyal ke UI thread untuk menampilkan dialog
            # (Qt signal bersifat thread-safe — aman dipanggil dari background thread)
            self.malware_bridge.malware_detected.emit(alert_data)

            # Tunggu sampai user membuat keputusan (atau sampai proteksi dimatikan)
            while not response_event.wait(timeout=0.3):
                if self._shutdown_event.is_set() or not self.running:
                    # Proteksi dimatikan saat menunggu — default ke "izinkan" (aman)
                    logger.info("Protection stopped while waiting for user — defaulting to allow")
                    return 0

            # Ambil keputusan yang disimpan oleh UI thread
            if response_holder:
                decision = response_holder[0]
                logger.warning(f"[DECISION] User decision received: {decision} (1=quarantine, 0=allow) for {file_path}")
                return decision
            logger.warning(f"[DECISION] No decision received, defaulting to allow for {file_path}")

        # Tanpa bridge UI — selalu izinkan (tidak pernah otomatis menghapus tanpa persetujuan user)
        return 0

    # ================================================================
    # FUNGSI MEMATIKAN PROSES
    # ================================================================

    def _kill_process_tree(self, proc, timeout: float = 3.0) -> bool:
        """
        Menghentikan proses beserta semua proses turunannya (child processes).

        Menggunakan taskkill di Windows atau terminate/kill via psutil.
        Melakukan dua kali percobaan untuk memastikan proses benar-benar mati.

        Mengembalikan True jika semua proses berhasil dihentikan.
        """
        try:
            import psutil
            import subprocess

            root_pid = proc.pid  # PID proses utama yang akan dimatikan

            if sys.platform == "win32":
                # Di Windows, gunakan taskkill dengan flag /T (kill tree) dan /F (force)
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # Jalankan tanpa jendela
                result = subprocess.run(
                    ["taskkill", "/PID", str(root_pid), "/T", "/F"],  # Kill tree secara paksa
                    capture_output=True, text=True,
                    creationflags=creationflags, timeout=10,
                )
                if result.returncode == 0:
                    # taskkill berhasil — verifikasi proses benar-benar mati
                    try:
                        psutil.Process(root_pid)  # Jika ini tidak raise exception, proses masih hidup
                    except psutil.NoSuchProcess:
                        return True  # Proses sudah mati
                else:
                    logger.warning(
                        "taskkill failed PID=%s: %s %s",
                        root_pid, result.stdout.strip(), result.stderr.strip()
                    )

            # Kumpulkan semua proses yang akan dimatikan (proses utama + semua child)
            targets = []
            try:
                targets.extend(proc.children(recursive=True))  # Semua proses turunan
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            targets.append(proc)  # Tambahkan proses utama ke daftar

            # Percobaan 1: Kirim sinyal terminate (lebih sopan, memberi kesempatan cleanup)
            for target in targets:
                try:
                    if target.is_running():
                        target.terminate()  # Minta proses berhenti dengan baik
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Tunggu sampai semua proses mati (atau timeout)
            _, alive = psutil.wait_procs(targets, timeout=timeout)

            # Percobaan 2: Kill paksa proses yang masih hidup
            for target in alive:
                try:
                    target.kill()  # Kill paksa tanpa ampun
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Tunggu lagi setelah kill paksa
            _, alive_after = psutil.wait_procs(alive, timeout=timeout)
            if not alive_after:
                return True  # Semua proses berhasil dimatikan

            # Masih ada yang hidup — coba taskkill sekali lagi sebagai upaya terakhir
            if sys.platform == "win32":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                result = subprocess.run(
                    ["taskkill", "/PID", str(root_pid), "/T", "/F"],
                    capture_output=True, text=True,
                    creationflags=creationflags, timeout=10,
                )
                try:
                    psutil.Process(root_pid)
                    return False  # Proses masih hidup — gagal
                except psutil.NoSuchProcess:
                    return True  # Proses akhirnya mati

            return False  # Gagal mematikan semua proses
        except Exception as e:
            logger.error(f"Failed to kill process tree: {e}")
            return False

    def _taskkill_by_image_name(self, file_path: str) -> bool:
        """
        Menghentikan proses berdasarkan nama file eksekutabelnya
        menggunakan perintah taskkill Windows.

        Hanya berfungsi untuk file .exe, .scr, .com, .bat, dan .cmd.
        Mengembalikan True jika berhasil.
        """
        if sys.platform != "win32":
            return False

        image_name = Path(file_path).name  # Ambil hanya nama file (tanpa folder)
        # Hanya ekstensi yang bisa dijadikan image name untuk taskkill
        if not image_name.lower().endswith((".exe", ".scr", ".com", ".bat", ".cmd")):
            return False

        try:
            import subprocess
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            # Gunakan /IM untuk kill berdasarkan nama image (bukan PID)
            result = subprocess.run(
                ["taskkill", "/IM", image_name, "/T", "/F"],
                capture_output=True, text=True,
                creationflags=creationflags, timeout=10,
            )
            if result.returncode == 0:
                logger.warning(f"taskkill by image name succeeded: {image_name}")
                return True
            logger.warning(
                "taskkill by image name failed %s: %s %s",
                image_name, result.stdout.strip(), result.stderr.strip()
            )
        except Exception as e:
            logger.warning(f"taskkill by image name error {image_name}: {e}")
        return False

    def _kill_process_by_pid(self, pid: int) -> bool:
        """
        Menghentikan proses tertentu berdasarkan nomor PID-nya.

        Mencoba via psutil terlebih dahulu, lalu via taskkill jika gagal.
        Mengembalikan True jika proses berhasil dihentikan.
        """
        try:
            import psutil
            proc = psutil.Process(pid)
            return self._kill_process_tree(proc)  # Gunakan fungsi kill tree yang lengkap
        except Exception as e:
            logger.warning(f"Could not kill PID={pid} via psutil: {e}")

        # psutil gagal — coba via taskkill langsung
        if sys.platform == "win32":
            try:
                import subprocess
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                result = subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True, text=True,
                    creationflags=creationflags, timeout=10,
                )
                if result.returncode == 0:
                    return True  # Berhasil
                logger.warning(
                    "taskkill by PID failed %s: %s %s",
                    pid, result.stdout.strip(), result.stderr.strip()
                )
            except Exception as e:
                logger.warning(f"taskkill by PID error {pid}: {e}")

        return False  # Semua cara gagal

    def _kill_processes_for_file(self, file_path: str) -> int:
        """
        Mencari dan menghentikan semua proses yang berkaitan dengan file tertentu.

        Memeriksa apakah ada proses yang menjalankan, membuka, atau
        mereferensikan file tersebut, lalu mematikan semuanya.

        Mengembalikan jumlah proses yang berhasil dihentikan.
        """
        try:
            import psutil
        except ImportError:
            return 0  # psutil tidak tersedia

        # Normalisasi path target untuk perbandingan yang akurat
        target_path  = os.path.normcase(os.path.abspath(file_path))
        killed_count = 0    # Hitung berapa proses yang berhasil dimatikan
        seen_pids    = set() # Hindari kill proses yang sama dua kali

        # Iterasi semua proses yang sedang berjalan
        for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
            try:
                # Lewati proses yang sudah ditangani atau proses MangoDefend sendiri
                if proc.pid in seen_pids or proc.pid == os.getpid():
                    continue

                # Kumpulkan semua path yang terkait dengan proses ini
                matches = []
                exe_path = proc.info.get("exe")
                if exe_path:
                    matches.append(exe_path)  # Path exe proses ini

                # Tambahkan semua argumen baris perintah (bisa jadi ada path file)
                cmdline = proc.info.get("cmdline") or []
                matches.extend(arg for arg in cmdline if isinstance(arg, str))

                # Tambahkan semua file yang sedang dibuka oleh proses ini
                try:
                    for opened in proc.open_files() or []:
                        matches.append(opened.path)
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass  # Tidak bisa baca daftar file yang dibuka — lewati

                # Cek apakah salah satu path cocok dengan file target
                matched = any(
                    os.path.normcase(os.path.abspath(c.strip('"'))) == target_path
                    for c in matches if c
                )

                if matched:
                    seen_pids.add(proc.pid)  # Tandai sudah ditangani
                    if self._kill_process_tree(proc):
                        killed_count += 1  # Berhasil dimatikan
                    else:
                        logger.warning(f"Could not kill process using malware file: PID={proc.pid}")

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue  # Proses sudah mati atau tidak ada izin — lewati
            except Exception as e:
                logger.debug(f"Process match failed for {file_path}: {e}")

        # Jika belum ada yang berhasil dimatikan, coba via nama image sebagai upaya terakhir
        if killed_count == 0 and self._taskkill_by_image_name(file_path):
            killed_count = 1

        return killed_count

    def _kill_all_instances(self, exe_path: str) -> int:
        """
        Menghentikan semua proses yang menjalankan file eksekutabel yang sama.

        Berguna untuk memastikan tidak ada salinan malware yang masih berjalan
        meski dengan proses atau nama yang berbeda.

        Mengembalikan jumlah instance yang berhasil dihentikan.
        """
        try:
            import psutil
        except ImportError:
            return 0

        # Normalisasi path target
        target_path  = os.path.normcase(os.path.abspath(exe_path))
        killed_count = 0

        # Iterasi semua proses dan cari yang menjalankan exe yang sama
        for proc in psutil.process_iter(["pid", "exe"]):
            try:
                if proc.pid == os.getpid():
                    continue  # Jangan kill diri sendiri
                proc_exe = proc.info.get("exe") or ""
                if not proc_exe:
                    continue  # Proses tanpa exe (proses sistem) — lewati
                # Bandingkan path exe proses dengan target
                if os.path.normcase(os.path.abspath(proc_exe)) == target_path:
                    if self._kill_process_tree(proc):
                        killed_count += 1
                    else:
                        logger.warning(f"Failed to kill instance PID={proc.pid}: {exe_path}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                logger.debug(f"Instance-kill check failed for {exe_path}: {e}")

        if killed_count:
            logger.warning(f"Kill all instances: {killed_count} process(es) for {exe_path}")

        return killed_count

    # ================================================================
    # KARANTINA
    # Memindahkan file berbahaya ke folder aman agar tidak bisa dijalankan
    # ================================================================

    def _quarantine_file(self, file_path: str) -> bool:
        """
        Memindahkan file berbahaya ke folder karantina agar tidak bisa diakses.

        File diberi nama baru dengan tambahan timestamp dan ekstensi
        ".quarantined" agar mudah diidentifikasi. Jika file masih digunakan
        oleh proses lain, fungsi ini akan mencoba menghentikan proses tersebut
        terlebih dahulu sebelum memindahkan file.

        Jika karantina benar-benar tidak bisa dilakukan, file dihapus permanen.
        """
        try:
            src = Path(file_path)
            if not src.exists():
                logger.warning(f"[QUARANTINE] Source file not found, cannot move: {file_path}")
                return False  # File sudah tidak ada — mungkin sudah dihapus sebelumnya

            # Pastikan folder karantina sudah ada
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)

            # Buat nama file karantina: timestamp_namafile.quarantined
            # Contoh: 1718123456_malware.exe.quarantined
            timestamp      = int(time.time())
            quarantine_name = f"{timestamp}_{src.name}.quarantined"
            dest           = self.quarantine_dir / quarantine_name

            last_err = None
            # Coba pindahkan file hingga 12 kali (masing-masing jeda 0.5 detik = total maks 6 detik)
            for attempt in range(12):
                try:
                    shutil.move(str(src), str(dest))  # Pindahkan file ke karantina
                    self.stats["files_quarantined"] += 1  # Catat statistik
                    logger.info(f"Quarantined: {src.name} → {dest}")
                    return True  # Berhasil, keluar dari fungsi
                except (PermissionError, OSError) as e:
                    last_err = e  # Simpan error terakhir
                    # Setiap percobaan ke-0, 4, 8 — coba matikan proses yang menahan file
                    if attempt in (0, 4, 8):
                        # FIXED: Jangan sweep open_files() semua proses saat retry karantina.
                        # Cukup hentikan instance exe/nama image yang sama agar retry tetap cepat.
                        self._kill_all_instances(str(src))
                        self._taskkill_by_image_name(str(src))
                    logger.debug(f"Quarantine attempt {attempt+1} blocked, retrying... ({e})")
                    time.sleep(0.5)  # Tunggu sebentar sebelum coba lagi

            # Semua percobaan habis — lemparkan error terakhir
            raise last_err

        except Exception as e:
            logger.error(f"Failed to quarantine {file_path}: {e}")
            # Karantina gagal total — hapus file secara permanen sebagai pilihan terakhir
            try:
                os.remove(file_path)
                logger.info(f"Deleted malware: {file_path}")
                return False
            except Exception:
                logger.error(f"Could not delete malware file: {file_path}")
                return False

    # ================================================================
    # FUNGSI PEMBANTU
    # ================================================================

    def _get_default_paths(self) -> List[str]:
        """
        Mendapatkan daftar semua drive lokal yang tersedia di Windows
        untuk dijadikan target pemantauan default.

        Di sistem non-Windows, mengembalikan root "/" sebagai gantinya.
        """
        if sys.platform == "win32":
            drives = []
            # GetLogicalDrives mengembalikan bitmask: bit ke-0 = A:, bit ke-2 = C:, dst.
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for index in range(26):  # 26 huruf alphabet untuk drive A: sampai Z:
                if bitmask & (1 << index):  # Cek apakah bit drive ini aktif
                    drive      = f"{chr(65 + index)}:\\"  # chr(65) = 'A', chr(67) = 'C', dst.
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
                    # Tipe 2 = removable (flashdisk), tipe 3 = fixed (HDD/SSD)
                    # Hanya pantau drive yang bisa diakses
                    if drive_type in (2, 3) and os.path.exists(drive):
                        drives.append(drive)
            return drives
        return ["/"]  # Di Linux/Mac, pantau dari root

    def _should_ignore_path(self, file_path: str) -> bool:
        """
        Memeriksa apakah file atau folder ini harus DILEWATI saat pemindaian.

        File dilewati jika:
        - Berada di folder sistem yang dikecualikan (Windows, Program Files, dll.)
        - Memiliki ekstensi yang ada di daftar putih atau SKIP_EXTENSIONS
        - Berada di dalam folder karantina MangoDefend sendiri

        Mengembalikan True jika file harus dilewati (diabaikan).
        """
        try:
            path        = Path(file_path)
            # Ambil semua bagian path dalam huruf kecil untuk perbandingan case-insensitive
            lower_parts = {part.lower() for part in path.parts}
            # Cek apakah ada bagian path yang cocok dengan folder yang dikecualikan
            if lower_parts & EXCLUDED_DIR_NAMES:
                return True  # Lewati — file ada di folder sistem
            ext = path.suffix.lower()  # Ambil ekstensi file
            # Cek apakah ekstensi ada di whitelist atau daftar skip
            if ext in self.whitelist_extensions or ext in SKIP_EXTENSIONS:
                return True  # Lewati — ekstensi tidak berbahaya
            # Cek apakah file ada di dalam folder karantina MangoDefend sendiri
            quarantine = str(self.quarantine_dir.resolve()).lower()
            current    = str(path.resolve()).lower()
            if current.startswith(quarantine):
                return True  # Lewati — ini file karantina, jangan dipindai lagi
        except Exception:
            return True  # Jika ada error saat cek, lebih aman diabaikan
        return False  # File ini perlu dipindai

    def _is_system_process(self, exe_path: str) -> bool:
        """
        Memeriksa apakah proses ini adalah proses sistem Windows yang tidak perlu dipindai.

        Proses dari folder Windows, Program Files, atau proses MangoDefend sendiri
        dianggap aman dan tidak perlu diperiksa.

        Mengembalikan True jika ini adalah proses sistem.
        """
        exe_lower    = exe_path.lower()
        # Daftar folder sistem yang dianggap terpercaya
        system_paths = [
            os.environ.get("SYSTEMROOT", "C:\\Windows").lower(),          # C:\Windows
            os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files")).lower(),  # C:\Program Files
            os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")).lower(),
        ]
        try:
            import psutil
            # Cek apakah exe ini adalah MangoDefend sendiri
            own_exe = psutil.Process(os.getpid()).exe().lower()
            if exe_lower == own_exe:
                return True  # Jangan scan diri sendiri
        except Exception:
            pass
        # Cek apakah exe ada di salah satu folder sistem
        for sys_path in system_paths:
            if exe_lower.startswith(sys_path):
                return True  # Ini adalah proses sistem, lewati

        return False  # Bukan proses sistem, perlu dipindai

    def is_running(self) -> bool:
        """Mengembalikan True jika perlindungan real-time sedang aktif."""
        return self.running

    def get_mode(self) -> str:
        """Mengembalikan mode perlindungan yang sedang aktif (misalnya 'pseudo-blocking')."""
        return self.mode

    def get_stats(self) -> dict:
        """
        Mengambil statistik perlindungan real-time terkini untuk ditampilkan di dasbor.

        Termasuk jumlah file yang dipindai, malware yang terdeteksi,
        proses yang dihentikan, waktu aktif, dan ukuran cache.
        """
        # Hitung berapa lama proteksi sudah berjalan
        uptime = 0
        if self.stats["start_time"]:
            uptime = time.time() - self.stats["start_time"]  # Waktu sekarang - waktu mulai

        # Gabungkan statistik utama dengan info tambahan (uptime, ukuran cache, jumlah kunci)
        return {
            **self.stats,                              # Semua statistik utama
            "uptime_seconds": round(uptime, 1),        # Waktu aktif dalam detik
            "cache_size":     len(self.scan_cache),    # Berapa file sudah di-cache
            "active_locks":   len(self._active_locks), # Berapa file sedang dikunci
        }


# ================================================================
# Titik Masuk CLI (untuk pengujian langsung dari terminal)
# ================================================================

if __name__ == "__main__":
    # Konfigurasi logging agar pesan muncul di terminal
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Fungsi yang dipanggil saat malware terdeteksi (untuk mode CLI/test)
    def on_malware(file_path, result):
        print(f"\n🚨 MALWARE ALERT!")
        print(f"File: {file_path}")
        print(f"Result: {result.get('result', 'Unknown')}")
        print(f"Confidence: {result.get('confidence', 0):.1%}")

    # Buat instance perlindungan real-time
    protection = RealtimeProtection(
        scan_delay=2,
        on_malware_detected=on_malware,
    )

    # Aktifkan perlindungan
    protection.start()

    print(f"\n🛡️ Real-time protection running (mode: {protection.get_mode()})")
    print("Press Ctrl+C to stop\n")

    try:
        # Loop utama — tampilkan statistik setiap 10 detik
        while True:
            time.sleep(10)
            stats = protection.get_stats()
            print(
                f"[Stats] Scanned: {stats['files_scanned']} | "
                f"Blocked: {stats['files_blocked']} | "
                f"Malware: {stats['malware_detected']} | "
                f"Killed: {stats['processes_killed']} | "
                f"Locks: {stats['active_locks']}"
            )
    except KeyboardInterrupt:
        print("\nStopping...")
        protection.stop()  # Matikan proteksi dengan rapi
