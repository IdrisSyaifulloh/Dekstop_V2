"""
Scan Thread — menjalankan pemindaian malware di latar belakang.

Dengan menggunakan thread terpisah, tampilan aplikasi tetap lancar
dan tidak membeku saat proses pemindaian sedang berlangsung.
Thread ini berkomunikasi dengan tampilan melalui sinyal (Signal),
sehingga progres pemindaian bisa ditampilkan secara langsung.
"""

from PySide6.QtCore import QThread, Signal
from core.scanner import MalwareScanner
from pathlib import Path


# ─── KONSTANTA PERFORMA ───────────────────────────────────────────────────────

# Jeda antar tahap pemindaian file tunggal (dalam milidetik).
# Nilai 0 berarti tidak ada jeda — proses berjalan secepat mungkin.
# Nilai bisa dinaikkan (misalnya 200) jika ingin animasi progres terlihat lebih halus.
STAGE_DELAY_MS = 0

# Jeda antar file saat full scan (dalam milidetik).
# Nilai 0 berarti tidak ada jeda antar file — scan secepat mungkin.
# Nilai bisa dinaikkan untuk memberi napas pada CPU agar tidak terlalu panas.
FILE_SCAN_DELAY_MS = 0

# Batas maksimal jumlah file yang dipindai dalam satu sesi full scan.
# Dibatasi 2000 agar proses tidak berjalan terlalu lama pada perangkat
# dengan storage besar (ratusan ribu file).
MAX_FILES_TO_SCAN = 2000

# Jeda setelah proses pengumpulan daftar file selesai (dalam milidetik).
# Digunakan agar pengguna sempat melihat pesan "Ditemukan X file"
# sebelum proses pemindaian dimulai.
COLLECTION_PAUSE_MS = 300

# Daftar ekstensi file yang akan disertakan saat full scan perangkat.
# Hanya file-file jenis ini yang akan dipindai karena:
# - File executable (.exe, .dll, .bat, dll.) adalah target utama malware
# - File dokumen (.pdf, .doc, dll.) bisa mengandung makro berbahaya
# - File arsip (.zip, .rar) bisa menyembunyikan malware di dalamnya
# - File gambar (.png, .jpg, dll.) digunakan dalam dataset malware visualization
SCAN_EXTENSIONS = frozenset({
    # File eksekutabel dan skrip — paling sering digunakan malware
    '.exe', '.dll', '.bat', '.cmd', '.ps1', '.vbs', '.js',
    # File paket aplikasi — bisa mengandung installer berbahaya
    '.jar', '.apk', '.msi', '.scr', '.com',
    # File arsip/kompresi — bisa menyembunyikan file berbahaya di dalamnya
    '.zip', '.rar', '.7z',
    # File gambar — digunakan dalam dataset malware visualization
    '.png', '.jpg', '.jpeg', '.bmp',
    # File dokumen — bisa mengandung makro atau skrip tersembunyi
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
})


