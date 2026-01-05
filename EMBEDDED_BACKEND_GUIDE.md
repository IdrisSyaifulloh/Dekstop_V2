# Embedded Backend - User Guide

## 🎯 Apa itu Embedded Backend?

**Embedded Backend** adalah backend FastAPI yang berjalan **di dalam aplikasi desktop** Anda. Tidak perlu hosting, tidak perlu Docker, tidak perlu setup server!

## ✨ Keuntungan

✅ **Tidak Perlu Hosting** - Backend berjalan lokal di komputer user
✅ **Tidak Perlu Setup** - User cukup jalankan EXE
✅ **Tetap Ada Backend** - Semua fitur sync dan logging tetap jalan
✅ **Privacy** - Data tidak keluar dari komputer user
✅ **Gratis** - Tidak ada biaya hosting

## 🏗️ Cara Kerja

```
User's Computer
├── MangoDefend.exe
│   ├── Desktop UI (PySide6)
│   ├── ML Scanner
│   └── Embedded Backend (FastAPI) ← Runs in background thread
│       └── SQLite Database
```

**Flow:**
1. User jalankan `MangoDefend.exe`
2. Embedded backend start otomatis di background (port 8000)
3. Desktop app connect ke `http://127.0.0.1:8000`
4. Semua fitur sync dan logging berjalan normal
5. Data disimpan di SQLite lokal (`~/.mangodefend/database.db`)

## 🚀 Cara Menggunakan

### **1. Default (Embedded Backend Enabled)**

```ini
# config.ini
[Backend]
use_embedded = true  # Default
```

**User hanya perlu:**
1. Extract ZIP
2. Run `MangoDefend.exe`
3. ✅ Done! Backend sudah jalan otomatis

### **2. Disable Embedded Backend**

```ini
# config.ini
[Backend]
use_embedded = false
url = https://api.yourdomain.com  # Use external backend
```

## 📊 Database

**Location:** `C:\Users\<username>\.mangodefend\database.db` (Windows)

**Schema:**
```sql
CREATE TABLE scan_results (
    id INTEGER PRIMARY KEY,
    filename TEXT,
    label TEXT,
    file_hash TEXT UNIQUE,
    created_at TIMESTAMP
)
```

## 🔌 API Endpoints

Backend menyediakan endpoints yang sama seperti backend eksternal:

### **Health Check**
```http
GET http://127.0.0.1:8000/health
```

Response:
```json
{
  "status": "healthy",
  "service": "MangoDefend Embedded Backend",
  "version": "1.0.0",
  "mode": "embedded"
}
```

### **Save Scan Result**
```http
POST http://127.0.0.1:8000/scanning-file
Content-Type: application/json

{
  "filename": "virus.exe",
  "label": "Malware",
  "file_hash": "abc123..."
}
```

### **Get History**
```http
GET http://127.0.0.1:8000/history-scan?limit=10
```

### **Get Statistics**
```http
GET http://127.0.0.1:8000/stats
```

Response:
```json
{
  "total_scans": 150,
  "by_label": {
    "Malware": 45,
    "Benign": 105
  }
}
```

## 🔧 Technical Details

### **Implementation**

**File:** `core/embedded_backend.py`

**Key Components:**
- FastAPI app running in background thread
- SQLite database for storage
- CORS enabled for localhost
- Auto-start on app launch
- Auto-stop on app exit

### **Thread Safety**

Backend runs in daemon thread:
```python
self.server_thread = threading.Thread(
    target=self._run_server,
    daemon=True,
    name="EmbeddedBackend"
)
```

### **Port Configuration**

Default: `127.0.0.1:8000` (localhost only)

**Why 127.0.0.1?**
- Only accessible from local computer
- Not accessible from network
- More secure

## 📦 Building EXE

Embedded backend akan ter-bundle dalam EXE:

```python
# MangoDefend.spec
hiddenimports=[
    'uvicorn',
    'fastapi',
    'sqlite3',
    ...
]
```

**EXE Size:** ~250-300 MB (includes FastAPI + uvicorn)

## 🆚 Comparison

| Feature | Embedded Backend | External Backend | No Backend |
|---------|------------------|------------------|------------|
| Setup | None | Docker/VPS | None |
| Hosting Cost | Free | $5-20/month | Free |
| Data Privacy | Local only | Server | Local only |
| Multi-device Sync | ❌ | ✅ | ❌ |
| Internet Required | ❌ | ✅ | ❌ |
| Centralized Logging | ❌ | ✅ | ❌ |

## ✅ Best Use Cases

**Embedded Backend cocok untuk:**
- ✅ Tugas Akhir / Demo
- ✅ Standalone desktop app
- ✅ Privacy-focused users
- ✅ Offline environments
- ✅ Single-user applications

**External Backend lebih baik untuk:**
- ✅ Multi-user systems
- ✅ Centralized monitoring
- ✅ Cross-device sync
- ✅ Team collaboration

## 🐛 Troubleshooting

### Port 8000 Already in Use

**Error:** `Address already in use`

**Solution:**
```ini
# Change port in code
embedded_backend = EmbeddedBackend(port=8001)
```

### Backend Not Starting

**Check:**
1. Port available? `netstat -an | findstr :8000`
2. Firewall blocking? Allow in Windows Firewall
3. Check logs in console

### Database Locked

**Error:** `database is locked`

**Solution:**
- Close other instances of app
- Delete `~/.mangodefend/database.db` and restart

## 🎉 Summary

Embedded Backend adalah solusi **perfect** untuk:
- Distribusi EXE tanpa setup
- Tetap punya backend functionality
- Tidak perlu hosting
- Privacy-first approach

**User experience:**
1. Download EXE
2. Run
3. ✅ Everything works!

No Docker, no hosting, no setup! 🚀
