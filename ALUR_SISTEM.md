# Dokumentasi Teknis: Alur Sistem MangoDefend

**Aplikasi:** MangoDefend — Desktop Antimalware
**Bahasa:** Python 3.11
**GUI:** PySide6 (Qt)
**Model AI:** ResNet-18 → ONNX Runtime
**Platform:** Windows 10/11

---

## DAFTAR ISI

1. [Gambaran Umum Sistem](#1-gambaran-umum-sistem)
2. [Proses 1 — Konversi File Biner ke Citra (Binary Visualization)](#2-proses-1--konversi-file-biner-ke-citra-binary-visualization)
3. [Proses 2 — Inferensi Model ONNX](#3-proses-2--inferensi-model-onnx)
4. [Proses 3 — Pemindaian Manual (Scan File/Folder)](#4-proses-3--pemindaian-manual-scan-filefolder)
5. [Proses 4 — Windows File Locking](#5-proses-4--windows-file-locking)
6. [Proses 5 — Real-Time Protection: Watchdog](#6-proses-5--real-time-protection-watchdog)
7. [Proses 6 — Real-Time Protection: Process Monitor](#7-proses-6--real-time-protection-process-monitor)
8. [Proses 7 — Karantina File Malware](#8-proses-7--karantina-file-malware)
9. [Proses 8 — Dialog Alert ke Pengguna](#9-proses-8--dialog-alert-ke-pengguna)
10. [Alur Lengkap End-to-End](#10-alur-lengkap-end-to-end)

---

## 1. Gambaran Umum Sistem

MangoDefend bekerja dengan **dua jalur perlindungan** yang berjalan paralel:

```
┌─────────────────────────────────────────────────────────┐
│                    MANGODEFEND                          │
│                                                         │
│   JALUR A: Watchdog                JALUR B: Process     │
│   ─────────────────                Monitor              │
│   Pantau folder baru        ──     Pantau PID baru      │
│   Download/Desktop/Temp            setiap 5ms           │
│          │                                │             │
│          ▼                                ▼             │
│   File Baru Terdeteksi         Proses Baru Terdeteksi   │
│          │                                │             │
│          ▼                                ▼             │
│   LOCK FILE (CreateFileW)      SUSPEND PROSES (psutil)  │
│          │                                │             │
│          └──────────────┬─────────────────┘             │
│                         ▼                               │
│              BINARY VISUALIZATION                       │
│              (File → Citra Grayscale)                   │
│                         │                               │
│                         ▼                               │
│              ONNX RUNTIME INFERENSI                     │
│              (ResNet-18: Benign/Malware)                 │
│                         │                               │
│              ┌──────────┴──────────┐                    │
│              ▼                     ▼                    │
│           BENIGN               MALWARE                  │
│           Unlock/Resume        Alert Dialog             │
│                                │                        │
│                         ┌──────┴───────┐                │
│                         ▼              ▼                │
│                      KARANTINA      IZINKAN             │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Proses 1 — Konversi File Biner ke Citra (Binary Visualization)

### Konsep

Setiap file (`.exe`, `.dll`, `.pdf`, dll.) dibaca sebagai **byte mentah**, lalu diubah menjadi **matriks 2D grayscale** yang dapat diproses oleh model CNN (ResNet-18).

### Algoritma

Menggunakan metode **UCSB (Nataraj et al.)** — lebar gambar ditentukan berdasarkan ukuran file:

| Ukuran File | Lebar Citra |
|-------------|-------------|
| < 10 KB | 32 px |
| < 100 KB | 256 px |
| < 500 KB | 512 px |
| < 1 MB | 768 px |
| < 10 MB | 1024 px |
| >= 10 MB | 2048+ px |

### Kode — `utils/file_converter.py`

```python
@staticmethod
def calculate_width(file_size_kb: float) -> int:
    """Tentukan lebar citra berdasarkan ukuran file (metode UCSB)"""
    if file_size_kb < 10:   return 32
    elif file_size_kb < 100: return 256
    elif file_size_kb < 500: return 512
    elif file_size_kb < 1000: return 768
    elif file_size_kb < 10000: return 1024
    else: return 2048

@staticmethod
def binary_to_matrix(byte_data: bytes, width: int) -> np.ndarray:
    """Ubah byte array menjadi matriks 2D"""
    byte_array = np.frombuffer(byte_data, dtype=np.uint8)
    height = math.ceil(len(byte_array) / width)
    # Padding agar dimensi pas
    padded = np.pad(byte_array, (0, width * height - len(byte_array)), "constant")
    return padded.reshape((height, width))

def convert_file_to_image(self, file_path: str) -> dict:
    """Pipeline utama konversi: file → gambar grayscale PNG"""
    with open(file_path, "rb") as f:
        binary_data = f.read()

    file_size_kb = len(binary_data) / 1024
    width = self.calculate_width(file_size_kb)       # Tentukan lebar
    matrix = self.binary_to_matrix(binary_data, width)  # Byte → 2D

    # Simpan sebagai citra grayscale ke folder temp
    img = Image.fromarray(matrix.astype(np.uint8), mode="L")
    img.save(output_path)

    return {"output_image": str(output_path), "width": width}
```

### Alur Visual

```
namafile.exe (12 KB)
    │
    ▼
Baca sebagai byte: [4D 5A 90 00 03 00 00 00 ...]
    │
    ▼
calculate_width(12) → lebar = 256 px
    │
    ▼
Reshape → matriks (H × 256), setiap byte = 1 piksel (0–255)
    │
    ▼
Simpan sebagai PNG grayscale ke %TEMP%\mangodefend_temp\
    │
    ▼
output: namafile_gray_20260304153045.png
```

---

## 3. Proses 2 — Inferensi Model ONNX

### Konsep

Citra grayscale hasil konversi dimasukkan ke model **ResNet-18** yang sudah dikonversi ke format ONNX. Output adalah probabilitas dua kelas: `Benign` atau `Malware`.

### Kode — `core/scanner.py`

**A. Load Model ONNX (saat pertama scan)**

```python
def load_model(self, aggressive: bool = False):
    sess_options = ort.SessionOptions()

    if aggressive:
        # Mode full scan: threading lebih tinggi
        sess_options.intra_op_num_threads = min(4, cpu_count)
        sess_options.execution_mode = ort.ExecutionMode.ORT_PARALLEL
    else:
        # Mode realtime: hemat CPU
        sess_options.intra_op_num_threads = min(2, cpu_count)
        sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

    self.session = ort.InferenceSession(
        self.model_path,          # models/Modelv3.onnx
        providers=["CPUExecutionProvider"],
        sess_options=sess_options
    )
```

**B. Preprocessing dan Inferensi**

```python
def _predict(self, image: Image.Image):
    # 1. Resize ke 224×224 (ukuran input ResNet-18)
    image = image.resize((224, 224))

    # 2. Normalisasi pixel 0–255 → 0.0–1.0
    img = np.array(image).astype(np.float32) / 255.0

    # 3. Grayscale → 3 channel (duplikat) agar kompatibel ResNet
    img = np.stack([img] * 3, axis=0)       # shape: (3, 224, 224)
    img = np.expand_dims(img, axis=0)        # shape: (1, 3, 224, 224)

    # 4. Jalankan inferensi ONNX
    input_name = self.session.get_inputs()[0].name
    output_name = self.session.get_outputs()[0].name
    result = self.session.run([output_name], {input_name: img})

    # 5. Ambil prediksi
    output = result[0][0]                    # [score_benign, score_malware]
    predicted = int(np.argmax(output))       # 0=Benign, 1=Malware
    return output.tolist(), predicted
```

**C. Pipeline Lengkap scan_file()**

```python
def scan_file(self, file_path: str) -> dict:
    # 1. Cek apakah file gambar langsung atau perlu konversi
    if Path(file_path).suffix.lower() in [".png", ".jpg", ".jpeg"]:
        image_path = file_path
    else:
        conversion = self.converter.convert_file_to_image(file_path)
        image_path = conversion["output_image"]

    # 2. Buka citra dan prediksi
    image = Image.open(image_path).convert("L")
    output, predicted = self._predict(image)

    # 3. Hapus file temp setelah scan
    os.remove(image_path)

    # 4. Kembalikan hasil
    return {
        "result": CLASS_NAMES[predicted],    # "Benign" atau "Malware"
        "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "model": {"predicted_output": output},
        "file": {
            "file_name": Path(file_path).name,
            "file_size": os.path.getsize(file_path),
            "file_hash": self._hash_file(file_path),  # SHA-256
        },
    }
```

### Alur Visual

```
citra.png (224×224 grayscale)
    │
    ▼
Normalisasi: pixel / 255.0
    │
    ▼
Stack 3 channel: shape (1, 3, 224, 224)
    │
    ▼
ONNX Session.run() → [0.02, 0.98]
                       Benign  Malware
    │
    ▼
argmax → 1 → "Malware" (confidence 98%)
```

---

## 4. Proses 3 — Pemindaian Manual (Scan File/Folder)

### Konsep

User memilih file atau folder dari UI, kemudian scan dijalankan di **thread terpisah** agar UI tidak freeze.

### Kode — `core/scan_thread.py` → `ui/components/scan_view.py`

```python
# Di scan_view.py — memulai scan di background thread
def _start_scan(self, path: str):
    self.scan_thread = ScanThread(path)
    self.scan_thread.progress_updated.connect(self._on_progress)
    self.scan_thread.scan_complete.connect(self._on_scan_complete)
    self.scan_thread.start()

# Di scan_thread.py — logika scan berjalan di thread ini
class ScanThread(QThread):
    def run(self):
        scanner = MalwareScanner()
        for file_path in self.files_to_scan:
            result = scanner.scan_file(file_path)
            self.progress_updated.emit(file_path, result)
```

### Alur

```
User klik "Scan File" di UI
    │
    ▼
Pilih file via QFileDialog
    │
    ▼
ScanThread.start() → berjalan di background
    │
    ├── FileConverter.convert_file_to_image()
    ├── MalwareScanner._predict()
    └── Emit signal → update UI (progress bar, hasil)
    │
    ▼
Hasil muncul di UI:
    ✅ Benign — file aman
    🚨 Malware — tampilkan alert
    │
    ▼
Tersimpan ke riwayat (QListWidget) + SQLite
```

---

## 5. Proses 4 — Windows File Locking

### Konsep

Ketika file baru terdeteksi, MangoDefend **langsung mengunci file** menggunakan Windows API `CreateFileW` dengan mode `FILE_SHARE_NONE`. Ini mencegah **semua proses lain** (termasuk user) membuka file tersebut selama scan berlangsung.

### Kode — `core/realtime_protection.py`

```python
# Konfigurasi Windows API
kernel32 = ctypes.windll.kernel32
GENERIC_READ   = 0x80000000
OPEN_EXISTING  = 3
FILE_SHARE_NONE = 0x00000000   # Kunci eksklusif — tidak boleh dibagikan

class FileLock:
    def acquire(self, max_retries=5, retry_delay=0.3) -> bool:
        for attempt in range(max_retries):
            handle = kernel32.CreateFileW(
                self.file_path,
                GENERIC_READ,
                FILE_SHARE_NONE,   # <-- KUNCI EKSKLUSIF
                None,
                OPEN_EXISTING,
                FILE_ATTRIBUTE_NORMAL,
                None
            )
            if handle != INVALID_HANDLE_VALUE:
                self._handle = handle
                self._locked = True
                return True  # Berhasil dikunci

            # Jika error 32 = file sedang dipakai, coba lagi
            if kernel32.GetLastError() == 32:
                time.sleep(retry_delay)
                continue
        return False

    def release(self):
        """Lepas kunci — file bisa diakses normal kembali"""
        kernel32.CloseHandle(self._handle)
        self._locked = False
```

### Alur

```
File baru muncul di folder monitor
    │
    ▼
FileLock.acquire()
    ├── CreateFileW(FILE_SHARE_NONE)
    └── Handle disimpan di _active_locks[file_path]
    │
    ▼
File TERKUNCI — tidak bisa dibuka/dieksekusi siapapun
    │
    ▼
Scan selesai:
    ├── Benign  → FileLock.release() → file bisa diakses
    └── Malware → _quarantine_file() → FileLock.release()
```

---

## 6. Proses 5 — Real-Time Protection: Watchdog

### Konsep

Library `watchdog` memantau sistem file secara *event-driven*. Begitu ada file baru muncul di folder yang dipantau, sistem langsung menguncinya dan memasukkan ke antrian scan.

### Folder yang Dipantau

```python
def _get_default_paths(self) -> List[str]:
    home = Path.home()
    return [
        str(home / "Downloads"),   # C:\Users\saefu\Downloads
        str(home / "Desktop"),     # C:\Users\saefu\Desktop
        str(home / "Documents"),   # C:\Users\saefu\Documents
        os.environ.get("TEMP"),    # C:\Users\saefu\AppData\Local\Temp
    ]
```

### Kode — `core/realtime_protection.py`

```python
def _on_new_file(self, file_path: str):
    """Dipanggil watchdog saat file baru terdeteksi"""
    if file_path in self.scan_cache:
        return  # Sudah pernah discan, lewati

    # LANGSUNG kunci file sebelum siapapun bisa buka
    lock = FileLock(file_path)
    got_lock = lock.acquire(max_retries=5, retry_delay=0.1)

    if got_lock:
        self._active_locks[file_path] = lock
        self.stats["files_blocked"] += 1
        logger.info(f"🔒 LOCKED: {file_path}")

    # Masukkan ke antrian scan
    self._scan_queue.put(file_path)
```

```python
def _scan_worker(self):
    """Thread worker yang memproses antrian scan"""
    while self.running:
        file_path = self._scan_queue.get(timeout=1)

        # Pastikan file terkunci sebelum scan
        locked = self._ensure_locked(file_path)

        # Scan dengan ONNX
        scan_result = self.scanner.scan_file(file_path)

        if scan_result.get('result') == 'Malware':
            # Tampilkan alert ke user (file masih terkunci)
            action = self._ask_user_decision(file_path, scan_result)
            self._release_lock(file_path)
            if action == 1:   # Pengguna pilih karantina
                self._quarantine_file(file_path)
        else:
            # Bersih → lepas kunci
            self._release_lock(file_path)
            self.scan_cache.add(file_path)
```

### Alur

```
watchdog.Observer() memantau folder Downloads, Desktop, Temp
    │
    ▼ (event: file baru)
_on_new_file("C:\Users\saefu\Downloads\setup.exe")
    │
    ▼
FileLock.acquire() → file terkunci
    │
    ▼
_scan_queue.put(file_path)
    │
    ▼ (scan_worker thread)
scanner.scan_file() → Benign / Malware
    │
    ├── Benign  → release lock → "✅ Clean"
    └── Malware → alert dialog → karantina / izinkan
```

---

## 7. Proses 6 — Real-Time Protection: Process Monitor

### Konsep

Selain memantau file baru, MangoDefend juga memantau **proses baru yang dijalankan**. Begitu PID baru terdeteksi, proses tersebut langsung di-*suspend* (dibekukan) sebelum sempat mengeksekusi atau me-*render* file apapun.

### Kode — `core/realtime_protection.py`

```python
def _process_monitor_worker(self):
    """Polling PID setiap 5ms untuk deteksi proses baru"""
    import psutil

    while self.running:
        current_pids = set(psutil.pids())
        new_pids = current_pids - self._known_pids
        self._known_pids = current_pids

        for pid in new_pids:
            try:
                proc = psutil.Process(pid)

                # ── LANGSUNG SUSPEND sebelum apapun ──
                pre_suspended = False
                try:
                    exe_path = proc.exe()
                    if exe_path and not self._is_system_process(exe_path):
                        proc.suspend()         # Bekukan proses!
                        pre_suspended = True
                        logger.debug(f"⏸️ Pre-suspended: {proc.name()} (PID={pid})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

                # Cek apakah proses membuka file berbahaya via args
                cmdline = proc.cmdline()
                if len(cmdline) > 1:
                    for arg in cmdline[1:]:
                        clean_arg = os.path.normpath(arg.strip())
                        if os.path.isfile(clean_arg):
                            arg_ext = Path(clean_arg).suffix.lower()
                            if arg_ext in DANGEROUS_EXTENSIONS:
                                # Scan file yang dibuka (proses sudah frozen)
                                self._scan_opened_file(
                                    proc, pid, clean_arg,
                                    already_suspended=pre_suspended
                                )
                                pre_suspended = False
                                break

                # Jika tidak ada file berbahaya → resume proses
                if pre_suspended:
                    proc.resume()

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        time.sleep(0.005)  # Poll setiap 5ms
```

### Kenapa Harus Suspend Dulu?

```
TANPA suspend:
  PID baru terdeteksi → cek exe → cek cmdline → scan → (terlambat!)
  Photos.exe sudah sempat render gambar malware sebelum scan selesai ❌

DENGAN suspend:
  PID baru terdeteksi → SUSPEND → cek exe → cek cmdline → scan
  Photos.exe BEKU selama scan → tidak bisa render apapun ✅
```

### Alur

```
psutil.pids() dipoll setiap 5ms
    │
    ▼ (PID baru ditemukan)
psutil.Process(pid).suspend()  ← LANGSUNG BEKUKAN
    │
    ▼
Baca proc.exe() dan proc.cmdline()
    │
    ├── File berbahaya di args?
    │       ├── Ya → scanner.scan_file() → hasil
    │       │         ├── Benign → proc.resume()
    │       │         └── Malware → alert → proc.kill() + karantina
    │       └── Tidak → proc.resume()
    │
    └── Exe berbahaya?
            ├── Ya → scanner.scan_file(exe) → hasil
            └── Tidak → proc.resume()
```

---

## 8. Proses 7 — Karantina File Malware

### Konsep

File yang dikonfirmasi malware dipindahkan ke folder khusus karantina dengan nama yang diubah agar tidak bisa dieksekusi secara tidak sengaja.

### Lokasi Karantina

```
C:\Users\saefu\.mangodefend\quarantine\
```

### Kode — `core/realtime_protection.py`

```python
def _quarantine_file(self, file_path: str):
    """Pindahkan file malware ke folder karantina"""
    src = Path(file_path)

    # Buat nama unik dengan timestamp
    timestamp = int(time.time())
    quarantine_name = f"{timestamp}_{src.name}.quarantined"
    # Contoh: 1741096245_virus.exe.quarantined

    dest = self.quarantine_dir / quarantine_name
    shutil.move(str(src), str(dest))   # Pindahkan (bukan copy)

    self.stats["files_quarantined"] += 1
    logger.info(f"🗑️ Quarantined: {src.name} → {dest}")
```

### Alur

```
Hasil scan = "Malware"
    │
    ▼
Alert dialog muncul (proses/file masih terkunci/frozen)
    │
    ├── User klik "Karantina"
    │       │
    │       ▼
    │   shutil.move(file → ~/.mangodefend/quarantine/timestamp_nama.quarantined)
    │   proc.kill() (jika dari process monitor)
    │   stats["files_quarantined"] += 1
    │
    └── User klik "Izinkan"
            │
            ▼
        scan_cache.add(file_path)  ← tidak akan discan lagi
        proc.resume() / lock.release()
```

---

## 9. Proses 8 — Dialog Alert ke Pengguna

### Konsep

Saat malware terdeteksi, thread proteksi **tidak boleh langsung kill** — harus menunggu keputusan pengguna. Dialog ditampilkan di UI thread (main thread), sementara thread proteksi menunggu menggunakan `threading.Event`.

### Kode — `core/realtime_protection.py`

```python
def _ask_user_decision(self, file_path: str, scan_result: dict) -> int:
    """
    Tampilkan alert ke user, tunggu respon.
    Return: 0 = Izinkan, 1 = Karantina
    """
    response_event = threading.Event()
    response_holder = []

    alert_data = {
        "file_path": file_path,
        "scan_result": scan_result,
        "response_event": response_event,
        "response_holder": response_holder,
    }

    # Kirim sinyal ke UI thread (thread-safe)
    self.malware_bridge.malware_detected.emit(alert_data)

    # Tunggu user klik tombol (tapi tetap cek shutdown setiap 0.3 detik)
    while not response_event.wait(timeout=0.3):
        if self._shutdown_event.is_set():
            return 0  # App ditutup → izinkan (jangan kill paksa)

    return response_holder[0] if response_holder else 0
```

### Alur

```
Malware terdeteksi (di background thread)
    │
    ▼
malware_bridge.malware_detected.emit(alert_data)
    │                              ↑ sinyal Qt (thread-safe)
    ▼ (di main/UI thread)
MalwareAlertDialog.show()
    │
    ▼
Pengguna membaca info:
    - Nama file
    - Confidence score
    - PID proses yang membuka
    │
    ├── Klik "Karantina" → response_holder[0] = 1
    └── Klik "Izinkan"   → response_holder[0] = 0
    │
    ▼
response_event.set()  ← membuka blokade thread proteksi
    │
    ▼
Thread proteksi lanjut eksekusi sesuai keputusan user
```

---

## 10. Alur Lengkap End-to-End

### Skenario: User double-click file `.exe` yang ternyata malware

```
1. User double-click "installer.exe" di Desktop
       │
       ▼
2. Windows kirim event buka file ke Shell
       │
       ▼
3. [JALUR B] Process Monitor deteksi PID baru (explorer.exe → installer.exe)
       │
       ▼
4. proc.suspend()  ← installer.exe BEKU seketika
       │
       ▼
5. Baca cmdline: ["installer.exe"] → file path = "C:\Users\saefu\Desktop\installer.exe"
       │
       ▼
6. FileConverter.convert_file_to_image("installer.exe")
       │  ├── Baca bytes: [4D 5A 90 00 ...]
       │  ├── calculate_width(ukuran) → 512 px
       │  ├── Reshape → matriks 2D
       │  └── Simpan PNG ke %TEMP%\mangodefend_temp\
       │
       ▼
7. MalwareScanner._predict(image)
       │  ├── Resize 224×224
       │  ├── Normalisasi → (1, 3, 224, 224)
       │  └── ONNX session.run() → [0.01, 0.99]
       │
       ▼
8. Hasil: "Malware" (confidence 99%)
       │
       ▼
9. _ask_user_decision() → emit sinyal ke UI thread
       │
       ▼
10. Alert Dialog muncul (installer.exe masih BEKU)
        │
        ├── User klik "Karantina"
        │       │
        │       ▼
        │  11a. proc.kill()
        │  12a. shutil.move("installer.exe" → "~/.mangodefend/quarantine/1741096245_installer.exe.quarantined")
        │  13a. Notifikasi Windows: "Malware dikarantina: installer.exe"
        │
        └── User klik "Izinkan"
                │
                ▼
           11b. proc.resume()
           12b. scan_cache.add(file_path)  ← tidak discan lagi
```

---

### Skenario: File `.exe` baru didownload dari browser

```
1. Browser download "setup.exe" ke folder Downloads
       │
       ▼
2. [JALUR A] Watchdog FileCreatedEvent → _on_new_file("setup.exe")
       │
       ▼
3. FileLock.acquire() → CreateFileW(FILE_SHARE_NONE)
       File TERKUNCI — browser pun tidak bisa selesaikan write
       (retry hingga 5x setiap 0.3 detik menunggu download selesai)
       │
       ▼
4. _scan_queue.put("setup.exe")
       │
       ▼
5. scan_worker thread mengambil dari queue
       │
       ▼
6. convert_file_to_image() → _predict() → hasil
       │
       ▼
7. Benign:
       └── _release_lock() → CreateFileW handle ditutup
           File bisa diakses/dieksekusi normal
           scan_cache.add(file_path)

   Malware:
       └── Alert dialog (file masih terkunci!)
           → Karantina: release lock → shutil.move ke quarantine/
           → Izinkan: release lock → scan_cache.add()
```

---

## Ringkasan Komponen

| Komponen | File | Fungsi |
|----------|------|--------|
| `FileConverter` | `utils/file_converter.py` | Konversi biner → citra grayscale (UCSB method) |
| `MalwareScanner` | `core/scanner.py` | Load ONNX, inferensi, hash file |
| `FileLock` | `core/realtime_protection.py` | Windows API CreateFileW eksklusif |
| `RealtimeProtection` | `core/realtime_protection.py` | Watchdog + process monitor + karantina |
| `ScanThread` | `core/scan_thread.py` | Scan manual di background thread |
| `MalwareAlertDialog` | `ui/dialogs/malware_alert.py` | Dialog konfirmasi ke user |
| `ScanView` | `ui/components/scan_view.py` | UI scan manual + drag & drop |
| `ProtectionView` | `ui/components/protection_view.py` | Toggle proteksi + statistik live |
| `ModelUpdater` | `core/model_updater.py` | Cek & download versi model terbaru |
| `LocalQueue` | `core/local_queue.py` | Simpan riwayat scan ke SQLite |

---

*Dokumen ini menjelaskan alur teknis lengkap aplikasi MangoDefend berdasarkan analisis kode sumber.*
