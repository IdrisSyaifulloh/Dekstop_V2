"""
Scan Thread
Background worker thread for malware scanning (single file and batch)
"""
import os
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from core.scanner import MalwareScanner


class ScanThread(QThread):
    """Thread for running malware scan on a single file."""
    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(int, str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.scanner = MalwareScanner()
        self.is_canceled = False

    def run(self):
        try:
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
                self.msleep(200)

            result = self.scanner.scan_file(self.file_path)
            self.progress.emit(100, "Selesai!")
            self.msleep(200)
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))

    def cancel(self):
        self.is_canceled = True


class BatchScanThread(QThread):
    """Thread for scanning multiple files (folder or device scan)."""
    file_scanned = Signal(dict)   # result for each file
    batch_finished = Signal(dict)  # summary
    error = Signal(str)
    progress = Signal(int, str)   # percentage, message

    # Extensions to scan in batch mode (dangerous types)
    SCAN_EXTENSIONS = {
        ".exe", ".dll", ".scr", ".bat", ".cmd",
        ".ps1", ".vbs", ".js", ".jar", ".msi",
        ".com", ".pif", ".wsf", ".hta", ".cpl",
        ".sys", ".drv", ".bin", ".dat",
    }

    def __init__(self, folder_path: str = None, full_device: bool = False):
        super().__init__()
        self.folder_path = folder_path
        self.full_device = full_device
        self.scanner = MalwareScanner()
        self.is_canceled = False

    def run(self):
        try:
            self.scanner.load_model(aggressive=True)

            # Collect files to scan
            self.progress.emit(0, "Mengumpulkan file...")
            files = self._collect_files()

            if not files:
                self.progress.emit(100, "Tidak ada file yang perlu discan")
                self.batch_finished.emit({
                    "total": 0, "scanned": 0,
                    "malware": 0, "clean": 0, "errors": 0,
                    "results": []
                })
                return

            total = len(files)
            scanned = 0
            malware_count = 0
            clean_count = 0
            error_count = 0
            results = []

            for i, file_path in enumerate(files):
                if self.is_canceled:
                    break

                # Progress
                pct = int((i / total) * 100)
                fname = Path(file_path).name
                self.progress.emit(pct, f"Memindai ({i+1}/{total}): {fname}")

                try:
                    result = self.scanner.scan_file(file_path, is_full_scan=True)
                    if result is None:
                        continue  # skipped by scanner

                    scanned += 1
                    result_type = result.get("result", "Unknown")

                    if result_type == "Malware":
                        malware_count += 1
                        results.append(result)
                        self.file_scanned.emit(result)
                    else:
                        clean_count += 1

                except Exception:
                    error_count += 1

            self.progress.emit(100, f"Selesai! {scanned} file discan")

            summary = {
                "total": total,
                "scanned": scanned,
                "malware": malware_count,
                "clean": clean_count,
                "errors": error_count,
                "results": results,
            }
            self.batch_finished.emit(summary)

        except Exception as e:
            self.error.emit(str(e))

    def _collect_files(self) -> list:
        """Collect files to scan."""
        files = []

        if self.full_device:
            # Scan common user directories
            home = Path.home()
            scan_dirs = [
                home / "Downloads",
                home / "Desktop",
                home / "Documents",
                Path("C:/Program Files"),
                Path("C:/Program Files (x86)"),
            ]
            # Also check all drive roots for suspicious files
            import string
            for letter in string.ascii_uppercase:
                drive = Path(f"{letter}:/")
                if drive.exists() and drive != Path("C:/"):
                    scan_dirs.append(drive)
        else:
            scan_dirs = [Path(self.folder_path)] if self.folder_path else []

        for scan_dir in scan_dirs:
            if self.is_canceled:
                break
            if not scan_dir.exists():
                continue
            try:
                for root, dirs, filenames in os.walk(scan_dir):
                    if self.is_canceled:
                        break
                    # Skip system/hidden directories
                    dirs[:] = [d for d in dirs if not d.startswith('.')
                               and d not in ('$Recycle.Bin', 'System Volume Information',
                                             'Windows', 'node_modules', '.git',
                                             '__pycache__', 'venv', '.venv')]
                    for fname in filenames:
                        if self.is_canceled:
                            break
                        fpath = os.path.join(root, fname)
                        ext = Path(fname).suffix.lower()
                        if ext in self.SCAN_EXTENSIONS:
                            try:
                                size = os.path.getsize(fpath)
                                if size > 0 and size < 10 * 1024 * 1024:  # 10MB max
                                    files.append(fpath)
                            except (OSError, PermissionError):
                                pass
            except (OSError, PermissionError):
                pass

        return files

    def cancel(self):
        self.is_canceled = True