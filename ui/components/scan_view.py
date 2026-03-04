"""
Scan View - File, Folder, and Device Scanner Interface
Interface for scanning files, folders, or entire device for malware
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QFileDialog, QListWidget,
    QListWidgetItem, QScrollArea, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from ui.widgets.glass_card import GlassCard
from ui.styles.figma_theme import Colors, Typography


class ScanView(QWidget):
    """
    File scanner view with support for file, folder, and full device scanning.
    
    Signals:
        scan_requested(str): Scan a single file
        folder_scan_requested(str): Scan all files in a folder
        device_scan_requested: Scan entire device
    """
    
    scan_requested = Signal(str)
    folder_scan_requested = Signal(str)
    device_scan_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dark = True
        self.setAcceptDrops(True)
        self.setup_ui()
    
    def setup_ui(self):
        """Build scan view UI"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        
        content = QWidget()
        content.setStyleSheet("background:transparent;")
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 32)
        layout.setSpacing(24)
        
        # ===== HEADER CARD =====
        header_card = GlassCard()
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(40, 36, 40, 36)
        header_layout.setSpacing(16)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # TEXTED
        title = QLabel("Smart Malware Scanner")
        title.setStyleSheet(f"""
            color:white;font-size:26px;font-weight:bold;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)
        
        desc = QLabel("Pilih file, folder, atau scan seluruh perangkat\nuntuk mendeteksi malware menggunakan AI")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet(f"""
            color:{Colors.DARK_TEXT_MUTED};font-size:13px;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        header_layout.addWidget(desc)
        
        layout.addWidget(header_card)
        
        # ===== SCAN OPTIONS (3 cards) =====
        options_grid = QGridLayout()
        options_grid.setSpacing(16)
        
        # File scan card
        file_card = self._create_scan_option(
            icon="📄",
            title="Scan File",
            desc="Pilih satu file untuk\ndipindai secara mendalam",
            btn_text="📁  Pilih File",
            accent="rgba(255,165,0,1)",
            callback=self._browse_file
        )
        options_grid.addWidget(file_card, 0, 0)
        
        # Folder scan card
        folder_card = self._create_scan_option(
            icon="📂",
            title="Scan Folder",
            desc="Pindai semua file dalam\nfolder yang dipilih",
            btn_text="📂  Pilih Folder",
            accent="rgba(139,92,246,1)",
            callback=self._browse_folder
        )
        options_grid.addWidget(folder_card, 0, 1)
        
        # Device scan card
        device_card = self._create_scan_option(
            icon="💻",
            title="Scan Perangkat",
            desc="Scan seluruh file berbahaya\ndi seluruh perangkat Anda",
            btn_text="🖥️  Mulai Full Scan",
            accent="rgba(255,107,53,1)",
            callback=self._start_device_scan
        )
        options_grid.addWidget(device_card, 0, 2)
        
        layout.addLayout(options_grid)
        
        # ===== DRAG & DROP AREA =====
        drop_area = QFrame()
        drop_area.setMinimumHeight(80)
        drop_area.setStyleSheet(f"""
            QFrame{{
                background:rgba(255,255,255,0.02);
                border:2px dashed rgba(255,255,255,0.1);
                border-radius:16px;
            }}
        """)
        drop_layout = QVBoxLayout(drop_area)
        drop_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        drop_text = QLabel("Atau drag & drop file di sini")
        drop_text.setStyleSheet(f"""
            color:{Colors.DARK_TEXT_MUTED};font-size:13px;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        drop_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(drop_text)
        
        layout.addWidget(drop_area)
        
        # ===== SCAN HISTORY =====
        history_card = self._create_history_section()
        layout.addWidget(history_card)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def _create_scan_option(self, icon: str, title: str, desc: str,
                            btn_text: str, accent: str, callback) -> GlassCard:
        """Create a scan option card."""
        card = GlassCard()
        card.setMinimumHeight(220)
        
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 24, 24, 24)
        cl.setSpacing(12)
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon
        ic = QLabel(icon)
        ic.setStyleSheet("font-size:36px;background:transparent;")
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(ic)
        
        # Title
        tl = QLabel(title)
        tl.setStyleSheet(f"""
            color:white;font-size:16px;font-weight:bold;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        tl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(tl)
        
        # Description
        dl = QLabel(desc)
        dl.setWordWrap(True)
        dl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dl.setStyleSheet(f"""
            color:{Colors.DARK_TEXT_MUTED};font-size:11px;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        cl.addWidget(dl)
        
        cl.addSpacing(4)
        
        # Button
        btn = QPushButton(btn_text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumWidth(160)
        btn.setFixedHeight(42)
         
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 165, 0, 0.15);
                border: 1px solid rgba(255, 165, 0, 0.4);
                border-radius: 14px;
                padding: 10px 20px;
                color: {Colors.ORANGE_400};
                font-weight: 600;
                font-size: 13px;
                font-size: 14px;
                font-family: {Typography.FONT_FAMILY};
            }}
            QPushButton:hover {{
                background: rgba(255, 165, 0, 0.25);
                border: 1px solid rgba(255, 165, 0, 0.6);
            }}
            QPushButton:pressed {{
                background: rgba(255, 165, 0, 0.35);
            }}  

        """) 
        btn.clicked.connect(callback)
        
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.addWidget(btn)
        cl.addLayout(btn_row)
        
        return card
    
    def _create_history_section(self) -> GlassCard:
        """Create scan history list."""
        card = GlassCard()
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(14)
        
        header = QHBoxLayout()
        header.setSpacing(8)
        ht = QLabel("Riwayat Pemindaian")
        ht.setStyleSheet(f"""
            color:white;font-size:16px;font-weight:bold;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        header.addWidget(ht)
        header.addStretch()
        layout.addLayout(header)
        
        self.history_list = QListWidget()
        self.history_list.setStyleSheet(f"""
            QListWidget{{
                background:transparent;border:none;
                color:white;font-size:13px;
            }}
            QListWidget::item{{
                background:rgba(255,255,255,0.04);
                border:1px solid rgba(255,255,255,0.08);
                border-radius:10px;
                padding:12px;margin-bottom:6px;
            }}
            QListWidget::item:hover{{
                background:rgba(255,255,255,0.07);
                border:1px solid rgba(255,165,0,0.3);
            }}
        """)
        self.history_list.setMinimumHeight(120)
        self.history_list.addItem("Belum ada riwayat pemindaian")
        layout.addWidget(self.history_list)
        
        return card
    
    # ── Actions ──
    
    def _browse_file(self):
        """Open file browser dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Pilih File untuk Dipindai", "", "All Files (*.*)"
        )
        if file_path:
            self.scan_requested.emit(file_path)
    
    def _browse_folder(self):
        """Open folder browser dialog"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Pilih Folder untuk Dipindai", ""
        )
        if folder_path:
            self.folder_scan_requested.emit(folder_path)
    
    def _start_device_scan(self):
        """Start full device scan"""
        self.device_scan_requested.emit()
    
    # ── Drag & Drop ──
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                import os
                if os.path.isdir(path):
                    self.folder_scan_requested.emit(path)
                else:
                    self.scan_requested.emit(path)
                event.acceptProposedAction()
    
    # ── History ──
    
    def add_to_history(self, filename: str, result: str, timestamp: str):
        """Add scan result to history"""
        if self.history_list.count() == 1:
            first = self.history_list.item(0)
            if first and first.text() == "Belum ada riwayat pemindaian":
                self.history_list.clear()
        
        icon = "" if result == "Benign" else ""
        item_text = f"{icon} {filename}\n{result} • {timestamp}"
        item = QListWidgetItem(item_text)
        self.history_list.insertItem(0, item)
        
        while self.history_list.count() > 20:
            self.history_list.takeItem(self.history_list.count() - 1)
    
    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
