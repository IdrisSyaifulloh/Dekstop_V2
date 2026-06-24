"""
Notification Manager — Pengelola notifikasi desktop lintas platform.

Modul ini menampilkan peringatan di layar pengguna ketika malware terdeteksi,
model baru tersedia, atau status proteksi berubah. Notifikasi tampil sebagai
pop-up kecil di sudut layar tanpa mengganggu pekerjaan pengguna.

Mendukung tiga sistem operasi:
- Windows : menggunakan pustaka win10toast (pop-up di pojok kanan bawah)
- macOS   : menggunakan perintah osascript (notifikasi sistem bawaan Apple)
- Linux   : menggunakan perintah notify-send (notifikasi desktop standar)

Jika semua cara gagal, pesan dicetak langsung ke konsol sebagai cadangan.
"""
import logging
from typing import Optional
from datetime import datetime
import platform

# Logger untuk mencatat kejadian dan error tanpa mengganggu alur utama
logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Pengelola notifikasi desktop yang bekerja di Windows, macOS, dan Linux.

    Kelas ini secara otomatis mendeteksi sistem operasi yang digunakan
    dan memilih cara yang tepat untuk menampilkan notifikasi, sehingga
    kode pemanggil tidak perlu tahu detail teknis setiap platform.
    """

    def __init__(self, app_name: str = "MangoDefend"):
        """
        Siapkan pengelola notifikasi dan inisialisasi pustaka sesuai sistem operasi.

        app_name digunakan sebagai nama pengirim notifikasi yang terlihat di layar.
        """
        # Simpan nama aplikasi untuk ditampilkan di judul notifikasi
        self.app_name = app_name

        # Deteksi sistem operasi: "Windows", "Darwin" (macOS), atau "Linux"
        self.system = platform.system()

        # Daftar riwayat notifikasi yang pernah ditampilkan (disimpan di memori)
        self.notification_history = []

        # Muat pustaka notifikasi yang sesuai untuk sistem operasi ini
        self._init_platform()

    def _init_platform(self):
        """
        Muat pustaka notifikasi khusus untuk sistem operasi yang terdeteksi.

        Setiap sistem operasi memiliki cara berbeda untuk menampilkan notifikasi:
        - Windows menggunakan pustaka pihak ketiga 'win10toast'
        - macOS menggunakan skrip AppleScript melalui perintah 'osascript'
        - Linux menggunakan perintah 'notify-send' yang biasanya sudah terpasang
        """
        if self.system == "Windows":
            try:
                # Coba impor pustaka win10toast untuk notifikasi Toast Windows 10/11
                from win10toast import ToastNotifier

                # Buat objek penampil notifikasi Windows dan simpan untuk dipakai nanti
                self.toaster = ToastNotifier()
                logger.info("Notifikasi Windows berhasil diinisialisasi")
            except ImportError:
                # Pustaka win10toast tidak terpasang — gunakan fallback (cetak ke konsol)
                logger.warning("win10toast tidak tersedia, menggunakan cadangan")
                self.toaster = None

        elif self.system == "Darwin":
            # macOS tidak perlu pustaka tambahan — cukup menjalankan skrip AppleScript
            # via perintah 'osascript' yang sudah ada di setiap Mac
            logger.info("Notifikasi macOS berhasil diinisialisasi")

        else:
            # Linux menggunakan perintah 'notify-send' yang biasanya sudah tersedia
            # di sebagian besar distribusi Linux desktop (Ubuntu, Fedora, dll.)
            logger.info("Notifikasi Linux berhasil diinisialisasi")

    def show_malware_alert(
        self,
        file_path: str,
        file_name: str,
        threat_level: str = "High"
    ):
        """
        Tampilkan peringatan desktop ketika malware terdeteksi di komputer.

        Peringatan ini muncul segera saat proteksi real-time menemukan file
        berbahaya, sehingga pengguna langsung tahu ada ancaman meski sedang
        mengerjakan hal lain di komputer. Selain ditampilkan, kejadian ini
        juga dicatat ke dalam riwayat notifikasi untuk referensi mendatang.

        file_path    : lokasi lengkap file yang terdeteksi (misalnya C:\\Downloads\\virus.exe)
        file_name    : nama file saja tanpa path (misalnya virus.exe)
        threat_level : tingkat bahaya — biasanya "High", "Medium", atau "Low"
        """
        # Susun judul notifikasi yang mencantumkan tingkat ancaman
        title = f"Malware Terdeteksi - Ancaman {threat_level}"

        # Susun isi pesan yang informatif tentang file yang berbahaya
        message = (
            f"File: {file_name}\n"
            f"Lokasi: {file_path}\n\n"
            f"Tindakan diperlukan!"
        )

        # Tampilkan notifikasi dengan ikon peringatan (segitiga kuning)
        self.show_notification(title, message, icon="warning")

        # Catat kejadian ini ke dalam riwayat notifikasi di memori
        # Berguna untuk menampilkan daftar ancaman yang pernah terdeteksi
        self.notification_history.append({
            "type":         "malware_alert",    # Jenis notifikasi
            "file_path":    file_path,          # Lokasi file berbahaya
            "file_name":    file_name,          # Nama file berbahaya
            "threat_level": threat_level,       # Tingkat bahaya
            "timestamp":    datetime.now().isoformat()  # Waktu deteksi
        })

    def show_model_update(self, version: str, size_mb: float):
        """
        Tampilkan notifikasi bahwa versi model AI yang lebih baru tersedia untuk diunduh.

        Notifikasi ini bersifat informatif — tidak mendesak seperti peringatan malware.
        Pengguna bisa memilih kapan ingin memperbarui model.

        version : nomor versi model baru (misalnya "v4")
        size_mb : ukuran file model dalam megabyte (dibulatkan 1 angka desimal)
        """
        title = "Pembaruan Model Tersedia"
        message = (
            f"Versi {version} telah tersedia\n"
            f"Ukuran: {size_mb:.1f} MB\n\n"
            f"Perbarui sekarang?"
        )

        # Gunakan ikon informasi (lingkaran biru dengan huruf i)
        self.show_notification(title, message, icon="info")

    def show_protection_status(self, enabled: bool):
        """
        Tampilkan notifikasi ketika status proteksi real-time berubah.

        Dipanggil saat pengguna mengaktifkan atau menonaktifkan proteksi
        melalui tampilan aplikasi, agar pengguna mendapat konfirmasi visual
        bahwa perubahan berhasil diterapkan.

        enabled : True jika proteksi baru saja diaktifkan, False jika dimatikan
        """
        if enabled:
            # Proteksi baru saja dihidupkan
            title   = "Proteksi Diaktifkan"
            message = "Proteksi real-time kini aktif melindungi komputer Anda"
        else:
            # Proteksi baru saja dimatikan
            title   = "Proteksi Dinonaktifkan"
            message = "Proteksi real-time dimatikan — komputer Anda tidak terlindungi"

        self.show_notification(title, message, icon="info")

    def show_notification(
        self,
        title:    str,
        message:  str,
        icon:     str = "info",
        duration: int = 10
    ):
        """
        Tampilkan notifikasi menggunakan cara yang sesuai dengan sistem operasi.

        Ini adalah metode inti yang dipanggil oleh semua metode notifikasi lainnya.
        Metode ini secara otomatis memilih cara yang tepat berdasarkan sistem operasi,
        dan jika semua cara gagal, pesan akan dicetak langsung ke konsol.

        title    : judul notifikasi (teks tebal di bagian atas)
        message  : isi pesan notifikasi
        icon     : jenis ikon — "info" (biru), "warning" (kuning), atau "error" (merah)
        duration : berapa detik notifikasi ditampilkan sebelum menghilang otomatis
        """
        try:
            if self.system == "Windows":
                # Gunakan Toast Notification khusus Windows
                self._show_windows(title, message, duration)
            elif self.system == "Darwin":
                # Gunakan AppleScript khusus macOS
                self._show_macos(title, message)
            else:
                # Gunakan notify-send khusus Linux
                self._show_linux(title, message, icon)
        except Exception as e:
            # Jika semua cara gagal, cetak ke konsol sebagai cadangan terakhir
            logger.error(f"Gagal menampilkan notifikasi: {e}")
            # Cetak pesan dengan garis pemisah agar mudah dibaca di konsol
            print(f"\n{'='*50}")
            print(f"{title}")
            print(f"{message}")
            print(f"{'='*50}\n")

    def _show_windows(self, title: str, message: str, duration: int):
        """
        Tampilkan notifikasi Toast di Windows menggunakan pustaka win10toast.

        Notifikasi Toast adalah pop-up kecil yang muncul di pojok kanan bawah
        layar selama beberapa detik lalu menghilang sendiri. Jika pustaka
        win10toast tidak terpasang, gunakan cadangan (cetak ke konsol).

        threaded=True berarti notifikasi ditampilkan di thread terpisah sehingga
        tidak memblokir proses utama aplikasi selama menunggu notifikasi hilang.
        """
        if self.toaster:
            try:
                # Tampilkan notifikasi Toast — threaded agar tidak memblokir aplikasi
                self.toaster.show_toast(
                    title,
                    message,
                    duration=duration,   # Berapa detik sebelum menghilang otomatis
                    threaded=True        # Jalankan di thread terpisah agar non-blocking
                )
            except Exception as e:
                logger.error(f"Error notifikasi Windows: {e}")
                # Jika win10toast error, gunakan cadangan konsol
                self._fallback_notification(title, message)
        else:
            # win10toast tidak terpasang — langsung gunakan cadangan
            self._fallback_notification(title, message)

    def _show_macos(self, title: str, message: str):
        """
        Tampilkan notifikasi di macOS menggunakan perintah osascript.

        osascript adalah perintah bawaan macOS untuk menjalankan skrip AppleScript.
        Skrip 'display notification' membuat notifikasi muncul di Notification Center
        (pojok kanan atas layar Mac). Ini tidak memerlukan instalasi pustaka tambahan.
        """
        import subprocess

        # Susun skrip AppleScript untuk menampilkan notifikasi macOS
        # Tanda kutip di dalam string Python menggunakan escape backslash
        script = f'display notification "{message}" with title "{title}"'

        try:
            # Jalankan skrip AppleScript melalui perintah osascript di terminal
            # check=True agar exception dilempar jika perintah gagal
            # capture_output=True agar output perintah tidak muncul di konsol
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True
            )
        except Exception as e:
            logger.error(f"Error notifikasi macOS: {e}")
            # Jika osascript gagal (misalnya izin ditolak), gunakan cadangan
            self._fallback_notification(title, message)

    def _show_linux(self, title: str, message: str, icon: str):
        """
        Tampilkan notifikasi di Linux menggunakan perintah notify-send.

        notify-send adalah perintah standar di sebagian besar distribusi Linux
        desktop untuk mengirim notifikasi ke server notifikasi sistem (seperti
        dunst, notify-osd, atau GNOME Shell notifications).

        Nama ikon menggunakan konvensi Freedesktop Icon Naming Specification —
        nama-nama standar yang dikenali oleh hampir semua tema ikon Linux.
        """
        import subprocess

        # Peta dari nama ikon internal ke nama ikon standar Freedesktop
        icon_map = {
            "info":    "dialog-information",  # Lingkaran biru dengan huruf 'i'
            "warning": "dialog-warning",      # Segitiga kuning dengan tanda seru
            "error":   "dialog-error"         # Lingkaran merah dengan tanda silang
        }

        # Dapatkan nama ikon yang sesuai; gunakan ikon info jika tidak dikenali
        icon_name = icon_map.get(icon, "dialog-information")

        try:
            # Jalankan perintah notify-send dengan opsi:
            # -i : tentukan ikon yang digunakan
            subprocess.run(
                ["notify-send", "-i", icon_name, title, message],
                check=True,
                capture_output=True
            )
        except FileNotFoundError:
            # Perintah notify-send tidak ditemukan — distribusi Linux tanpa desktop?
            logger.warning("notify-send tidak ditemukan di sistem ini")
            self._fallback_notification(title, message)
        except Exception as e:
            logger.error(f"Error notifikasi Linux: {e}")
            self._fallback_notification(title, message)

    def _fallback_notification(self, title: str, message: str):
        """
        Cetak notifikasi ke konsol sebagai cadangan terakhir.

        Digunakan ketika semua cara platform-spesifik gagal atau tidak tersedia.
        Garis pemisah '=' membuat pesan mudah terlihat di antara output lain di konsol.
        """
        # Cetak garis pemisah panjang agar notifikasi mudah dibaca di konsol
        print(f"\n{'='*60}")
        print(f"NOTIFIKASI: {title}")
        print(f"{message}")
        print(f"{'='*60}\n")

    def get_history(self, limit: int = 10):
        """
        Kembalikan sejumlah notifikasi terakhir dari riwayat.

        Menggunakan slice [-limit:] untuk mengambil 'limit' elemen terakhir
        dari daftar riwayat. Misalnya: get_history(5) → 5 notifikasi terbaru.
        Berguna untuk menampilkan log aktivitas di halaman riwayat aplikasi.

        limit : jumlah maksimal notifikasi yang dikembalikan (default 10)
        """
        # Slice negatif [-limit:] mengambil elemen dari akhir daftar
        return self.notification_history[-limit:]

    def clear_history(self):
        """
        Hapus semua catatan riwayat notifikasi dari memori.

        Riwayat hanya tersimpan di memori (bukan di disk), sehingga
        otomatis terhapus saat aplikasi ditutup. Metode ini berguna
        jika pengguna ingin mengosongkan riwayat tanpa menutup aplikasi.
        """
        # clear() menghapus semua elemen dari daftar tanpa menghapus objek daftarnya
        self.notification_history.clear()


# ─── PENGUJIAN CEPAT ─────────────────────────────────────────────────────────
# Blok ini hanya berjalan jika file ini dijalankan langsung (bukan diimpor)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Buat objek pengelola notifikasi
    notif = NotificationManager()

    # Uji peringatan malware
    notif.show_malware_alert(
        file_path="C:\\Users\\test\\Downloads\\virus.exe",
        file_name="virus.exe",
        threat_level="High"
    )

    import time
    time.sleep(2)

    # Uji notifikasi pembaruan model
    notif.show_model_update(version="v4", size_mb=45.2)

    time.sleep(2)

    # Uji notifikasi status proteksi
    notif.show_protection_status(enabled=True)

    # Tampilkan riwayat notifikasi yang telah dikirim
    print("\nRiwayat Notifikasi:")
    for item in notif.get_history():
        print(f"  - {item}")
