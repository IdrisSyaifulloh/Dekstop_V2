# 🧪 Skenario Pengujian TA

**Judul TA**: *Pengembangan Antimalware Menggunakan Model Machine Learning CNN Dengan Representasi Gambar*

---

## 1. Pengujian Accuracy Model

### Tools yang Digunakan

| Tool | Fungsi |
|------|--------|
| **scikit-learn** | Menghitung accuracy, precision, recall, F1-score, confusion matrix |
| **PyTorch** | Menjalankan model untuk inferensi |
| **matplotlib / seaborn** | Visualisasi confusion matrix |

### Metrik yang Diukur

| Metrik | Rumus | Penjelasan |
|--------|-------|------------|
| **Accuracy** | (TP+TN) / Total | Persentase prediksi benar secara keseluruhan |
| **Precision** | TP / (TP+FP) | Dari yang diprediksi malware, berapa yang benar malware? |
| **Recall** | TP / (TP+FN) | Dari semua malware asli, berapa yang berhasil terdeteksi? |
| **F1-Score** | 2×(Precision×Recall)/(Precision+Recall) | Rata-rata harmonis precision dan recall |

> **TP** = True Positive (prediksi malware, aslinya malware)  
> **TN** = True Negative (prediksi benign, aslinya benign)  
> **FP** = False Positive (prediksi malware, aslinya benign) — "salah alarm"  
> **FN** = False Negative (prediksi benign, aslinya malware) — "lolos deteksi"

### Skenario Pengujian Model

| ID | Skenario | Dataset | Tujuan |
|----|----------|---------|--------|
| M-01 | **Evaluasi data test (20%)** | 20% dari dataset `maldeb/` | Mengukur akurasi model pada data yang tidak pernah dilihat saat training |
| M-02 | **Confusion Matrix** | Data test | Visualisasi distribusi prediksi benar vs salah untuk setiap kelas |
| M-03 | **Per-class accuracy** | Data test | Memastikan model tidak bias ke salah satu kelas |
| M-04 | **Pengujian file real** | File .exe aman (Notepad, Calculator) + malware sample | Menguji model di file asli yang dikonversi menjadi gambar |

### Kode Pengujian Accuracy

```python
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)
import matplotlib.pyplot as plt
import seaborn as sns

# Setelah model selesai training, evaluasi di test set:
model.eval()
all_preds, all_labels = [], []

with torch.no_grad():
    for inputs, labels in test_loader:
        inputs, labels = inputs.to(device), labels.to(device)
        outputs = model(inputs)
        _, preds = torch.max(outputs, 1)
        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

# 1. Classification Report (accuracy, precision, recall, f1)
print(classification_report(all_labels, all_preds,
      target_names=["Benign", "Malware"]))

# 2. Confusion Matrix
cm = confusion_matrix(all_labels, all_preds)
plt.figure(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=["Benign", "Malware"],
            yticklabels=["Benign", "Malware"])
plt.xlabel("Prediksi")
plt.ylabel("Aktual")
plt.title("Confusion Matrix - CNN ResNet-18")
plt.savefig("confusion_matrix.png")
plt.show()
```

### Contoh Tabel Hasil Pengujian Accuracy

| Metrik | Nilai |
|--------|-------|
| Accuracy | 98% |
| Precision (Malware) | ...% |
| Recall (Malware) | ...% |
| F1-Score (Malware) | ...% |
| Precision (Benign) | ...% |
| Recall (Benign) | ...% |
| F1-Score (Benign) | ...% |

### Contoh Confusion Matrix

|  | Prediksi Benign | Prediksi Malware |
|--|---|---|
| **Aktual Benign** | TN = ... | FP = ... |
| **Aktual Malware** | FN = ... | TP = ... |

---

## 2. Pengujian Responsif GUI dan Fitur

### Tools yang Digunakan

| Tool | Fungsi |
|------|--------|
| **Pengujian Manual (Black Box Testing)** | Menguji fungsionalitas dari sudut pandang pengguna |
| **Stopwatch / Time Measurement** | Mengukur waktu respon fitur |
| **Screenshot** | Dokumentasi visual hasil pengujian |

### Skenario Pengujian GUI & Fitur

#### A. Fitur Scan File

| ID | Skenario | Langkah | Hasil yang Diharapkan | Status |
|----|----------|---------|----------------------|--------|
| G-01 | Scan file `.exe` aman | 1. Klik menu Scan → 2. Pilih file → 3. Tunggu hasil | Hasil: "Benign", dialog muncul < 5 detik | ☐ |
| G-02 | Scan file `.exe` malware | 1. Klik menu Scan → 2. Pilih file malware → 3. Tunggu hasil | Hasil: "Malware", dialog muncul < 5 detik | ☐ |
| G-03 | Scan file non-executable | 1. Klik menu Scan → 2. Pilih file .txt/.pdf | File diproses tanpa error | ☐ |
| G-04 | Scan file besar (>5 MB) | 1. Klik menu Scan → 2. Pilih file besar | Scan berhasil, GUI tetap responsif (tidak freeze) | ☐ |
| G-05 | Batal scan saat proses | 1. Mulai scan → 2. Klik batal | Scan berhenti, tidak crash | ☐ |

