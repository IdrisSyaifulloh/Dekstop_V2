"""
Config Manager — membaca dan menyimpan pengaturan aplikasi.

Semua pengaturan disimpan dalam file config.ini di folder utama aplikasi.
Jika file belum ada, pengaturan bawaan akan dibuat secara otomatis.
File config.ini menggunakan format teks biasa sehingga bisa dibuka
dan diedit dengan Notepad jika diperlukan.
"""
import configparser
import os
from pathlib import Path
from typing import Any, Optional


class ConfigManager:
    """
    Pengelola pengaturan aplikasi yang membaca dan menyimpan file config.ini.

    Kelas ini bertindak sebagai "pintu masuk" tunggal ke semua pengaturan
    aplikasi. Setiap bagian kode yang membutuhkan pengaturan cukup memanggil
    kelas ini, tanpa perlu tahu di mana file disimpan atau format detailnya.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Siapkan pengelola pengaturan dan muat file konfigurasi.

        Jika lokasi file tidak ditentukan, aplikasi akan mencari config.ini
        di folder utama program (dua tingkat di atas file ini).
        Jika file belum ada, nilai bawaan akan dibuat secara otomatis.
        """
        if config_path is None:
            # Cari folder utama aplikasi: naik dua tingkat dari lokasi file ini
            # Contoh: core/config_manager.py → naik ke core/ → naik ke root/
            app_dir = Path(__file__).parent.parent
            config_path = app_dir / "config.ini"

        # Simpan lokasi file sebagai string untuk digunakan saat membaca/menyimpan
        self.config_path = str(config_path)

        # ConfigParser adalah pembaca file .ini bawaan Python
        self.config = configparser.ConfigParser()

        # Muat pengaturan dari file, atau buat pengaturan bawaan jika belum ada
        self._load()

    def _load(self):
        """
        Muat pengaturan dari file. Jika file belum ada, buat pengaturan bawaan.

        Ini dipanggil otomatis saat objek ConfigManager pertama kali dibuat.
        """
        if os.path.exists(self.config_path):
            # File ada: baca isinya dan muat ke dalam objek config
            self.config.read(self.config_path)
        else:
            # File belum ada (pertama kali dijalankan): buat nilai-nilai bawaan
            self._create_default()

    def _create_default(self):
        """
        Buat file config.ini baru dengan nilai-nilai bawaan yang wajar.

        Nilai bawaan dipilih agar aplikasi langsung bisa berjalan tanpa
        konfigurasi manual dari pengguna. Setiap nilai memiliki alasan:
        """
        # Bagian [Backend]: pengaturan koneksi ke server
        self.config['Backend'] = {
            # Alamat server lokal — 'localhost' berarti server di komputer yang sama
            # Port 8000 adalah port default yang umum untuk server pengembangan
            'url': 'http://localhost:8000',

            # Batas waktu menunggu respons server: 10 detik cukup untuk koneksi lokal
            # Jika server tidak merespons dalam 10 detik, dianggap gagal
            'timeout': '10',

            # Jumlah percobaan ulang jika koneksi gagal: 3 kali cukup tanpa membuat
            # pengguna menunggu terlalu lama
            'retry_attempts': '3',

            # Pengganda waktu tunggu antar percobaan ulang (exponential backoff)
            # Percobaan ke-1: langsung, ke-2: tunggu 2 detik, ke-3: tunggu 4 detik
            'retry_backoff': '2.0'
        }

        # Bagian [Sync]: pengaturan sinkronisasi data ke server
        self.config['Sync'] = {
            # Aktifkan sinkronisasi secara default agar data terkirim ke server
            'enabled': 'true',

            # Kirim data ke server setiap 30 detik — cukup sering tanpa terlalu
            # membebani koneksi internet
            'interval': '30',

            # Kirim maksimal 50 data sekaligus — cukup efisien tanpa membuat
            # permintaan HTTP terlalu besar
            'batch_size': '50',

            # Tampung maksimal 1000 data di antrian sebelum yang lama dihapus
            # untuk mencegah memori habis jika server lama tidak bisa dihubungi
            'max_queue_size': '1000'
        }

        # Bagian [App]: pengaturan umum perilaku aplikasi
        self.config['App'] = {
            # Jalankan sinkronisasi otomatis saat aplikasi dibuka
            'auto_sync': 'true',

            # Tampilkan notifikasi sistem (pop-up di pojok layar) saat ada peringatan
            'show_notifications': 'true',

            # Level detail log: 'INFO' mencatat kejadian penting tanpa terlalu banyak
            # pesan teknis. Gunakan 'DEBUG' untuk melihat lebih banyak detail.
            'log_level': 'INFO'
        }

        # Simpan nilai-nilai bawaan ini ke file config.ini di disk
        self.save()

    def save(self):
        """
        Simpan pengaturan yang ada di memori ke dalam file config.ini.

        Dipanggil setiap kali ada pengaturan yang berubah agar perubahan
        tersebut tidak hilang saat aplikasi ditutup.
        """
        # Buka file dengan mode tulis ('w') — file lama akan ditimpa seluruhnya
        with open(self.config_path, 'w') as f:
            self.config.write(f)

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """
        Ambil nilai TEKS dari pengaturan, atau kembalikan nilai cadangan jika tidak ditemukan.

        Ini adalah metode paling dasar — mengembalikan string apa adanya.
        Untuk angka atau benar/salah, gunakan get_int(), get_float(), atau get_bool().

        Contoh: get('Backend', 'url') → 'http://localhost:8000'
        """
        try:
            # Coba baca nilai dari section dan key yang diminta
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            # Section atau key tidak ditemukan → kembalikan nilai cadangan
            return fallback

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """
        Ambil nilai ANGKA BULAT dari pengaturan, atau kembalikan nilai cadangan jika tidak valid.

        Berbeda dengan get() yang mengembalikan string, metode ini langsung
        mengonversi nilai ke tipe integer (bilangan bulat, misalnya 10, 30, 1000).
        Jika nilai di file bukan angka (misalnya 'abc'), dikembalikan fallback.

        Contoh: get_int('Backend', 'timeout') → 10
        """
        try:
            # getint() membaca nilai sebagai bilangan bulat secara langsung
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            # Section/key tidak ada, atau isinya bukan angka bulat yang valid
            return fallback

    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """
        Ambil nilai ANGKA DESIMAL dari pengaturan, atau kembalikan nilai cadangan jika tidak valid.

        Digunakan untuk nilai yang mengandung koma desimal seperti 2.0, 1.5, dsb.
        Berbeda dengan get_int() yang hanya menerima bilangan bulat.

        Contoh: get_float('Backend', 'retry_backoff') → 2.0
        """
        try:
            # getfloat() membaca nilai sebagai angka desimal (float)
            return self.config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            # Section/key tidak ada, atau isinya bukan angka desimal yang valid
            return fallback

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """
        Ambil nilai BENAR/SALAH dari pengaturan, atau kembalikan nilai cadangan jika tidak valid.

        Metode ini mengenali berbagai cara menulis benar/salah dalam file .ini:
        - Benar: 'true', 'yes', 'on', '1'
        - Salah: 'false', 'no', 'off', '0'
        Ini berbeda dengan get() yang hanya mengembalikan string 'true'/'false'.

        Contoh: get_bool('Sync', 'enabled') → True
        """
        try:
            # getboolean() membaca nilai sebagai boolean (benar/salah) secara langsung
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            # Section/key tidak ada, atau isinya bukan nilai boolean yang dikenali
            return fallback

    def set(self, section: str, key: str, value: Any):
        """
        Simpan sebuah nilai ke pengaturan. Bagian (section) dibuat otomatis jika belum ada.

        Nilai apapun akan dikonversi ke string terlebih dahulu karena
        file .ini hanya menyimpan teks. Perubahan belum tersimpan ke disk
        hingga metode save() dipanggil.
        """
        # Buat section baru jika belum ada (agar tidak error saat langsung set nilai)
        if not self.config.has_section(section):
            self.config.add_section(section)

        # Simpan nilai setelah dikonversi ke string (semua nilai di .ini adalah teks)
        self.config.set(section, key, str(value))

    def get_backend_url(self) -> str:
        """
        Kembalikan alamat URL server backend yang dikonfigurasi.

        Digunakan oleh modul lain untuk mengetahui ke mana harus mengirim data.
        Nilai 'http://localhost:8000' digunakan jika pengaturan tidak ditemukan.
        """
        return self.get('Backend', 'url', 'http://localhost:8000')

    def get_backend_timeout(self) -> int:
        """
        Kembalikan batas waktu permintaan ke server backend (dalam detik).

        Jika server tidak merespons dalam waktu ini, permintaan dianggap gagal
        dan akan dicoba ulang sesuai pengaturan retry_attempts.
        """
        return self.get_int('Backend', 'timeout', 10)

    def get_sync_interval(self) -> int:
        """
        Kembalikan jeda waktu antar sinkronisasi data (dalam detik).

        Semakin kecil angkanya, semakin sering data dikirim ke server
        (tapi lebih banyak menggunakan bandwidth internet).
        """
        return self.get_int('Sync', 'interval', 30)

    def get_sync_batch_size(self) -> int:
        """
        Kembalikan jumlah maksimal data yang dikirim dalam satu sesi sinkronisasi.

        Mengirim terlalu banyak sekaligus bisa membuat permintaan HTTP terlalu besar,
        sedangkan terlalu sedikit berarti butuh lebih banyak permintaan.
        """
        return self.get_int('Sync', 'batch_size', 50)

    def is_sync_enabled(self) -> bool:
        """
        Periksa apakah sinkronisasi data ke server diaktifkan.

        Mengembalikan True jika sinkronisasi aktif, False jika dimatikan.
        Sinkronisasi dimatikan jika pengguna tidak ingin mengirim data ke server.
        """
        return self.get_bool('Sync', 'enabled', True)

    def is_auto_sync(self) -> bool:
        """
        Periksa apakah sinkronisasi otomatis berjalan saat aplikasi dibuka.

        Jika True, sinkronisasi dimulai segera setelah aplikasi menyala.
        Jika False, sinkronisasi hanya berjalan saat pengguna memintanya.
        """
        return self.get_bool('App', 'auto_sync', True)

    def get_log_level(self) -> str:
        """
        Kembalikan tingkat detail pencatatan log (misalnya 'INFO' atau 'DEBUG').

        'INFO': hanya mencatat kejadian penting (default untuk pengguna biasa)
        'DEBUG': mencatat semua detail teknis (berguna untuk mencari masalah)
        'WARNING': hanya mencatat peringatan dan error
        """
        return self.get('App', 'log_level', 'INFO')


