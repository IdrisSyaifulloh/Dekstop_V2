"""
Real-time Protection - Pseudo-Blocking Mode
Uses Windows file locks to block access to new files while scanning.

Flow:
  1. Watchdog detects new file (e.g., .exe downloaded)
  2. IMMEDIATELY acquire exclusive lock on file (blocks all access)
  3. Scan file with AI model (ONNX)
  4. If clean → release lock (file can be opened normally)
  5. If malware → quarantine/delete, then release lock

This provides near-kernel-level protection without requiring a signed
kernel driver, making the app fully standalone.
"""

import os
import sys
import time
import ctypes
import threading
import logging
import shutil
from pathlib import Path
from typing import Set, Callable, Optional, List
from queue import Queue, Empty

from .scanner import MalwareScanner

logger = logging.getLogger(__name__)

# ================================================================
# Windows File Locking via CreateFileW
# ================================================================

if sys.platform == "win32":
    import ctypes.wintypes

    kernel32 = ctypes.windll.kernel32

    GENERIC_READ = 0x80000000
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x00000080
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    INVALID_HANDLE_VALUE = ctypes.wintypes.HANDLE(-1).value

    # Share modes
    FILE_SHARE_NONE = 0x00000000      # Exclusive lock (no sharing)
    FILE_SHARE_READ = 0x00000001      # Allow others to read