#### B. Fitur Scan Folder

| ID | Skenario | Langkah | Hasil yang Diharapkan | Status |
|----|----------|---------|----------------------|--------|
| G-06 | Scan folder kecil (< 10 file) | 1. Pilih Scan Folder → 2. Pilih folder | Semua file discan, progress bar berjalan | ☐ |
| G-07 | Scan folder besar (> 50 file) | 1. Pilih Scan Folder → 2. Pilih folder | Scan berjalan tanpa crash, GUI responsif | ☐ |
| G-08 | Scan folder kosong | 1. Pilih folder kosong | Muncul pesan yang sesuai | ☐ |

#### C. Fitur Real-Time Protection

| ID | Skenario | Langkah | Hasil yang Diharapkan | Status |
|----|----------|---------|----------------------|--------|
| G-09 | Toggle ON | 1. Buka menu Protection → 2. Aktifkan toggle | Status berubah "Active", monitoring dimulai | ☐ |
| G-10 | Toggle OFF | 1. Buka menu Protection → 2. Matikan toggle | Status berubah "Inactive", monitoring berhenti | ☐ |
| G-11 | Deteksi file malware real-time | 1. Aktifkan protection → 2. Copy file malware ke folder yang dimonitor | Notifikasi muncul, file terdeteksi | ☐ |
| G-12 | File aman tidak di-flag | 1. Aktifkan protection → 2. Copy file .txt biasa | Tidak ada alarm palsu | ☐ |

#### D. Tampilan Hasil Scan (Result Dialog)

| ID | Skenario | Langkah | Hasil yang Diharapkan | Status |
|----|----------|---------|----------------------|--------|
| G-13 | Hasil scan benign | Scan file aman | Dialog hijau, status "Benign" | ☐ |
| G-14 | Hasil scan malware | Scan file malware | Dialog merah, status "Malware" | ☐ |
| G-15 | Info detail file | Klik hasil scan | Tampil nama file, ukuran, hash, model info | ☐ |

#### E. Navigasi & UI

| ID | Skenario | Langkah | Hasil yang Diharapkan | Status |
|----|----------|---------|----------------------|--------|
| G-16 | Navigasi sidebar | Klik setiap menu di sidebar (Dashboard, Scan, Protection, Update) | Halaman berubah sesuai menu, transisi smooth | ☐ |
| G-17 | Resize window | Drag sudut window untuk resize | Layout menyesuaikan, tidak ada elemen yang terpotong | ☐ |
| G-18 | Minimize & restore | Minimize → klik di taskbar | Window kembali normal | ☐ |
| G-19 | Dashboard info | Buka halaman Dashboard | Semua info tampil (total scan, model version, dll) | ☐ |

#### F. Model Update

| ID | Skenario | Langkah | Hasil yang Diharapkan | Status |
|----|----------|---------|----------------------|--------|
| G-20 | Cek versi model | Buka halaman Update | Tampil versi model saat ini & ukuran file | ☐ |

### Tabel Ringkasan Hasil Pengujian GUI

| Kategori | Total Skenario | Berhasil | Gagal | Persentase Keberhasilan |
|----------|---------------|----------|-------|------------------------|
| Scan File | 5 | ... | ... | ...% |
| Scan Folder | 3 | ... | ... | ...% |
| Real-Time Protection | 4 | ... | ... | ...% |
| Result Dialog | 3 | ... | ... | ...% |
| Navigasi & UI | 4 | ... | ... | ...% |
| Model Update | 1 | ... | ... | ...% |
| **TOTAL** | **20** | **...** | **...** | **...%** |

### Pengukuran Waktu Respon

| Fitur | Waktu Respon | Kategori |
|-------|-------------|----------|
| Scan single file (.exe kecil) | ... detik | ☐ Baik (< 3s) / ☐ Cukup (3-10s) / ☐ Lambat (> 10s) |
| Scan single file (.exe besar) | ... detik | ☐ Baik / ☐ Cukup / ☐ Lambat |
| Navigasi antar halaman | ... detik | ☐ Baik (< 1s) / ☐ Cukup / ☐ Lambat |
| Buka aplikasi | ... detik | ☐ Baik (< 5s) / ☐ Cukup (5-15s) / ☐ Lambat |
| Toggle real-time protection | ... detik | ☐ Baik (< 1s) / ☐ Cukup / ☐ Lambat |
