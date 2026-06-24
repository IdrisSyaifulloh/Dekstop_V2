"""
Scan Thread — Thread latar belakang untuk memindai malware.
Digunakan untuk scan satu file (ScanThread) dan scan banyak file sekaligus (BatchScanThread).
Thread ini berjalan di belakang layar agar UI tidak membeku saat scan berlangsung.
"""

# ================================================================
# Import pustaka yang dibutuhkan
# ================================================================
import os           # Untuk operasi file: cek keberadaan file, baca path, dll.
import threading    # Untuk membuat dan mengelola thread tambahan
from queue import Queue, Empty  # Antrean thread-safe untuk komunikasi antar thread
from pathlib import Path        # Cara modern Python untuk bekerja dengan path file
from PySide6.QtCore import QThread, Signal  # QThread = thread Qt, Signal = sinyal ke UI


# ================================================================
# ScanThread — Thread untuk memindai SATU file
# Dipakai saat user klik "Scan File" dari halaman scan
# ================================================================

class ScanThread(QThread):
    """Thread untuk memindai satu file malware di latar belakang."""

    # Sinyal yang dikirim ke UI setelah scan selesai (membawa hasil scan)
    finished = Signal(dict)
    # Sinyal yang dikirim ke UI jika terjadi error (membawa pesan error)
    error = Signal(str)
    # Sinyal progress: angka persentase (0-100) dan pesan status
    progress = Signal(int, str)

    def __init__(self, file_path):
        """Siapkan thread dengan path file yang akan dipindai."""
        super().__init__()
        self.file_path = file_path   # Path file yang akan dipindai
        self.scanner = None          # Objek scanner (dibuat saat run() dipanggil)
        self.is_canceled = False     # Flag untuk membatalkan scan di tengah jalan

    def run(self):
        """
        Jalankan proses scan ketika thread dimulai.

        Mengirim update progress bertahap ke UI agar loading bar bergerak,
        lalu memanggil scanner AI untuk hasil sebenarnya.
        """
        try:
            # Import scanner di sini (bukan di __init__) agar tidak memperlambat startup
            from core.scanner import MalwareScanner
            self.scanner = MalwareScanner()  # Buat instance scanner AI

            # Daftar tahap progress yang ditampilkan di UI selama scan berlangsung
            # Format: (persentase, pesan_status)
            stages = [
                (10, "Memulai pemindaian..."),       # Tahap awal
                (25, "Menganalisis file..."),          # Membaca file
                (40, "Memproses dengan AI..."),        # Kirim ke model AI
                (60, "Mendeteksi malware..."),         # Model sedang mendeteksi
                (80, "Menyelesaikan analisis..."),     # Hampir selesai
                (95, "Hampir selesai...")              # Sedikit lagi
            ]

            # Kirim setiap tahap progress ke UI dengan jeda kecil agar terasa natural
            for value, message in stages:
                if self.is_canceled:
                    return  # Hentikan jika user membatalkan scan

                self.progress.emit(value, message)  # Kirim update progress ke UI
                self.msleep(200)                    # Tunggu 200ms sebelum tahap berikutnya

            # Lakukan scan sebenarnya menggunakan model AI
            result = self.scanner.scan_file(self.file_path)

            # Kirim progress 100% — scan selesai
            self.progress.emit(100, "Selesai!")
            self.msleep(200)  # Jeda kecil agar tampilan 100% sempat terlihat

            # Kirim hasil scan ke UI melalui sinyal finished
            self.finished.emit(result)

        except Exception as e:
            # Jika terjadi error tak terduga, kirim pesan error ke UI
            self.error.emit(str(e))

    def cancel(self):
        """Minta pembatalan scan — thread akan berhenti di tahap berikutnya."""
        self.is_canceled = True  # Set flag, thread akan cek ini di setiap iterasi


# ================================================================
# BatchScanThread — Thread untuk memindai BANYAK file sekaligus
# Dipakai saat user klik "Scan Folder" atau "Scan Perangkat"
# ================================================================