# ─── POLA SINGLETON ──────────────────────────────────────────────────────────
# Instance tunggal ConfigManager yang dibagikan ke seluruh bagian aplikasi.
# Dimulai dengan None, akan diisi saat get_config() pertama kali dipanggil.
_config_instance: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """
    Kembalikan satu instance ConfigManager yang digunakan bersama oleh seluruh aplikasi.

    Ini adalah implementasi pola desain "Singleton" — memastikan hanya ada
    SATU objek ConfigManager yang hidup sepanjang aplikasi berjalan. Manfaatnya:
    - Tidak perlu membuat objek baru setiap kali membutuhkan pengaturan
    - Perubahan pengaturan di satu tempat langsung terlihat di tempat lain
    - Hemat memori karena file config.ini hanya dibaca sekali

    Cara kerja:
    - Pertama kali dipanggil: _config_instance masih None → buat objek baru
    - Panggilan berikutnya: _config_instance sudah ada → kembalikan yang sama
    """
    # Gunakan variabel global agar instance bisa diakses dan diubah dari luar fungsi
    global _config_instance

    if _config_instance is None:
        # Belum pernah dibuat sebelumnya: buat instance baru dan simpan
        _config_instance = ConfigManager()

    # Kembalikan instance yang sudah ada (baik baru dibuat maupun yang lama)
    return _config_instance


# ─── PENGUJIAN CEPAT ─────────────────────────────────────────────────────────
# Blok ini hanya berjalan jika file ini dijalankan langsung (bukan diimpor)
if __name__ == "__main__":
    config = ConfigManager()

    print(f"Backend URL: {config.get_backend_url()}")
    print(f"Sync interval: {config.get_sync_interval()}s")
    print(f"Sync enabled: {config.is_sync_enabled()}")
    print(f"Log level: {config.get_log_level()}")
