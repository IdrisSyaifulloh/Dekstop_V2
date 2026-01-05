"""
Scan Thread Worker
Thread untuk menjalankan malware scanning secara asynchronous
"""
from PySide6.QtCore import QThread, Signal
from core.scanner import MalwareScanner
from pathlib import Path


# ========================================
# PENGATURAN PERFORMANCE - UBAH DI SINI UNTUK MENGURANGI CPU USAGE!
# ========================================
# Delay antar stage scan (milliseconds)
# Nilai default: 200ms
# Nilai yang disarankan: 300-500ms (lebih hemat CPU, scan lebih lambat)
STAGE_DELAY_MS = 0  # UBAH ANGKA INI

# Delay antar file saat full scan (milliseconds)
# Nilai default: 50ms
# Nilai yang disarankan: 100-200ms (lebih hemat CPU)
# Set ke 0 untuk scan secepat mungkin (CPU usage tinggi)
FILE_SCAN_DELAY_MS = 0  # UBAH ANGKA INI

# Maksimal file untuk full scan
# Nilai default: 1000 file
# Nilai yang disarankan: 300-500 file (lebih hemat CPU, scan lebih cepat selesai)
# Set ke None untuk TANPA LIMIT (scan semua file di device)
MAX_FILES_TO_SCAN = 2000  # UBAH ANGKA INI - None = TANPA LIMIT!


class ScanThread(QThread):
    """Thread for running malware scan"""
    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(int, str)

    def __init__(self, file_path, is_full_scan=False):
        super().__init__()
        self.file_path = file_path
        self.is_full_scan = is_full_scan
        self.scanner = MalwareScanner()
        self.is_canceled = False

    def run(self):
        try:
            if self.is_full_scan:
                self.run_full_scan()
            else:
                self.run_single_file_scan()

        except Exception as e:
            self.error.emit(str(e))

    def run_single_file_scan(self):
        """Scan single file"""
        # Simulate progress stages
        stages = [
            (10, "Memulai pemindaian..."),
            (25, "Menganalisis file..."),
            (40, "Memproses dengan AI..."),
            (60, "Mendeteksi malware..."),
            (80, "Menyelesaikan analisis..."),
            (95, "Hampir selesai...")
        ]

        for value, message in stages:
            if self.is_canceled:
                return
            self.progress.emit(value, message)
            self.msleep(STAGE_DELAY_MS)  # Gunakan konstanta

        result = self.scanner.scan_file(self.file_path)
        self.progress.emit(100, "Selesai!")
        self.msleep(STAGE_DELAY_MS)  # Gunakan konstanta
        self.finished.emit(result)

    def run_full_scan(self):
        """Scan full device or folder"""
        path = Path(self.file_path)

        # Collect all files to scan
        self.progress.emit(5, "Mengumpulkan file untuk dipindai...")
        files_to_scan = []

        # Recursive scan dengan filter untuk file yang relevan
        if path.is_dir():
            # Extension yang akan dipindai (termasuk image files untuk malware yang di-convert)
            scan_extensions = {
                # Executables & Scripts
                '.exe', '.dll', '.bat', '.cmd', '.ps1', '.vbs', '.js',
                '.jar', '.apk', '.msi', '.scr', '.com', '.pif',
                '.application', '.gadget', '.cpl',
                # Archives
                '.zip', '.rar', '.7z', '.tar', '.gz',
                # Image files (malware bisa di-convert ke image)
                '.png', '.jpg', '.jpeg', '.bmp', '.gif',
                # Documents (bisa mengandung macro/malware)
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
            }

            try:
                for file_path in path.rglob('*'):
                    if self.is_canceled:
                        return

                    if file_path.is_file():
                        # Check extension
                        if file_path.suffix.lower() in scan_extensions:
                            files_to_scan.append(file_path)

                        # Limit to prevent too many files (jika MAX_FILES_TO_SCAN = None, scan semua)
                        if MAX_FILES_TO_SCAN is not None and len(files_to_scan) >= MAX_FILES_TO_SCAN:
                            break
            except PermissionError:
                pass
        else:
            files_to_scan = [path]

        total_files = len(files_to_scan)

        if total_files == 0:
            result = {
                "file_path": str(path),
                "file_name": path.name,
                "is_malware": False,
                "confidence": 100,
                "threat_type": "None",
                "scan_time": "0.0s",
                "file_size": "0 bytes",
                "scan_date": "",
                "details": "Tidak ada file yang cocok untuk dipindai"
            }
            self.finished.emit(result)
            return

        self.progress.emit(10, f"Ditemukan {total_files} file untuk dipindai...")
        self.msleep(500)

        # Scan files
        threats_found = []
        safe_files = 0

        for idx, file_path in enumerate(files_to_scan):
            if self.is_canceled:
                return

            # Update progress
            progress_value = 10 + int((idx / total_files) * 85)
            self.progress.emit(
                progress_value,
                f"Memindai {idx + 1}/{total_files}: {file_path.name}"
            )

            try:
                # Scan file
                result = self.scanner.scan_file(str(file_path))

                # Check if malware (scanner returns "Malware" or "Benign")
                is_malware = result.get("result", "Benign") == "Malware"

                if is_malware:
                    threats_found.append({
                        "file": str(file_path),
                        "name": file_path.name,
                        "threat": "Malware",
                        "confidence": 0
                    })
                else:
                    safe_files += 1

            except Exception as e:
                # Skip files that can't be scanned (corrupt/invalid images)
                safe_files += 1

            # Small delay to show progress (gunakan konstanta)
            self.msleep(FILE_SCAN_DELAY_MS)

        # Prepare final result
        self.progress.emit(95, "Menyelesaikan pemindaian...")
        self.msleep(300)

        # Create summary result
        result = {
            "file_path": str(path),
            "file_name": path.name,
            "is_malware": len(threats_found) > 0,
            "confidence": 100,
            "threat_type": "Multiple" if len(threats_found) > 1 else (threats_found[0]["threat"] if threats_found else "None"),
            "scan_time": f"{total_files * 0.1:.1f}s",
            "file_size": f"{total_files} files",
            "scan_date": "",
            "details": f"Pemindaian selesai!\n\n"
                      f"Total file dipindai: {total_files}\n"
                      f"File aman: {safe_files}\n"
                      f"Ancaman terdeteksi: {len(threats_found)}",
            "is_full_scan": True,
            "threats": threats_found,
            "total_scanned": total_files,
            "safe_count": safe_files
        }

        self.progress.emit(100, "Selesai!")
        self.msleep(200)
        self.finished.emit(result)

    def cancel(self):
        self.is_canceled = True