class BatchScanThread(QThread):
    """Thread untuk memindai banyak file (scan folder atau scan seluruh perangkat)."""

    # Sinyal yang dikirim setiap kali satu file selesai dipindai (membawa hasil file itu)
    file_scanned = Signal(dict)
    # Sinyal yang dikirim setelah SEMUA file selesai dipindai (membawa ringkasan total)
    batch_finished = Signal(dict)
    # Sinyal jika terjadi error fatal (bukan per-file, tapi error keseluruhan)
    error = Signal(str)
    # Sinyal progress: persentase (0-100) dan pesan status
    progress = Signal(int, str)
    # Sinyal khusus jika jumlah file melebihi batas maksimum scan perangkat
    limit_reached = Signal(dict)

    # Daftar ekstensi file yang akan dipindai dalam mode batch
    # Hanya tipe file yang berpotensi berbahaya yang di-scan
    SCAN_EXTENSIONS = frozenset({
        ".exe", ".dll", ".scr", ".bat", ".cmd",   # Program dan skrip Windows
        ".ps1", ".vbs", ".js", ".jar", ".msi",    # Skrip dan installer
        ".com", ".pif", ".wsf", ".hta", ".cpl",   # Tipe program lainnya
        ".sys", ".drv", ".bin", ".dat",            # Driver dan file biner
    })

    # Batas maksimum file yang dipindai saat scan perangkat penuh
    # Agar scan tidak berjalan terlalu lama dan memberatkan sistem
    _DEVICE_SCAN_FILE_LIMIT = 2000

    def __init__(self, folder_path: str = None, full_device: bool = False):
        """
        Siapkan thread batch scan.

        folder_path: path folder yang akan dipindai (untuk scan folder)
        full_device: True jika ingin scan seluruh perangkat (Downloads, Desktop, dll.)
        """
        super().__init__()
        self.folder_path = folder_path      # Path folder target scan
        self.full_device = full_device      # Mode scan seluruh perangkat atau tidak
        self.scanner = None                 # Objek scanner AI (dibuat saat run())
        self.is_canceled = False            # Flag pembatalan scan

        # Variabel untuk mengelola batas jumlah file saat scan perangkat
        self._enforce_device_limit = True           # Apakah batas file masih diberlakukan
        self._limit_decision_event = threading.Event()  # Event untuk menunggu keputusan user
        self._limit_continue_all = False            # Apakah user memilih lanjut semua
        self._limit_prompt_sent = False             # Apakah sinyal batas sudah dikirim ke UI

    def run(self):
        """
        Jalankan proses scan batch ketika thread dimulai.

        Menggunakan teknik streaming: file dikumpulkan dan dipindai BERSAMAAN
        tanpa menunggu semua file terkumpul dulu. Ini membuat hasil scan
        muncul lebih cepat di UI.
        """
        try:
            # Import scanner di sini agar tidak memperlambat startup
            from core.scanner import MalwareScanner
            self.scanner = MalwareScanner()
            # aggressive=True = muat model dalam mode yang lebih sensitif mendeteksi malware
            self.scanner.load_model(aggressive=True)

            # Kirim progress awal ke UI
            self.progress.emit(0, "Mengumpulkan dan memindai file...")

            # Antrean untuk komunikasi antara thread pengumpul file dan thread scan
            # maxsize=256 membatasi memori yang dipakai antrean
            file_queue = Queue(maxsize=256)
            # Objek khusus sebagai penanda "pengumpulan file sudah selesai"
            done_marker = object()
            # Mutex untuk mengakses variabel statistik dari dua thread secara aman
            stats_lock = threading.Lock()
            found_count = 0      # Total file yang ditemukan (terus bertambah)
            collect_errors = 0   # Jumlah error saat mengumpulkan file

            def collector():
                """
                Thread pengumpul file — berjalan paralel dengan thread scan.
                Menemukan file dan memasukkannya ke antrean satu per satu.
                """
                nonlocal found_count, collect_errors  # Akses variabel dari scope luar
                try:
                    # Iterasi setiap file yang ditemukan oleh _iter_files()
                    for file_path in self._iter_files():
                        if self.is_canceled:
                            break  # Hentikan jika user membatalkan

                        # Masukkan file ke antrean (retry sampai berhasil atau dibatalkan)
                        queued = False
                        while not self.is_canceled:
                            try:
                                # block=False dengan timeout — jangan tunggu terlalu lama
                                file_queue.put(file_path, timeout=0.2)
                                queued = True
                                break  # Berhasil dimasukkan, lanjut ke file berikutnya
                            except Exception:
                                continue  # Antrean penuh, coba lagi

                        if not queued:
                            break  # Dibatalkan saat menunggu

                        # Tambah hitungan file yang ditemukan (thread-safe)
                        with stats_lock:
                            found_count += 1
                except Exception:
                    collect_errors += 1  # Catat error pengumpulan
                finally:
                    # Kirim tanda selesai ke thread scan agar tahu pengumpulan sudah tuntas
                    while not self.is_canceled:
                        try:
                            file_queue.put(done_marker, timeout=0.2)
                            break  # Berhasil kirim tanda selesai
                        except Exception:
                            continue  # Coba lagi jika antrean penuh

            # Jalankan collector di thread terpisah agar bisa berjalan paralel dengan scan
            collector_thread = threading.Thread(
                target=collector,
                daemon=True,              # Otomatis mati saat program utama ditutup
                name="BatchFileCollector" # Nama thread untuk memudahkan debugging
            )
            collector_thread.start()  # Mulai mengumpulkan file

            # Variabel statistik hasil scan
            scanned = 0        # Jumlah file yang sudah dipindai
            malware_count = 0  # Jumlah malware yang ditemukan
            clean_count = 0    # Jumlah file bersih
            error_count = 0    # Jumlah file yang gagal dipindai
            results = []       # Daftar hasil scan malware (untuk ringkasan akhir)

            # Loop utama: ambil file dari antrean dan pindai satu per satu
            while not self.is_canceled:
                try:
                    # Ambil satu file dari antrean (tunggu maksimal 0.2 detik)
                    item = file_queue.get(timeout=0.2)
                except Empty:
                    # Antrean kosong sementara — tampilkan progress dan tunggu
                    with stats_lock:
                        current_found = found_count
                    self.progress.emit(
                        min(95, 5 + scanned),  # Progress tidak pernah melebihi 95% sampai benar-benar selesai
                        f"Mencari file... ditemukan {current_found}, discan {scanned}"
                    )
                    continue  # Kembali ke atas loop dan coba ambil lagi

                # Cek apakah ini tanda "selesai" dari collector
                if item is done_marker:
                    break  # Semua file sudah dikumpulkan — keluar dari loop

                # Item adalah path file biasa
                file_path = item
                if self.is_canceled:
                    break  # Cek lagi setelah ambil dari antrean

                # Hitung progres berdasarkan file yang dipindai vs total yang ditemukan
                with stats_lock:
                    current_found = max(found_count, scanned + 1)  # Minimal current+1

                # Hitung persentase progress (5% sampai 95%)
                pct = min(95, 5 + int((scanned / max(current_found, 1)) * 90))
                fname = Path(file_path).name  # Ambil hanya nama file (tanpa path lengkap)
                self.progress.emit(
                    pct,
                    f"Memindai {scanned + 1}/{current_found}: {fname}"  # Tampilkan "X/Y: nama_file"
                )

                try:
                    # Pindai file menggunakan AI
                    # is_full_scan=True jika ini scan perangkat penuh (mode lebih teliti)
                    result = self.scanner.scan_file(file_path, is_full_scan=self.full_device)
                    if result is None:
                        continue  # Scanner tidak bisa memproses file ini, lewati

                    scanned += 1  # Tambah hitungan file yang dipindai
                    result_type = result.get("result", "Unknown")  # Ambil label hasil

                    # Kirim hasil file ini ke UI segera (agar muncul di tabel secara real-time)
                    self.file_scanned.emit(result)

                    # Kategorikan hasil
                    if result_type == "Malware":
                        malware_count += 1      # Tambah hitungan malware
                        results.append(result)  # Simpan untuk ringkasan akhir
                    else:
                        clean_count += 1        # Tambah hitungan file bersih

                except (OSError, PermissionError):
                    # Error akses file (dikunci oleh proses lain, tidak ada izin, dll.)
                    error_count += 1
                except Exception:
                    # Error lain per-file — catat tapi jangan hentikan scan keseluruhan
                    error_count += 1

            # Tunggu thread collector selesai (maks 1 detik)
            collector_thread.join(timeout=1)

            # Ambil total file yang ditemukan setelah collector selesai
            with stats_lock:
                total = found_count

            # Kasus khusus: tidak ada file yang ditemukan sama sekali
            if total == 0 and scanned == 0:
                self.progress.emit(100, "Tidak ada file yang perlu discan")
                # Kirim ringkasan kosong ke UI
                self.batch_finished.emit({
                    "total": 0, "scanned": 0,
                    "malware": 0, "clean": 0, "errors": error_count + collect_errors,
                    "results": []
                })
                return  # Selesai

            # Kirim progress 100% — semua file sudah dipindai
            self.progress.emit(100, f"Selesai! {scanned} file discan")

            # Buat ringkasan akhir scan
            summary = {
                "total": total,              # Total file yang ditemukan
                "scanned": scanned,          # Total file yang berhasil dipindai
                "malware": malware_count,    # Jumlah malware yang terdeteksi
                "clean": clean_count,        # Jumlah file bersih
                "errors": error_count + collect_errors,  # Total error (scan + pengumpulan)
                "results": results,          # Daftar detail hasil malware
                "scan_limit": self._DEVICE_SCAN_FILE_LIMIT,          # Batas maksimum file
                "continued_beyond_limit": not self._enforce_device_limit,  # Apakah melampaui batas
            }
            # Kirim ringkasan ke UI untuk ditampilkan di dialog hasil
            self.batch_finished.emit(summary)

        except Exception as e:
            # Error fatal yang menghentikan seluruh proses scan
            self.error.emit(str(e))

    def _get_scan_dirs(self) -> list[Path]:
        """
        Menentukan folder-folder mana saja yang akan dipindai.

        Untuk scan folder biasa: hanya folder yang dipilih user.
        Untuk scan perangkat penuh: folder-folder yang paling berisiko
        (Downloads, Desktop, Temp, AppData, Roaming).
        """
        if self.full_device:
            # Scan perangkat: hanya folder yang paling relevan dan tidak terlalu besar
            home = Path.home()
            scan_dirs = [
                home / "Downloads",
                home / "Desktop",
                home / "Documents",
                home / "AppData" / "Local" / "Temp",
                home / "AppData" / "Local" / "Temp" / "Low",
            ]
            # Tambahkan drive lain (D:, E:, dll.) — hanya root langsung, tidak rekursif penuh
            import string, ctypes
            for letter in string.ascii_uppercase:
                if letter == "C":
                    continue
                drive = Path(f"{letter}:/")
                if drive.exists():
                    try:
                        drive_type = ctypes.windll.kernel32.GetDriveTypeW(str(drive))
                        # 2 = removable, 3 = fixed — skip network/CD/RAM drives
                        if drive_type in (2, 3):
                            scan_dirs.append(drive)
                    except Exception:
                        pass
        else:
            # Scan folder biasa: hanya scan folder yang dipilih user
            scan_dirs = [Path(self.folder_path)] if self.folder_path else []

        return scan_dirs

    def _iter_files(self):
        """
        Generator yang menghasilkan path file satu per satu saat ditemukan.

        Tidak menunggu semua file terkumpul dulu — setiap file langsung
        diserahkan ke antrean scan begitu ditemukan. Ini membuat scan
        bisa dimulai lebih awal meski pengumpulan belum selesai.
        """
        seen: set[str] = set()        # Set path file yang sudah ditemukan (untuk hindari duplikat)
        visited_dirs: set[str] = set() # Set folder yang sudah dikunjungi (untuk hindari loop)
        yielded = 0                    # Hitung total file yang sudah dihasilkan

        # Iterasi setiap folder target
        for scan_dir in self._get_scan_dirs():
            if self.is_canceled:
                break  # Hentikan jika dibatalkan
            if not scan_dir.exists():
                continue  # Lewati folder yang tidak ada

            try:
                # Jalan rekursif melalui folder dan sub-folder
                # followlinks=True = ikuti juga symbolic link / junction folder
                for root, dirs, filenames in os.walk(scan_dir, followlinks=True):
                    if self.is_canceled:
                        break  # Hentikan di setiap level jika dibatalkan

                    # Deteksi loop: cegah infinite loop dari symlink/junction yang melingkar
                    try:
                        real_root = os.path.realpath(root)  # Resolve symlink ke path asli
                    except (OSError, PermissionError):
                        real_root = root  # Jika gagal resolve, pakai path asli
                    if real_root in visited_dirs:
                        # Folder ini sudah pernah dikunjungi — ini loop!
                        dirs.clear()  # Kosongkan daftar sub-folder agar os.walk tidak masuk lebih dalam
                        continue
                    visited_dirs.add(real_root)  # Tandai folder ini sudah dikunjungi

                    # Cek batas file untuk scan perangkat penuh
                    if self.full_device and self._should_stop_at_limit(yielded):
                        return  # Batas tercapai, hentikan

                    # Proses setiap file dalam folder ini
                    for fname in filenames:
                        if self.is_canceled:
                            break  # Hentikan jika dibatalkan

                        fpath = os.path.join(root, fname)  # Gabungkan path folder + nama file

                        # Lewati file yang sudah pernah ditemukan sebelumnya
                        if fpath in seen:
                            continue
                        seen.add(fpath)  # Tandai file ini sudah ditemukan

                        try:
                            if os.path.isfile(fpath):  # Pastikan ini file (bukan folder atau symlink)
                                yielded += 1    # Tambah hitungan file yang dihasilkan
                                yield fpath     # Serahkan path file ke pemanggil (collector)
                        except (OSError, PermissionError):
                            pass  # Lewati jika tidak bisa akses

                        # Cek batas lagi di dalam loop file
                        if self.full_device and self._should_stop_at_limit(yielded):
                            return  # Batas tercapai, hentikan

            except (OSError, PermissionError):
                pass  # Lewati folder yang tidak bisa diakses (akses ditolak, dll.)

    def _collect_files(self) -> list:
        """
        Kumpulkan semua file yang akan dipindai ke dalam satu daftar.

        Catatan: Fungsi ini mengumpulkan SEMUA file dulu sebelum scan dimulai.
        Untuk performa lebih baik, gunakan _iter_files() yang streaming.
        Fungsi ini masih ada untuk keperluan kompatibilitas.
        """
        files = []
        for file_path in self._iter_files():
            files.append(file_path)  # Tambahkan setiap file ke daftar
        return files

    def _should_stop_at_limit(self, file_count: int) -> bool:
        """
        Cek apakah jumlah file sudah mencapai batas maksimum scan perangkat.

        Jika batas tercapai:
        1. Kirim sinyal ke UI agar muncul dialog konfirmasi ke user
        2. Blokir thread ini sampai user membuat keputusan
        3. Jika user memilih lanjut, hapus batas dan teruskan
        4. Jika user memilih berhenti, kembalikan True (hentikan scan)

        Mengembalikan True jika scan harus dihentikan.
        """
        # Jika batas tidak diberlakukan atau belum mencapai batas, lanjut
        if not self._enforce_device_limit or file_count < self._DEVICE_SCAN_FILE_LIMIT:
            return False

        # Batas tercapai — kirim sinyal ke UI satu kali saja
        if not self._limit_prompt_sent:
            self._limit_prompt_sent = True  # Tandai sinyal sudah dikirim
            # Kirim info ke UI: berapa batasnya dan sudah berapa file ditemukan
            self.limit_reached.emit({
                "limit": self._DEVICE_SCAN_FILE_LIMIT,
                "file_count": file_count,
            })

        # Tunggu sampai user membuat keputusan (cek setiap 0.2 detik)
        while not self._limit_decision_event.wait(timeout=0.2):
            if self.is_canceled:
                return True  # User membatalkan scan — hentikan

        # User sudah membuat keputusan — cek pilihannya
        if self._limit_continue_all:
            # User memilih lanjut — hapus batas dan jangan berhenti
            self._enforce_device_limit = False
            return False

        # User memilih berhenti — hentikan scan
        return True

    def set_limit_decision(self, continue_all: bool):
        """
        Terima keputusan dari UI tentang apakah scan harus dilanjutkan melewati batas.

        continue_all=True  → lanjutkan scan tanpa batas
        continue_all=False → hentikan scan di batas ini
        """
        self._limit_continue_all = continue_all     # Simpan keputusan user
        self._limit_decision_event.set()             # Buka blokir yang menunggu keputusan

    def cancel(self):
        """
        Batalkan scan yang sedang berjalan.

        Juga membuka blokir jika thread sedang menunggu keputusan batas file,
        agar thread tidak macet selamanya.
        """
        self.is_canceled = True              # Set flag pembatalan
        self._limit_decision_event.set()     # Buka blokir waiting agar thread bisa keluar
