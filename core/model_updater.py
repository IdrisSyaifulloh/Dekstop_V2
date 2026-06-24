"""
Model Updater — memeriksa dan mengunduh pembaruan model AI secara otomatis.

Modul ini menghubungi server untuk melihat apakah ada versi model yang lebih baru,
mengunduhnya secara bertahap (streaming), memverifikasi keutuhannya dengan hash SHA-256,
lalu menginstalnya menggantikan model lama. Model lama dicadangkan sebelum ditimpa
sehingga bisa dikembalikan jika model baru ternyata bermasalah.
"""
import json
import hashlib
import requests
import shutil
from pathlib import Path
from typing import Optional, Dict, Callable
from datetime import datetime
import logging

# Buat objek logger untuk mencatat kejadian penting ke file log aplikasi
logger = logging.getLogger(__name__)


class ModelUpdater:
    """
    Pengelola pembaruan model AI dari server backend.

    Bertanggung jawab atas seluruh siklus hidup model:
    memeriksa → mengunduh → memverifikasi → mencadangkan → menginstal → membersihkan.
    """

    def __init__(self, backend_url: str = "http://localhost:8000", models_dir: str = "models"):
        """
        Siapkan pengelola pembaruan dengan menentukan alamat server dan folder model.

        Folder model dan folder cadangan (backup) akan dibuat otomatis
        jika belum ada, sehingga tidak perlu membuat folder manual.
        """
        # Hapus garis miring di akhir URL agar tidak ada '//' saat URL digabung
        self.backend_url = backend_url.rstrip('/')

        # Konversi path folder ke objek Path untuk kemudahan navigasi
        self.models_dir = Path(models_dir)

        # Buat folder model jika belum ada; exist_ok=True agar tidak error jika sudah ada
        self.models_dir.mkdir(exist_ok=True)

        # Folder khusus untuk menyimpan cadangan model lama
        self.backup_dir = self.models_dir / "backups"

        # Buat folder cadangan jika belum ada
        self.backup_dir.mkdir(exist_ok=True)

        # File JSON yang menyimpan informasi versi model yang terpasang saat ini
        self.version_file = self.models_dir / "version.json"

    def get_current_version(self) -> Optional[Dict]:
        """
        Baca informasi versi model yang sedang terpasang.

        Strategi pembacaan versi (dua tingkat):
        1. UTAMA: Baca file version.json yang berisi metadata versi lengkap
        2. FALLBACK: Jika version.json tidak ada, tebak versi dari nama file .onnx

        Fallback diperlukan untuk kompatibilitas mundur — jika model dipasang
        secara manual tanpa melalui proses update otomatis, version.json mungkin
        tidak ada. Dalam kasus ini kita tebak versi dari nama file seperti
        "Modelv3.onnx" → versi "v3".

        Mengembalikan None jika tidak ada model sama sekali di folder.
        """
        if self.version_file.exists():
            try:
                # Buka dan baca file JSON yang berisi data versi
                with open(self.version_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                # File ada tapi rusak atau formatnya salah — catat dan lanjutkan ke fallback
                logger.error(f"Failed to read version file: {e}")

        # FALLBACK: Cari file model dengan pola nama "Modelv*.onnx" di folder models
        model_files = list(self.models_dir.glob("Modelv*.onnx"))
        if model_files:
            # Ambil file pertama yang ditemukan (biasanya hanya ada satu)
            filename = model_files[0].name

            # Ekstrak versi dari nama file:
            # "Modelv3.onnx" → hilangkan "Model" → "v3.onnx" → hilangkan ".onnx" → "v3"
            version = filename.replace("Model", "").replace(".onnx", "")

            # Kembalikan info versi minimal yang bisa digunakan untuk perbandingan
            return {
                "version": version,
                "filename": filename,
                # Gunakan waktu sekarang sebagai perkiraan tanggal instalasi
                "installed_date": datetime.now().isoformat()
            }

        # Tidak ada file model apapun — kembalikan None
        return None

    def check_for_updates(self) -> Optional[Dict]:
        """
        Hubungi server untuk memeriksa apakah ada versi model yang lebih baru.

        Cara perbandingan versi:
        - Versi berbentuk string seperti 'v3', 'v4', 'v10', dll.
        - Perbandingan menggunakan operator > pada string (perbandingan leksikografis)
        - Ini berarti 'v4' > 'v3' benar, tapi 'v10' < 'v9' secara string!
        - Untuk versi singkat seperti ini, perbandingan string sudah cukup.

        Mengembalikan dictionary berisi status pembaruan, atau None jika
        server tidak dapat dihubungi (offline atau URL salah).
        """
        try:
            # Kirim permintaan GET ke endpoint server untuk mendapatkan info versi terbaru
            # timeout=10 berarti jika server tidak merespons dalam 10 detik, hentikan
            response = requests.get(
                f"{self.backend_url}/model/latest",
                timeout=10
            )
            # raise_for_status() akan melempar error jika server merespons dengan kode error
            # (400, 404, 500, dll.) sehingga kita bisa tangani di blok except
            response.raise_for_status()

            # Konversi respons JSON dari server menjadi dictionary Python
            latest = response.json()

            # Baca versi model yang saat ini terpasang di komputer pengguna
            current = self.get_current_version()

            if current is None:
                # Belum ada model apapun terpasang → pembaruan pasti diperlukan
                return {
                    "update_available": True,
                    "current_version": None,
                    "latest_version": latest['version'],
                    "latest_info": latest
                }

            # Ambil string versi; 'v0' digunakan sebagai nilai default teraman
            # jika key 'version' tidak ada dalam data
            current_ver = current.get('version', 'v0')
            latest_ver  = latest.get('version', 'v0')

            # Bandingkan versi secara leksikografis (perbandingan string)
            # Contoh: 'v4' > 'v3' → True → ada pembaruan
            if latest_ver > current_ver:
                return {
                    "update_available": True,
                    "current_version": current_ver,
                    "latest_version": latest_ver,
                    "latest_info": latest
                }

            # Versi sama atau lebih lama dari yang terpasang → tidak perlu update
            return {
                "update_available": False,
                "current_version": current_ver,
                "latest_version": latest_ver
            }

        except Exception as e:
            # Gagal menghubungi server (tidak ada internet, URL salah, server mati, dll.)
            logger.error(f"Failed to check for updates: {e}")
            return None

    def download_model(
        self,
        version: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Optional[Path]:
        """
        Unduh versi model tertentu dari server secara bertahap (streaming).

        Mengapa streaming dan bukan unduh sekaligus?
        - File model bisa berukuran puluhan atau ratusan MB
        - Mengunduh sekaligus akan memakan seluruh memori RAM sebelum disimpan ke disk
        - Streaming mengunduh dan menyimpan ke disk potongan demi potongan (8192 byte sekali)
          sehingga RAM yang digunakan tetap kecil meski file besar

        File disimpan ke lokasi sementara (.tmp) agar jika unduhan gagal di tengah jalan,
        file model asli tidak rusak atau tertimpa setengah-setengah.

        progress_callback dipanggil setiap kali satu potongan berhasil diunduh,
        sehingga tampilan bisa memperbarui progress bar secara real-time.

        Mengembalikan lokasi file sementara (.tmp) atau None jika unduhan gagal.
        """
        try:
            # Susun URL lengkap endpoint pengunduhan dengan nomor versi
            url = f"{self.backend_url}/model/download/{version}"

            # Mulai permintaan HTTP dengan stream=True agar data tidak langsung
            # dimuat ke memori tapi mengalir secara bertahap
            # timeout=30 untuk unduhan yang lebih lama dari pemeriksaan versi
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            # Baca ukuran total file dari header HTTP (jika server menyediakannya)
            # Nilai 0 digunakan jika server tidak memberitahu ukuran file
            total_size = int(response.headers.get('content-length', 0))

            # Tentukan lokasi file sementara: nama file + ekstensi .tmp
            # File .tmp adalah "file setengah jadi" yang akan diganti nama jika selesai
            temp_file = self.models_dir / f"Model{version}.onnx.tmp"

            # Penghitung byte yang sudah berhasil diunduh
            downloaded = 0

            # Buka file sementara dalam mode tulis biner
            with open(temp_file, 'wb') as f:
                # Unduh dan tulis data dalam potongan 8192 byte (8 KB) per iterasi
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        # Tulis potongan ini ke file sementara di disk
                        f.write(chunk)

                        # Perbarui penghitung total byte yang sudah diunduh
                        downloaded += len(chunk)

                        # Jika ada fungsi callback progres, panggil dengan info terkini
                        # Tampilan akan menggunakan ini untuk memperbarui progress bar
                        if progress_callback:
                            progress_callback(downloaded, total_size)

            logger.info(f"Downloaded model {version}: {downloaded} bytes")
            # Kembalikan lokasi file sementara untuk diproses selanjutnya
            return temp_file

        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            return None

    def verify_model(self, file_path: Path, expected_hash: str) -> bool:
        """
        Periksa keutuhan file model dengan membandingkan sidik jari SHA-256-nya.

        Mengapa kita perlu memverifikasi?
        - Unduhan melalui internet bisa rusak di tengah jalan karena gangguan koneksi
        - Seseorang mungkin memodifikasi file di server (serangan man-in-the-middle)
        - Hash SHA-256 adalah "sidik jari" unik: file asli dan file rusak akan
          menghasilkan hash yang berbeda sama sekali

        File dibaca per potongan 4096 byte karena:
        - File model bisa sangat besar (puluhan hingga ratusan MB)
        - Membaca seluruh file sekaligus bisa menguras RAM
        - 4096 byte = 4 KB = ukuran satu blok disk, efisien untuk I/O

        Mengembalikan True jika file utuh dan cocok, False jika ada perbedaan.
        """
        try:
            # Buat objek penghitung hash SHA-256
            sha256_hash = hashlib.sha256()

            # Buka file dalam mode baca biner
            with open(file_path, "rb") as f:
                # Baca file per 4096 byte hingga habis (sentinel b"" = akhir file)
                for byte_block in iter(lambda: f.read(4096), b""):
                    # Masukkan setiap potongan ke dalam penghitung hash
                    sha256_hash.update(byte_block)

            # Dapatkan hash akhir sebagai string heksadesimal 64 karakter
            actual_hash = sha256_hash.hexdigest()

            # Bandingkan hash file yang diunduh dengan hash yang diberikan server
            # lower() digunakan agar perbandingan tidak case-sensitive (A vs a)
            if actual_hash.lower() == expected_hash.lower():
                logger.info("Model verification successful")
                return True  # File utuh dan sesuai
            else:
                logger.error(f"Hash mismatch: {actual_hash} != {expected_hash}")
                return False  # File rusak atau telah dimodifikasi

        except Exception as e:
            logger.error(f"Failed to verify model: {e}")
            return False

    def backup_current_model(self) -> bool:
        """
        Buat salinan cadangan (backup) dari model yang sedang terpasang.

        Mengapa perlu backup?
        - Jika model baru ternyata bermasalah (crash, akurasi turun drastis, dll.),
          kita bisa mengembalikan model lama melalui fungsi rollback()

        Nama file cadangan diberi cap waktu (timestamp) agar unik dan tidak
        tertimpa cadangan sebelumnya. Contoh: Modelv3.onnx.20240615_143022.bak

        Hanya 2 cadangan terbaru yang disimpan karena:
        - Setiap file model bisa puluhan MB — menyimpan terlalu banyak boros disk
        - 2 cadangan sudah cukup untuk rollback ke versi sebelumnya
        - Cadangan lebih lama tidak lagi berguna karena model terus berkembang
        """
        try:
            # Baca info model yang sedang terpasang
            current = self.get_current_version()

            if not current:
                # Tidak ada model terpasang sama sekali — tidak ada yang perlu dicadangkan
                return True

            # Susun path ke file model yang sedang aktif
            current_file = self.models_dir / current['filename']

            if not current_file.exists():
                # File model tidak ditemukan di disk (mungkin sudah dihapus manual)
                return True

            # Buat cap waktu untuk nama file cadangan
            # Format: YYYYMMDD_HHMMSS, contoh: 20240615_143022
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Susun nama file cadangan: nama_asli.timestamp.bak
            backup_file = self.backup_dir / f"{current['filename']}.{timestamp}.bak"

            # Salin file model ke folder backup (shutil.copy2 juga menyalin metadata)
            shutil.copy2(current_file, backup_file)
            logger.info(f"Backed up model to {backup_file}")

            # Hapus cadangan lama jika sudah lebih dari 2 cadangan tersimpan
            self._cleanup_old_backups(keep=2)

            return True

        except Exception as e:
            logger.error(f"Failed to backup model: {e}")
            return False

    def install_model(self, temp_file: Path, version: str, metadata: Dict) -> bool:
        """
        Pasang model baru dari file sementara ke lokasi resminya.

        Urutan langkah instalasi (penting untuk keamanan data):
        1. BACKUP: Cadangkan model lama terlebih dahulu
           → Jika instalasi gagal setelah ini, model lama masih bisa dikembalikan
        2. PINDAH: Pindahkan file sementara (.tmp) ke lokasi final (.onnx)
           → shutil.move lebih aman dari rename karena bekerja lintas drive/partisi
        3. CATAT: Simpan metadata versi baru ke version.json
           → Ini memudahkan pemeriksaan versi di kemudian hari

        Mengapa file sementara (.tmp) dulu?
        - Jika aplikasi tiba-tiba mati saat unduhan berlangsung, file .tmp yang
          tidak lengkap tidak akan menggantikan model yang sedang berjalan
        """
        try:
            # LANGKAH 1: Cadangkan model yang sedang aktif sebelum diganti
            if not self.backup_current_model():
                # Peringatan saja — instalasi tetap dilanjutkan meski backup gagal
                logger.warning("Backup failed, continuing anyway...")

            # LANGKAH 2: Tentukan nama file final dan pindahkan dari lokasi sementara
            final_file = self.models_dir / f"Model{version}.onnx"

            # Pindahkan file .tmp ke nama final — setelah ini model baru sudah aktif
            shutil.move(str(temp_file), str(final_file))

            # LANGKAH 3: Simpan informasi versi ke file JSON untuk referensi mendatang
            version_info = {
                "version": version,
                "filename": final_file.name,
                # Catat kapan model ini dipasang
                "installed_date": datetime.now().isoformat(),
                # Hash SHA-256 untuk verifikasi di masa mendatang
                "sha256": metadata.get('sha256'),
                # Ukuran file dalam byte
                "size": metadata.get('size'),
                # Catatan perubahan dari versi ini
                "release_notes": metadata.get('release_notes')
            }

            # Tulis info versi ke file JSON dengan indentasi agar mudah dibaca
            with open(self.version_file, 'w') as f:
                json.dump(version_info, f, indent=2)

            logger.info(f"Installed model {version} successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to install model: {e}")
            return False

    def rollback(self) -> bool:
        """
        Kembalikan model ke versi cadangan terakhir.

        Berguna jika model baru ternyata bermasalah — misalnya crash,
        akurasi jauh berkurang, atau format output berubah sehingga
        aplikasi tidak bisa membacanya.

        Mengembalikan True jika pemulihan berhasil, False jika gagal.
        """
        try:
            # Ambil semua file cadangan, diurutkan dari yang terbaru (reverse=True)
            backups = sorted(self.backup_dir.glob("*.bak"), reverse=True)

            if not backups:
                # Tidak ada cadangan tersimpan — tidak bisa rollback
                logger.error("No backup found for rollback")
                return False

            # Ambil cadangan yang paling baru (indeks 0 setelah diurutkan terbalik)
            latest_backup = backups[0]

            # Ekstrak nama file asli dari nama cadangan:
            # "Modelv3.onnx.20240615_143022.bak" → stem = "Modelv3.onnx.20240615_143022"
            # → split('.')[0] = "Modelv3" → + ".onnx" = "Modelv3.onnx"
            original_name = latest_backup.stem.split('.')[0] + '.onnx'
            restore_path  = self.models_dir / original_name

            # Salin file cadangan ke lokasi model aktif (timpa jika ada)
            shutil.copy2(latest_backup, restore_path)

            logger.info(f"Rolled back to {original_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to rollback: {e}")
            return False

    def _cleanup_old_backups(self, keep: int = 2):
        """
        Hapus file cadangan lama, pertahankan hanya sejumlah cadangan terbaru.

        Cara kerja slice backups[keep:]:
        - backups adalah list file cadangan diurutkan dari terbaru ke terlama
        - backups[0] = cadangan terbaru, backups[1] = kedua terbaru, dst.
        - backups[keep:] = ambil semua elemen mulai dari indeks 'keep' ke akhir
        - Jika keep=2, maka backups[2:] = semua cadangan kecuali 2 yang terbaru
        - Semua cadangan dalam backups[2:] inilah yang dihapus

        Contoh: 5 cadangan [A, B, C, D, E] → keep=2 → hapus [C, D, E] → tersisa [A, B]
        """
        try:
            # Kumpulkan semua file cadangan, urutkan dari terbaru ke terlama
            backups = sorted(self.backup_dir.glob("*.bak"), reverse=True)

            # Hapus semua cadangan di luar jumlah yang ingin dipertahankan
            for backup in backups[keep:]:
                # unlink() menghapus file dari disk secara permanen
                backup.unlink()
                logger.debug(f"Removed old backup: {backup}")

        except Exception as e:
            logger.error(f"Failed to cleanup backups: {e}")

    def update_model(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict:
        """
        Jalankan seluruh proses pembaruan model secara otomatis dalam satu langkah.

        Urutan langkah lengkap:
        1. Periksa apakah ada pembaruan di server
        2. Unduh model baru jika tersedia
        3. Verifikasi integritas file yang diunduh (jika hash tersedia)
        4. Instal model baru (dengan backup otomatis model lama)

        Mengembalikan dictionary berisi:
        - "success": True/False — apakah proses berhasil
        - "message": pesan keterangan hasil proses
        - "version": versi yang berhasil dipasang (hanya jika berhasil)
        """
        # LANGKAH 1: Periksa ketersediaan pembaruan di server
        update_info = self.check_for_updates()

        if not update_info or not update_info.get('update_available'):
            # Tidak ada pembaruan — tidak perlu melanjutkan proses
            return {
                "success": False,
                "message": "No update available"
            }

        # Ambil informasi detail versi terbaru dari server
        latest_info = update_info['latest_info']
        version     = latest_info['version']

        # LANGKAH 2: Unduh model baru secara streaming (potongan demi potongan)
        temp_file = self.download_model(version, progress_callback)

        if not temp_file:
            # Unduhan gagal — hentikan proses
            return {
                "success": False,
                "message": "Download failed"
            }

        # LANGKAH 3: Verifikasi keutuhan file jika server menyediakan hash
        # Kondisi khusus: abaikan jika hash masih berupa placeholder "PUT_YOUR_HASH_HERE"
        if 'sha256' in latest_info and latest_info['sha256'] != "PUT_YOUR_HASH_HERE":
            if not self.verify_model(temp_file, latest_info['sha256']):
                # Hash tidak cocok — file mungkin rusak atau dimodifikasi
                # Hapus file sementara yang tidak valid
                temp_file.unlink()
                return {
                    "success": False,
                    "message": "Verification failed - file corrupted"
                }

        # LANGKAH 4: Instal model baru (backup model lama + pindah file + simpan versi)
        if self.install_model(temp_file, version, latest_info):
            return {
                "success": True,
                "message": f"Successfully updated to {version}",
                "version": version
            }
        else:
            return {
                "success": False,
                "message": "Installation failed"
            }


# ─── PENGUJIAN CEPAT ─────────────────────────────────────────────────────────
# Blok ini hanya berjalan jika file ini dijalankan langsung (bukan diimpor)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    updater = ModelUpdater()

    # Cek apakah ada pembaruan tersedia
    update_info = updater.check_for_updates()
    print(f"Update info: {update_info}")

    if update_info and update_info.get('update_available'):
        print(f"Update available: {update_info['latest_version']}")

        def progress(downloaded, total):
            """Tampilkan persentase unduhan model ke konsol sebagai indikator visual."""
            # Hitung persentase; hindari pembagian dengan nol jika total tidak diketahui
            percent = (downloaded / total) * 100 if total > 0 else 0
            # \r mengembalikan kursor ke awal baris agar persentase diperbarui di tempat
            print(f"Download progress: {percent:.1f}%", end='\r')

        result = updater.update_model(progress_callback=progress)
        print(f"\nUpdate result: {result}")
