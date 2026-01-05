"""
RMAV Desktop - MangoDefend Style UI
Exact replica of Frontend/gui design
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QFrame, QScrollArea,
    QMessageBox, QSizePolicy, QDialog
)
from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont
from PySide6.QtWidgets import QApplication  # Add this for processEvents
from pathlib import Path
from datetime import datetime

# Import components from separate modules
from ui.components.navbar import SimpleNavbar
from ui.dialogs.scanning_dialog import ScanningDialog
from ui.dialogs.result_dialog import ResultDialog
from ui.dialogs.scan_choice_dialog import ScanChoiceDialog
from core.scan_thread import ScanThread


class ModernWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.scan_history = []
        self.is_scanning = False
        self.scan_worker = None
        self.scan_dialog = None
        self.result_dialog = None
        self.is_dark_mode = False
        self.init_ui()
        self.apply_mango_theme()


    def init_ui(self):
        self.setWindowTitle("MangoDefend - Pemindai Malware AI")
        self.setGeometry(100, 100, 1000, 700)
        self.setMinimumSize(900, 650)


        # Main container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)


        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)

        # === NAVBAR ===
        self.navbar = SimpleNavbar(central_widget)
        self.navbar.menu_clicked.connect(self.show_menu)
        self.navbar.dark_mode_toggled.connect(self.on_dark_mode_toggle)
        main_layout.addWidget(self.navbar)

        # Content area with better padding
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(60, 30, 60, 60)
        content_layout.setSpacing(40)
        content.setLayout(content_layout)

        # === STATUS INDICATOR WITH TOGGLE ===
        status_container = QHBoxLayout()
        status_container.setAlignment(Qt.AlignmentFlag.AlignRight)
        status_container.setSpacing(10)
        
        # Real-time Protection Status Label
        self.rtp_status_label = QLabel("Perlindungan Real-time:")
        self.rtp_status_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 13px;
                font-weight: 600;
            }
        """)
        status_container.addWidget(self.rtp_status_label)
        
        # Toggle Switch Button
        self.rtp_toggle_btn = QPushButton("OFF")
        self.rtp_toggle_btn.setObjectName("toggleButton")
        self.rtp_toggle_btn.setFixedSize(80, 35)
        self.rtp_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rtp_toggle_btn.clicked.connect(self.toggle_realtime_protection)
        self.rtp_toggle_btn.setStyleSheet("""
            QPushButton#toggleButton {
                background: #FF4444;
                border: none;
                border-radius: 17px;
                color: white;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#toggleButton:hover {
                background: #FF6666;
            }
        """)
        status_container.addWidget(self.rtp_toggle_btn)
        
        content_layout.addLayout(status_container)


        # Center content
        center_layout = QVBoxLayout()
        center_layout.setSpacing(25)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)


        # Scan icon with better size
        self.scan_icon = QLabel("")
        self.scan_icon.setObjectName("scanIcon")
        self.scan_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scan_icon.setFixedSize(140, 140)
        center_layout.addWidget(self.scan_icon, alignment=Qt.AlignmentFlag.AlignCenter)


        # Add spacing after icon
        center_layout.addSpacing(10)


        # Title
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.setSpacing(5)


        run_label = QLabel("Jalankan ")
        run_label.setObjectName("mainTitle")
        title_layout.addWidget(run_label)


        smart_label = QLabel("Smart")
        smart_label.setObjectName("smartTitle")
        title_layout.addWidget(smart_label)


        scan_label = QLabel(" Scan")
        scan_label.setObjectName("scanTitle")
        title_layout.addWidget(scan_label)


        center_layout.addLayout(title_layout)


        # Add spacing after title
        center_layout.addSpacing(5)


        # Description with better styling
        desc_label = QLabel("Lindungi perangkat Anda dengan sistem deteksi malware\nbertenaga AI yang canggih dan akurat.")
        desc_label.setObjectName("descriptionText")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        center_layout.addWidget(desc_label)


        content_layout.addStretch(2)
        content_layout.addLayout(center_layout)
        content_layout.addStretch(1)


        # Action buttons with better spacing
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(25)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)


        self.update_btn = QPushButton("Pembaruan")
        self.update_btn.setObjectName("actionButton")
        self.update_btn.setFixedSize(165, 90)
        self.update_btn.clicked.connect(self.show_update_info)
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons_layout.addWidget(self.update_btn)


        self.malware_btn = QPushButton("Pemindai Malware")
        self.malware_btn.setObjectName("actionButton")
        self.malware_btn.setFixedSize(165, 90)
        self.malware_btn.clicked.connect(self.run_scanner)
        self.malware_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons_layout.addWidget(self.malware_btn)


        self.protection_btn = QPushButton("Perlindungan Realtime")
        self.protection_btn.setObjectName("actionButton")
        self.protection_btn.setFixedSize(165, 90)
        self.protection_btn.clicked.connect(self.show_protection_info)
        self.protection_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons_layout.addWidget(self.protection_btn)


        content_layout.addLayout(buttons_layout)
        content_layout.addStretch(2)


        main_layout.addWidget(content)
        
        # Start status update timer
        from PySide6.QtCore import QTimer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_protection_status)
        self.status_timer.start(2000)  # Update every 2 seconds


    def show_menu(self):
        """Handle menu button click"""
        QMessageBox.information(
            self, "Menu",
            "Menu akan segera hadir!\n\nFitur:\n- Pengaturan\n- Riwayat Scan\n- Tentang"
        )

    def on_dark_mode_toggle(self, is_dark):
        """Handle dark mode toggle dari navbar"""
        self.is_dark_mode = is_dark
        self.apply_mango_theme()
        
        # Update scan dialog jika ada
        if self.scan_dialog:
            self.scan_dialog.apply_style(is_dark)
        
        # Update navbar
        self.navbar.apply_style(is_dark)


    def apply_mango_theme(self):
        """Apply Modern MangoDefend theme with improved UI"""
        if self.is_dark_mode:
            self.setStyleSheet("""
                /* DARK MODE - Modern & Clean */
                QMainWindow {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #0F0F0F, stop:0.5 #1A1A1A, stop:1 #252525);
                }


                QLabel#scanIcon {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #FF8C00, stop:0.3 #FFA500, stop:0.7 #FFB732, stop:1 #32CD32);
                    border-radius: 65px;
                    font-size: 56px;
                    color: white;
                    border: 4px solid rgba(255, 165, 0, 0.3);
                    padding: 5px;
                }


                QLabel#mainTitle {
                    color: #FFFFFF;
                    font-size: 42px;
                    font-weight: 700;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    letter-spacing: 1px;
                }


                QLabel#smartTitle {
                    color: #FFA500;
                    font-size: 42px;
                    font-weight: 700;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    letter-spacing: 1px;
                    text-shadow: 0 0 20px rgba(255, 165, 0, 0.5);
                }


                QLabel#scanTitle {
                    color: #32CD32;
                    font-size: 42px;
                    font-weight: 700;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    letter-spacing: 1px;
                    text-shadow: 0 0 20px rgba(50, 205, 50, 0.3);
                }


                QLabel#descriptionText {
                    color: #CCCCCC;
                    font-size: 17px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    max-width: 600px;
                    line-height: 1.6;
                }


                QPushButton#actionButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(40, 40, 40, 0.95), stop:1 rgba(30, 30, 30, 0.95));
                    border: 3px solid #FFA500;
                    border-radius: 16px;
                    color: #FFA500;
                    font-size: 13px;
                    font-weight: 600;
                    padding: 15px 10px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }


                QPushButton#actionButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FFA500, stop:1 #FF8C00);
                    color: white;
                    border: 3px solid #FFB732;
                    transform: translateY(-2px);
                }


                QPushButton#actionButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FF8C00, stop:1 #FF7F00);
                    border: 3px solid #FF8C00;
                }
            """)
        else:
            self.setStyleSheet("""
                /* LIGHT MODE - Modern & Vibrant */
                QMainWindow {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #FFF5E6, stop:0.5 #FFE4B5, stop:1 #FFDAB9);
                }


                QLabel#scanIcon {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #FF8C00, stop:0.3 #FFA500, stop:0.7 #FFD700, stop:1 #32CD32);
                    border-radius: 65px;
                    font-size: 56px;
                    color: white;
                    border: 4px solid rgba(255, 140, 0, 0.4);
                    padding: 5px;
                }


                QLabel#mainTitle {
                    color: #2C2C2C;
                    font-size: 42px;
                    font-weight: 700;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    letter-spacing: 1px;
                }


                QLabel#smartTitle {
                    color: #FF8C00;
                    font-size: 42px;
                    font-weight: 700;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    letter-spacing: 1px;
                    text-shadow: 0 2px 4px rgba(255, 140, 0, 0.3);
                }


                QLabel#scanTitle {
                    color: #228B22;
                    font-size: 42px;
                    font-weight: 700;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    letter-spacing: 1px;
                    text-shadow: 0 2px 4px rgba(34, 139, 34, 0.2);
                }


                QLabel#descriptionText {
                    color: #444444;
                    font-size: 17px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    max-width: 600px;
                    line-height: 1.6;
                }


                QPushButton#actionButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(255, 255, 255, 0.95), stop:1 rgba(255, 250, 240, 0.95));
                    border: 3px solid #FF8C00;
                    border-radius: 16px;
                    color: #2C2C2C;
                    font-size: 13px;
                    font-weight: 600;
                    padding: 15px 10px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }


                QPushButton#actionButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FFA500, stop:1 #FF8C00);
                    color: white;
                    border: 3px solid #FFB732;
                    transform: translateY(-2px);
                }


                QPushButton#actionButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FF8C00, stop:1 #FF7F00);
                    border: 3px solid #FF8C00;
                }
            """)


    def run_scanner(self):
        """Start malware scanner"""
        if self.is_scanning:
            return

        # Show choice dialog
        choice_dialog = ScanChoiceDialog(self, self.is_dark_mode)
        result = choice_dialog.exec()

        if result != QDialog.DialogCode.Accepted:
            return

        choice = choice_dialog.get_choice()

        if choice == "file":
            self.run_file_scan()
        elif choice == "device":
            self.run_device_scan()

    def run_file_scan(self):
        """Scan a single file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih File untuk di-Scan",
            "",
            "Semua File (*.*);;Executable (*.exe *.dll);;Archives (*.zip *.rar)"
        )


        if not file_path:
            return


        # Validate file
        if not Path(file_path).exists():
            QMessageBox.critical(self, "Error", "File tidak ditemukan!")
            return


        # Check file size
        file_size = Path(file_path).stat().st_size
        if file_size > 10 * 1024 * 1024:
            QMessageBox.warning(
                self, "File Terlalu Besar",
                f"Ukuran file melebihi batas 10 MB.\nUkuran: {file_size / (1024*1024):.2f} MB"
            )
            return


        self.current_file = file_path
        self.start_scan()

    def run_device_scan(self):
        """Scan full device"""
        # Konfirmasi dari user
        reply = QMessageBox.question(
            self, "Konfirmasi Full Device Scan",
            "Pemindaian full device akan memindai semua file di perangkat Anda.\n\n"
            "Proses ini mungkin memakan waktu lama.\n\n"
            "Apakah Anda yakin ingin melanjutkan?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Pilih drive atau folder untuk di-scan
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Pilih Folder/Drive untuk di-Scan",
            ""
        )

        if not folder_path:
            return

        # Set path untuk full scan
        self.current_file = folder_path
        self.start_scan(is_full_scan=True)


    def start_scan(self, is_full_scan=False):
        """Start scanning process"""
        self.is_scanning = True


        # Create scanning overlay
        if not self.scan_dialog:
            self.scan_dialog = ScanningDialog(self.centralWidget())
            self.scan_dialog.set_cancel_callback(self.cancel_scan)


        self.scan_dialog.setGeometry(self.centralWidget().rect())
        self.scan_dialog.start()


        # Start scan worker
        self.scan_worker = ScanThread(self.current_file, is_full_scan=is_full_scan)
        self.scan_worker.progress.connect(self.update_scan_progress)
        self.scan_worker.finished.connect(self.scan_finished)
        self.scan_worker.error.connect(self.scan_error)
        self.scan_worker.start()


    def update_scan_progress(self, value, message):
        """Update progress"""
        if self.scan_dialog and self.scan_dialog.isVisible():
            self.scan_dialog.update_progress(value, message)


    def scan_finished(self, result):
        """Handle scan completion"""
        self.is_scanning = False


        if self.scan_dialog:
            self.scan_dialog.finish()


        self.scan_history.append(result)


        # Show custom result dialog
        self.result_dialog = ResultDialog(result, self.centralWidget())
        self.result_dialog.show_dialog()


        self.cleanup_scan_worker()


    def scan_error(self, error_msg):
        """Handle scan error"""
        self.is_scanning = False


        if self.scan_dialog:
            self.scan_dialog.finish()


        QMessageBox.critical(
            self, "❌ Error Pemindaian",
            f"Terjadi kesalahan saat memindai:\n\n{error_msg}\n\nSilakan coba lagi."
        )


        self.cleanup_scan_worker()


    def cancel_scan(self):
        """Cancel scanning"""
        if self.scan_worker:
            self.scan_worker.cancel()


        if self.scan_dialog:
            self.scan_dialog.finish()


        self.is_scanning = False
        self.cleanup_scan_worker()


        QMessageBox.information(self, "Dibatalkan", "Pemindaian telah dibatalkan.")


    def cleanup_scan_worker(self):
        """Cleanup scan worker"""
        if self.scan_worker:
            if self.scan_worker.isRunning():
                self.scan_worker.quit()
                self.scan_worker.wait(2000)
            self.scan_worker = None


    def show_update_info(self):
        """Check for model updates and show update dialog."""
        # Check if model_updater is available
        if not hasattr(self, 'model_updater') or self.model_updater is None:
            QMessageBox.information(
                self, "📦 Model Update",
                "Model updater tidak tersedia.\n\n"
                "Pastikan backend berjalan dan model API aktif."
            )
            return
        
        # Show checking dialog
        checking_msg = QMessageBox(self)
        checking_msg.setWindowTitle("🔍 Memeriksa Update")
        checking_msg.setText("Memeriksa versi model terbaru...")
        checking_msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
        checking_msg.show()
        QApplication.processEvents()
        
        try:
            # Check for updates
            update_info = self.model_updater.check_for_updates()
            checking_msg.close()
            
            if not update_info:
                QMessageBox.warning(
                    self, "⚠️ Error",
                    "Tidak dapat memeriksa update.\n\n"
                    "Pastikan backend berjalan."
                )
                return
            
            if update_info.get('update_available'):
                # Update available
                latest = update_info['latest_info']
                current_ver = update_info.get('current_version', 'Unknown')
                latest_ver = latest['version']
                size_mb = latest.get('size_mb', 0)
                
                reply = QMessageBox.question(
                    self, 
                    "📦 Update Tersedia!",
                    f"Model baru tersedia!\n\n"
                    f"Versi Saat Ini: {current_ver}\n"
                    f"Versi Terbaru: {latest_ver}\n"
                    f"Ukuran: {size_mb} MB\n\n"
                    f"Catatan: {latest.get('release_notes', 'Peningkatan akurasi')}\n\n"
                    f"Download dan install sekarang?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.download_and_install_model()
            else:
                # Already latest
                current_ver = update_info.get('current_version', 'Unknown')
                QMessageBox.information(
                    self, "✅ Model Terbaru",
                    f"Anda sudah menggunakan model terbaru!\n\n"
                    f"Versi: {current_ver}"
                )
        
        except Exception as e:
            checking_msg.close()
            QMessageBox.critical(
                self, "❌ Error",
                f"Terjadi kesalahan:\n\n{str(e)}"
            )
    
    def download_and_install_model(self):
        """Download and install model update."""
        # Show progress dialog
        progress_msg = QMessageBox(self)
        progress_msg.setWindowTitle("📥 Downloading Model")
        progress_msg.setText("Mendownload model baru...\n\n0%")
        progress_msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
        progress_msg.show()
        
        def progress_callback(downloaded, total):
            if total > 0:
                percent = (downloaded / total) * 100
                progress_msg.setText(
                    f"Mendownload model baru...\n\n"
                    f"{percent:.1f}% ({downloaded / (1024*1024):.1f} MB / {total / (1024*1024):.1f} MB)"
                )
                QApplication.processEvents()
        
        try:
            # Download and install
            result = self.model_updater.update_model(progress_callback=progress_callback)
            progress_msg.close()
            
            if result.get('success'):
                QMessageBox.information(
                    self, "✅ Update Berhasil!",
                    f"Model berhasil diupdate!\n\n"
                    f"Versi: {result.get('version')}\n\n"
                    f"Aplikasi akan menggunakan model baru untuk scan berikutnya."
                )
            else:
                QMessageBox.warning(
                    self, "⚠️ Update Gagal",
                    f"Update gagal:\n\n{result.get('message')}"
                )
        
        except Exception as e:
            progress_msg.close()
            QMessageBox.critical(
                self, "❌ Error",
                f"Terjadi kesalahan saat update:\n\n{str(e)}"
            )

    def show_protection_info(self):
        """Show real-time protection status and toggle."""
        # Check if realtime_protection is available
        if not hasattr(self, 'realtime_protection') or self.realtime_protection is None:
            QMessageBox.information(
                self, "🛡️ Perlindungan Real-time",
                "Perlindungan real-time tidak tersedia.\n\n"
                "Aktifkan di config.ini:\n"
                "[RealtimeProtection]\n"
                "enabled = true"
            )
            return
        
        # Check current status
        is_running = self.realtime_protection.is_running()
        stats = self.realtime_protection.get_stats()
        
        # Build status message
        status_text = f"Status: {'🟢 Aktif' if is_running else '🔴 Tidak Aktif'}\n\n"
        
        if is_running:
            status_text += f"📊 Statistik:\n"
            status_text += f"• File dipindai: {stats.get('files_scanned', 0)}\n"
            status_text += f"• Malware terdeteksi: {stats.get('malware_detected', 0)}\n"
            status_text += f"• Folder dimonitor: {stats.get('monitored_paths', 0)}\n"
            status_text += f"• Queue: {stats.get('queue_size', 0)}\n\n"
            
            reply = QMessageBox.question(
                self, "🛡️ Perlindungan Real-time",
                status_text + "Matikan perlindungan real-time?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    self.realtime_protection.stop()
                    QMessageBox.information(
                        self, "✅ Dimatikan",
                        "Perlindungan real-time telah dimatikan."
                    )
                    # Update badge immediately
                    self.update_protection_status()
                except Exception as e:
                    QMessageBox.critical(
                        self, "❌ Error",
                        f"Gagal mematikan perlindungan:\n\n{str(e)}"
                    )
        else:
            reply = QMessageBox.question(
                self, "🛡️ Perlindungan Real-time",
                status_text + 
                "Perlindungan real-time akan:\n"
                "• Monitor semua file baru\n"
                "• Auto-scan untuk malware\n"
                "• Notifikasi jika terdeteksi ancaman\n\n"
                "Aktifkan sekarang?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    # Only start if not already running
                    if not self.realtime_protection.is_running():
                        self.realtime_protection.start()
                        QMessageBox.information(
                            self, "✅ Aktif",
                            "Perlindungan real-time telah diaktifkan!\n\n"
                            "Semua file baru akan dipindai otomatis."
                        )
                        # Update badge immediately
                        self.update_protection_status()
                    else:
                        QMessageBox.information(
                            self, "ℹ️ Info",
                            "Perlindungan real-time sudah aktif!"
                        )
                except Exception as e:
                    QMessageBox.critical(
                        self, "❌ Error",
                        f"Gagal mengaktifkan perlindungan:\n\n{str(e)}"
                    )

    def toggle_realtime_protection(self):
        """Toggle real-time protection ON/OFF."""
        if not hasattr(self, 'realtime_protection') or self.realtime_protection is None:
            QMessageBox.warning(
                self, "⚠️ Tidak Tersedia",
                "Real-time protection tidak tersedia.\n\n"
                "Pastikan fitur diaktifkan di config.ini"
            )
            return
        
        is_running = self.realtime_protection.is_running()
        
        if is_running:
            # Turn OFF
            try:
                self.realtime_protection.stop()
                self.update_protection_status()
                QMessageBox.information(
                    self, "✅ Dimatikan",
                    "Perlindungan real-time telah dimatikan."
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "❌ Error",
                    f"Gagal mematikan:\n\n{str(e)}"
                )
        else:
            # Turn ON
            try:
                if not self.realtime_protection.is_running():
                    self.realtime_protection.start()
                    self.update_protection_status()
                    QMessageBox.information(
                        self, "✅ Aktif",
                        "Perlindungan real-time telah diaktifkan!\n\n"
                        "Semua file baru akan dipindai otomatis."
                    )
            except Exception as e:
                QMessageBox.critical(
                    self, "❌ Error",
                    f"Gagal mengaktifkan:\n\n{str(e)}"
                )

    def update_protection_status(self):
        """Update real-time protection toggle button."""
        if hasattr(self, 'realtime_protection') and self.realtime_protection:
            is_running = self.realtime_protection.is_running()
            
            if is_running:
                # Active - Green toggle
                self.rtp_toggle_btn.setText("ON")
                self.rtp_toggle_btn.setStyleSheet("""
                    QPushButton#toggleButton {
                        background: #32CD32;
                        border: none;
                        border-radius: 17px;
                        color: white;
                        font-size: 12px;
                        font-weight: 700;
                    }
                    QPushButton#toggleButton:hover {
                        background: #28A428;
                    }
                """)
            else:
                # Inactive - Red toggle
                self.rtp_toggle_btn.setText("OFF")
                self.rtp_toggle_btn.setStyleSheet("""
                    QPushButton#toggleButton {
                        background: #FF4444;
                        border: none;
                        border-radius: 17px;
                        color: white;
                        font-size: 12px;
                        font-weight: 700;
                    }
                    QPushButton#toggleButton:hover {
                        background: #FF6666;
                    }
                """)
        else:
            # Not available - Gray toggle
            self.rtp_toggle_btn.setText("N/A")
            self.rtp_toggle_btn.setEnabled(False)
            self.rtp_toggle_btn.setStyleSheet("""
                QPushButton#toggleButton {
                    background: #888888;
                    border: none;
                    border-radius: 17px;
                    color: white;
                    font-size: 12px;
                    font-weight: 700;
                }
            """)


    def resizeEvent(self, event):
        """Handle window resize"""
        super().resizeEvent(event)


        # Update scan dialog geometry
        if self.scan_dialog:
            self.scan_dialog.setGeometry(self.centralWidget().rect())
            if self.scan_dialog.isVisible():
                self.scan_dialog.raise_()
