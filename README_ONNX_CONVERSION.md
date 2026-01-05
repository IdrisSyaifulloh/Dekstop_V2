# Panduan Konversi Model maldebCNN ke ONNX

## 📋 Daftar File

Berikut adalah file-file yang telah dibuat untuk konversi model:

1. **`konversi_model_onnx.md`** - Dokumentasi lengkap untuk laporan magang
2. **`convert_to_onnx.py`** - Script untuk konversi model PyTorch ke ONNX
3. **`inference_onnx.py`** - Script untuk menggunakan model ONNX

## 🚀 Cara Menggunakan

### Langkah 1: Instalasi Dependencies

Pastikan semua library yang diperlukan sudah terinstall:

```bash
pip install torch torchvision onnx onnxruntime pillow
```

### Langkah 2: Konversi Model

Jalankan script konversi:

```bash
python convert_to_onnx.py
```

**Catatan**: Pastikan file `imgcnnmaldeb.pth` ada di folder yang sama dengan script.

Output yang dihasilkan:
- File `maldebCNN.onnx` - Model dalam format ONNX

### Langkah 3: Testing Model ONNX

Jalankan script inference untuk testing:

```bash
python inference_onnx.py
```

Script ini akan meminta:
1. Path ke single image untuk prediksi
2. Path ke folder berisi multiple images untuk batch prediction

## 📊 Untuk Laporan Magang

File `konversi_model_onnx.md` berisi:

- ✅ Penjelasan lengkap tentang ONNX
- ✅ Arsitektur model maldebCNN
- ✅ Langkah-langkah konversi detail
- ✅ Script lengkap dengan penjelasan
- ✅ Cara verifikasi dan testing
- ✅ Perbandingan performa
- ✅ Troubleshooting
- ✅ Diagram visual (flowchart dan arsitektur)

Anda dapat menggunakan dokumentasi ini langsung di laporan magang Anda.

## 🔍 Struktur Model

```
Input: 224x224x3 (RGB Image/Spectrogram)
    ↓
ResNet-18 Backbone
    ↓
Feature Extraction (512 features)
    ↓
Fully Connected Layer
    ↓
Output: 2 classes (Benign/Malware)
```

## 💡 Tips

1. **Untuk laporan**: Gunakan diagram dan penjelasan dari `konversi_model_onnx.md`
2. **Untuk demo**: Gunakan `inference_onnx.py` untuk menunjukkan cara kerja model
3. **Untuk deployment**: Model ONNX dapat digunakan di berbagai platform

## 📝 Contoh Output Konversi

```
============================================================
KONVERSI MODEL PYTORCH KE ONNX
============================================================

[1/6] Loading PyTorch model...
✓ Model loaded successfully from 'imgcnnmaldeb.pth'

[2/6] Preparing dummy input...
✓ Dummy input created with shape: torch.Size([1, 3, 224, 224])

[3/6] Exporting to ONNX format...
✓ Model exported to 'maldebCNN.onnx'
  File size: 44.92 MB

[4/6] Verifying ONNX model...
✓ ONNX model is valid!

[5/6] Testing with ONNX Runtime...
✓ Inference completed successfully

[6/6] Comparing outputs...
  ✓ Outputs match! Conversion successful.

============================================================
KONVERSI BERHASIL!
============================================================
```

## 🎯 Keuntungan ONNX

- **Portabilitas**: Dapat dijalankan di berbagai platform
- **Performa**: Optimasi runtime yang lebih baik
- **Deployment**: Lebih mudah untuk production
- **Interoperabilitas**: Support berbagai framework

## 📚 Referensi

- [PyTorch ONNX Documentation](https://pytorch.org/docs/stable/onnx.html)
- [ONNX Official Website](https://onnx.ai/)
- [ONNX Runtime](https://onnxruntime.ai/)

---

**Dibuat untuk**: Laporan Magang MangoDefend Project  
**Tanggal**: 2026-01-01
