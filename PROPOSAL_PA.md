# PROPOSAL PROYEK AKHIR

**Program Studi:** Teknik Informatika / Sistem Informasi
**Tanggal:** Maret 2026

---

## 1. Judul Proyek Akhir

**"Rancang Bangun Aplikasi Desktop Antimalware dengan Integrasi Model Deep Learning berbasis ONNX, Perlindungan Real-Time, dan Karantina Otomatis pada Windows"**

---

## 2. Tujuan Proyek Akhir

1. Merancang dan membangun aplikasi desktop antimalware *standalone* yang dapat berjalan pada sistem operasi Windows tanpa memerlukan instalasi tambahan.
2. Mengintegrasikan model *deep learning* berbasis arsitektur **ResNet-18** (yang telah dilatih oleh anggota tim) ke dalam aplikasi menggunakan **ONNX Runtime** untuk inferensi yang cepat dan efisien.
3. Melakukan konversi format model dari PyTorch (`.pth`) ke **ONNX** (*Open Neural Network Exchange*) menggunakan `torch.onnx.export` untuk meningkatkan portabilitas dan kecepatan inferensi.
4. Menerapkan mekanisme perlindungan *real-time* berbasis *file locking* (Windows API `CreateFileW`) dan pemantauan proses (*process monitor*) agar file berbahaya tidak dapat dieksekusi sebelum proses pemindaian selesai.
5. Membangun sistem karantina otomatis untuk mengisolasi file yang terdeteksi sebagai malware sehingga tidak dapat membahayakan sistem.
6. Menyediakan fitur pembaruan model *machine learning* secara otomatis dari server untuk menjaga akurasi deteksi terhadap ancaman terbaru.
7. Menyimpan dan mengelola riwayat hasil pemindaian secara lokal menggunakan basis data SQLite.

---

## 3. Variabel yang Diukur

| No | Variabel | Indikator Pengukuran |
|----|----------|----------------------|
| 1 | **CPU Usage** | Persentase penggunaan CPU saat *realtime protection* aktif |
| 2 | **Memory Usage** | Penggunaan RAM oleh aplikasi selama pemindaian (MB) |
| 3 | **Scan Throughput** | Jumlah file yang dapat dipindai per detik |
| 4 | **UI Response Time** | Waktu respons antarmuka saat pengguna melakukan scan (ms) |
| 5 | **Scan Time** | Waktu rata-rata pemindaian per file (ms) |
| 6 | **Response Time Real-Time Protection** | Waktu dari deteksi file/proses baru hingga proses berhasil di-*suspend* (ms) |
| 7 | **Startup Model Time** | Waktu yang dibutuhkan untuk memuat model ONNX saat aplikasi dijalankan (ms) |

---

## 4. Metode Pengembangan

Metode pengembangan yang digunakan adalah **Prototype Model (Iterative Prototyping)**.

Metode ini dipilih karena:
- Fitur dibangun secara bertahap dan dievaluasi di setiap iterasi
- Model *machine learning* mengalami peningkatan versi (v2 → v3 ONNX) berdasarkan hasil evaluasi
- Memungkinkan perbaikan desain UI dan logika proteksi secara berulang berdasarkan hasil pengujian

### Tahapan Pengembangan

| Tahap | Kegiatan |
|-------|----------|
| **1. Analisis Kebutuhan** | Identifikasi ancaman malware, kebutuhan proteksi real-time, dan kebutuhan pengguna |
| **2. Perancangan** | Desain arsitektur CNN, desain antarmuka UI, perancangan alur perlindungan file dan proses |
| **3. Implementasi** | Konversi format model `.pth` → ONNX, integrasi ONNX Runtime ke scanner, pembangunan seluruh aplikasi desktop PySide6 |
| **4. Pengujian** | Uji akurasi model, uji perlindungan real-time, uji performa pemindaian |
| **5. Evaluasi & Perbaikan** | Iterasi perbaikan model dan fitur berdasarkan hasil pengujian |

---

## 5. Metode, Teknik, Algoritma, dan Framework yang Digunakan

### a. Binary Visualization (Metode UCSB)
File biner dikonversi menjadi citra grayscale sebelum diklasifikasi oleh CNN. Metode ini dikembangkan oleh Nataraj et al. (UCSB).