class ScanThread(QThread):
    """
    Thread terpisah untuk menjalankan pemindaian tanpa membuat tampilan aplikasi membeku.

    QThread adalah kelas dari framework Qt yang memungkinkan kode berjalan
    di thread berbeda dari tampilan utama. Tanpa thread terpisah, tombol dan
    animasi di aplikasi akan "membeku" saat model AI sedang bekerja.
    """

    # Sinyal yang dikirim ketika pemindaian selesai, berisi dictionary hasil scan
    finished = Signal(dict)

    # Sinyal yang dikirim jika terjadi error yang tidak terduga
    error = Signal(str)

    # Sinyal progres: mengirim persentase (0-100) dan pesan status terkini
    progress = Signal(int, str)

    def __init__(self, file_path: str, is_full_scan: bool = False):
        """
        Simpan target pemindaian dan siapkan pemindai yang akan digunakan.

        file_path  : lokasi file atau folder yang ingin dipindai
        is_full_scan : True = pindai seluruh folder/perangkat,
                       False = pindai hanya satu file saja
        """
        super().__init__()
        # Simpan path target yang akan dipindai
        self.file_path = file_path
        # Tandai apakah ini scan menyeluruh atau scan satu file
        self.is_full_scan = is_full_scan
        # Buat objek pemindai yang akan menjalankan model AI
        self.scanner = MalwareScanner()
        # Flag untuk membatalkan pemindaian di tengah jalan
        self.is_canceled = False

    def cancel(self):
        """
        Tandai pemindaian agar berhenti secepat mungkin.

        Penghentian tidak langsung terjadi — thread akan berhenti saat
        ia memeriksa flag is_canceled di awal setiap iterasi atau tahap.
        """
        self.is_canceled = True

    def run(self):
        """
        Pilih mode pemindaian lalu kirimkan hasilnya ke tampilan melalui sinyal.

        Metode run() adalah metode khusus QThread yang dijalankan secara otomatis
        ketika thread dimulai dengan .start(). Jangan panggil run() langsung.

        Pemilihan mode:
        - is_full_scan=True  → pindai banyak file dari folder/perangkat
        - is_full_scan=False → pindai hanya satu file yang ditentukan
        """
        try:
            if self.is_full_scan:
                # Mode full scan: telusuri seluruh folder dan pindai semua file
                self._run_full_scan()
            else:
                # Mode single scan: pindai satu file tertentu saja
                self._run_single_scan()
        except Exception as e:
            # Jika terjadi error tak terduga, kirim pesan error ke tampilan
            self.error.emit(str(e))

    def _run_single_scan(self):
        """
        Pindai satu file dan kirimkan progres bertahap ke tampilan.

        Progres dikirim dalam beberapa tahap agar pengguna dapat melihat
        perkembangan pemindaian secara langsung di layar. Setiap tahap
        menggambarkan langkah yang sedang dikerjakan oleh model AI.
        """
        # Daftar tahap pemindaian: (persentase_progres, pesan_status)
        # Tahap-tahap ini berjalan SEBELUM pemindaian sebenarnya dimulai
        # agar pengguna tahu bahwa aplikasi sedang bersiap-siap
        stages = [
            (10, "Memulai pemindaian..."),    # Persiapan awal
            (30, "Menganalisis file..."),      # Membaca isi file
            (50, "Memproses dengan AI..."),    # Model AI sedang bekerja
            (75, "Mendeteksi ancaman..."),     # Model AI menganalisis pola
            (95, "Menyelesaikan analisis...")  # Hampir selesai
        ]

        # Kirim setiap tahap progres ke tampilan satu per satu
        for value, msg in stages:
            # Cek apakah pengguna sudah menekan tombol "Batal"
            if self.is_canceled:
                return  # Keluar dari metode ini, thread akan berhenti
            # Kirim progres ke tampilan (tampilan akan memperbarui progress bar)
            self.progress.emit(value, msg)
            # Tunggu sebentar sesuai STAGE_DELAY_MS sebelum tahap berikutnya
            self.msleep(STAGE_DELAY_MS)

        try:
            # Jalankan pemindaian file yang sesungguhnya menggunakan model AI
            result = self.scanner.scan_file(self.file_path)
        except Exception as e:
            # Jika file tidak bisa dipindai (rusak, tidak ada izin, dll.),
            # tetap kirim hasil dengan status "Unknown" agar tampilan tidak hang
            self.finished.emit({
                "is_full_scan": False,
                "result": "Unknown",
                "confidence": 0,
                "details": f"File tidak dapat dipindai: {e}"
            })
            return

        # Tandai progres 100% dan kirim pesan selesai
        self.progress.emit(100, "Selesai")
        # Kirim hasil pemindaian ke tampilan melalui sinyal finished
        self.finished.emit(result)

    def _run_full_scan(self):
        """
        Pindai banyak file dari folder atau perangkat lalu buat ringkasan hasilnya.

        Proses terdiri dari dua fase:
        1. PENGUMPULAN: Telusuri semua subfolder dan kumpulkan file yang cocok
        2. PEMINDAIAN: Pindai setiap file satu per satu dan catat hasilnya

        Hasil akhir berisi jumlah file aman, file berbahaya, file gagal dipindai,
        dan daftar lengkap ancaman yang ditemukan.
        """
        # Buat objek Path dari string agar mudah bernavigasi di folder
        base_path = Path(self.file_path)

        # Beritahu pengguna bahwa proses pengumpulan daftar file sedang berlangsung
        self.progress.emit(5, "Mengumpulkan file untuk dipindai...")

        # Daftar file yang akan dipindai (akan diisi selama fase pengumpulan)
        files_to_scan = []

        try:
            if base_path.is_dir():
                # Jika target adalah folder: telusuri semua subfolder secara rekursif
                # rglob("*") artinya "cari semua file di semua subfolder"
                for f in base_path.rglob("*"):
                    # Cek apakah pengguna sudah menekan tombol "Batal"
                    if self.is_canceled:
                        return

                    # Hanya tambahkan file (bukan folder) dengan ekstensi yang didukung
                    if f.is_file() and f.suffix.lower() in SCAN_EXTENSIONS:
                        files_to_scan.append(f)

                    # Berhenti mengumpulkan jika sudah mencapai batas maksimal
                    # untuk mencegah proses yang terlalu lama pada storage besar
                    if MAX_FILES_TO_SCAN and len(files_to_scan) >= MAX_FILES_TO_SCAN:
                        break
            else:
                # Jika target bukan folder (misalnya drive C:\), tambahkan langsung
                files_to_scan.append(base_path)
        except PermissionError:
            # Abaikan folder yang tidak bisa diakses karena izin sistem
            pass

        # Hitung total file yang berhasil dikumpulkan
        total_files = len(files_to_scan)

        # Jika tidak ada file yang cocok, langsung kirim hasil kosong
        if total_files == 0:
            self.finished.emit({
                "is_full_scan": True,
                "details": "Tidak ada file yang cocok untuk dipindai.",
                "files_scanned": 0,
                "malware_found": 0,
                "corrupt_count": 0
            })
            return

        # Beritahu pengguna berapa file yang ditemukan
        self.progress.emit(10, f"Ditemukan {total_files} file")

        # Tunggu sebentar agar pengguna sempat membaca pesan di atas
        self.msleep(COLLECTION_PAUSE_MS)

        # Inisialisasi penghitung dan daftar hasil
        safe_files = 0       # Jumlah file yang dinyatakan aman
        malware_found = 0    # Jumlah file yang terdeteksi sebagai malware
        corrupt_files = []   # Daftar file yang gagal dipindai (rusak/tidak bisa dibaca)
        threats_found = []   # Daftar detail ancaman yang ditemukan

        # Pindai setiap file satu per satu
        for idx, file_path in enumerate(files_to_scan, start=1):
            # Cek apakah pengguna sudah menekan tombol "Batal" sebelum setiap file
            if self.is_canceled:
                return

            # Hitung persentase progres:
            # - Rentang 10-95% digunakan untuk fase pemindaian (85% dari total)
            # - Rumus: 10 + (indeks_file / total_file) × 85
            percent = 10 + int((idx / total_files) * 85)

            # Kirim progres ke tampilan dengan nama file yang sedang dipindai
            self.progress.emit(
                percent,
                f"Memindai {idx}/{total_files}: {file_path.name}"
            )

            try:
                # Pindai file menggunakan model AI
                # is_full_scan=True mengaktifkan mode aggressive (lebih banyak thread CPU)
                result = self.scanner.scan_file(str(file_path))

                if result.get("result") == "Malware":
                    # File terdeteksi sebagai malware: tambahkan ke daftar ancaman
                    malware_found += 1
                    threats_found.append({
                        "file": str(file_path),
                        "name": file_path.name,
                        "threat": "Malware"
                    })
                else:
                    # File dinyatakan aman: tambahkan ke penghitung aman
                    safe_files += 1

            except Exception as e:
                # Jika file tidak bisa dipindai karena alasan apapun,
                # catat sebagai "file rusak" beserta pesan errornya
                corrupt_files.append({
                    "file": str(file_path),
                    "name": file_path.name,
                    "error": str(e)
                })

            # Tunggu sebentar sesuai FILE_SCAN_DELAY_MS sebelum file berikutnya
            self.msleep(FILE_SCAN_DELAY_MS)

        # Susun ringkasan hasil pemindaian seluruh file
        summary = {
            # Tandai ini sebagai hasil full scan agar tampilan bisa menampilkan dengan benar
            "is_full_scan": True,
            # Total file yang berhasil dikumpulkan dan dicoba dipindai
            "files_scanned": total_files,
            # Jumlah file yang dinyatakan aman
            "safe_count": safe_files,
            # Jumlah file yang terdeteksi sebagai malware
            "malware_found": malware_found,
            # Jumlah file yang gagal dipindai
            "corrupt_count": len(corrupt_files),
            # Daftar detail setiap ancaman yang ditemukan
            "threats": threats_found,
            # Daftar file yang gagal dipindai beserta alasannya
            "corrupt_files": corrupt_files,
            # Teks ringkasan yang akan ditampilkan di layar pengguna
            "details": (
                f"Pemindaian selesai!\n\n"
                f"Total file dipindai: {total_files}\n"
                f"File aman: {safe_files}\n"
                f"Ancaman terdeteksi: {malware_found}\n"
                f"File gagal dipindai: {len(corrupt_files)}"
            )
        }

        # Tandai progres 100% dan kirim pesan selesai
        self.progress.emit(100, "Selesai")
        # Kirim ringkasan hasil ke tampilan melalui sinyal finished
        self.finished.emit(summary)