class FileLock:
    """
    Locks a file using Windows CreateFileW with no sharing mode.
    While locked, no other process can open/execute the file.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._handle = None
        self._locked = False

    def acquire(self, max_retries: int = 5, retry_delay: float = 0.3) -> bool:
        """
        Acquire exclusive lock on the file.
        Returns True if lock acquired, False otherwise.
        """
        if sys.platform != "win32":
            return False

        for attempt in range(max_retries):
            try:
                handle = kernel32.CreateFileW(
                    self.file_path,
                    GENERIC_READ,
                    FILE_SHARE_NONE,    # NO SHARING = exclusive lock
                    None,
                    OPEN_EXISTING,
                    FILE_ATTRIBUTE_NORMAL,
                    None
                )

                if handle != INVALID_HANDLE_VALUE:
                    self._handle = handle
                    self._locked = True
                    return True

                # File might still be in use (e.g., being downloaded)
                error_code = kernel32.GetLastError()
                if error_code == 32:  # ERROR_SHARING_VIOLATION
                    time.sleep(retry_delay)
                    continue
                else:
                    return False

            except Exception as e:
                logger.debug(f"Lock attempt {attempt + 1} failed for {self.file_path}: {e}")
                time.sleep(retry_delay)

        return False

    def release(self):
        """Release the file lock."""
        if self._handle and self._locked:
            try:
                kernel32.CloseHandle(self._handle)
            except Exception:
                pass
            finally:
                self._handle = None
                self._locked = False

    @property
    def is_locked(self) -> bool:
        return self._locked

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


# ================================================================
# FILE EXTENSION FILTERS
# ================================================================

# Extensions to SKIP (clearly safe, non-executable files)
SKIP_EXTENSIONS = {
    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg', '.webp', '.tiff',
    # Videos
    '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
    # Audio
    '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma',
    # Documents (text-based)
    '.txt', '.md', '.csv', '.json', '.xml', '.yaml', '.yml', '.ini', '.cfg',
    '.log', '.html', '.css',
    # Fonts
    '.ttf', '.otf', '.woff', '.woff2',
    # Archives (scan these!)
    # '.zip', '.rar', '.7z', '.tar', '.gz',  # NOT skipped
    # Temporary/system
    '.tmp', '.temp', '.lock', '.gitignore', '.gitattributes',
}

# Executable/dangerous extensions (used for process monitor)
DANGEROUS_EXTENSIONS = {
    '.exe', '.dll', '.scr', '.bat', '.cmd',
    '.ps1', '.vbs', '.js', '.jar', '.msi',
    '.com', '.pif', '.wsf', '.hta',
}


class RealtimeProtection:
    """
    Real-time file system protection with pseudo-blocking.

    When a new dangerous file appears (e.g., .exe), it is immediately
    locked (exclusive file handle) so no process can execute it.
    The file is then scanned with AI. If clean, the lock is released.
    If malware, the file is quarantined/deleted.
    """

    def __init__(
        self,
        monitored_paths: Optional[List[str]] = None,
        scan_delay: int = 1,
        max_queue_size: int = 10000,
        on_malware_detected: Optional[Callable] = None,
        quarantine_dir: Optional[str] = None,
    ):
        """
        Initialize real-time protection.

        Args:
            monitored_paths: Paths to monitor (default: all user folders)
            scan_delay: Delay before scanning newly created files (seconds)
            max_queue_size: Max scan queue size
            on_malware_detected: Callback(file_path, scan_result)
            quarantine_dir: Directory to move malware files to
        """
        self.monitored_paths = monitored_paths
        self.scan_delay = max(scan_delay, 1)
        self.max_queue_size = min(max_queue_size, 10000)
        self.on_malware_detected = on_malware_detected
        self.malware_bridge = None  # Set from UI (MalwareAlertBridge)

        # Quarantine directory
        if quarantine_dir:
            self.quarantine_dir = Path(quarantine_dir)
        else:
            self.quarantine_dir = Path.home() / ".mangodefend" / "quarantine"

        # Components
        self.scanner = MalwareScanner()

        # State
        self.running = False
        self.mode = "none"
        self._scan_threads: List[threading.Thread] = []
        self._observer = None
        self._scan_queue = None
        self._active_locks: dict = {}  # file_path -> FileLock
        self._lock_mutex = threading.Lock()

        # Statistics
        self.stats = {
            "files_scanned": 0,
            "malware_detected": 0,
            "files_blocked": 0,
            "files_quarantined": 0,
            "processes_suspended": 0,
            "processes_killed": 0,
            "start_time": None,
            "mode": "none"
        }

        # Scan cache (avoid re-scanning known clean files)
        self.scan_cache: Set[str] = set()
        self.cache_ttl = 300  # 5 minutes

        # Whitelist extensions (files to skip scanning)
        self.whitelist_extensions: Set[str] = set()

        # Process monitor state
        self._known_pids: Set[int] = set()

        logger.info("RealtimeProtection initialized (pseudo-blocking + scan-on-execute)")

    # ================================================================
    # START / STOP
    # ================================================================

    def start(self):
        """Start real-time protection with pseudo-blocking."""
        if self.running:
            logger.warning("Protection already running")
            return

        self.running = True
        self.stats["start_time"] = time.time()

        # Ensure quarantine directory exists
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        # Start both protection layers
        self._start_watchdog_mode()
        self._start_process_monitor()

    def stop(self):
        """Stop real-time protection."""
        if not self.running:
            return

        logger.info("Stopping real-time protection...")
        self.running = False

        # Stop watchdog observer
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None

        # Wait for scan threads
        for t in self._scan_threads:
            t.join(timeout=5)
        self._scan_threads.clear()

        # Release any remaining locks
        with self._lock_mutex:
            for file_path, lock in self._active_locks.items():
                lock.release()
                logger.debug(f"Released remaining lock: {file_path}")
            self._active_locks.clear()

        self.mode = "none"
        self.stats["mode"] = "none"
        logger.info("Real-time protection stopped")

    # ================================================================
    # WATCHDOG + PSEUDO-BLOCKING
    # ================================================================

    def _start_watchdog_mode(self):
        """Start watchdog monitoring with pseudo-blocking."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            logger.error("watchdog not installed! Run: pip install watchdog")
            self.running = False
            return

        if not self.monitored_paths:
            self.monitored_paths = self._get_default_paths()

        self._scan_queue = Queue(maxsize=self.max_queue_size)

        # Create event handler
        protection = self

        class PseudoBlockHandler(FileSystemEventHandler):
            """Intercept ALL new files and scan them."""

            def on_created(self, event):
                if event.is_directory:
                    return
                protection._on_new_file(event.src_path)

            def on_modified(self, event):
                if event.is_directory:
                    return
                file_path = event.src_path

                # Only scan modified files if not already being handled
                if file_path not in protection.scan_cache:
                    with protection._lock_mutex:
                        if file_path not in protection._active_locks:
                            protection._on_new_file(file_path)

        # Start observer
        self._observer = Observer()
        handler = PseudoBlockHandler()

        for path in self.monitored_paths:
            try:
                if os.path.exists(path):
                    self._observer.schedule(handler, path, recursive=True)
                    logger.info(f"📂 Monitoring: {path}")
            except Exception as e:
                logger.error(f"Failed to monitor {path}: {e}")

        self._observer.start()

        # Start scan workers (2 threads for parallel scanning)
        for i in range(2):
            t = threading.Thread(
                target=self._scan_worker,
                daemon=True,
                name=f"ScanWorker-{i}"
            )
            t.start()
            self._scan_threads.append(t)

        # Start cache cleanup thread
        t_cache = threading.Thread(
            target=self._cache_cleanup_worker,
            daemon=True,
            name="CacheCleanup"
        )
        t_cache.start()
        self._scan_threads.append(t_cache)

        self.mode = "pseudo-blocking"
        self.stats["mode"] = "pseudo-blocking"
        logger.info("✅ Real-time protection started (PSEUDO-BLOCKING MODE)")

    def _on_new_file(self, file_path: str):
        """
        Handle a newly detected file:
        1. Acquire exclusive lock (blocks access)
        2. Queue for scanning
        """
        if file_path in self.scan_cache:
            return

        # Acquire lock immediately
        lock = FileLock(file_path)
        if lock.acquire(max_retries=3, retry_delay=0.2):
            with self._lock_mutex:
                self._active_locks[file_path] = lock

            self.stats["files_blocked"] += 1
            logger.info(f"🔒 LOCKED: {file_path} (queued for scan)")

            # Queue for scanning
            try:
                self._scan_queue.put(file_path, block=False)
            except Exception:
                # Queue full, release lock
                lock.release()
                with self._lock_mutex:
                    self._active_locks.pop(file_path, None)
        else:
            # Could not lock — file might be in use by downloader
            # Queue it for a delayed scan without lock
            logger.debug(f"Could not lock {file_path}, queuing for delayed scan")
            try:
                self._scan_queue.put(file_path, block=False)
            except Exception:
                pass

    def _scan_worker(self):
        """Worker thread: scan files and decide allow/quarantine."""
        logger.info(f"Scan worker started: {threading.current_thread().name}")

        while self.running:
            try:
                try:
                    file_path = self._scan_queue.get(timeout=1)
                except Empty:
                    continue

                # Small delay to let file be fully written
                time.sleep(self.scan_delay)

                if not os.path.exists(file_path):
                    self._release_lock(file_path)
                    continue

                # Scan with AI
                is_malware = False
                scan_result = None

                try:
                    scan_result = self.scanner.scan_file(file_path)
                    self.stats["files_scanned"] += 1

                    if scan_result and scan_result.get('result') == 'Malware':
                        is_malware = True
                        self.stats["malware_detected"] += 1

                except Exception as e:
                    logger.error(f"Scan error for {file_path}: {e}")
                    # Fail-open: release lock on error
                    self._release_lock(file_path)
                    continue

                if is_malware:
                    # MALWARE — ask user what to do
                    logger.warning(f"🚨 MALWARE BLOCKED: {file_path}")

                    action = self._ask_user_decision(file_path, scan_result)

                    # Release lock before quarantine (need to move file)
                    self._release_lock(file_path)

                    if action == 1:  # ACTION_KILL (quarantine)
                        self._quarantine_file(file_path)
                        self.stats["malware_detected"] += 1
                    else:
                        # User chose to continue — just release lock
                        logger.info(f"▶️ User allowed file: {os.path.basename(file_path)}")
                        self.scan_cache.add(file_path)
                else:
                    # CLEAN — release lock, add to cache
                    self._release_lock(file_path)
                    self.scan_cache.add(file_path)
                    logger.info(f"✅ Clean: {os.path.basename(file_path)}")

            except Exception as e:
                logger.error(f"Scan worker error: {e}")
                time.sleep(1)

        logger.info(f"Scan worker stopped: {threading.current_thread().name}")

    def _release_lock(self, file_path: str):
        """Release file lock if held."""
        with self._lock_mutex:
            lock = self._active_locks.pop(file_path, None)
            if lock:
                lock.release()
                logger.debug(f"🔓 Unlocked: {file_path}")

    def _quarantine_file(self, file_path: str):
        """Move malware file to quarantine directory."""
        try:
            src = Path(file_path)
            if not src.exists():
                return

            # Create unique quarantine name
            timestamp = int(time.time())
            quarantine_name = f"{timestamp}_{src.name}.quarantined"
            dest = self.quarantine_dir / quarantine_name

            shutil.move(str(src), str(dest))
            self.stats["files_quarantined"] += 1
            logger.info(f"🗑️ Quarantined: {src.name} → {dest}")

        except Exception as e:
            logger.error(f"Failed to quarantine {file_path}: {e}")
            # Try to delete instead
            try:
                os.remove(file_path)
                logger.info(f"🗑️ Deleted malware: {file_path}")
            except Exception:
                logger.error(f"Could not delete malware file: {file_path}")

    def _cache_cleanup_worker(self):
        """Periodically clean scan cache to re-scan files."""
        while self.running:
            time.sleep(60)
            if len(self.scan_cache) > 1000:
                self.scan_cache.clear()
                logger.debug("Scan cache cleared")

    # ================================================================
    # HELPER METHODS
    # ================================================================

    def _get_default_paths(self) -> List[str]:
        """Get default paths to monitor (user-focused, not all drives)."""
        home = Path.home()
        paths = [
            str(home / "Downloads"),
            str(home / "Desktop"),
            str(home / "Documents"),
        ]

        # Add common temp/download locations
        temp = os.environ.get("TEMP", "")
        if temp and os.path.exists(temp):
            paths.append(temp)

        return [p for p in paths if os.path.exists(p)]

    def is_running(self) -> bool:
        """Check if protection is running."""
        return self.running

    def get_mode(self) -> str:
        """Get current protection mode."""
        return self.mode

    def get_stats(self) -> dict:
        """Get protection statistics."""
        uptime = 0
        if self.stats["start_time"]:
            uptime = time.time() - self.stats["start_time"]

        return {
            **self.stats,
            "uptime_seconds": round(uptime, 1),
            "cache_size": len(self.scan_cache),
            "active_locks": len(self._active_locks),
        }


    # ================================================================
    # SCAN-ON-EXECUTE (Process Monitor)
    # ================================================================

    def _start_process_monitor(self):
        """
        Start monitoring new process creation.
        When a new .exe runs, suspend it → scan → resume or kill.
        """
        try:
            import psutil
            # Take snapshot of currently running PIDs
            self._known_pids = set(psutil.pids())

            t = threading.Thread(
                target=self._process_monitor_worker,
                daemon=True,
                name="ProcessMonitor"
            )
            t.start()
            self._scan_threads.append(t)
            logger.info("🔍 Process monitor started (scan-on-execute)")

        except ImportError:
            logger.warning("psutil not installed, scan-on-execute disabled. Run: pip install psutil")

    def _process_monitor_worker(self):
        """
        Poll for new processes and scan:
        1. The executable itself (if not a system process)
        2. Any file being opened (from command-line arguments)
        
        This catches BOTH new executables AND existing files being clicked.
        """
        import psutil

        logger.info("Process monitor worker started (scan-on-click for all files)")

        while self.running:
            try:
                current_pids = set(psutil.pids())
                new_pids = current_pids - self._known_pids
                self._known_pids = current_pids

                for pid in new_pids:
                    if not self.running:
                        break

                    try:
                        proc = psutil.Process(pid)
                        exe_path = proc.exe()

                        if not exe_path:
                            continue

                        is_system = self._is_system_process(exe_path)

                        # ── LAYER A: Scan the executable itself ──
                        # (Skip for system/trusted processes like notepad.exe)
                        if not is_system and exe_path not in self.scan_cache:
                            self._scan_and_handle_process(proc, pid, exe_path)
                            continue  # Process was handled (resumed or killed)

                        # ── LAYER B: Scan files being OPENED by this process ──
                        # This runs for ALL processes (including system ones!)
                        # When user double-clicks a file, Windows runs a program
                        # with the file path as argument. We scan those files.
                        try:
                            cmdline = proc.cmdline()
                            logger.info(f"🔎 New process: {proc.name()} PID={pid} args={len(cmdline)-1}")

                            if len(cmdline) > 1:
                                for arg in cmdline[1:]:
                                    # Clean the argument (remove quotes, strip whitespace)
                                    clean_arg = arg.strip().strip('"').strip("'")

                                    # Skip flags/options (start with - or /)
                                    if clean_arg.startswith('-') or clean_arg.startswith('/'):
                                        continue

                                    # Normalize path
                                    try:
                                        clean_arg = os.path.normpath(clean_arg)
                                    except Exception:
                                        continue

                                    # Check if argument is a file path
                                    if os.path.isfile(clean_arg):
                                        # Skip already scanned
                                        if clean_arg in self.scan_cache:
                                            continue

                                        logger.info(f"📂 File opened: {os.path.basename(clean_arg)} by {proc.name()}")
                                        # Scan the file being opened
                                        self._scan_opened_file(proc, pid, clean_arg)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                    except Exception as e:
                        logger.debug(f"Process monitor error for PID {pid}: {e}")

                # Poll interval: 150ms (fast enough to catch new processes)
                time.sleep(0.15)

            except Exception as e:
                logger.error(f"Process monitor error: {e}")
                time.sleep(1)

        logger.info("Process monitor worker stopped")

    def _scan_and_handle_process(self, proc, pid: int, exe_path: str):
        """Suspend process, scan its executable, ask user if malware."""
        import psutil

        try:
            logger.info(f"⏸️ SUSPENDED process: {proc.name()} (PID={pid})")
            proc.suspend()
            self.stats["processes_suspended"] += 1

            result = self.scanner.scan_file(exe_path)
            self.stats["files_scanned"] += 1

            if result and result.get('result') == 'Malware':
                # Ask user what to do
                action = self._ask_user_decision(exe_path, result)

                if action == 1:  # ACTION_KILL
                    logger.warning(f"🚨 KILLED malware process: {proc.name()} (PID={pid})")
                    proc.kill()
                    self.stats["malware_detected"] += 1
                    self.stats["processes_killed"] += 1
                    self._quarantine_file(exe_path)
                else:
                    # User chose to continue
                    logger.info(f"▶️ User allowed process: {proc.name()} (PID={pid})")
                    proc.resume()
                    self.scan_cache.add(exe_path)
            else:
                proc.resume()
                self.scan_cache.add(exe_path)
                logger.info(f"▶️ Resumed clean process: {proc.name()} (PID={pid})")

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        except Exception as e:
            logger.error(f"Scan error for PID {pid}: {e}")
            try:
                proc.resume()
            except Exception:
                pass

    def _scan_opened_file(self, proc, pid: int, file_path: str):
        """Scan a file that is being opened by a process."""
        import psutil

        try:
            logger.info(f"🔍 Scanning opened file: {os.path.basename(file_path)} (opened by {proc.name()}, PID={pid})")

            result = self.scanner.scan_file(file_path)
            self.stats["files_scanned"] += 1

            if result and result.get('result') == 'Malware':
                # Ask user what to do
                action = self._ask_user_decision(file_path, result)

                if action == 1:  # ACTION_KILL
                    logger.warning(f"🚨 MALWARE found: {file_path}")
                    logger.warning(f"🚨 KILLING process: {proc.name()} (PID={pid})")
                    try:
                        proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    self.stats["malware_detected"] += 1
                    self.stats["processes_killed"] += 1
                    self._quarantine_file(file_path)
                else:
                    logger.info(f"▶️ User allowed file: {os.path.basename(file_path)}")
                    self.scan_cache.add(file_path)
            else:
                self.scan_cache.add(file_path)
                logger.info(f"✅ Clean file: {os.path.basename(file_path)}")

        except Exception as e:
            logger.error(f"Error scanning opened file {file_path}: {e}")

    def _ask_user_decision(self, file_path: str, scan_result: dict) -> int:
        """
        Ask user via UI what to do with detected malware.
        Returns: 0 = continue, 1 = kill & quarantine
        """
        if self.malware_bridge:
            import threading as _threading
            response_event = _threading.Event()
            response_holder = []  # Will hold [action_int]

            alert_data = {
                "file_path": file_path,
                "scan_result": scan_result,
                "response_event": response_event,
                "response_holder": response_holder,
            }

            # Emit signal to UI thread
            self.malware_bridge.malware_detected.emit(alert_data)

            # Wait for user to respond (max 60 seconds)
            response_event.wait(timeout=60)

            if response_holder:
                return response_holder[0]

        # Default: kill & quarantine (if no UI bridge or timeout)
        return 1

    def _is_system_process(self, exe_path: str) -> bool:
        """Check if exe is a system/trusted process (skip scanning)."""
        exe_lower = exe_path.lower()
        system_paths = [
            os.environ.get("SYSTEMROOT", "C:\\Windows").lower(),
            os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files")).lower(),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")).lower(),
        ]
        # Skip our own process
        if os.getpid() == os.getpid():  # Always skip self
            try:
                import psutil
                if exe_lower == psutil.Process(os.getpid()).exe().lower():
                    return True
            except Exception:
                pass

        for sys_path in system_paths:
            if exe_lower.startswith(sys_path):
                return True
        return False


# ================================================================
# CLI Entry Point
# ================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    def on_malware(file_path, result):
        print(f"\n🚨 MALWARE ALERT!")
        print(f"File: {file_path}")
        print(f"Result: {result.get('result', 'Unknown')}")
        print(f"Confidence: {result.get('confidence', 0):.1%}")

    protection = RealtimeProtection(
        scan_delay=2,
        on_malware_detected=on_malware,
    )

    protection.start()

    print(f"\n🛡️ Real-time protection running (mode: {protection.get_mode()})")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            time.sleep(10)
            stats = protection.get_stats()
            print(f"[Stats] Scanned: {stats['files_scanned']} | "
                  f"Blocked: {stats['files_blocked']} | "
                  f"Malware: {stats['malware_detected']} | "
                  f"Killed: {stats['processes_killed']} | "
                  f"Locks: {stats['active_locks']}")
    except KeyboardInterrupt:
        print("\nStopping...")
        protection.stop()
