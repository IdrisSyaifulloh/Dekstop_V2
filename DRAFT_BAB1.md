# BAB 1 - PENDAHULUAN (DRAFT)

**Judul TA**: *Pengembangan Antimalware Menggunakan Model Machine Learning CNN Dengan Representasi Gambar*

---

## 1.1 Latar Belakang

Ancaman siber di Indonesia terus mengalami peningkatan yang signifikan dari tahun ke tahun. Berdasarkan data Badan Siber dan Sandi Negara (BSSN), pada periode Januari hingga Agustus 2024, tercatat sebanyak 122,79 juta anomali trafik internet di Indonesia. Dari jumlah tersebut, aktivitas *malware* mendominasi dengan persentase 59,26% atau sekitar 72,77 juta serangan, diikuti oleh aktivitas *trojan* sebesar 18,20% [1]. Pada tahun 2025, angka ini melonjak drastis — BSSN mencatat 3,64 miliar anomali trafik serangan siber hanya dalam periode Januari hingga Juli 2025, di mana 83,68% di antaranya merupakan serangan berbasis *malware* [2]. Data ini menunjukkan bahwa *malware* tetap menjadi ancaman siber paling dominan yang dihadapi Indonesia.

Di tingkat global, AV-TEST Institute mencatat rata-rata lebih dari 450.000 program berbahaya (*malware*) dan *Potentially Unwanted Applications* (PUA) baru terdaftar setiap harinya [3]. Jumlah total sampel *malware* yang terdaftar di database AV-TEST untuk sistem Windows meningkat dari 920 juta pada tahun 2024 menjadi 995 juta pada tahun 2025, yang merepresentasikan pertumbuhan sebesar 8% [4]. Tingginya volume *malware* baru yang muncul setiap hari menjadi tantangan besar bagi metode deteksi tradisional berbasis *signature* yang memerlukan pembaruan database secara manual dan tidak mampu mendeteksi varian *malware* baru (*zero-day*) yang belum terdaftar.

Untuk mengatasi keterbatasan deteksi berbasis *signature*, beberapa penelitian telah mengeksplorasi penggunaan teknik *machine learning* untuk deteksi *malware*. Salah satu pendekatan yang menarik perhatian adalah teknik visualisasi *malware* sebagai gambar. Teknik ini bekerja dengan mengonversi *binary file* menjadi representasi gambar, kemudian menggunakan *Convolutional Neural Network* (CNN) untuk mengklasifikasikan gambar tersebut sebagai *malware* atau *benign* (aman). Penelitian yang dipublikasikan di IEEE pada tahun 2023 menunjukkan bahwa metode konversi *malware binary* menjadi gambar *grayscale* yang diklasifikasikan menggunakan CNN mampu menghasilkan akurasi yang tinggi dalam mendeteksi dan mengkategorikan *malware* [5]. Pada tahun 2024, penelitian yang dipublikasikan di MDPI *Applied Sciences* mengembangkan sistem klasifikasi *malware* berbasis gambar menggunakan arsitektur CNN dan *Vision Transformer* (ViT) yang menunjukkan akurasi tinggi dalam membedakan file berbahaya dan aman [6].

Meskipun penelitian-penelitian tersebut menunjukkan efektivitas CNN dalam klasifikasi *malware* berbasis gambar, sebagian besar penelitian hanya berfokus pada pengembangan model dan evaluasi akurasi tanpa mengimplementasikan model tersebut ke dalam aplikasi yang dapat digunakan oleh pengguna secara langsung. Oleh karena itu, penelitian ini bertujuan untuk **mengembangkan aplikasi *antimalware* berbasis desktop** yang mengimplementasikan model CNN dengan representasi gambar, dilengkapi dengan fitur *real-time protection*, konversi file otomatis, serta antarmuka pengguna yang interaktif, sehingga dapat dimanfaatkan secara langsung untuk mendeteksi ancaman *malware*.

---

## 1.2 Rumusan Masalah dan Solusi

### Rumusan Masalah

1. Pada penelitian sebelumnya pada klasifikasi *malware* representasi gambar hanya berfokus pada akurasi model dan belum dimplementasikan pada perangkat lunak aplikasi yang siap dipakai oleh pengguna akhir (*end-user*).

2. Diperlukannya sebuah arsitektur untuk menjebatani (*deploy*) dan mengintegrasikan model *Machine Learning* agar dapat digunakan secara ringan untuk inferensi sistem pada tingkat lokal / komputer *desktop*.

3. Integrasi model *machine learning* (CNN) pada lingkungan *desktop* memerlukan suatu rancangan antarmuka pengguna grafis (GUI) dan komponen pemantauan waktu nyata (*real-time protection*) agar model dapat menerima *input* file dari pengguna dasar (*end-user*) dengan baik.

4. Proses konversi format berkas asali (ekstensi `.exe` atau `.dll`) menjadi bentuk representasi gambar secara dinamis untuk kemudian diproses oleh model pendeteksi (*inferensi*), memerlukan pendekatan arsitektur khusus agar tidak membebani kinerja dan memori (*resource*) komputer pengguna secara berlebihan.

### Solusi

