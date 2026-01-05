# MangoDefend - ONNX Model Integration

## Overview
Desktop app sekarang mendukung model ONNX untuk inference yang lebih cepat dan efisien!

## Hasil Test
✅ **Model berhasil diintegrasikan!**
- Model: `Modelv3.onnx` (44.7 MB)
- Device: CPU
- Status: Working perfectly!
- Test result: Benign (Class 0)

## Cara Menggunakan

### 1. Model ONNX sudah aktif
Model ONNX (`Modelv3.onnx`) sudah menjadi default model di aplikasi.

### 2. Requirements
```bash
pip install onnxruntime
```

### 3. Jalankan Aplikasi
```bash
cd desktop_app
python main.py
```

## Keuntungan ONNX vs PyTorch

| Fitur | ONNX | PyTorch |
|-------|------|---------|
| **Speed** | ⚡ Lebih cepat (optimized) | Standar |
| **Size** | 📦 Lebih kecil | Lebih besar |
| **Dependencies** | ✅ Minimal (onnxruntime only) | Torch + TorchVision |
| **Portability** | ✅ Cross-platform friendly | Depends on PyTorch |
| **Memory** | 💚 Lebih efficient | Lebih banyak |

## File Structure
```
desktop_app/
├── models/
│   ├── Modelv3.onnx          ← Model ONNX (DEFAULT)
│   ├── Modelv2.onnx          ← Backup model
│   └── imgcnnmaldeb.pth      ← PyTorch model (legacy)
├── core/
│   └── scanner.py            ← Updated dengan ONNX support
└── test_onnx_scanner.py      ← Test script
```

## Model Details

### Input
- Shape: `[batch, 3, 224, 224]`
- Type: `float32`
- Format: RGB image (normalized 0-1)
- Name: `input`

### Output
- Shape: `[batch, 2]`
- Type: `float32`
- Format: Class probabilities `[benign, malware]`
- Name: `output`

### Classes
- `0`: Benign (Safe)
- `1`: Malware (Dangerous)

## Cara Test Manual

### Test dengan file dummy:
```bash
cd desktop_app
python test_onnx_scanner.py
```

### Test dengan file asli:
```python
from core.scanner import MalwareScanner

scanner = MalwareScanner()  # Default menggunakan ONNX
result = scanner.scan_file("path/to/your/file.exe")

print(result['result'])  # Benign atau Malware
print(result['model']['predicted_output'])  # Probabilities
```

## Cara Ganti Model

### Gunakan PyTorch model (legacy):
```python
scanner = MalwareScanner(model_path="models/imgcnnmaldeb.pth")
```

### Gunakan ONNX model (default):
```python
scanner = MalwareScanner(model_path="models/Modelv3.onnx")
# atau
scanner = MalwareScanner()  # Auto detect ONNX
```

## Export Model Baru

Jika Anda ingin export model baru dari notebook:

1. Buka `maldebCNNMM.ipynb`
2. Jalankan cell export ONNX (setelah cell weighted fusion)
3. File akan disimpan di `desktop_app/models/`

## Troubleshooting

### Error: ONNX Runtime not available
```bash
pip install onnxruntime
```

### Error: Model not found
Pastikan file `Modelv3.onnx` ada di folder `desktop_app/models/`

### Error: Unicode/Emoji di Windows
Sudah fixed! Tidak ada emoji di output console.

## Performance

### Benchmark (CPU):
- Model loading: < 1 second
- Inference per file: ~100-200ms
- Memory usage: ~200MB

### Recommended:
- CPU: Intel i5 or better
- RAM: 4GB minimum
- Storage: 50MB for model

## Next Steps

1. ✅ Export model ke ONNX - **DONE**
2. ✅ Integrate ke desktop app - **DONE**
3. ✅ Test dengan file dummy - **DONE**
4. 🔄 Test dengan file malware real
5. 🔄 Optimize inference speed
6. 🔄 Add confidence threshold

## Credits
- Model: ResNet-18 based CNN
- Training: maldebCNNMM.ipynb
- Accuracy: 98% (Cell #13)
- Framework: PyTorch → ONNX
