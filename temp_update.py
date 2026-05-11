import sys
import os

file_path = r"c:\Users\saefu\Documents\dekstop\desktop_app\DRAFT_BAB3.md"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_content = []
state = 0
for line in lines:
    if line.startswith("## 3.2.1 Gambaran Sistem Saat Ini"):
        state = 1
        new_content.append("## 3.2 Pemodelan Sistem\n\n")
        new_content.append("Pada tahap perancangan sistem, dilakukan proses pemodelan sistem guna memberikan gambaran menyeluruh mengenai alur kerja, struktur, dan komponen-komponen utama dalam sistem deteksi *malware* yang akan dibangun. *(Catatan: Karena penelitian ini dikerjakan secara individu tanpa pembagian tim, blok pada sistem tidak memerlukan pemecahan batasan batas-kerja dengan garis putus-putus).*\n\n")
        new_content.append("### 3.2.1 Gambaran Umum dan Blok Diagram Sistem\n\n")
        new_content.append("Blok diagram digunakan untuk menggambarkan struktur keseluruhan sistem *antimalware* beserta interaksi komponen utamanya. Pemodelan fungsional ini direpresentasikan melalui tiga fase utama, yaitu **Input** (Masukan Sensor/Pengguna), **Proses** (Pengolahan Aplikasi), dan **Output** (Hasil Prediksi dan Tindakan).\\n\n")
        new_content.append("```mermaid\n")
        new_content.append("graph TD\n")
        new_content.append("    classDef inputNode fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px;\n")
        new_content.append("    classDef processNode fill:#fff3e0,stroke:#ff9800,stroke-width:2px;\n")
        new_content.append("    classDef outputNode fill:#e8f5e9,stroke:#4caf50,stroke-width:2px;\n\n")
        new_content.append("    subgraph INPUT [\"1. INPUT (Data Masukan)\"]\n")
        new_content.append("        I1[Berkas Eksekusi Manual <br> .exe, .dll]:::inputNode\n")
        new_content.append("        I2[Trigger Deteksi Sensor <br> File System Baru]:::inputNode\n")
        new_content.append("    end\n\n")
        new_content.append("    subgraph PROSES [\"2. PROSES (Pengolahan oleh Sistem/Aplikasi)\"]\n")
        new_content.append("        P1[Modul Validasi Ekstensi & Ketapan Ukuran Berkas]:::processNode\n")
        new_content.append("        P2[Penguraian Array Byte Binary File]:::processNode\n")
        new_content.append("        P3[Transformasi Struktur UCSB: <br> Konversi Binary ke Gambar Grayscale]:::processNode\n")
        new_content.append("        P4[Pre-processing Gambar: <br> Resize Matriks 224x224 & Normalisasi]:::processNode\n")
        new_content.append("        P5[Algoritma Inferensi Identifikasi Malware<br> Model Mesin ONNX ResNet-18]:::processNode\n")
        new_content.append("        \n")
        new_content.append("        P1 --> P2 --> P3 --> P4 --> P5\n")
        new_content.append("    end\n\n")
        new_content.append("    subgraph OUTPUT [\"3. OUTPUT (Hasil Deteksi, Keputusan & Laporan)\"]\n")
        new_content.append("        O1[Indeks Kategorisasi Prediksi: Malware / Benign]:::outputNode\n")
        new_content.append("        O2[Tindakan Sistem Peringatan <br> Isolasi Karantina / Penghapusan File]:::outputNode\n")
        new_content.append("        O3[Visualisasi Layar GUI <br> Peringatan Modul & Log Status]:::outputNode\n")
        new_content.append("    end\n\n")
        new_content.append("    I1 -->|Pengguna melakukan Scan| P1\n")
        new_content.append("    I2 -->|Sistem Monitoring Real-time| P1\n")
        new_content.append("    P5 --> O1\n")
        new_content.append("    O1 -->|Modul Kebijakan Pertahanan| O2\n")
        new_content.append("    O1 -->|Sinkronisasi Antarmuka Layar| O3\n")
        new_content.append("```\n\n")
        new_content.append("**Penjelasan Alur Kerja Blok Diagram Sistem:**\n\n")
        new_content.append("1. **Input**: Sumber fasilitas gerbang pemicu yang menampung objek sasaran kecurigaan. Input ini dieksekusi melalui **dua cara**, yang pertama secara pasif (manual) oleh tangan pengguna aplikasi melalui *interface scan*, maupun secara pro-aktif mendeteksi *real-time* dari modul *Watchdog Observer* yang otomatis mencatat file baru setiap mendeteksi perubahan masuk dalam struktur penyimpanan komputer.\n")
        new_content.append("2. **Proses**: Tahapan sentral inti perhitungan di dalam perangkat lunak aplikasi. Sistem memulai perhitungannya dengan *whitelist* (pemberitahuan yang sah) untuk hanya menangkap kelompok file `.exe` dan `.dll`. File target lalu dibuka dan *di-ekstrak* rentetan *byte binary*-nya secara mentah. Struktur acak byte angka ini dicetak/ditransformasikan menjadi citra gambar representasi statis (gambar *grayscale*). Sesuai struktur masukan model Machine Learning pendeteksi, dimensi ukuran gambar itu kemudian ditingkatkan spesifikasinya (*resize*) menyentuh rasio baku resolusi dimensi 224x224 pixel dan di-normalisasikan agar dapat disuplai (*feed forward*) ke komputasi mesin kalkulator utama **ONNX Runtime (Jaringan CNN ResNet-18)** untuk diselesaikan klasifikasinya.\n")
        new_content.append("3. **Output**: Perumusan luaran sistem kesimpulan dan implementasi solusi akhir. Aplikasi memusatkan hasil ke dalam vonis kategorisasi file **Aman (*Benign*)** atau **Berbahaya/Virus (*Malware*)**. Jika divonis berbahaya, alur berlanjut menuju kebijakan penanganan mitigasi ancaman otomatis berupa menyita berkasnya (*Karantina*) atau pemusnaham (*Delete*) dari sistem ruang harddisk. Seluruh alur mitigasi ini bersama-sama juga menerbitkan dan meng-update pelaporan statis secara interaktif pada notifikasi pop-up GUI pengguna.\n\n")
        new_content.append("### 3.2.2 Flowchart Diagram Aplikasi\n\n")
        new_content.append("*Flowchart* (diagram alir bersimbol) berikut digunakan memvisualisasikan lebih detail tentang urutan langkah-langkah tata kerja fungsional dan logis penanganan satu file *step-by-step* termasuk pada pengambilan dan pencabangan keputusan di dalam aplikasi:\n\n")
        new_content.append("```mermaid\n")
        new_content.append("flowchart TD\n")
        new_content.append("    START([Mulai Eksekusi Proses]) --> GET_FILE[/Input: Terima Berkas File Sasaran/]\n")
        new_content.append("    GET_FILE --> CHK_VALID{Validasi/Decision:\nApakah File Memiliki\nEkstensi (.exe / .dll)?}\n")
        new_content.append("    \n")
        new_content.append("    CHK_VALID -- Tidak --> END_IGNORE([Terminasi File Selesai - Abaikan])\n")
        new_content.append("    CHK_VALID -- Ya --> READ_BIN[Tahap Pengerjaan: Ekstraksi Data Binary Mentah]\n")
        new_content.append("    \n")
        new_content.append("    READ_BIN --> CONV_IMG[Tahap Pengerjaan: Susun Algoritma Binary Menjadi Citra Pixels]\n")
        new_content.append("    CONV_IMG --> RESIZE[Tahap Pengerjaan: Pelatihan Dimensi Resolusi ke 224x224]\n")
        new_content.append("    RESIZE --> INFER[Tahap Pengerjaan: Feedforward Proses ke Mesin ONNX]\n")
        new_content.append("    \n")
        new_content.append("    INFER --> CHECK_MALWARE{Percabangan Prediksi:\nApakah Skor File\nMelebihi Toleransi Malware?}\n")
        new_content.append("    \n")
        new_content.append("    CHECK_MALWARE -- Kasus Prediksi Aman (Benign) --> LOG_SAFE[Tahap Pengerjaan: Catat Histori Event File Valid]\n")
        new_content.append("    LOG_SAFE --> END_SAFE([Prosedur Scan Selesai - Aman])\n")
        new_content.append("    \n")
        new_content.append("    CHECK_MALWARE -- Kasus Terbukti Malware --> ALERT[Tahap Pengerjaan: Tampilkan GUI Alert Bahaya!]\n")
        new_content.append("    ALERT --> USER_CHOICE{Penanganan Ancaman:\nTindakan Pengguna\natau Respons Sistem?}\n")
        new_content.append("    \n")
        new_content.append("    USER_CHOICE -- Opsi Kurung Isolasi --> ACT_QUARANTINE[Tahap Modifikasi: Paksa Pindah File ke Lokasi Vault Karantina]\n")
        new_content.append("    USER_CHOICE -- Opsi Pembersihan --> ACT_DELETE[Tahap Modifikasi: Perintah Hapus Menyeluruh Target File]\n")
        new_content.append("    \n")
        new_content.append("    ACT_QUARANTINE --> NOTIF[Tahap Display: Tampilkan Output UI Pop-up Status Berhasil]\n")
        new_content.append("    ACT_DELETE --> NOTIF\n")
        new_content.append("    \n")
        new_content.append("    NOTIF --> END_MALWARE([Prosedur Mitigasi Selesai])\n")
        new_content.append("```\n\n")
    elif state == 1 and line.startswith("## 3.2 Kualitas/Kinerja Sistem"):
        state = 2
        new_content.append(line.replace("## 3.2", "## 3.3"))
    elif state == 1:
        pass
    elif state == 2 and line.startswith("## 3.3 Kebutuhan Perangkat Kerja"):
        new_content.append(line.replace("## 3.3", "## 3.4"))
    elif state == 2 and line.startswith("### 3.3.1"):
        new_content.append(line.replace("### 3.3.1", "### 3.4.1"))
    elif state == 2 and line.startswith("### 3.3.2"):
        new_content.append(line.replace("### 3.3.2", "### 3.4.2"))
    elif state == 2 and line.startswith("## 3.4 Dataset"):
        new_content.append(line.replace("## 3.4", "## 3.5"))
    else:
        new_content.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_content)
print("Berhasil!")