**Alur konversi:**
```
File (.exe/.dll/.pdf/...) → Baca sebagai Byte Array 
→ Reshape menjadi Matriks 2D → Simpan sebagai Citra Grayscale 
→ Resize ke 224×224 → Input CNN
```

Lebar citra ditentukan berdasarkan ukuran file:

| Ukuran File | Lebar Citra |
|-------------|-------------|
| < 10 KB     | 32 px       |
| < 100 KB    | 256 px      |
| < 500 KB    | 512 px      |
| < 1 MB      | 768 px      |
| < 10 MB     | 1024 px     |

### b. Integrasi Model ResNet-18 via ONNX
- **Arsitektur Model:** ResNet-18 (dilatih oleh anggota tim, bukan bagian tugas ini)
- **Kontribusi pada tahap ini:**
  1. Menulis skrip konversi `convert_to_onnx.py`: memuat `imgcnnmaldeb.pth` → ekspor ke `.onnx` via `torch.onnx.export` (opset v11, `do_constant_folding=True`)
  2. Mengintegrasikan ONNX Runtime ke `scanner.py` dengan dua mode threading:
     - Mode *realtime*: `intra_op_num_threads=2`, `ORT_SEQUENTIAL` (hemat CPU)
     - Mode *agresif*: `intra_op_num_threads=4`, `ORT_PARALLEL` (throughput tinggi)
  3. Menghubungkan pipeline: File → Binary Visualization → ONNX Inferensi → Hasil klasifikasi
- **Input:** Citra grayscale 224×224 (dikonversi ke 3-channel untuk kompatibilitas ResNet)
- **Output:** `Benign` / `Malware` + nilai *confidence* (softmax)

### c. Windows File Locking (CreateFileW API)
- Menggunakan fungsi `CreateFileW` dari Windows Kernel32 API via `ctypes`
- Mode akses: `FILE_SHARE_NONE` — mengunci file secara eksklusif
- File baru yang terdeteksi langsung dikunci sebelum proses scan dimulai
- Tidak ada proses lain yang dapat membuka, mengeksekusi, atau memodifikasi file selama kunci aktif

### d. Process Monitor & Suspend
- Polling `psutil.pids()` setiap 5ms untuk mendeteksi proses baru
- Proses baru langsung di-*suspend* (`proc.suspend()`) sebelum sempat me-*render* atau mengeksekusi file
- Setelah scan selesai: proses di-*resume* jika aman, di-*kill* dan file dikarantina jika malware

### e. Watchdog Filesystem Monitoring
- Menggunakan library `watchdog` untuk memantau perubahan sistem file
- Direktori yang dipantau: Downloads, Desktop, Documents, Temp
- Event `FileCreatedEvent` dan `FileModifiedEvent` memicu antrian pemindaian otomatis

### f. Offline Queue dengan SQLite
- Hasil pemindaian disimpan ke basis data lokal SQLite
- Mendukung operasi *offline* tanpa ketergantungan koneksi internet
- Riwayat pemindaian dapat diakses kapan saja dari antarmuka aplikasi

---

## 6. Perangkat dan Software yang Digunakan

### Perangkat Keras (Hardware)

| Perangkat | Spesifikasi / Fungsi |
|-----------|----------------------|
| PC / Laptop | Pengembangan dan target *deployment* aplikasi |
| GPU (opsional) | Akselerasi training model CNN (NVIDIA CUDA) |

### Perangkat Lunak (Software) dan Library

| Kategori | Nama Tools |
|----------|------------|
| **Bahasa Pemrograman** | Python 3.11 |
| **GUI Framework** | PySide6 (Qt for Python) |
| **Konversi Model** | PyTorch (`torch.onnx.export`) |
| **ML Inferensi** | ONNX Runtime |
| **Pemrosesan Citra** | Pillow (PIL), NumPy |
| **Manajemen Proses** | psutil |
| **Monitor Sistem File** | Watchdog |
| **Basis Data Lokal** | SQLite3 (built-in Python) |
| **Packaging Executable** | PyInstaller 6.x |
| **IDE** | Visual Studio Code |
| **Version Control** | Git & GitHub |
| **Sistem Operasi Target** | Windows 10 / Windows 11 (64-bit) |
| **Notebook Eksperimen** | Jupyter Notebook |

