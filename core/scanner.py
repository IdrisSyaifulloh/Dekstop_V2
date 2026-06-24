"""
Malware Scanner — berbasis model ONNX.

Semua jenis file diproses melalui teknik binary visualization sebelum
dikirim ke model AI. Artinya, file dibaca sebagai kumpulan byte mentah
lalu disusun menjadi gambar grayscale, kemudian model memutuskan apakah
file tersebut aman atau berbahaya.

Pendekatan ini konsisten dengan cara model dilatih
(Malware Visualization / Binary-to-Image, seperti pada paper Nataraj et al.).
"""

import os
import math
import shutil
import tempfile
import zipfile
import numpy as np
from PIL import Image
from datetime import datetime
from pathlib import Path
import psutil
import hashlib

# FileConverter digunakan untuk mengekstrak isi file PDF, Office, dan ZIP
# sebelum dianalisis oleh model AI
from utils.file_converter import FileConverter

try:
    # onnxruntime adalah pustaka yang digunakan untuk menjalankan model AI format ONNX
    import onnxruntime as ort
except ImportError:
    # Jika pustaka belum terinstal, hentikan program dengan pesan yang jelas
    raise RuntimeError("Install onnxruntime first")

# Lokasi default file model AI yang akan digunakan jika tidak ditentukan lain
DEFAULT_MODEL_PATH = "models/Modelv3.onnx"

# Daftar label hasil prediksi: indeks 0 berarti Aman, indeks 1 berarti Malware
CLASS_NAMES = ["Benign", "Malware"]

# Ekstensi gambar dataset/visualisasi malware.
# File seperti *_L.png sudah berupa gambar input model, jadi harus dibuka
# sebagai gambar yang sesungguhnya — bukan dibaca sebagai kumpulan byte PNG mentah.
# Ini penting agar model melihat pola visual malware, bukan header file PNG.
_IMAGE_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp",
})

# Ekstensi file yang membutuhkan proses ekstraksi isi terlebih dahulu
# sebelum dapat dianalisis, karena isi aslinya tersembunyi di dalam format khusus
_CONVERTER_EXTENSIONS = frozenset({
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
})

# Ekstensi arsip yang isinya harus diekstrak lalu setiap file di dalamnya dipindai satu per satu
# Ini berbeda dari _CONVERTER_EXTENSIONS — arsip bisa berisi banyak file berbahaya sekaligus
_ARCHIVE_EXTENSIONS = frozenset({
    ".zip", ".rar", ".7z", ".iso",
})


def _bytes_to_binary_image(data: bytes) -> Image.Image:
    """
    Ubah isi mentah sebuah file menjadi gambar grayscale.

    Cara kerjanya:
    - Setiap byte dalam file dijadikan satu piksel (nilai 0 hingga 255).
    - Semua piksel disusun menjadi kotak (bujur sangkar) supaya membentuk gambar.
    - Sisa ruang kosong di sudut bawah kanan diisi dengan piksel hitam (nilai 0).

    Inilah cara model AI melihat dan mempelajari pola file malware saat pelatihan.
    """
    # Jika file kosong (tidak ada isi), kembalikan gambar hitam 1x1 piksel
    # supaya proses selanjutnya tidak error
    if not data:
        return Image.fromarray(np.zeros((1, 1), dtype=np.uint8), mode="L")

    # Hitung jumlah total byte dalam file
    n = len(data)

    # Tentukan panjang sisi bujur sangkar yang cukup menampung semua byte.
    # Contoh: 100 byte → sisi = ceil(sqrt(100)) = 10 → gambar 10x10 = 100 piksel
    side = math.ceil(math.sqrt(n))

    # Total piksel dalam gambar (sisi × sisi), bisa lebih besar dari jumlah byte
    total = side * side

    # Ubah data byte mentah menjadi array bilangan bulat 0–255
    arr = np.frombuffer(data, dtype=np.uint8)

    # Jika jumlah byte kurang dari total piksel, tambahkan piksel hitam (nilai 0)
    # di bagian akhir supaya ukuran array pas untuk dibentuk menjadi bujur sangkar
    if len(arr) < total:
        arr = np.pad(arr, (0, total - len(arr)), constant_values=0)

    # Bentuk ulang array panjang menjadi matriks 2D (baris × kolom) seperti gambar
    img_array = arr.reshape((side, side))

    # Buat objek gambar dari matriks, mode "L" berarti grayscale (hitam-putih bertingkat)
    return Image.fromarray(img_array, mode="L")


