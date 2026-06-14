===========================================
   MangoDefend - Malware Detection AI
===========================================

Aplikasi On :
Folder Dist 

FITUR UTAMA:
✅ Scan File/Folder untuk malware
✅ Real-time Protection (toggle ON/OFF)
✅ Model Auto-Update
✅ Scan History & Statistics
✅ Desktop Notifications
✅ Offline Mode (tidak perlu internet)

CARA MENGGUNAKAN:

1. SCAN FILE:
   - Klik "Pemindai Malware"
   - Pilih "Scan File"
   - Pilih file yang ingin di-scan
   - Tunggu hasil scan

2. REAL-TIME PROTECTION:
   - Lihat toggle di pojok kanan atas
   - Klik toggle untuk ON/OFF
   - ON (hijau) = Aktif, semua file baru di-scan otomatis
   - OFF (merah) = Tidak aktif

3. UPDATE MODEL:
   - Klik "Pembaruan"
   - Jika ada update, klik "Yes" untuk download
   - Model baru akan terinstall otomatis

SYSTEM REQUIREMENTS:
- Windows 10/11 (64-bit)
- 4GB RAM minimum
- 500MB disk space
- (Optional) Internet untuk model update

VERSION: 1.0.2
BUILD DATE: 2025-12-23

BUILD DARI SOURCE:

1. Install Python 3.11 dan Inno Setup 6.
2. Buat virtualenv lalu install dependency:
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
3. Pastikan model ada di folder models/.
4. Untuk membuat installer Windows, jalankan:
   build_installer.bat

Catatan:
- Folder build/, dist/, installer/MangoDefend/, dataset/, dan file .exe adalah hasil build/data besar,
  jadi tidak dicommit ke Git.
- File resep build yang perlu dicommit adalah MangoDefend.spec dan installer/MangoDefend_Setup.iss.
- Jika installer\vc_redist.x64.exe belum ada, download Microsoft Visual C++ Redistributable x64
  lalu taruh di folder installer/.