---

        ## 7. Gambaran Sistem

        ### Arsitektur Umum

        Sistem terdiri dari dua komponen utama: **Antarmuka Pengguna (UI)** dan **Core Engine (Mesin Inti)**, yang bekerja bersama untuk memberikan perlindungan berlapis.

        ```
        ┌──────────────────────────────────────────────────────────────┐
        │                     APLIKASI MANGODEFEND                     │
        │                                                              │
        │  ┌──────────────────┐     ┌──────────────────────────────┐  │
        │  │   UI DESKTOP     │     │        CORE ENGINE           │  │
        │  │   (PySide6)      │◄───►│                              │  │
        │  │                  │     │  ┌───────────┐ ┌──────────┐  │  │
        │  │  • Dashboard     │     │  │ Watchdog  │ │ Process  │  │  │
        │  │  • Scan View     │     │  │ Filesystem│ │ Monitor  │  │  │
        │  │  • Perlindungan  │     │  │ Monitor   │ │ (PID)    │  │  │
        │  │  • Pembaruan     │     │  └─────┬─────┘ └────┬─────┘  │  │
        │  └──────────────────┘     │  File  │        Proses│       │  │
        │                           │  Baru  ▼        Baru ▼        │  │
        │  ┌──────────────────┐     │  ┌──────────────────────────┐ │  │
        │  │   ALERT DIALOG   │◄────┤  │  FILE LOCKING /          │ │  │
        │  │  (Malware Found) │     │  │  PROCESS SUSPEND         │ │  │
        │  │                  │     │  └─────────────┬────────────┘ │  │
        │  │  [Karantina]     │     │                ▼              │  │
        │  │  [Izinkan]       │     │  ┌──────────────────────────┐ │  │
        │  └──────────────────┘     │  │     MALWARE SCANNER      │ │  │
        │                           │  │                          │ │  │
        │                           │  │  File Biner              │ │  │
        │                           │  │     ↓                    │ │  │
        │                           │  │  Konversi ke Citra       │ │  │
        │                           │  │  (Binary Visualization)  │ │  │
        │                           │  │     ↓                    │ │  │
        │                           │  │  CNN-ONNX Inferensi      │ │  │
        │                           │  │     ↓                    │ │  │
        │                           │  │  Benign / Malware        │ │  │
        │                           │  └─────────────┬────────────┘ │  │
        │                           │                ▼              │  │
        │                           │  ┌──────────────────────────┐ │  │
        │                           │  │ Benign  → Resume / Unlock│ │  │
        │                           │  │ Malware → Kill + Karantina│ │  │
        │                           │  └──────────────────────────┘ │  │
        │                           └──────────────────────────────  │  │
        │                                                              │
        │  ┌───────────────────────────────────────────────────────┐  │
        │  │  PENYIMPANAN LOKAL                                    │  │
        │  │  SQLite (riwayat scan) | models/Modelv3.onnx          │  │
        │  │  quarantine/ (file terkarantina)                      │  │
        │  └───────────────────────────────────────────────────────┘  │
        └──────────────────────────────────────────────────────────────┘
        ```

        ### Dua Jalur Perlindungan

        **Jalur A — Perlindungan File Baru (Watchdog)**
        ```
        File baru terdeteksi di folder Monitor
            → Kunci file eksklusif (CreateFileW)
            → Antri ke scan queue
            → Konversi biner ke citra grayscale
            → Inferensi CNN-ONNX
            → Benign: Lepas kunci → File dapat diakses normal
            → Malware: Tampilkan alert → Karantina / Izinkan (pilihan user)
        ```

        **Jalur B — Perlindungan Proses (Process Monitor)**
        ```
        Proses baru terdeteksi (PID baru)
            → Suspend proses segera (sebelum render/eksekusi)
            → Baca cmdline → identifikasi file yang dibuka
            → Konversi biner ke citra grayscale
            → Inferensi CNN-ONNX
            → Benign: Resume proses → berjalan normal
            → Malware: Tampilkan alert → Kill proses + Karantina file
        ```

        ### Alur Pemindaian Manual

        ```
        User pilih file/folder di UI
            → ScanThread menjalankan scan di background
            → FileConverter konversi file ke citra
            → MalwareScanner inferensi ONNX
            → Hasil ditampilkan di UI (Benign / Malware + confidence %)
            → Tersimpan ke riwayat (SQLite)
        ```

        ---

        *Dokumen ini dibuat berdasarkan analisis kode sumber aplikasi MangoDefend.*
