# Real-time Protection & Model Update - User Guide

Panduan lengkap untuk menggunakan fitur **Real-time Protection** dan **Auto-Update Model** di MangoDefend.

## 🛡️ Real-time Protection

### Apa itu Real-time Protection?

Real-time Protection adalah fitur background service yang secara otomatis:
- **Monitor** semua file baru yang dibuat/dimodifikasi
- **Scan** file secara real-time menggunakan AI
- **Notify** user jika malware terdeteksi
- **Block** file berbahaya sebelum dijalankan

### Cara Mengaktifkan

#### 1. Via Config File

Edit `config.ini`:
```ini
[RealtimeProtection]
enabled = true
scan_delay = 5
action_on_malware = notify
show_notifications = true
```

#### 2. Via UI (Coming Soon)

Toggle switch di main window untuk enable/disable protection.

### Folder yang Di-monitor

**Windows:**
- Semua drive (C:\\, D:\\, E:\\, dll)

**macOS:**
- ~/Downloads
- ~/Desktop
- ~/Documents
- /Volumes (external drives)

**Linux:**
- ~/Downloads
- ~/Desktop
- ~/Documents
- /media (removable media)
- /mnt (mount points)

### Whitelist

File dengan ekstensi tertentu akan **di-skip** untuk performa:

```ini
whitelist_extensions = .txt,.log,.md,.json
```

Anda bisa menambahkan ekstensi lain sesuai kebutuhan.

### Cara Kerja

```
File baru dibuat
    ↓
Wait 5 detik (scan_delay)
    ↓
Check whitelist
    ↓
Scan dengan AI
    ↓
Jika Malware → Notify user
Jika Benign → Ignore
```

### Notifikasi

Ketika malware terdeteksi, Anda akan menerima:

**Windows:**
- Toast notification (pojok kanan bawah)

**macOS:**
- Notification Center alert

**Linux:**
- Desktop notification (notify-send)

**Isi Notifikasi:**
```
🚨 Malware Detected - High Threat
File: suspicious.exe
Location: C:\Users\...\Downloads\suspicious.exe

Action required!
```

### Performance

**CPU Usage:**
- Idle: < 5%
- Scanning: 10-20% (temporary)

**RAM Usage:**
- ~200-300 MB

**Tips untuk Performa:**
1. Increase `scan_delay` jika terlalu banyak file
2. Add folder ke whitelist jika tidak perlu di-scan
3. Disable untuk folder development/build

---

## 📦 Model Update

### Apa itu Model Update?

Sistem untuk **auto-download** model AI terbaru dari backend server.

### Cara Kerja

1. **Check** versi model setiap 24 jam
2. **Notify** user jika ada update
3. **Ask** user sebelum download
4. **Download** model baru (40-50 MB)
5. **Verify** SHA256 hash
6. **Backup** model lama
7. **Install** model baru
8. **Reload** scanner

### Konfigurasi

```ini
[ModelUpdate]
enabled = true
check_interval = 86400  # 24 hours
ask_before_download = true
model_api_url = http://localhost:8000
```

### Manual Update

Anda bisa trigger manual update via UI:

1. Klik "Check for Updates"
2. Lihat changelog versi baru
3. Klik "Download & Install"
4. Wait progress bar selesai
5. Model otomatis ter-reload

### Rollback

Jika model baru bermasalah:

```python
from core.model_updater import ModelUpdater

updater = ModelUpdater()
updater.rollback()  # Restore previous version
```

### Backup

Model lama akan di-backup otomatis:

```
models/
├── Modelv3.onnx          (current)
└── backups/
    ├── Modelv2.onnx.20251222_083000.bak
    └── Modelv1.onnx.20251221_120000.bak
```

Hanya 2 backup terakhir yang disimpan.

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install watchdog win10toast
```

### 2. Enable Features

Edit `config.ini`:

```ini
[RealtimeProtection]
enabled = true

