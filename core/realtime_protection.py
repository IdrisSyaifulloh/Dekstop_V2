"""
Real-time Protection - File system monitoring and malware detection
Cross-platform support (Windows, Linux, macOS)
"""
import os
import time
import threading
import logging
from pathlib import Path
from typing import Set, Callable, Optional, List
from queue import Queue, Empty
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from .scanner import MalwareScanner
from .local_queue import LocalQueue

logger = logging.getLogger(__name__)


class MalwareDetectionHandler(FileSystemEventHandler):
    """File system event handler for malware detection."""
    
    def __init__(self, protection_service):
        super().__init__()
        self.protection = protection_service
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            self.protection.queue_scan(event.src_path, priority=1)
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory:
            # Lower priority for modifications
            self.protection.queue_scan(event.src_path, priority=2)


class RealtimeProtection:
    """Real-time file system protection service."""
    
    def __init__(
        self,
        monitored_paths: Optional[List[str]] = None,
        scan_delay: int = 15,  # UBAH ANGKA INI (5-30) - Delay lebih lama = CPU lebih rendah
        max_queue_size: int = 10000000000,  # Perbesar dari 100 ke 1000 untuk menghindari queue full
        on_malware_detected: Optional[Callable] = None
    ):
        """
        Initialize real-time protection.
        
        Args:
            monitored_paths: List of paths to monitor (None = all drives)
            scan_delay: Delay in seconds before scanning new file
                       - 5 detik = scan cepat, CPU usage tinggi
                       - 15 detik = balanced (REKOMENDASI)
                       - 30 detik = scan lambat, CPU usage rendah
            max_queue_size: Maximum scan queue size (default: 1000)
            on_malware_detected: Callback(file_path, scan_result)
        """
        self.monitored_paths = monitored_paths or self._get_all_drives()
        self.scan_delay = scan_delay
        # Queue size yang realistis (10 miliar terlalu besar, akan crash)
        # 10000 = cukup besar untuk menampung banyak file
        self.max_queue_size = min(max_queue_size, 10000)  # Maksimal 10000
        self.on_malware_detected = on_malware_detected
        
        # Components
        self.scanner = MalwareScanner()
        self.local_queue = LocalQueue()
        self.observer = Observer()
        
        # Scan queue with priority
        self.scan_queue = Queue(maxsize=self.max_queue_size)
        
        # ========================================
        # WHITELIST - KOSONGKAN UNTUK SCAN SEMUA FILE!
        # ========================================
        # Whitelist (files to skip) - KOSONG = SCAN SEMUA
        self.whitelist: Set[str] = set()
        
        # Whitelist extensions - KOSONG = SCAN SEMUA EKSTENSI
        self.whitelist_extensions: Set[str] = set()  # Kosong!
        
        # Whitelist folder paths - KOSONG = SCAN SEMUA FOLDER
        self.whitelist_folders: Set[str] = set()  # Kosong!
        
        # Recently scanned cache (to avoid re-scanning)
        self.scan_cache: Set[str] = set()
        self.cache_ttl = 300  # 5 minutes
        
        # State
        self.running = False
        self._scan_thread: Optional[threading.Thread] = None
        self._cleanup_thread: Optional[threading.Thread] = None
        
        # Statistics
        self.stats = {
            "files_scanned": 0,
            "malware_detected": 0,
            "files_quarantined": 0,
            "start_time": None
        }
        
        logger.info(f"RealtimeProtection initialized for {len(self.monitored_paths)} paths")
    
    def _get_all_drives(self) -> List[str]:
        """
        Get all available drives (cross-platform).
        
        Returns:
            List of drive/mount paths
        """
        import platform
        
        drives = []
        system = platform.system()
        
        if system == "Windows":
            # Windows: Get all drive letters
            import string
            from ctypes import windll
            
            bitmask = windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drive = f"{letter}:\\"
                    if os.path.exists(drive):
                        drives.append(drive)
                bitmask >>= 1
        
        elif system == "Darwin":  # macOS
            # macOS: Monitor common user directories
            home = Path.home()
            drives = [
                str(home / "Downloads"),
                str(home / "Desktop"),
                str(home / "Documents"),
                "/Volumes"  # External drives
            ]
        
        else:  # Linux
            # Linux: Monitor home and common mount points
            home = Path.home()
            drives = [
                str(home / "Downloads"),
                str(home / "Desktop"),
                str(home / "Documents"),
                "/media",  # Removable media
                "/mnt"     # Mount points
            ]
        
        # Filter only existing paths
        drives = [d for d in drives if os.path.exists(d)]
        
        logger.info(f"Detected {len(drives)} drives/paths to monitor")
        return drives
    
    def add_to_whitelist(self, path: str):
        """Add file/folder to whitelist."""
        self.whitelist.add(os.path.abspath(path))
        logger.info(f"Added to whitelist: {path}")
    
    def remove_from_whitelist(self, path: str):
        """Remove file/folder from whitelist."""
        abs_path = os.path.abspath(path)
        if abs_path in self.whitelist:
            self.whitelist.remove(abs_path)
            logger.info(f"Removed from whitelist: {path}")
    
    def is_whitelisted(self, file_path: str) -> bool:
        """
        Check if file should be skipped.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file is whitelisted
        """
        abs_path = os.path.abspath(file_path)
        
        # Check exact path
        if abs_path in self.whitelist:
            return True
        
        # Check parent directories
        for whitelist_path in self.whitelist:
            if abs_path.startswith(whitelist_path):
                return True
        
        # Check extension (jika whitelist_extensions kosong, tidak ada yang di-skip)
        if self.whitelist_extensions:
            ext = Path(file_path).suffix.lower()
            if ext in self.whitelist_extensions:
                return True
        
        return False
    
    def queue_scan(self, file_path: str, priority: int = 1):
        """
        Add file to scan queue.
        
        Args:
            file_path: Path to file
            priority: Priority (1=high, 2=normal, 3=low)
        """
        # Skip if whitelisted (jika whitelist kosong, tidak ada yang di-skip)
        if self.is_whitelisted(file_path):
            logger.debug(f"Skipping whitelisted file: {file_path}")
            return
        
        # Skip if recently scanned
        if file_path in self.scan_cache:
            logger.debug(f"Skipping cached file: {file_path}")
            return
        
        # Check if file exists
        try:
            if not os.path.exists(file_path):
                return
            
            # TIDAK ADA BATASAN UKURAN - SCAN SEMUA FILE!
            # (Komentar: file besar akan lambat di-scan tapi tetap di-scan)
            
        except (OSError, PermissionError, FileNotFoundError) as e:
            # Skip files that cause OS errors (permission denied, path too long, etc)
            # Ini tidak bisa dihindari - Windows tidak izinkan akses file tertentu
            logger.debug(f"Skipping file due to OS error: {file_path} - {e}")
            return
        except Exception as e:
            logger.debug(f"Skipping file due to error: {file_path} - {e}")
            return
        
        # Add to queue
        try:
            self.scan_queue.put((priority, time.time(), file_path), block=False)
            logger.debug(f"Queued for scan: {file_path}")
        except:
            # Queue full - just skip this file
            # Tidak bisa dihindari jika terlalu banyak file sekaligus
            pass  # Don't log warning to avoid spam
    
    def _scan_worker(self):
        """Background worker for scanning queued files."""
        logger.info("Scan worker started")
        
        while self.running:
            try:
                # Get next file from queue (with timeout)
                try:
                    priority, queued_time, file_path = self.scan_queue.get(timeout=1)
                except Empty:
                    continue
                
                # Apply scan delay
                elapsed = time.time() - queued_time
                if elapsed < self.scan_delay:
                    time.sleep(self.scan_delay - elapsed)
                
                # Check if file still exists
                if not os.path.exists(file_path):
                    continue
                
                # Scan file
                try:
                    logger.info(f"Scanning: {file_path}")
                    result = self.scanner.scan_file(file_path)
                    
                    # Update stats
                    self.stats["files_scanned"] += 1
                    
                    # Add to cache
                    self.scan_cache.add(file_path)
                    
                    # Check result
                    if result['result'] == 'Malware':
                        self.stats["malware_detected"] += 1
                        logger.warning(f"🚨 MALWARE DETECTED: {file_path}")
                        
                        # Callback
                        if self.on_malware_detected:
                            self.on_malware_detected(file_path, result)
                    
                    else:
                        logger.info(f"✅ Clean: {file_path}")
                
                except Exception as e:
                    logger.error(f"Scan error for {file_path}: {e}")
                
            except Exception as e:
                logger.error(f"Scan worker error: {e}")
        
        logger.info("Scan worker stopped")
    
    def _cache_cleanup_worker(self):
        """Background worker to cleanup scan cache."""
        while self.running:
            time.sleep(60)  # Check every minute
            
            # Clear cache periodically
            if len(self.scan_cache) > 1000:
                logger.info("Clearing scan cache")
                self.scan_cache.clear()
    
    def start(self):
        """Start real-time protection."""
        if self.running:
            logger.warning("Protection already running")
            return
        
        logger.info("Starting real-time protection...")
        self.running = True
        self.stats["start_time"] = time.time()
        
        # Start scan worker thread
        self._scan_thread = threading.Thread(target=self._scan_worker, daemon=True)
        self._scan_thread.start()
        
        # Start cache cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cache_cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        
        # Setup file system watchers
        handler = MalwareDetectionHandler(self)
        
        for path in self.monitored_paths:
            try:
                self.observer.schedule(handler, path, recursive=True)
                logger.info(f"Monitoring: {path}")
            except Exception as e:
                logger.error(f"Failed to monitor {path}: {e}")
        
        # Start observer
        self.observer.start()
        
        logger.info("✅ Real-time protection started")
    
    def stop(self):
        """Stop real-time protection."""
        if not self.running:
            return
        
        logger.info("Stopping real-time protection...")
        self.running = False
        
        # Stop observer
        self.observer.stop()
        self.observer.join(timeout=5)
        
        # Wait for threads
        if self._scan_thread:
            self._scan_thread.join(timeout=5)
        
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        logger.info("✅ Real-time protection stopped")
    
    def is_running(self) -> bool:
        """Check if real-time protection is running."""
        return self.running
    
    def get_stats(self) -> dict:
        """Get protection statistics."""
        uptime = 0
        if self.stats["start_time"]:
            uptime = time.time() - self.stats["start_time"]
        
        return {
            **self.stats,
            "uptime_seconds": uptime,
            "queue_size": self.scan_queue.qsize(),
            "cache_size": len(self.scan_cache),
            "monitored_paths": len(self.monitored_paths)
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    def on_malware(file_path, result):
        print(f"\n🚨 MALWARE ALERT!")
        print(f"File: {file_path}")
        print(f"Result: {result['result']}")
        print(f"Confidence: {result['model']['predicted_output']}")
    
    # Create protection service
    protection = RealtimeProtection(
        scan_delay=3,
        on_malware_detected=on_malware
    )
    
    # Start protection
    protection.start()
    
    print("Real-time protection running...")
    print("Monitoring all drives for malware")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            time.sleep(10)
            stats = protection.get_stats()
            print(f"Stats: {stats}")
    except KeyboardInterrupt:
        print("\nStopping...")
        protection.stop()
