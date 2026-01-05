# 📦 Panduan Distribusi MangoDefend ke Multiple Users

## 🎯 Skenario: 3 User

Anda punya 3 user yang akan menggunakan MangoDefend. Ada beberapa cara distribusi:

---

## 🚀 Cara 1: Standalone EXE (Recommended untuk 3 User)

### **Konsep:**
- Setiap user dapat **copy EXE yang sama**
- Embedded backend berjalan lokal di setiap laptop
- Data independen per user

### **Langkah Distribusi:**

#### **Step 1: Build EXE**

```bash
# Di laptop developer
cd desktop_app
pyinstaller MangoDefend.spec
```

**Output:** `dist/MangoDefend/` folder

#### **Step 2: Prepare Distribution Package**

```
MangoDefend_v1.0/
├── MangoDefend.exe
├── config.ini
├── models/
│   └── Modelv3.onnx
├── assets/
│   └── icon.ico
└── README.txt
```

#### **Step 3: Compress**

```bash
# Zip folder
Compress-Archive -Path dist/MangoDefend -DestinationPath MangoDefend_v1.0.zip
```

#### **Step 4: Distribute**

**Option A: USB Flash Drive**
```
1. Copy MangoDefend_v1.0.zip ke flash disk
2. Kasih ke User 1, 2, 3
3. Mereka extract di laptop masing-masing
4. Run MangoDefend.exe
```

**Option B: Google Drive / OneDrive**
```
1. Upload MangoDefend_v1.0.zip ke cloud
2. Share link ke User 1, 2, 3
3. Mereka download & extract
4. Run MangoDefend.exe
```

**Option C: Email**
```
1. Attach MangoDefend_v1.0.zip (jika < 25MB)
2. Email ke User 1, 2, 3
3. Mereka download & extract
4. Run MangoDefend.exe
```

---

### **User Experience:**

**User 1 (Laptop A):**
```
1. Extract MangoDefend_v1.0.zip
2. Double-click MangoDefend.exe
3. ✅ Embedded backend start (127.0.0.1:8000)
4. ✅ Data tersimpan di C:\Users\User1\.mangodefend\
```

**User 2 (Laptop B):**
```
1. Extract MangoDefend_v1.0.zip
2. Double-click MangoDefend.exe
3. ✅ Embedded backend start (127.0.0.1:8000)
4. ✅ Data tersimpan di C:\Users\User2\.mangodefend\
```

**User 3 (Laptop C):**
```
1. Extract MangoDefend_v1.0.zip
2. Double-click MangoDefend.exe
3. ✅ Embedded backend start (127.0.0.1:8000)
4. ✅ Data tersimpan di C:\Users\User3\.mangodefend\
```

**Catatan:**
- ✅ Setiap user independen
- ✅ Tidak perlu setup backend
- ✅ Tidak perlu network
- ❌ Data tidak sync antar user

---

## 🌐 Cara 2: Shared Backend (Untuk Data Terpusat)

### **Konsep:**
- 1 laptop jadi server (atau cloud)
- 3 user connect ke server yang sama
- Data terpusat

### **Langkah Setup:**

#### **Step 1: Setup Server**

**Option A: 1 Laptop Jadi Server**
```bash
# Di laptop yang akan jadi server
cd backend
docker-compose up -d

# Get IP address
ipconfig
# Example: 192.168.1.100
```

**Option B: Cloud Server**
```bash
# Deploy ke DigitalOcean/AWS/Railway
# Get URL: https://api.mangodefend.com
```

#### **Step 2: Build EXE dengan Config Server**

Edit `config.ini`:
```ini
[Backend]
use_embedded = false
url = http://192.168.1.100:8000  # IP server
```

Build EXE:
```bash
pyinstaller MangoDefend.spec
```

#### **Step 3: Distribute ke 3 User**

Sama seperti Cara 1, tapi:
- ✅ Semua user connect ke 1 backend
- ✅ Data terpusat
- ✅ Scan history sync

---

## 📊 Comparison

| Aspek | Cara 1 (Standalone) | Cara 2 (Shared Backend) |
|-------|---------------------|-------------------------|
| **Setup** | Mudah | Medium |
| **User Experience** | Extract & Run | Extract & Run |
| **Data** | Independen | Terpusat |
| **Network** | Tidak perlu | Perlu LAN/Internet |
| **Maintenance** | Per user | Centralized |
| **Recommended for** | 3 user (demo/TA) | Production |

---

## 🎯 Rekomendasi untuk 3 User

### **Untuk Tugas Akhir / Demo:**

**Gunakan Cara 1 (Standalone)**

**Alasan:**
- ✅ Mudah distribusi (1 file ZIP)
- ✅ User tidak perlu setup apapun
- ✅ Tidak perlu network
- ✅ Fokus ke fitur desktop app

**Distribusi:**
```
1. Build EXE
2. Zip folder
3. Share via:
   - USB flash disk
   - Google Drive
   - Email
4. User extract & run
```

---

### **Untuk Production / Real Users:**

**Gunakan Cara 2 (Shared Backend)**

**Alasan:**
- ✅ Data terpusat
- ✅ Model update untuk semua user sekaligus
- ✅ Analytics
- ✅ Centralized monitoring

---

## 📝 README.txt untuk User

Buat file `README.txt` di dalam ZIP:

```
===========================================
   MangoDefend - Malware Detection AI
===========================================

CARA INSTALL:
1. Extract folder MangoDefend_v1.0.zip
2. Buka folder MangoDefend
3. Double-click MangoDefend.exe
4. Tunggu beberapa detik (backend akan start otomatis)
5. Aplikasi siap digunakan!

FITUR:
- Scan File/Folder untuk malware
- Real-time Protection (toggle ON/OFF)
- Model Auto-Update
- Scan History

SYSTEM REQUIREMENTS:
- Windows 10/11
- 4GB RAM minimum
- 500MB disk space

TROUBLESHOOTING:
- Jika ada error, run as Administrator
- Jika Windows Defender block, add to exception
- Jika lambat, disable real-time protection

KONTAK:
Email: your.email@example.com
```

---

## 🔒 Windows Defender Issue

**Masalah:** Windows Defender mungkin block EXE

**Solusi untuk User:**
```
1. Klik "More info"
2. Klik "Run anyway"

Atau:

1. Windows Security → Virus & threat protection
2. Manage settings
3. Add exclusion → Folder
4. Pilih folder MangoDefend
```

---

## 📦 Checklist Distribusi

**Sebelum distribusi, pastikan:**

- [ ] EXE sudah di-build dan tested
- [ ] Model ML sudah ter-bundle
- [ ] Config.ini sudah benar
- [ ] README.txt sudah dibuat
- [ ] ZIP file size reasonable (< 500MB)
- [ ] Tested di laptop lain (clean install)
- [ ] Antivirus tidak block

---

## 🎉 Quick Start untuk 3 User

```bash
# 1. Build EXE
pyinstaller MangoDefend.spec

# 2. Zip
Compress-Archive -Path dist/MangoDefend -DestinationPath MangoDefend_v1.0.zip

# 3. Share
# Upload ke Google Drive atau copy ke flash disk

# 4. Instruksi ke user:
# "Download, extract, run MangoDefend.exe"
```

**DONE!** 3 user bisa langsung pakai! 🚀
