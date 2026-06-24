"""
Pengonversi File — Mengubah file biner menjadi gambar untuk diproses model machine learning.

Cara kerja secara umum:
Setiap file di komputer (termasuk virus/malware) tersimpan sebagai rangkaian angka 0–255.
Modul ini membaca angka-angka tersebut dan menyusunnya menjadi gambar piksel (grayscale).
Gambar inilah yang kemudian dianalisis oleh model CNN (jaringan saraf tiruan)
untuk memutuskan apakah file tersebut berbahaya atau aman.
"""
import math
import numpy as np
from PIL import Image
from pathlib import Path
from datetime import datetime
import tempfile
import os


class FileConverter:
    """
    Mengubah file biner (seperti .exe atau .dll) menjadi gambar grayscale
    agar bisa dianalisis oleh model CNN lewat ONNX Runtime.

    Proses konversi:
    1. Baca semua byte (angka 0–255) dari file
    2. Susun byte-byte tersebut menjadi matriks persegi panjang
    3. Simpan matriks sebagai gambar PNG grayscale
    4. Model CNN menerima gambar ini sebagai input dan memprediksi label

    Pendekatan ini berasal dari riset UCSB (University of California Santa Barbara)
    yang menunjukkan bahwa pola visual dari data biner bisa membedakan malware dari file normal.
    """

    def __init__(self, output_dir=None):
        """
        Menyiapkan konverter dengan menentukan folder penyimpanan gambar hasil konversi.

        Kenapa pakai tempfile?
        Gambar hasil konversi hanya dibutuhkan sementara — dibuat sebelum scan,
        dikirim ke model ML, lalu tidak diperlukan lagi. Menyimpan di folder sementara
        sistem operasi (temp folder) memastikan:
        1. Tidak mengotori folder pengguna dengan file-file sementara
        2. Sistem operasi akan membersihkan folder temp secara otomatis (saat restart/reboot)
        3. Tidak perlu izin khusus — folder temp selalu bisa ditulis oleh semua aplikasi

        Contoh lokasi temp di berbagai sistem:
        - Windows: C:\\Users\\NamaPengguna\\AppData\\Local\\Temp\\mangodefend_temp
        - Linux/Mac: /tmp/mangodefend_temp

        Parameter:
            output_dir — folder tujuan penyimpanan gambar (opsional).
                         Jika tidak diisi, otomatis menggunakan folder temp sistem.
        """
        if output_dir is None:
            # tempfile.gettempdir() mengembalikan lokasi folder temp sistem operasi
            # Buat subfolder "mangodefend_temp" di dalamnya agar gambar kita terpisah
            output_dir = os.path.join(tempfile.gettempdir(), "mangodefend_temp")

        # Ubah path string menjadi objek Path untuk manipulasi file yang lebih mudah
        self.output_dir = Path(output_dir)

        # Buat folder jika belum ada.
        # parents=True: buat folder induk juga jika belum ada
        # exist_ok=True: tidak error jika folder sudah ada
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def calculate_width(file_size_kb: float) -> int:
        """
        Menentukan lebar gambar (dalam piksel) yang sesuai berdasarkan ukuran file.

        Kenapa lebar gambar perlu disesuaikan dengan ukuran file?
        Jika semua file menggunakan lebar yang sama (misalnya 32 piksel),
        file besar akan menghasilkan gambar yang sangat tinggi (ribuan baris piksel)
        sehingga pola visual menjadi sulit terlihat dan model ML kurang akurat.
        Sebaliknya, file kecil dengan lebar besar akan menghasilkan gambar hampir kosong.

        Standar UCSB (University of California Santa Barbara):
        Riset asli yang mempopulerkan teknik ini menetapkan tabel standar ukuran file → lebar.
        Tabel ini dipilih berdasarkan eksperimen agar gambar yang dihasilkan memiliki
        rasio aspek yang wajar (tidak terlalu lonjong ke bawah atau ke samping),
        sehingga pola visual malware mudah dikenali oleh model CNN.

        Tabel ukuran → lebar:
        | Ukuran File    | Lebar Gambar |
        |----------------|--------------|
        | < 10 KB        | 32 piksel    |
        | 10 – 30 KB     | 64 piksel    |
        | 30 – 60 KB     | 128 piksel   |
        | 60 – 100 KB    | 256 piksel   |
        | 100 – 200 KB   | 384 piksel   |
        | 200 – 500 KB   | 512 piksel   |
        | 500 KB – 1 MB  | 768 piksel   |
        | 1 – 10 MB      | 1024 piksel  |
        | 10 – 50 MB     | 2048 piksel  |
        | 50 – 100 MB    | 4096 piksel  |
        | 100 – 500 MB   | 8192 piksel  |
        | > 500 MB       | 16384 piksel |

        Parameter:
            file_size_kb — ukuran file dalam satuan KB (kilobyte)

        Mengembalikan:
            lebar gambar dalam satuan piksel
        """
        if file_size_kb < 10:
            return 32        # file sangat kecil: gambar kecil 32x? piksel
        elif file_size_kb < 30:
            return 64        # file kecil: gambar 64x? piksel
        elif file_size_kb < 60:
            return 128       # file kecil-menengah: gambar 128x? piksel
        elif file_size_kb < 100:
            return 256       # file menengah: gambar 256x? piksel
        elif file_size_kb < 200:
            return 384       # file menengah-besar: gambar 384x? piksel
        elif file_size_kb < 500:
            return 512       # file besar: gambar 512x? piksel
        elif file_size_kb < 1000:
            return 768       # mendekati 1 MB: gambar 768x? piksel
        elif file_size_kb < 10000:
            return 1024      # file 1–10 MB: gambar 1024x? piksel
        elif file_size_kb < 50000:
            return 2048      # file 10–50 MB: gambar 2048x? piksel
        elif file_size_kb < 100000:
            return 4096      # file 50–100 MB: gambar 4096x? piksel
        elif file_size_kb < 500000:
            return 8192      # file 100–500 MB: gambar 8192x? piksel
        else:
            return 16384     # file sangat besar (>500 MB): gambar 16384x? piksel

    @staticmethod
    def binary_to_matrix(byte_data: bytes, width: int) -> np.ndarray:
        """
        Mengubah data biner mentah menjadi matriks piksel 2D (array dua dimensi).
        Matriks ini nantinya disimpan sebagai gambar grayscale.

        Cara kerja:
        Anggap file sebagai satu baris panjang berisi ribuan angka (0–255).
        Fungsi ini memotong baris panjang tersebut menjadi beberapa baris
        yang masing-masing sepanjang 'width' angka, seperti membagi teks panjang
        menjadi paragraf-paragraf yang lebarnya sama.

        Kenapa perlu padding?
        Jika jumlah byte tidak habis dibagi 'width', baris terakhir akan kekurangan angka.
        Misalnya 100 byte dengan lebar 32: baris terakhir hanya 4 byte (100 - 3×32 = 4).
        Sisa ruang di baris terakhir diisi dengan angka 0 (piksel hitam).
        Tanpa padding, numpy tidak bisa membentuk matriks persegi panjang yang rapi.

        Kenapa perlu reshape?
        np.frombuffer menghasilkan array 1 dimensi (satu baris panjang).
        reshape((height, width)) mengubahnya menjadi array 2 dimensi
        dengan 'height' baris dan 'width' kolom — inilah yang menjadi gambar.

        Parameter:
            byte_data — data biner mentah yang dibaca dari file (objek bytes)
            width     — lebar gambar dalam piksel (jumlah kolom)

        Mengembalikan:
            array numpy 2D dengan bentuk (height, width), dtype uint8 (nilai 0–255)
        """
        # Ubah data bytes menjadi array numpy 1D berisi angka 0–255
        # np.frombuffer adalah cara efisien untuk konversi tanpa menyalin data di memori
        byte_array = np.frombuffer(byte_data, dtype=np.uint8)

        # Hitung tinggi gambar (jumlah baris) menggunakan pembulatan ke atas.
        # math.ceil memastikan baris terakhir selalu disertakan meski tidak penuh.
        # Contoh: 100 byte, width=32 → ceil(100/32) = ceil(3.125) = 4 baris
        height = math.ceil(len(byte_array) / width)

        # Hitung berapa angka yang perlu ditambahkan agar array pas untuk di-reshape.
        # (width * height) adalah kapasitas total matriks, dikurangi panjang data asli
        # menghasilkan jumlah padding yang diperlukan.
        # np.pad menambahkan angka 0 di akhir array (mode "constant" dengan nilai default 0).
        padded = np.pad(byte_array, (0, width * height - len(byte_array)), "constant")

        # Ubah array 1D menjadi matriks 2D: (height baris) × (width kolom)
        return padded.reshape((height, width))

    def convert_file_to_image(
        self,
        file_path: str,
        width_override: int = None,
        color_mode: str = "gray"
    ) -> dict:
        """
        Mengubah satu file biner menjadi gambar PNG dan mengembalikan informasi hasilnya.

        Langkah-langkah konversi:
        1. Baca semua byte dari file target dalam mode biner
        2. Tangani file kosong dengan membuat data placeholder 32×32 piksel
        3. Hitung ukuran file dalam KB untuk menentukan lebar gambar
        4. Tentukan lebar gambar (dari parameter atau dari tabel standar UCSB)
        5. Konversi byte menjadi matriks piksel 2D menggunakan binary_to_matrix
        6. Buat nama file output unik dengan timestamp
        7. Simpan matriks sebagai gambar PNG (grayscale atau RGB)
        8. Kembalikan kamus berisi informasi gambar hasil konversi

        Kenapa pakai timestamp di nama file?
        Jika file yang sama dipindai dua kali dalam satu sesi, tanpa timestamp
        gambar kedua akan menimpa gambar pertama. Dengan timestamp (format YYYYMMDDHHmmss)
        setiap konversi menghasilkan nama file unik sehingga tidak ada konflik.
        Contoh nama file: document_gray_20240615143022.png

        Parameter:
            file_path      — lokasi lengkap file yang akan dikonversi
            width_override — lebar gambar paksa (opsional, mengganti perhitungan otomatis)
            color_mode     — "gray" untuk grayscale (default), "rgb" untuk berwarna

        Mengembalikan:
            kamus berisi:
            - original_filename : nama file asli
            - output_image      : lokasi lengkap gambar yang dihasilkan
            - color_mode        : mode warna yang digunakan
            - width             : lebar gambar dalam piksel
            - size_kb           : ukuran file asli dalam KB
        """
        # Ubah path string menjadi objek Path untuk kemudahan pengelolaan
        file_path_obj = Path(file_path)

        # ── LANGKAH 1: BACA FILE DALAM MODE BINER ───────────────────────────────
        # Mode "rb" (read binary) membaca file apa adanya sebagai angka 0–255
        # tanpa interpretasi apapun (berbeda dengan mode "r" yang menginterpretasi sebagai teks)
        with open(file_path, "rb") as f:
            binary_data = f.read()

        # ── LANGKAH 2: TANGANI FILE KOSONG ──────────────────────────────────────
        # File kosong (0 byte) tidak bisa dikonversi menjadi gambar bermakna.
        # Ini bisa terjadi untuk file placeholder, file yang baru dibuat, atau file rusak.
        # Buat data pengganti berisi 32×32 = 1024 byte bernilai 0 (gambar hitam polos).
        # File seperti ini hampir pasti tidak mengandung kode yang bisa dieksekusi.
        if len(binary_data) == 0:
            binary_data = bytes(32 * 32)  # 1024 byte bernilai 0 = gambar hitam 32×32

        # ── LANGKAH 3: HITUNG UKURAN FILE DALAM KB ──────────────────────────────
        # Bagi jumlah byte dengan 1024 untuk mendapatkan ukuran dalam kilobyte
        file_size_kb = len(binary_data) / 1024

        # ── LANGKAH 4: TENTUKAN LEBAR GAMBAR ────────────────────────────────────
        # Gunakan lebar paksa jika diberikan (misalnya untuk pengujian/debugging),
        # jika tidak gunakan tabel standar UCSB berdasarkan ukuran file
        width = width_override if width_override else self.calculate_width(file_size_kb)

        # ── LANGKAH 5: KONVERSI BYTE KE MATRIKS PIKSEL ──────────────────────────
        # binary_to_matrix menyusun data biner menjadi array 2D (height × width)
        matrix = self.binary_to_matrix(binary_data, width)

        # ── LANGKAH 6: BUAT NAMA FILE OUTPUT UNIK DENGAN TIMESTAMP ──────────────
        # Format timestamp: tahun(4)+bulan(2)+hari(2)+jam(2)+menit(2)+detik(2)
        # Contoh: 20240615143022 = 15 Juni 2024 pukul 14:30:22
        # Ini memastikan tidak ada dua gambar dengan nama sama meskipun file sama dipindai ulang
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_filename = f"{file_path_obj.stem}_{color_mode}_{timestamp}.png"
        output_path = self.output_dir / output_filename  # gabungkan folder dan nama file

        # ── LANGKAH 7: SIMPAN SEBAGAI GAMBAR PNG ────────────────────────────────
        # Image.fromarray membuat gambar dari array numpy
        # Mode "L" adalah mode grayscale PIL (Luminance) — setiap piksel 1 nilai 0–255
        img = Image.fromarray(matrix.astype(np.uint8), mode="L")

        # Jika mode RGB diminta, konversi dari grayscale ke RGB
        # (setiap piksel grayscale menjadi piksel RGB dengan nilai R=G=B yang sama)
        if color_mode == "rgb":
            img = img.convert("RGB")

        # Simpan gambar ke file PNG di folder output
        img.save(output_path)

        # ── LANGKAH 8: KEMBALIKAN INFORMASI HASIL ───────────────────────────────
        # Kamus ini digunakan oleh scanner untuk melacak gambar mana yang harus dikirim ke model
        return {
            "original_filename": file_path_obj.name,       # nama file asli (contoh: "virus.exe")
            "output_image":      str(output_path),         # lokasi lengkap gambar hasil konversi
            "color_mode":        color_mode,               # "gray" atau "rgb"
            "width":             width,                    # lebar gambar dalam piksel
            "size_kb":           round(file_size_kb, 2),   # ukuran file dibulatkan 2 angka desimal
        }