1. Mengadopsi teknologi *Machine Learning* dengan pendekatan *pre-trained* CNN (seperti arsitektur ResNet) sebagai *engine* pendeteksi *malware* dalam aplikasi, melanjutkan penelitian sebelumnya menjadi wujud fisik sebuah *software*.

2. Mengimplementasikan konversi arsitektur kerangka *neural network* ke dalam wujud ONNX (*Open Neural Network Exchange*) dan mengeksekusinya menggunakan *ONNX Runtime*. Pendekatan ini dipilih agar model dapat melakukan klasifikasi (inferensi) dengan konsumsi parameter lokal yang sangat efisien dan cepat di lingkungan *desktop*.

3. Membangun dan merancang aplikasi *antimalware* antarmuka GUI tingkat masa kini (contohnya lewat *framework* PySide6) yang memiliki fitur perlindungan dasar esensial: pemindaian berkas (*file/folder scan*), pemantauan sistem nyata (*real-time protection*), hingga notifikasi ancaman yang intuitif.

---

## 1.3 Tujuan

1. Mengimplementasikan model *machine learning Convolutional Neural Network* (CNN) berbasis representasi gambar yang telah dilatih sebelumnya (*pre-trained*) ke dalam kerangka sebuah aplikasi *desktop*.

2. Membangun perangkat lunak *antimalware* dengan *Graphical User Interface* (GUI) yang interaktif dan dapat digunakan secara fungsional oleh pengguna akhir (*end-user*).

3. Menyediakan fitur pengamanan tingkat sistem pengguna seperti pemindaian (*scanning*) statis dan pemantauan berkas masukan secara langsung (*real-time protection*).

4. Menguji dan mengevaluasi ketanggapan performa (responsivitas) aplikasi *desktop*, serta memastikan fungsionalitas inferensi model yang diadopsi (*ONNX Runtime*) berjalan lancar saat mendeteksi *malware*.

---
## 1.4 Batasan Masalah

Agar ruang lingkup penelitian tetap terarah pada pembuatan aplikasi, batasan masalah yang ditetapkan adalah:

1. Penelitian ini pada pembuatan perangkat lunak (aplikasi *antimalware*), bukan mencari atau melatih ulang model. Model deteksi yang digunakan adalah model *machine learning* (CNN) yang sudah di latih (*pre-trained*) ,yang langsung diintegrasikan ke dalam aplikasi.
2. Aplikasi ini dibuat khusus untuk berjalan di atas sistem operasi **Windows 10/11**, karena fitur keamanannya memanfaatkan fungsi bawaan dari sistem Windows itu sendiri.
3. Sistem hanya memindai file eksekusi atau program (seperti ekstensi `.exe` atau `.dll`). Aplikasi tidak dirancang untuk memindai serangan malware jaringan atau malware yang langsung masuk ke memori komputer (*file-less malware*).
4. Proses deteksi murni melihat bentuk file sebelum dijalankan (mengubah kode menjadi gambar statis). Aplikasi tidak memantau atau menganalisis tingkah laku program saat aplikasi tersebut sedang aktif berjalan.
5. Jika ditemukan indikasi malware, aplikasi hanya akan melakukan tindakan penahanan (**Karantina**) atau **Penghapusan** file. Tidak ada fitur "pengobatan/pembersihan" untuk mengembalikan file asli yang sudah terinfeksi virus.
6. Pengujian aplikasi masih dilakukan pada tahap lingkungan laboratorium (terkontrol), belum diuji secara luas untuk menggantikan perangkat lunak antivirus utama pada penggunaan komputer harian (*production / real-world deployment*).

---

## Daftar Referensi

| No | Referensi | Link |
|----|-----------|------|
| [1] | BSSN - Data Anomali Trafik Internet Indonesia Januari-Agustus 2024 (122,79 juta serangan, 59,26% malware) | https://infobanknews.com (sumber: BSSN via InfobankNews) |
| [2] | BSSN - Data Anomali Trafik Serangan Siber Januari-Juli 2025 (3,64 miliar anomali, 83,68% malware) | https://tempo.co (sumber: BSSN via Tempo.co) |
| [3] | AV-TEST Institute - Malware Statistics 2024-2025 (450.000+ malware baru per hari) | https://www.av-test.org/en/statistics/malware/ |
| [4] | AV-TEST Institute - Total Malware Windows (920 juta 2024 → 995 juta 2025) | https://www.av-test.org/en/statistics/malware/ |
| [5] | IEEE Xplore (2023) - Malware Binary to Grayscale Image Classification using CNN | https://ieeexplore.ieee.org (cari: "malware image CNN classification 2023") |
| [6] | MDPI Applied Sciences (2024) - Enhanced Image-Based Malware Classification using CNN and ViT | https://www.mdpi.com (cari: "malware image classification CNN ResNet 2024") |

> ⚠️ **CATATAN PENTING**: Link di atas adalah sumber yang ditemukan melalui pencarian web. Sebelum dimasukkan ke TA, **pastikan untuk mengakses langsung** setiap link, verifikasi data, dan catat judul paper/artikel lengkap, penulis, tahun, dan DOI/URL yang tepat.
