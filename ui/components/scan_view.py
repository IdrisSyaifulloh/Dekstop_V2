"""
Scan View - File, Folder, and Device Scanner Interface
Interface for scanning files, folders, or entire device for malware.
"""
import os
import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QFileDialog, QListWidget,
    QListWidgetItem, QScrollArea, QGridLayout, QProgressBar,
)
from PySide6.QtCore import Qt, Signal

from ui.widgets import SoftCard
from ui.styles.figma_theme import Colors, Typography, StyleHelper


class ScanView(QWidget):
    """
    File scanner view with support for file, folder, and full device scanning.

    Signals:
        scan_requested(str): Emitted when a single file is selected for scanning.
        folder_scan_requested(str): Emitted when a folder is selected for scanning.
        device_scan_requested: Emitted when full-device scan is requested.
    """

    scan_requested = Signal(str)
    folder_scan_requested = Signal(str)
    device_scan_requested = Signal()

    def __init__(self, parent=None):
        """Initialize label registries and build the UI."""
        super().__init__(parent)
        self.is_dark = True
        self._scroll_ref = None

        # Populated in setup_ui() and updated by _apply_theme()
        self._primary_labels: list[QLabel] = []
        self._muted_labels: list[QLabel] = []
        self._soft_cards: list[SoftCard] = []

        self.setup_ui()

    # ------------------------------------------------------------------
    # THEME HELPERS
    # ------------------------------------------------------------------

    def _tp(self) -> str:
        """Return primary text color for the current theme."""
        return Colors.DARK_TEXT_PRIMARY if self.is_dark else Colors.LIGHT_TEXT_PRIMARY

    def _tm(self) -> str:
        """Return muted text color for the current theme."""
        return Colors.DARK_TEXT_MUTED if self.is_dark else Colors.LIGHT_TEXT_MUTED

    def _card_bg(self) -> str:
        """Return card background color for the current theme."""
        return "rgba(255,255,255,0.04)" if self.is_dark else "rgba(0,0,0,0.04)"

    def _card_border(self) -> str:
        """Return card border color for the current theme."""
        return "rgba(255,255,255,0.08)" if self.is_dark else "rgba(0,0,0,0.08)"

    def _reg_p(self, lbl: QLabel) -> QLabel:
        """Register a label as primary-color and return it for inline use."""
        self._primary_labels.append(lbl)
        return lbl

    def _reg_m(self, lbl: QLabel) -> QLabel:
        """Register a label as muted-color and return it for inline use."""
        self._muted_labels.append(lbl)
        return lbl

    # ------------------------------------------------------------------
    # BUILD UI
    # ------------------------------------------------------------------

    def setup_ui(self):
        """Construct the full scan view inside a scroll area."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_ref = scroll

        content = QWidget()
        content.setStyleSheet("background:transparent;")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 32)
        layout.setSpacing(24)

        # Header card
        header_card = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_500)
        self._soft_cards.append(header_card)
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(40, 36, 40, 36)
        header_layout.setSpacing(16)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = self._reg_p(QLabel("Smart Malware Scanner"))
        title.setStyleSheet(f"""
            color:{self._tp()};font-size:26px;font-weight:bold;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)

        desc = self._reg_m(QLabel(
            "Pilih file, folder, atau scan seluruh perangkat\nuntuk mendeteksi malware menggunakan AI"
        ))
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet(f"""
            color:{self._tm()};font-size:13px;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        header_layout.addWidget(desc)

        layout.addWidget(header_card)

        # Scan option cards (file / folder / device)
        options_grid = QGridLayout()
        options_grid.setSpacing(16)

        options_grid.addWidget(
            self._create_scan_option(
                icon="", title="Scan File",
                desc="Pilih satu file untuk\ndipindai secara mendalam",
                btn_text="Pilih File", accent=Colors.ORANGE_500,
                callback=self._browse_file,
            ),
            0, 0,
        )
        options_grid.addWidget(
            self._create_scan_option(
                icon="", title="Folder Scanner",
                desc="Pindai semua file dalam\nfolder yang dipilih",
                btn_text="Pilih Folder", accent=Colors.ORANGE_300,
                callback=self._browse_folder,
            ),
            0, 1,
        )
        options_grid.addWidget(
            self._create_scan_option(
                icon="", title="Scan Perangkat",
                desc="Scan seluruh file berbahaya\ndi seluruh perangkat Anda",
                btn_text="Mulai Full Scan", accent=Colors.RED_500,
                callback=self._start_device_scan,
            ),
            0, 2,
        )

        layout.addLayout(options_grid)

        # Inline progress panel (hidden until a scan starts)
        self._progress_panel = self._create_progress_panel()
        self._progress_panel.hide()
        layout.addWidget(self._progress_panel)

        # Scan history section
        layout.addWidget(self._create_history_section())

        layout.addStretch()

        scroll.setWidget(content)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _create_scan_option(
        self, icon: str, title: str, desc: str,
        btn_text: str, accent: str, callback,
    ) -> SoftCard:
        """Create a scan option card with icon, title, description, and trigger button."""
        card = SoftCard(is_dark=self.is_dark, accent=accent)
        self._soft_cards.append(card)
        card.set_interactive(True)
        card.clicked.connect(callback)
        card.setToolTip(f"Buka aksi: {title}")
        card.setMinimumHeight(220)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size:36px;background:transparent;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(icon_lbl)

        title_lbl = self._reg_p(QLabel(title))
        title_lbl.setStyleSheet(f"""
            color:{self._tp()};font-size:16px;font-weight:bold;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_lbl)

        desc_lbl = self._reg_m(QLabel(desc))
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setStyleSheet(f"""
            color:{self._tm()};font-size:11px;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        card_layout.addWidget(desc_lbl)

        card_layout.addSpacing(4)

        btn = QPushButton(btn_text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumWidth(160)
        btn.setFixedHeight(42)
        btn.setStyleSheet(StyleHelper.pill_button_outline(42))
        btn.clicked.connect(callback)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.addWidget(btn)
        card_layout.addLayout(btn_row)

        return card

    def _create_history_section(self) -> SoftCard:
        """Create the scan history card containing a scrollable list of past results."""
        card = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_400)
        self._soft_cards.append(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(8)
        ht = self._reg_p(QLabel("Riwayat Pemindaian"))
        ht.setStyleSheet(f"""
            color:{self._tp()};font-size:16px;font-weight:bold;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        header.addWidget(ht)
        header.addStretch()
        layout.addLayout(header)

        self.history_list = QListWidget()
        self._history_list_ref = self.history_list
        self.history_list.setMinimumHeight(120)
        self.history_list.addItem("Belum ada riwayat pemindaian")
        layout.addWidget(self.history_list)
        self._apply_history_list_theme()

        return card

    def _create_progress_panel(self) -> SoftCard:
        """Create the inline scanning progress panel shown during active scans."""
        card = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_500)
        self._soft_cards.append(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(12)

        # Header row: title + cancel button
        header = QHBoxLayout()
        self._scan_title_lbl = self._reg_p(QLabel("Memindai File..."))
        self._scan_title_lbl.setStyleSheet(f"""
            color:{self._tp()};font-size:15px;font-weight:bold;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        header.addWidget(self._scan_title_lbl)
        header.addStretch()

        self._cancel_scan_btn = QPushButton("Batalkan")
        self._cancel_scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_scan_btn.setFixedHeight(34)
        self._cancel_scan_btn.setMinimumWidth(100)
        self._cancel_scan_btn.setStyleSheet(StyleHelper.pill_button_outline(34))
        self._cancel_scan_btn.clicked.connect(self._on_cancel_scan_clicked)
        header.addWidget(self._cancel_scan_btn)

        layout.addLayout(header)

        self._scan_status_lbl = self._reg_m(QLabel("Menyiapkan..."))
        self._scan_status_lbl.setWordWrap(True)
        self._scan_status_lbl.setStyleSheet(f"""
            color:{self._tm()};font-size:12px;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        layout.addWidget(self._scan_status_lbl)

        self._scan_progress_bar = QProgressBar()
        self._scan_progress_bar.setRange(0, 100)
        self._scan_progress_bar.setValue(0)
        self._scan_progress_bar.setTextVisible(True)
        self._scan_progress_bar.setFixedHeight(20)
        self._apply_progress_bar_theme()
        layout.addWidget(self._scan_progress_bar)

        return card

    # ------------------------------------------------------------------
    # PROGRESS PANEL PUBLIC API
    # ------------------------------------------------------------------

    _cancel_scan_callback = None

    def set_cancel_scan_callback(self, callback):
        """Register a callback invoked when the user clicks the cancel button."""
        self._cancel_scan_callback = callback

    def _on_cancel_scan_clicked(self):
        """Forward cancel click to the registered callback if present."""
        if self._cancel_scan_callback:
            self._cancel_scan_callback()

    def show_scan_progress(self, title: str = "Memindai File..."):
        """Show the inline progress panel and reset its state."""
        self._scan_title_lbl.setText(title)
        self._scan_progress_bar.setValue(0)
        self._scan_status_lbl.setText("Menyiapkan...")
        self._progress_panel.show()

    def update_scan_progress(self, value: int, message: str):
        """Update progress bar value and status text during an active scan."""
        self._scan_progress_bar.setValue(value)
        self._scan_status_lbl.setText(message)

    def hide_scan_progress(self):
        """Hide the inline progress panel when scanning finishes or is cancelled."""
        self._progress_panel.hide()

    def _apply_progress_bar_theme(self):
        """Apply accent-colored styles to the progress bar widget."""
        accent = Colors.ORANGE_500
        bg = "rgba(255,255,255,0.1)" if self.is_dark else "rgba(0,0,0,0.06)"
        text_color = self._tp()
        self._scan_progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {accent};
                border-radius: 10px;
                background: {bg};
                color: {text_color};
                text-align: center;
                font-size: 11px;
                font-weight: 600;
            }}
            QProgressBar::chunk {{
                background: {accent};
                border-radius: 8px;
            }}
        """)

    # ------------------------------------------------------------------
    # SCAN ACTIONS
    # ------------------------------------------------------------------

    def _browse_file(self):
        """Open a file browser dialog and emit scan_requested with the chosen path."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Pilih File untuk Dipindai", "", "All Files (*.*)"
        )
        if file_path:
            self.scan_requested.emit(file_path)

    def _browse_folder(self):
        """Open a folder browser dialog and emit folder_scan_requested with the chosen path."""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Pilih Folder untuk Dipindai", ""
        )
        if folder_path:
            self.folder_scan_requested.emit(folder_path)

    def _start_device_scan(self):
        """Emit device_scan_requested to trigger a full-device scan."""
        self.device_scan_requested.emit()

    # ------------------------------------------------------------------
    # HISTORY
    # ------------------------------------------------------------------

    def add_to_history(self, filename: str, result: str, timestamp: str, file_path: str = ""):
        """Prepend a scan result to the history list, capping at 20 entries."""
        if self.history_list.count() == 1:
            first = self.history_list.item(0)
            if first and first.text() == "Belum ada riwayat pemindaian":
                self.history_list.clear()

        icon = "" if result == "Benign" else ""
        path_line = f"\nPath: {file_path}" if file_path else ""
        item_text = f"{icon} {filename}\n{result} • {timestamp}{path_line}"
        item = QListWidgetItem(item_text)
        if file_path:
            item.setToolTip(file_path)
        self.history_list.insertItem(0, item)

        while self.history_list.count() > 20:
            self.history_list.takeItem(self.history_list.count() - 1)

    # ------------------------------------------------------------------
    # THEME
    # ------------------------------------------------------------------

    def set_theme(self, is_dark: bool):
        """Switch theme and redraw all styled widgets."""
        self.is_dark = is_dark
        self._apply_theme()

    def _apply_theme(self):
        """Apply current theme colors to all registered labels, cards, and widgets."""
        tp = self._tp()
        tm = self._tm()

        for lbl in self._primary_labels:
            lbl.setStyleSheet(re.sub(r"color:[^;]+;", f"color:{tp};", lbl.styleSheet(), count=1))

        for lbl in self._muted_labels:
            lbl.setStyleSheet(re.sub(r"color:[^;]+;", f"color:{tm};", lbl.styleSheet(), count=1))

        for card in self._soft_cards:
            card.set_theme(self.is_dark)

        self._apply_history_list_theme()
        if hasattr(self, "_scan_progress_bar"):
            self._apply_progress_bar_theme()

    def _apply_history_list_theme(self):
        """Apply theme to the history QListWidget."""
        tp = self._tp()
        card_bg = self._card_bg()
        card_border = self._card_border()
        hover_bg = "rgba(255,255,255,0.07)" if self.is_dark else "rgba(0,0,0,0.06)"
        if hasattr(self, "history_list"):
            self.history_list.setStyleSheet(f"""
                QListWidget{{
                    background:transparent;border:none;
                    color:{tp};font-size:13px;
                }}
                QListWidget::item{{
                    background:{card_bg};
                    border:1px solid {card_border};
                    border-radius:10px;
                    padding:12px;margin-bottom:6px;
                }}
                QListWidget::item:hover{{
                    background:{hover_bg};
                    border:1px solid rgba(255,165,0,0.3);
                }}
            """)
