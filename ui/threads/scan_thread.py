"""
Scan Thread
Background worker thread for malware scanning
"""
from PySide6.QtCore import QThread, Signal
from core.scanner import MalwareScanner


class ScanThread(QThread):
    """Thread for running malware scan"""
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
                self.msleep(200)

            result = self.scanner.scan_file(self.file_path)
            self.progress.emit(100, "Selesai!")
            self.msleep(200)
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))

    def cancel(self):
        self.is_canceled = True
