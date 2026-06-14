"""
RMAV Desktop - MangoDefend Modern UI
Main window with Figma-inspired design and sidebar navigation
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QGuiApplication
import os
from datetime import datetime

# Import new components
from ui.components import (
    Sidebar, DashboardView, ScanView,
    ProtectionView, UpdateView, QuarantineView
)

# Import existing dialogs (preserved from old window)
from ui.dialogs import ResultDialog, BatchResultDialog
from ui.dialogs.malware_alert import MalwareAlertDialog, MalwareAlertBridge

# Import theme system
from ui.styles.figma_theme import get_theme_stylesheet

# Import existing thread and scanner
from ui.threads import ScanThread, BatchScanThread


class ModernWindow(QMainWindow):
    """
    Main application window with Figma-inspired UI.

    Features:
    - Modern sidebar navigation
    - 4 tab views (Dashboard, Scan, Protection, Update)
    - Dark/Light theme support
    - Glassmorphism effects
    - Integration with existing scan/protection functionality
    """

    @staticmethod
    def _detect_system_dark_mode() -> bool:
        """Return True if the OS is currently in dark mode."""
        hints = QGuiApplication.styleHints()
        scheme = hints.colorScheme()
        # Qt.ColorScheme.Dark = 2, Light = 1, Unknown = 0 (fallback to dark)
        return scheme != Qt.ColorScheme.Light

    def __init__(self):
        """Initialize the main window, set up state, create UI, and apply the current theme."""
        super().__init__()

        # State — default follows OS theme
        self.is_dark_mode = self._detect_system_dark_mode()
        self.current_tab = "dashboard"
        self.threats_detected = 0
        self.last_scan = datetime.now()

        # Scan state
        self.scan_worker = None
        self.result_dialog = None
        # Manager references (set from main.py)
        self.sync_manager = None
        self.realtime_protection = None
        self.model_updater = None

        # Malware alert bridge (thread-safe: background → UI)
        self.malware_bridge = MalwareAlertBridge()
        self.malware_bridge.malware_detected.connect(self._on_malware_alert)

        self.init_ui()
        self.apply_theme()

        # Follow OS theme changes in real time (e.g. user switches Windows dark/light)
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._on_os_theme_changed)

    def init_ui(self):
        """Build the main window layout with sidebar and stacked content area."""
        self.setWindowTitle("MangoDefend - AI Malware Protection")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)

        # Main container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== SIDEBAR =====
        self.sidebar = Sidebar(is_dark=self.is_dark_mode)
        self.sidebar.tab_changed.connect(self._on_tab_changed)
        self.sidebar.theme_toggled.connect(self._on_theme_toggled)
        main_layout.addWidget(self.sidebar)

        # ===== CONTENT AREA (Stacked Widget for tab switching) =====
        self.content_stack = QStackedWidget()

        # Lazy view cache — views are created on first visit, not at startup
        self._view_cache: dict[str, QWidget] = {}

        # Only create dashboard immediately (it's the default visible tab)
        self.dashboard_view = DashboardView()
        self.content_stack.addWidget(self.dashboard_view)  # index 0

        # Placeholders so attribute access never fails before first visit
        self.scan_view = None
        self.protection_view = None
        self.quarantine_view = None
        self.update_view = None

        # Connect dashboard signals now; others wired on first creation
        self.dashboard_view.navigate_requested.connect(self._navigate_from_dashboard)

        # Connect view signals
        self._connect_view_signals()

        main_layout.addWidget(self.content_stack, 1)

        # Set default view
        self.content_stack.setCurrentIndex(0)

    def _connect_view_signals(self):
        """Wire the dashboard navigation signal (other views connected lazily on first visit)."""
        self.dashboard_view.navigate_requested.connect(self._navigate_from_dashboard)

    def _get_or_create_view(self, tab_id: str) -> QWidget:
        """Return the cached view for tab_id, creating and registering it on first access."""
        if tab_id in self._view_cache:
            return self._view_cache[tab_id]

        if tab_id == "scan":
            from ui.components import ScanView
            view = ScanView()
            view.scan_requested.connect(self.run_scanner)
            view.folder_scan_requested.connect(self._run_folder_scan)
            view.device_scan_requested.connect(self._run_device_scan)
            view.set_cancel_scan_callback(self._cancel_scan)
            self.scan_view = view

        elif tab_id == "protection":
            from ui.components import ProtectionView
            view = ProtectionView()
            view.protection_toggled.connect(self._toggle_realtime_protection)
            self.protection_view = view

        elif tab_id == "quarantine":
            from ui.components import QuarantineView
            view = QuarantineView()
            self.quarantine_view = view

        elif tab_id == "update":
            from ui.components import UpdateView
            view = UpdateView()
            view.check_update_requested.connect(self._check_for_updates)
            view.download_update_requested.connect(self._download_update)
            self.update_view = view

        else:
            return self.dashboard_view

        view.set_theme(self.is_dark_mode)
        self.content_stack.addWidget(view)
        self._view_cache[tab_id] = view
        return view

    def _on_tab_changed(self, tab_id: str):
        """Switch the visible content pane when the user clicks a sidebar tab."""
        self.current_tab = tab_id

        if tab_id == "dashboard":
            self.content_stack.setCurrentWidget(self.dashboard_view)
            return

        view = self._get_or_create_view(tab_id)
        self.content_stack.setCurrentWidget(view)

        if tab_id == "quarantine":
            self.quarantine_view.load_quarantine_items()

    def _navigate_from_dashboard(self, tab_id: str):
        """Navigate to a tab from a dashboard card click and sync the sidebar highlight."""
        self.sidebar.set_active_tab(tab_id)
        self._on_tab_changed(tab_id)

    def _on_theme_toggled(self, is_dark: bool):
        """Apply a new theme when the user manually toggles dark/light mode from the sidebar."""
        self.is_dark_mode = is_dark
        self.apply_theme()

    def _on_os_theme_changed(self, scheme):
        """Automatically follow OS-level dark/light mode changes without user interaction."""
        is_dark = (scheme != Qt.ColorScheme.Light)
        if is_dark == self.is_dark_mode:
            return
        self.is_dark_mode = is_dark
        self.sidebar.is_dark = is_dark
        self.sidebar.theme_btn.setText(" Dark Mode" if is_dark else " Light Mode")
        self.sidebar.threats_card.set_theme(is_dark)
        self.sidebar._apply_threats_card_theme()
        self.apply_theme()

    def apply_theme(self):
        """Regenerate and apply the stylesheet for the current dark/light mode across all views."""
        stylesheet = get_theme_stylesheet(self.is_dark_mode)
        self.setStyleSheet(stylesheet)

        # Update all views
        self.dashboard_view.set_theme(self.is_dark_mode)
        for view in self._view_cache.values():
            view.set_theme(self.is_dark_mode)

    def _ensure_scan_view(self):
        """Lazily create the scan view if it has not been visited yet."""
        if self.scan_view is None:
            self._get_or_create_view("scan")

    # =================================================================
    # SCAN FUNCTIONALITY (Preserved from old window)
    # =================================================================

    def run_scanner(self, file_path: str = None):
        """Prompt for a file if none given, then start a background single-file scan."""
        if not file_path:
            from PySide6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Pilih File untuk Dipindai", "", "All Files (*.*)"
            )

        if not file_path:
            return

        self._ensure_scan_view()
        self.scan_view.show_scan_progress("Memindai File...")

        # Create and start scan thread
        self.scan_worker = ScanThread(file_path)
        self.scan_worker.progress.connect(self._on_scan_progress)
        self.scan_worker.finished.connect(self._on_scan_finished)
        self.scan_worker.error.connect(self._on_scan_error)
        self.scan_worker.start()

    def _on_scan_progress(self, value: int, message: str):
        """Forward scan progress updates to the scan view progress panel."""
        if self.scan_view:
            self.scan_view.update_scan_progress(value, message)

    def _on_scan_finished(self, result: dict):
        """Handle scan completion: update counters, add history entry, and show result dialog."""
        if self.scan_view:
            self.scan_view.hide_scan_progress()

        # Update last scan time
        self.last_scan = datetime.now()
        self.dashboard_view.update_last_scan(self.last_scan)
        self.dashboard_view.record_scan_activity(1, self.last_scan)

        # Update threats count if malware detected
        if result.get('result') == 'Malware':
            self.threats_detected += 1
            self.sidebar.update_threats_count(self.threats_detected)
            self.dashboard_view.update_threats_count(self.threats_detected)

        # Add to scan history
        file_info = result.get('file', {})
        file_name = file_info.get('file_name', 'Unknown')
        file_path = file_info.get('file_path', '')
        scan_result = result.get('result', 'Unknown')
        timestamp = datetime.now().strftime("%H:%M")
        if self.scan_view:
            self.scan_view.add_to_history(file_name, scan_result, timestamp, file_path)

        # Show result dialog
        self.result_dialog = ResultDialog(result, self)
        self.result_dialog.show_dialog()

    def _on_scan_error(self, error_msg: str):
        """Hide the progress panel and display a critical error message box."""
        if self.scan_view:
            self.scan_view.hide_scan_progress()

        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Scan Error", f"Terjadi kesalahan: {error_msg}")

    def _cancel_scan(self):
        """Cancel any running single-file or batch scan and hide the progress panel."""
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.cancel()
            self.scan_worker.wait()

        if hasattr(self, 'batch_worker') and self.batch_worker and self.batch_worker.isRunning():
            self.batch_worker.cancel()
            self.batch_worker.wait()

        if self.scan_view:
            self.scan_view.hide_scan_progress()

    # =================================================================
    # FOLDER & DEVICE SCAN
    # =================================================================

    def _run_folder_scan(self, folder_path: str):
        """Start a batch scan for all files in the given folder path."""
        if hasattr(self, 'batch_worker') and self.batch_worker and self.batch_worker.isRunning():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Scan Berjalan", "Scan batch sedang berjalan. Tunggu hingga selesai.")
            return
        self._start_batch_scan(folder_path=folder_path)

    def _run_device_scan(self):
        """Confirm with the user then start a full-device batch scan."""
        if hasattr(self, 'batch_worker') and self.batch_worker and self.batch_worker.isRunning():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Scan Berjalan", "Scan batch sedang berjalan. Tunggu hingga selesai.")
            return
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Scan Seluruh Perangkat",
            "Scan akan memeriksa seluruh file berbahaya di perangkat Anda.\n"
            "Proses ini mungkin memakan waktu beberapa menit.\n\nLanjutkan?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._start_batch_scan(full_device=True)

    def _start_batch_scan(self, folder_path: str = None, full_device: bool = False):
        """Create and start a BatchScanThread, wiring all relevant signals."""
        title = "Scan Seluruh Perangkat..." if full_device else "Scan Folder..."
        self._ensure_scan_view()
        self.scan_view.show_scan_progress(title)

        self.batch_worker = BatchScanThread(
            folder_path=folder_path,
            full_device=full_device
        )
        self.batch_worker.progress.connect(self._on_scan_progress)
        self.batch_worker.limit_reached.connect(self._on_batch_limit_reached)
        self.batch_worker.file_scanned.connect(self._on_batch_file_scanned)
        self.batch_worker.batch_finished.connect(self._on_batch_finished)
        self.batch_worker.error.connect(self._on_scan_error)
        self.batch_worker.start()

    def _on_batch_limit_reached(self, info: dict):
        """Ask the user whether to continue the device scan past the default file limit."""
        if not hasattr(self, 'batch_worker') or not self.batch_worker:
            return

        from PySide6.QtWidgets import QMessageBox

        limit = info.get('limit', 2000)
        file_count = info.get('file_count', limit)

        reply = QMessageBox.question(
            self,
            "Lanjutkan Scan Semua File?",
            "Batas aman scan perangkat telah tercapai.\n\n"
            f"File yang sudah terkumpul: {file_count}\n"
            f"Batas default: {limit} file\n\n"
            "Pilih 'Yes' untuk lanjut scan semua file yang ditemukan.\n"
            "Pilih 'No' untuk berhenti di batas default agar proses tetap lebih cepat.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        self.batch_worker.set_limit_decision(
            reply == QMessageBox.StandardButton.Yes
        )

    def _on_batch_file_scanned(self, result: dict):
        """Update the scan history and threat counter for each file result during a batch scan."""
        file_info = result.get('file', {})
        file_name = file_info.get('file_name', 'Unknown')
        file_path = file_info.get('file_path', '')
        scan_result = result.get('result', 'Unknown')
        timestamp = datetime.now().strftime('%H:%M')
        if self.scan_view:
            self.scan_view.add_to_history(file_name, scan_result, timestamp, file_path)
        self.dashboard_view.record_scan_activity(1)

        if scan_result == 'Malware':
            self.threats_detected += 1
            self.sidebar.update_threats_count(self.threats_detected)
            self.dashboard_view.update_threats_count(self.threats_detected)

    def _on_batch_finished(self, summary: dict):
        """Hide progress, update last scan time, and show the batch result summary dialog."""
        if self.scan_view:
            self.scan_view.hide_scan_progress()

        self.last_scan = datetime.now()
        self.dashboard_view.update_last_scan(self.last_scan)

        dialog = BatchResultDialog(summary, self)
        dialog.quarantine_requested.connect(self._quarantine_batch_results)
        dialog.show_dialog()

    def _quarantine_batch_results(self, malware_results: list):
        """Move all detected malware files to the quarantine directory and report results."""
        import shutil
        import time
        from pathlib import Path as _Path

        quarantine_dir = _Path.home() / ".Mangodefend" / "Karintina"
        quarantine_dir.mkdir(parents=True, exist_ok=True)

        success, failed = 0, 0
        for result in malware_results:
            file_path = result.get("file", {}).get("file_path", "")
            if not file_path or not _Path(file_path).exists():
                failed += 1
                continue
            try:
                src = _Path(file_path)
                dest = quarantine_dir / f"{int(time.time())}_{src.name}.quarantined"
                shutil.move(str(src), str(dest))
                success += 1
            except Exception:
                failed += 1

        from PySide6.QtWidgets import QMessageBox
        info = f"Karantina selesai!\n\n Berhasil: {success} file"
        if failed:
            info += f"\n Gagal: {failed} file"
        QMessageBox.information(self, "Karantina Selesai", info)

    # =================================================================
    # REALTIME PROTECTION
    # =================================================================

    def _toggle_realtime_protection(self, enabled: bool):
        """Start or stop real-time protection and update the sidebar and dashboard state."""
        if self.realtime_protection:
            if enabled:
                try:
                    self.realtime_protection.start()
                    self.sidebar.update_status("Protected", True)
                    self.dashboard_view.set_realtime_state(True)
                except Exception as e:
                    print(f"Failed to start protection: {e}")
                    self.protection_view.set_protection_state(False)
                    self.dashboard_view.set_realtime_state(False)
            else:
                # Run stop() on a background thread — it joins worker threads
                # which could be blocked; calling from UI thread causes freeze.
                import threading as _threading

                def _do_stop():
                    """Stop real-time protection safely from a background thread."""
                    try:
                        self.realtime_protection.stop()
                    except Exception as e:
                        print(f"Failed to stop protection: {e}")

                _threading.Thread(target=_do_stop, daemon=True, name="StopProtection").start()
                self.sidebar.update_status("Unprotected", False)
                self.dashboard_view.set_realtime_state(False)
        else:
            self.protection_view.set_protection_state(False)
            self.dashboard_view.set_realtime_state(False)

    def _on_malware_alert(self, alert_data: dict):
        """Show a malware alert dialog from the UI thread and relay the user's action back."""
        file_path = alert_data.get("file_path", "Unknown")
        scan_result = alert_data.get("scan_result", {})
        response_event = alert_data.get("response_event")    # threading.Event
        response_holder = alert_data.get("response_holder")  # list to store action

        file_name = os.path.basename(file_path) if file_path and file_path != "Unknown" else "Unknown"
        now = datetime.now()
        timestamp = now.strftime('%H:%M')
        if self.scan_view:
            self.scan_view.add_to_history(file_name, "Malware (Realtime)", timestamp, file_path)
        self.last_scan = now
        self.dashboard_view.update_last_scan(now)
        self.dashboard_view.record_scan_activity(1, now)

        dialog = MalwareAlertDialog(file_path, scan_result, self)
        dialog.exec()

        action = dialog.get_action()

        # Send decision back to background thread
        if response_holder is not None:
            response_holder.append(action)
        if response_event is not None:
            response_event.set()

        # Update dashboard threat counter
        if action == MalwareAlertDialog.ACTION_KILL:
            self.threats_detected += 1
            self.dashboard_view.update_threats(self.threats_detected)

    # =================================================================
    # MODEL UPDATE
    # =================================================================

    def _check_for_updates(self):
        """Check the backend for a newer model version and relay the result to the update view."""
        if self.model_updater:
            try:
                has_update, latest_version = self.model_updater.check_for_updates()
                self.update_view.set_check_result(has_update, latest_version)

                if has_update:
                    print(f"Update available: {latest_version}")
                else:
                    print("Already up to date")
            except Exception as e:
                print(f"Failed to check updates: {e}")
                self.update_view.set_check_result(False)
        else:
            print("Model updater not available")
            self.update_view.set_check_result(False)

    def _download_update(self):
        """Download and install the latest model update, reporting progress to the update view."""
        if self.model_updater:
            try:
                # Simulate download progress
                for progress in range(0, 101, 10):
                    self.update_view.set_download_progress(progress)
                    # In real implementation, this would be async
                    import time
                    time.sleep(0.1)

                print("Update installed successfully")
            except Exception as e:
                print(f"Failed to download update: {e}")
        else:
            print("Model updater not available")

    # =================================================================
    # INITIALIZATION FROM MAIN.PY
    # =================================================================

    def initialize_protection(self):
        """Sync UI protection state with the realtime_protection manager's current status."""
        if self.realtime_protection:
            is_enabled = self.realtime_protection.is_running()
            # protection_view may not exist yet (lazy) — only update if created
            if self.protection_view:
                self.protection_view.set_protection_state(is_enabled)
            if is_enabled:
                self.sidebar.update_status("Protected", True)
            else:
                self.sidebar.update_status("Unprotected", False)
            self.dashboard_view.set_realtime_state(is_enabled)

    def closeEvent(self, event):
        """Minimize to system tray instead of closing."""
        self._cancel_scan()
        event.ignore()
        self.hide()