class MalwareScanner:
    """
    Pemindai malware menggunakan model AI (ONNX).

    Semua jenis file — termasuk gambar seperti .png dan .jpg —
    dikonversi ke representasi byte-level sebelum dikirim ke model,
    bukan dibuka sebagai gambar biasa. Ini memastikan model selalu
    melihat pola byte file, bukan isi visual file tersebut.
    """

    def __init__(self, model_path: str | None = None):
        """Siapkan pemindai dengan menentukan lokasi file model AI."""
        # Jika lokasi model tidak diberikan, gunakan lokasi default
        # relatif terhadap folder induk modul ini
        if model_path is None:
            base_dir   = Path(__file__).resolve().parent.parent
            model_path = base_dir / DEFAULT_MODEL_PATH

        # Simpan path model sebagai string agar kompatibel dengan ONNX Runtime
        self.model_path = str(model_path)

        # session adalah objek model AI yang siap digunakan; None berarti belum dimuat
        self.session = None

        # device menunjukkan perangkat komputasi yang digunakan (CPU atau GPU/CUDA)
        self.device = "CPU"

        # converter digunakan untuk mengekstrak isi file PDF/Office/ZIP
        self.converter = FileConverter()

        # _aggressive menandai apakah mode pemindaian massal sedang aktif
        self._aggressive = False

    def load_model(self, aggressive: bool = False):
        """
        Muat model AI ke memori agar siap digunakan untuk memindai.

        Mode aggressive menggunakan lebih banyak thread CPU untuk
        mempercepat pemindaian massal (full scan). Mode normal
        menggunakan lebih sedikit thread agar tidak memberatkan komputer
        saat pengguna sedang menggunakan aplikasi lain.
        """
        # Jika model sudah dimuat dengan mode yang sama, tidak perlu dimuat ulang
        if self.session is not None and aggressive == self._aggressive:
            return

        # Tandai mode yang sedang digunakan, lalu reset sesi agar bisa dimuat ulang
        self._aggressive = aggressive
        self.session = None

        # Pastikan file model benar-benar ada sebelum mencoba memuatnya
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(self.model_path)

        # Mulai dengan CPU sebagai pilihan utama — selalu tersedia di semua komputer
        providers = ["CPUExecutionProvider"]

        # Cek apakah kartu grafis NVIDIA (GPU/CUDA) tersedia untuk mempercepat proses
        # Jika ada, masukkan GPU di urutan pertama supaya diprioritaskan
        if "CUDAExecutionProvider" in ort.get_available_providers():
            providers.insert(0, "CUDAExecutionProvider")
            self.device = "CUDA"

        # Ambil jumlah inti CPU yang tersedia di komputer
        cpu_count = psutil.cpu_count(logical=True)

        # Buat objek konfigurasi sesi ONNX untuk mengatur performa
        sess_options = ort.SessionOptions()

        if aggressive:
            # Mode full scan: gunakan lebih banyak thread (maks 4) supaya lebih cepat
            # min() dipakai agar tidak meminta lebih banyak thread dari yang tersedia
            sess_options.intra_op_num_threads = min(4, cpu_count)
            # ORT_PARALLEL: operasi dalam satu lapisan model dapat dijalankan sejajar
            sess_options.execution_mode = ort.ExecutionMode.ORT_PARALLEL
        else:
            # Mode scan biasa: cukup 2 thread agar tidak memberatkan komputer
            sess_options.intra_op_num_threads = min(2, cpu_count)
            # ORT_SEQUENTIAL: setiap langkah model berjalan satu per satu (lebih hemat)
            sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

        # Batasi thread antar lapisan model menjadi 1 untuk menghindari konflik
        sess_options.inter_op_num_threads = 1

        # Aktifkan optimasi dasar model: menggabungkan operasi sederhana agar lebih cepat
        # tanpa memakan waktu lama saat pertama kali model dimuat
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC

        # Muat model dari file dan simpan sebagai sesi yang siap digunakan
        self.session = ort.InferenceSession(
            self.model_path,
            providers=providers,
            sess_options=sess_options
        )

    def scan_file(self, file_path: str, is_full_scan: bool = False) -> dict:
        """
        Pindai satu file dan kembalikan hasilnya sebagai dictionary.

        Alur kerja untuk semua jenis file:
          1. Baca isi mentah file (byte per byte)
          2. Susun byte menjadi gambar grayscale
          3. Ubah ukuran gambar menjadi 224x224 piksel
          4. Kirim ke model AI untuk mendapatkan prediksi: Aman atau Malware

        Untuk file PDF, Office, dan ZIP, isi diekstrak dulu oleh FileConverter
        sebelum melewati langkah di atas.

        Catatan: set variabel lingkungan MANGODEFEND_TEST_MALWARE=1 untuk memaksa
        hasil "Malware" (hanya untuk keperluan pengujian tampilan, tidak
        mempengaruhi model asli).
        """
        # MODE PENGUJIAN: Jika variabel lingkungan ini diaktifkan, langsung kembalikan
        # hasil "Malware" palsu tanpa benar-benar menjalankan model AI.
        # Berguna saat pengembang ingin menguji tampilan peringatan malware.
        if os.environ.get("MANGODEFEND_TEST_MALWARE") == "1":
            file_path_obj = Path(file_path)
            try:
                # Coba baca ukuran file; jika gagal (file tidak ada), anggap 0 byte
                file_size = os.path.getsize(file_path)
            except OSError:
                file_size = 0
            # Kembalikan data palsu yang meniru format hasil pemindaian asli
            return {
                "result":    "Malware",
                "timestamp": __import__("datetime").datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                "model": {
                    "model":            "TEST_MODE",
                    # Nilai [0.02, 0.98] berarti model "yakin 98% ini malware" (palsu)
                    "predicted_output": [0.02, 0.98],
                },
                "device": {"device": "TEST"},
                "file": {
                    "file_name": file_path_obj.name,
                    "file_path": str(file_path),
                    "file_size": file_size,
                    "file_hash": self._hash_file(file_path),
                },
            }

        # Muat model AI jika belum dimuat, atau muat ulang jika mode berubah
        # is_full_scan=True mengaktifkan mode aggressive (lebih banyak thread)
        self.load_model(aggressive=is_full_scan)

        # Buat objek Path agar mudah mengambil nama file dan ekstensinya
        file_path_obj = Path(file_path)

        # Ambil ekstensi file dan ubah ke huruf kecil supaya perbandingan konsisten
        # Contoh: ".EXE" → ".exe", ".PDF" → ".pdf"
        ext = file_path_obj.suffix.lower()

        # Catat ukuran file dalam byte untuk dilaporkan di hasil akhir
        file_size = os.path.getsize(file_path)

        # Catat waktu mulai pemindaian untuk mengukur durasi total
        t_start = __import__("time").perf_counter()

        if ext in _IMAGE_EXTENSIONS:
            # File gambar seperti .png dan .jpg yang merupakan hasil visualisasi malware
            # dibuka sebagai gambar sungguhan (bukan byte mentah), karena model
            # dilatih dengan cara melihat gambar tersebut secara visual
            image = self._load_image_file(file_path)
        elif ext in _ARCHIVE_EXTENSIONS:
            # File arsip (ZIP, RAR, 7z, ISO) — scan setiap file di dalamnya satu per satu
            # Kembalikan hasil langsung dari scan_archive (bukan lewat _predict)
            scan_duration = __import__("time").perf_counter() - t_start
            return self.scan_archive(file_path)
        elif ext in _CONVERTER_EXTENSIONS:
            # File PDF, dokumen Office perlu diekstrak isinya dulu sebelum dianalisis
            image = self._scan_via_converter(file_path)
        else:
            # Untuk semua file lainnya (exe, dll, bat, dll.): baca langsung sebagai
            # kumpulan byte mentah lalu ubah menjadi gambar grayscale
            image = self._bytes_to_image(file_path)

        # Kirim gambar ke model AI dan dapatkan prediksi beserta tingkat keyakinannya
        output, predicted = self._predict(image)

        # Hitung berapa lama pemindaian berlangsung dalam detik
        scan_duration = __import__("time").perf_counter() - t_start

        # Susun dan kembalikan hasil pemindaian sebagai dictionary lengkap
        return {
            # CLASS_NAMES[0] = "Benign" (aman), CLASS_NAMES[1] = "Malware"
            "result":    CLASS_NAMES[predicted],
            "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "model": {
                # Catat nama file model yang digunakan (misalnya "Modelv3.onnx")
                "model":            Path(self.model_path).name,
                # Probabilitas untuk setiap kelas, misalnya [0.95, 0.05] = 95% aman
                "predicted_output": output,
            },
            "device": {
                # CPU atau CUDA (GPU) yang digunakan untuk komputasi
                "device": self.device,
            },
            "file": {
                "file_name": file_path_obj.name,
                "file_path": str(file_path),
                # Ukuran file dalam byte
                "file_size": file_size,
                # Sidik jari unik file (SHA-256) untuk identifikasi
                "file_hash": self._hash_file(file_path),
            },
            # Durasi total pemindaian, dibulatkan ke 3 angka desimal
            "scan_duration_seconds": round(scan_duration, 3),
        }

    def _bytes_to_image(self, file_path: str) -> Image.Image:
        """
        Baca isi mentah file lalu ubah menjadi gambar grayscale untuk dianalisis.

        Berbeda dengan membuka file gambar biasa — di sini semua file,
        termasuk .exe dan .dll, dibaca sebagai deretan byte mentah sehingga
        model melihat pola byte, bukan tipe file atau isi visualnya.
        Mode "rb" (read binary) memastikan tidak ada byte yang diubah saat dibaca.
        """
        # Buka file dalam mode biner agar semua byte terbaca apa adanya
        with open(file_path, "rb") as f:
            data = f.read()
        # Serahkan data byte ke fungsi konversi untuk dijadikan gambar grayscale
        return _bytes_to_binary_image(data)

    def _load_image_file(self, file_path: str) -> Image.Image:
        """
        Buka file gambar sebagai gambar grayscale.

        Ini penting untuk data uji seperti malware visualization PNG.
        Kalau PNG dibaca sebagai byte mentah, model melihat struktur file PNG
        yang terkompresi, bukan pola visual malware yang dipelajari saat training.
        Mengonversi ke RGB memastikan format gambar seragam dengan input model.
        """
        # Buka file sebagai gambar nyata (bukan byte mentah), lalu konversi ke RGB
        # RGB dipilih karena model dilatih dengan gambar 3-channel warna
        with Image.open(file_path) as image:
            return image.convert("RGB")

    def _scan_via_converter(self, file_path: str) -> Image.Image:
        """
        Ekstrak isi file PDF/Office/ZIP lalu analisis hasilnya sebagai gambar.

        Jika proses ekstraksi gagal karena alasan apapun (file rusak,
        format tidak didukung, dll.), file asli akan langsung dibaca sebagai
        byte mentah sebagai cadangan (fallback) agar proses tetap berjalan.
        """
        temp_image_path = None
        try:
            # Minta FileConverter untuk mengonversi isi file ke gambar sementara
            conversion = self.converter.convert_file_to_image(file_path)

            # Ambil lokasi file gambar sementara yang dihasilkan oleh converter
            temp_image_path = conversion.get("output_image")

            # Jika file gambar sementara berhasil dibuat dan ada di disk, buka sebagai gambar
            if temp_image_path and os.path.exists(temp_image_path):
                with Image.open(temp_image_path) as image:
                    return image.convert("RGB")

        except Exception:
            # Abaikan error apapun — kita akan gunakan fallback di bawah
            pass
        finally:
            # Selalu hapus file gambar sementara setelah selesai agar tidak
            # memenuhi ruang penyimpanan, baik proses berhasil maupun gagal
            if temp_image_path and os.path.exists(temp_image_path):
                try:
                    os.remove(temp_image_path)
                except OSError:
                    pass

        # FALLBACK: Jika ekstraksi gagal, baca file asli sebagai byte mentah
        return self._bytes_to_image(file_path)

    def scan_archive(self, archive_path: str) -> dict:
        """
        Ekstrak isi file arsip (ZIP, RAR, 7z, ISO) lalu pindai setiap file
        di dalamnya satu per satu menggunakan CNN.

        Kenapa perlu diekstrak dulu?
        File di dalam arsip terkompresi — byte-nya sudah berubah total akibat kompresi.
        CNN tidak akan mengenali pola malware jika melihat byte yang sudah terkompresi.
        Solusinya: ekstrak dulu ke folder sementara, lalu scan file aslinya.

        Mengembalikan hasil "Malware" jika ADA SATU SAJA file berbahaya di dalam arsip.
        Mengembalikan hasil "Benign" jika semua file di dalamnya aman.
        """
        import time as _time
        t_start = _time.perf_counter()

        archive_path_obj = Path(archive_path)
        ext = archive_path_obj.suffix.lower()

        # Buat folder sementara untuk menampung hasil ekstraksi
        # Folder ini akan dihapus otomatis setelah scan selesai
        temp_dir = tempfile.mkdtemp(prefix="mangodefend_archive_")

        malware_files = []   # Daftar file berbahaya yang ditemukan di dalam arsip
        scanned       = 0    # Jumlah file yang berhasil dipindai

        try:
            # Ekstrak isi arsip ke folder sementara
            if ext == ".zip":
                # Python punya dukungan bawaan untuk ZIP
                try:
                    with zipfile.ZipFile(archive_path, "r") as zf:
                        zf.extractall(temp_dir)
                except zipfile.BadZipFile:
                    # File ZIP rusak atau terenkripsi — fallback ke scan byte mentah
                    return self._fallback_scan(archive_path, t_start)

            elif ext in (".rar", ".7z", ".iso"):
                # RAR, 7z, dan ISO butuh library tambahan (py7zr atau rarfile)
                try:
                    if ext == ".rar":
                        import rarfile  # pip install rarfile
                        with rarfile.RarFile(archive_path) as rf:
                            rf.extractall(temp_dir)
                    else:
                        import py7zr  # pip install py7zr
                        with py7zr.SevenZipFile(archive_path, mode="r") as sz:
                            sz.extractall(temp_dir)
                except Exception:
                    # Library tidak terinstall atau file rusak — fallback ke byte mentah
                    return self._fallback_scan(archive_path, t_start)
            else:
                # Ekstensi tidak dikenal — fallback ke byte mentah
                return self._fallback_scan(archive_path, t_start)

            # Scan setiap file hasil ekstraksi satu per satu
            for root, _, filenames in os.walk(temp_dir):
                for fname in filenames:
                    extracted_path = os.path.join(root, fname)
                    try:
                        # Lewati file kosong
                        if os.path.getsize(extracted_path) <= 0:
                            continue

                        # Pindai file ini menggunakan CNN (rekursif — bisa handle arsip dalam arsip)
                        result = self.scan_file(extracted_path)
                        scanned += 1

                        # Jika file ini malware, catat nama aslinya di dalam arsip
                        if result and result.get("result") == "Malware":
                            # Ambil path relatif di dalam arsip (bukan path temp folder)
                            rel_path = os.path.relpath(extracted_path, temp_dir)
                            malware_files.append(rel_path)

                    except Exception:
                        pass  # Lewati file yang gagal dipindai (bisa jadi file sistem)

        finally:
            # Selalu hapus folder temp setelah selesai, baik berhasil maupun error
            shutil.rmtree(temp_dir, ignore_errors=True)

        scan_duration = _time.perf_counter() - t_start

        # Jika ada satu saja file malware di dalam arsip, seluruh arsip dianggap berbahaya
        is_malware = len(malware_files) > 0

        return {
            "result":    "Malware" if is_malware else "Benign",
            "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "model": {
                "model":            Path(self.model_path).name,
                "predicted_output": None,  # Tidak ada single output karena multi-file
            },
            "device": {
                "device": self.device,
            },
            "file": {
                "file_name":      archive_path_obj.name,
                "file_path":      str(archive_path),
                "file_size":      os.path.getsize(archive_path),
                "file_hash":      self._hash_file(archive_path),
                # Info tambahan khusus arsip
                "archive_scanned":       scanned,        # Jumlah file yang dipindai
                "archive_malware_files": malware_files,  # Nama file berbahaya di dalam arsip
            },
            "scan_duration_seconds": round(scan_duration, 3),
        }

    def _fallback_scan(self, file_path: str, t_start: float) -> dict:
        """
        Cadangan jika arsip tidak bisa diekstrak (rusak, terenkripsi, library tidak ada).
        Scan file arsip itu sendiri sebagai byte mentah.
        """
        import time as _time
        file_path_obj = Path(file_path)
        image         = self._bytes_to_image(file_path)
        output, predicted = self._predict(image)
        scan_duration = _time.perf_counter() - t_start
        return {
            "result":    CLASS_NAMES[predicted],
            "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "model": {
                "model":            Path(self.model_path).name,
                "predicted_output": output,
            },
            "device": {"device": self.device},
            "file": {
                "file_name": file_path_obj.name,
                "file_path": str(file_path),
                "file_size": os.path.getsize(file_path),
                "file_hash": self._hash_file(file_path),
            },
            "scan_duration_seconds": round(scan_duration, 3),
        }

    def _predict(self, image: Image.Image):
        """
        Kirim gambar ke model AI dan dapatkan prediksi hasilnya.

        Langkah-langkahnya:
        1. Perkecil gambar menjadi 224x224 piksel (ukuran input yang diharapkan model)
        2. Ubah nilai piksel dari rentang 0-255 menjadi 0.0-1.0 (normalisasi)
        3. Susun dimensi array sesuai format yang diharapkan model (channel, tinggi, lebar)
        4. Tambahkan dimensi batch karena model memproses dalam kelompok
        5. Jalankan model dan baca hasilnya
        """
        # Ubah ukuran gambar menjadi 224x224 piksel — ini adalah ukuran standar
        # yang digunakan saat melatih model; ukuran berbeda akan menghasilkan prediksi buruk
        image = image.resize((224, 224), Image.BILINEAR)

        if image.mode == "L":
            # Gambar grayscale (hitam-putih): nilai piksel antara 0-255
            # Bagi dengan 255.0 agar nilainya menjadi 0.0-1.0 (normalisasi)
            # Model bekerja lebih baik dengan nilai kecil dibanding nilai besar
            img = np.array(image).astype(np.float32) / 255.0

            # Model memerlukan 3 channel (R, G, B) — karena ini grayscale,
            # duplikasi channel yang sama sebanyak 3 kali untuk memenuhi format
            img = np.stack([img] * 3, axis=0)
        else:
            # Gambar berwarna (RGB): pastikan format benar dulu
            image = image.convert("RGB")

            # Normalisasi nilai piksel dari 0-255 menjadi 0.0-1.0
            img = np.array(image).astype(np.float32) / 255.0

            # Ubah susunan dimensi dari (tinggi, lebar, channel) menjadi
            # (channel, tinggi, lebar) — format yang diharapkan oleh model PyTorch/ONNX
            img = np.transpose(img, (2, 0, 1))

        # Tambahkan dimensi batch di depan: (3, 224, 224) → (1, 3, 224, 224)
        # Model biasanya memproses banyak gambar sekaligus (batch),
        # tapi di sini kita hanya kirim 1 gambar per kali
        img = np.expand_dims(img, axis=0)

        # Ambil nama variabel input dan output dari model ONNX
        # agar kita tahu "pintu masuk" dan "pintu keluar" data
        input_name  = self.session.get_inputs()[0].name
        output_name = self.session.get_outputs()[0].name

        # Jalankan model dengan gambar yang sudah disiapkan
        # Hasilnya berupa array angka mentah (logit/skor) untuk setiap kelas
        result = self.session.run([output_name], {input_name: img})

        # Ambil output untuk gambar pertama (indeks 0) dan pastikan tipe float32
        output = result[0][0].astype(np.float32)

        # Cari indeks kelas dengan skor tertinggi: 0 = Benign (aman), 1 = Malware
        predicted = int(np.argmax(output))

        # Ubah skor mentah menjadi probabilitas menggunakan softmax
        # sehingga nilainya berupa persentase yang mudah dipahami (jumlah = 100%)
        probs = self._softmax(output)

        # Kembalikan probabilitas sebagai list dan kelas prediksi sebagai angka
        return probs.tolist(), predicted

    @staticmethod
    def _softmax(values: np.ndarray) -> np.ndarray:
        """
        Ubah output model (logit/skor mentah) menjadi probabilitas agar mudah dibaca.

        Softmax memastikan semua nilai positif dan jumlahnya = 1.0 (100%).
        Contoh: skor [-1.2, 3.4] → probabilitas [0.02, 0.98] (2% aman, 98% malware).

        Kita kurangi nilai maksimum terlebih dahulu (shifted) untuk menghindari
        overflow saat menghitung eksponensial dari angka yang sangat besar.
        """
        # Kurangi nilai terbesar untuk stabilitas numerik (hindari angka terlalu besar)
        shifted = values - np.max(values)

        # Hitung eksponensial setiap nilai (fungsi matematika e^x)
        exp = np.exp(shifted)

        # Jumlahkan semua nilai eksponensial sebagai pembagi
        total = np.sum(exp)

        # Jika total nol (kasus sangat jarang), kembalikan distribusi merata
        if total == 0:
            return np.ones_like(values) / len(values)

        # Bagi setiap eksponensial dengan total untuk mendapatkan probabilitas
        return exp / total

    def _hash_file(self, file_path: str) -> str:
        """
        Hitung sidik jari unik (hash SHA-256) dari sebuah file.

        Hash SHA-256 adalah string 64 karakter yang unik untuk setiap file —
        jika isi file berubah satu bit pun, hash-nya akan berbeda sama sekali.
        Ini digunakan untuk mengidentifikasi file secara unik dalam laporan hasil scan.

        File dibaca per potongan 4096 byte (bukan sekaligus) karena:
        - File bisa sangat besar (ratusan MB atau lebih)
        - Membaca sekaligus bisa menguras memori komputer
        - 4096 byte = ukuran satu blok disk, efisien untuk pembacaan
        """
        # Buat objek penghitung hash SHA-256
        sha256 = hashlib.sha256()
        try:
            # Buka file dalam mode biner agar semua byte terbaca apa adanya
            with open(file_path, "rb") as f:
                # iter() dengan sentinel b"" akan terus membaca hingga file habis
                # Setiap iterasi membaca 4096 byte (satu blok disk)
                for chunk in iter(lambda: f.read(4096), b""):
                    # Masukkan setiap potongan ke dalam penghitung hash
                    sha256.update(chunk)
            # Kembalikan hash sebagai string heksadesimal (64 karakter)
            return sha256.hexdigest()
        except OSError:
            # Jika file tidak bisa dibaca (izin ditolak, dll.),
            # hitung hash dari path-nya saja sebagai cadangan
            return hashlib.sha256(file_path.encode()).hexdigest()

    def _skipped_result(self, file_path: str, file_path_obj: Path,
                        file_size: int, reason: str) -> dict:
        """
        Buat hasil pemindaian untuk file yang dilewati karena alasan tertentu.

        Misalnya file yang terlalu kecil, terlalu besar, atau jenis file
        yang tidak didukung akan dilewati dan diberi hasil "Skipped"
        beserta alasannya, agar tetap tercatat dalam laporan.
        """
        return {
            "result":    "Skipped",
            "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            # Simpan alasan mengapa file ini dilewati
            "reason":    reason,
            "model": {
                "model":            Path(self.model_path).name,
                # Tidak ada output prediksi karena file tidak diproses
                "predicted_output": None,
            },
            "device": {"device": self.device},
            "file": {
                "file_name": file_path_obj.name,
                "file_path": str(file_path),
                "file_size": file_size,
                "file_hash": self._hash_file(file_path),
            },
        }
