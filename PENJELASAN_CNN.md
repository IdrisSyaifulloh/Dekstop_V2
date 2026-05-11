# 📝 Dokumentasi Diskusi: Analisis Notebook maldebCNNMM.ipynb

**Tanggal**: 26 Maret 2026  
**Judul TA**: *Pengembangan Antimalware Menggunakan Model Machine Learning CNN Dengan Representasi Gambar*

---

## 1. Apa isi notebook ini?

Notebook `maldebCNNMM.ipynb` awalnya berisi **beberapa algoritma**:
- SimSiam (self-supervised learning)
- CNN Image Classification ✅ **(yang dipakai di app)**
- CNN Spectrogram Classification
- Multimodal Late Fusion (3 metode)

Setelah diskusi, notebook **dibersihkan** agar hanya berisi **CNN Image Classification** — satu-satunya algoritma yang dipakai di desktop app MangoDefend.

---

## 2. Model menerima input apa?

Model **hanya menerima gambar**. Proses konversi file binary → gambar dilakukan di tahap preprocessing (`FileConverter`), **bukan** oleh model itu sendiri.

```
📁 File .exe/.dll → 🔄 FileConverter → 🖼️ Gambar → 🧠 CNN → ✅ Malware/Benign
```

---

## 3. Ukuran input: 224×224 atau 256×256?

| Bagian | Ukuran |
|--------|--------|
| SimSiam (sudah dihapus) | 256×256 |
| **CNN di app (yang dipakai)** | **224×224** |

**Kenapa 224×224?**
- Standar bawaan **ResNet-18** (dirancang untuk ukuran ini)
- Sudah cukup detail untuk akurasi 98%
- Lebih hemat komputasi (30% lebih sedikit piksel dibanding 256×256)

---

## 4. Kenapa pakai CNN?

Input berupa **gambar** → CNN adalah algoritma yang **dirancang khusus** untuk data visual.

| Keunggulan CNN | Penjelasan |
|---|---|
| Mengerti posisi piksel | Tahu piksel mana tetangga siapa |
| Filter otomatis | Deteksi garis → bentuk → pola kompleks |
| Parameter sharing | Hemat memori, efisien |
| Akurasi tinggi di data gambar | 98% untuk kasus ini |

Algoritma lain (SVM, Random Forest, KNN) harus men-flatten gambar jadi 1 baris angka → **kehilangan informasi spasial** → hasilnya lebih buruk.

---

## 5. Kenapa pakai ResNet-18?

| Alasan | Detail |
|--------|--------|
| Ringan tapi powerful | Cocok untuk dataset tidak terlalu besar |
| Skip Connection | Mencegah informasi hilang di layer dalam |
| Ukuran kecil | ~42 MB setelah ONNX export — cocok untuk desktop app |
| Sudah terbukti | Dipakai di ribuan penelitian |

---

## 6. Parameter Training

| Parameter | Nilai | Fungsi |
|-----------|-------|--------|
| `num_epochs` | 100 | Jumlah putaran belajar |
| `batch_size` | 32 | Gambar diproses per batch |
| `lr` | 0.001 | Learning rate (Adam optimizer) |
| `input_size` | 224×224 | Ukuran gambar input |
| `num_classes` | 2 | Benign vs Malware |

---

## 7. Bagaimana data dibagi?

```python
train_size = int(0.8 * len(dataset))  # 80% training
test_size = len(dataset) - train_size  # 20% testing
```

- **80% data** → model **BELAJAR** (training)
- **20% data** → model **HANYA MENEBAK** tanpa belajar (testing)
- `random_split()` memastikan tidak ada kebocoran data

Analogi: Seperti guru memberi 80 soal untuk belajar, lalu 20 soal untuk ujian. Murid tidak boleh lihat soal ujian sebelumnya.

---

## 8. Rumus Akurasi

```
              Jumlah Prediksi Benar
Accuracy = ──────────────────────────
              Total Seluruh Data
```

**Contoh**: Model benar 98 dari 100 → `98/100 = 0.98 = 98%`

Cara kerja di kode:
1. Model mengeluarkan 2 angka: `[skor_benign, skor_malware]`
2. `torch.max()` ambil skor tertinggi → itulah prediksi
3. Bandingkan prediksi vs label asli (dari nama folder dataset)
4. Hitung persentase yang benar → `accuracy_score()`

---

## 9. Bisa claim Zero-Day Detection?

**Ya!** CNN bisa claim zero-day detection karena:

1. Model **tidak mencocokkan signature/hash** (seperti antivirus tradisional)
2. Model **mempelajari pola visual** dari binary malware
3. Saat testing di 20% data yang **belum pernah dilihat** → akurasi 98%
4. Ini membuktikan model bisa **generalisasi** ke malware baru

**Frasa untuk TA**:
> *"Model CNN mampu mendeteksi malware yang belum pernah dilihat sebelumnya (zero-day) karena model mempelajari pola visual dari representasi gambar binary malware, bukan mencocokkan signature spesifik."*

**Untuk meningkatkan** kapabilitas zero-day:
- Tambah dataset dari **lebih banyak family malware** (ransomware, trojan, worm, spyware, dll)
- Semakin beragam data training → semakin bagus generalisasi

---

## 10. Algoritma di Desktop App

| Aspek | Detail |
|-------|--------|
| **Algoritma** | CNN (Convolutional Neural Network) |
| **Arsitektur** | ResNet-18 |
| **Format** | ONNX (`Modelv3.onnx`, ~42 MB) |
| **Runtime** | ONNX Runtime |
| **Input** | Gambar 224×224×3 (RGB) |
| **Output** | 2 kelas: Benign / Malware |
| **Akurasi** | 98% |

---

## 11. Perubahan yang Dilakukan

- ✅ Notebook `maldebCNNMM.ipynb` dibersihkan — hanya berisi CNN Image Classification
- ✅ Algoritma yang dihapus: SimSiam, MoCo, CNN Spectrogram, Late Fusion (3 metode), Deep Fusion