[ModelUpdate]
enabled = true
```

### 3. Run Application

```bash
python main.py
```

**Console Output:**
```
✅ Sync manager started (backend: http://localhost:8000)
🛡️  Real-time protection started
📦 Model updater initialized
```

### 4. Test Real-time Protection

1. Download file test (atau create file baru)
2. Wait 5 detik
3. File akan di-scan otomatis
4. Jika malware → notification muncul

---

## ⚙️ Advanced Configuration

### Custom Monitored Paths

Jika tidak ingin monitor semua drive:

```python
from core.realtime_protection import RealtimeProtection

protection = RealtimeProtection(
    monitored_paths=[
        "C:\\Users\\YourName\\Downloads",
        "C:\\Users\\YourName\\Desktop"
    ]
)
```

### Custom Malware Action

```python
def on_malware(file_path, result):
    print(f"Malware: {file_path}")
    
    # Option 1: Delete file
    os.remove(file_path)
    
    # Option 2: Move to quarantine
    shutil.move(file_path, "quarantine/")
    
    # Option 3: Just notify (default)
    pass

protection = RealtimeProtection(
    on_malware_detected=on_malware
)
```

### Disable for Specific Folder

```python
protection.add_to_whitelist("C:\\Projects\\MyApp")
```

---

## 📊 Statistics

### Real-time Protection Stats

```python
stats = protection.get_stats()
print(stats)
```

**Output:**
```python
{
    "files_scanned": 150,
    "malware_detected": 3,
    "files_quarantined": 3,
    "uptime_seconds": 3600,
    "queue_size": 0,
    "cache_size": 145,
    "monitored_paths": 3
}
```

### Model Update Info

```python
updater = ModelUpdater()
current = updater.get_current_version()
print(current)
```

**Output:**
```python
{
    "version": "v3",
    "filename": "Modelv3.onnx",
    "installed_date": "2025-12-22T08:00:00",
    "sha256": "abc123...",
    "size": 44701612
}
```

---

## 🐛 Troubleshooting

### Real-time Protection Not Starting

**Error:** `Failed to start real-time protection`

**Solutions:**
1. Check `watchdog` installed: `pip install watchdog`
2. Check permissions (need read access to monitored folders)
3. Check config.ini syntax

### Notifications Not Showing

**Windows:**
```bash
pip install win10toast
```

**Linux:**
```bash
sudo apt install libnotify-bin
```

**macOS:**
- Should work out of the box

### Model Update Fails

**Error:** `Verification failed - file corrupted`

**Solutions:**
1. Check internet connection
2. Check backend running
3. Try manual download
4. Check disk space (need ~100MB)

### High CPU Usage

**Solutions:**
1. Increase `scan_delay` to 10-15 seconds
2. Add folders to whitelist
3. Reduce `max_queue_size`
4. Temporarily disable protection

---

## 🔒 Security Notes

### Real-time Protection
- ✅ Runs in background (daemon thread)
- ✅ No admin privileges required
- ✅ Safe to disable anytime
- ⚠️ Cannot prevent file execution (only notify)

### Model Update
- ✅ SHA256 verification
- ✅ Automatic backup
- ✅ Rollback capability
- ⚠️ Requires internet connection

---

## 📞 FAQ

**Q: Apakah real-time protection memperlambat komputer?**
A: Minimal impact. CPU usage < 5% saat idle, 10-20% saat scanning.

**Q: Bisa disable untuk folder tertentu?**
A: Ya, gunakan `add_to_whitelist()` atau tambahkan ekstensi ke config.

**Q: Berapa lama scan satu file?**
A: ~1-2 detik untuk file kecil, 5-10 detik untuk file besar.

**Q: Model update otomatis tanpa konfirmasi?**
A: Tidak, default `ask_before_download = true`. User harus approve.

**Q: Bisa rollback ke model lama?**
A: Ya, gunakan `updater.rollback()` atau restore dari backup.

**Q: Support macOS dan Linux?**
A: Ya, fully cross-platform!

---

## 🎯 Best Practices

1. **Enable real-time protection** untuk folder Downloads
2. **Whitelist** folder development untuk performa
3. **Check model updates** setiap minggu
4. **Monitor statistics** untuk track detections
5. **Backup config.ini** sebelum modifikasi

---

## 📈 Future Enhancements

- [ ] Quarantine system (encrypt malware files)
- [ ] UI controls untuk enable/disable
- [ ] Scheduled scans
- [ ] Cloud-based threat intelligence
- [ ] Automatic model updates (optional)

---

## 🎉 Summary

✅ **Real-time Protection** - Background monitoring semua drives
✅ **Cross-platform** - Windows, macOS, Linux
✅ **Smart Notifications** - Desktop alerts untuk threats
✅ **Model Updates** - Auto-download versi terbaru
✅ **SHA256 Verification** - Ensure model integrity
✅ **Automatic Backup** - Safe rollback capability

Selamat menggunakan MangoDefend! 🥭🛡️
