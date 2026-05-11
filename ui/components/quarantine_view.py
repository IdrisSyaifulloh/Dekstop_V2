"""
Quarantine View - Manage blocked items
Displays items currently in quarantine, allowing restore or permanent delete.
"""
import os
import shutil
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QMessageBox
)
from PySide6.QtCore import Qt
from ui.widgets.glass_card import GlassCard
from ui.styles.figma_theme import Colors, Typography, StyleHelper

class QuarantineView(QWidget):
    """
    Quarantine View component matching Figma design.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dark = True
        self.quarantine_dir = Path.home() / ".Mangodefend" / "Karintina"
        
        # Ensure quarantine directory exists
        if not self.quarantine_dir.exists():
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)
            
        self.setup_ui()
        self.load_quarantine_items()
        
    def setup_ui(self):
        """Build the UI structure."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 32)
        layout.setSpacing(24)

        # Header Section
        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        
        self.title_label = QLabel("Quarantine Manager")
        self.title_label.setStyleSheet(f"color: {self._tp()}; font-size: 28px; font-weight: bold; font-family: {Typography.FONT_FAMILY};")
        
        self.subtitle_label = QLabel("Manage isolated threats to protect your system.")
        self.subtitle_label.setStyleSheet(StyleHelper.muted_body())
        
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet(StyleHelper.pill_button_outline(36))
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_quarantine_items)
        header_layout.addWidget(self.refresh_btn)
        
        self.clear_all_btn = QPushButton("Empty Quarantine")
        self.clear_all_btn.setStyleSheet(StyleHelper.pill_button_danger(36))
        self.clear_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_all_btn.clicked.connect(self.empty_quarantine)
        header_layout.addWidget(self.clear_all_btn)
        
        layout.addLayout(header_layout)

        # Card Content
        self.card = GlassCard()
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)
        
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Date", "Original File", "Status", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setStyleSheet(self._table_style())
        
        card_layout.addWidget(self.table)
        layout.addWidget(self.card)
        
    def _tp(self) -> str:
        return Colors.DARK_TEXT_PRIMARY if self.is_dark else Colors.LIGHT_TEXT_PRIMARY
        
    def _card_bg(self) -> str:
        return "rgba(255, 255, 255, 0.05)" if self.is_dark else "rgba(255, 255, 255, 0.6)"
        
    def _card_border(self) -> str:
        return "rgba(255, 165, 0, 0.3)" if self.is_dark else Colors.LIGHT_BORDER

    def _table_style(self):
        bg = "transparent"
        text = self._tp()
        header_bg = "rgba(255, 165, 0, 0.1)" if self.is_dark else "rgba(255, 165, 0, 0.05)"
        return f"""
            QTableWidget {{
                background-color: {bg};
                color: {text};
                border: none;
                font-family: {Typography.FONT_FAMILY};
                font-size: 13px;
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {Colors.ORANGE_500};
                padding: 10px;
                border: none;
                font-weight: bold;
                font-family: {Typography.FONT_FAMILY};
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 12px 10px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }}
            QTableWidget::item:selected {{
                background-color: rgba(255, 165, 0, 0.1);
            }}
        """

    def load_quarantine_items(self):
        """Load items from the quarantine directory into the table."""
        self.table.setRowCount(0)
        
        if not self.quarantine_dir.exists():
            return
            
        files = []
        for file_path in self.quarantine_dir.glob("*.quarantined"):
            # Format: timestamp_filename.quarantined
            parts = file_path.name.split('_', 1)
            if len(parts) == 2:
                timestamp_str = parts[0]
                original_name = parts[1].replace(".quarantined", "")
                try:
                    ts = float(timestamp_str)
                    date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    date_str = "Unknown"
                    original_name = file_path.name
                
                files.append({
                    "path": str(file_path),
                    "date": date_str,
                    "name": original_name
                })
        
        # Sort newest first
        files.sort(key=lambda x: x["date"], reverse=True)
        
        self.table.setRowCount(len(files))
        for row, item in enumerate(files):
            # Date
            date_item = QTableWidgetItem(item["date"])
            self.table.setItem(row, 0, date_item)
            
            # Name
            name_item = QTableWidgetItem(item["name"])
            self.table.setItem(row, 1, name_item)
            
            # Status Badge
            status_lbl = QLabel("Quarantined")
            status_lbl.setStyleSheet(StyleHelper.tag_badge())
            status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            status_widget = QWidget()
            s_layout = QHBoxLayout(status_widget)
            s_layout.setContentsMargins(10, 4, 10, 4)
            s_layout.addWidget(status_lbl)
            self.table.setCellWidget(row, 2, status_widget)
            
            # Actions
            action_widget = QWidget()
            a_layout = QHBoxLayout(action_widget)
            a_layout.setContentsMargins(10, 2, 10, 2)
            a_layout.setSpacing(8)
            
            btn_restore = QPushButton("Restore")
            btn_restore.setStyleSheet(StyleHelper.pill_button_outline(24))
            btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_restore.clicked.connect(lambda checked, p=item["path"], n=item["name"]: self.restore_file(p, n))
            
            btn_del = QPushButton("Delete")
            btn_del.setStyleSheet(StyleHelper.pill_button_danger(24))
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.clicked.connect(lambda checked, p=item["path"]: self.delete_file(p))
            
            a_layout.addWidget(btn_restore)
            a_layout.addWidget(btn_del)
            a_layout.addStretch()
            self.table.setCellWidget(row, 3, action_widget)

    def delete_file(self, filepath: str):
        try:
            os.remove(filepath)
            self.load_quarantine_items()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to delete file: {e}")

    def restore_file(self, filepath: str, original_name: str):
        # Restore to Desktop by default since we don't save the original path
        desktop_dir = Path.home() / "Desktop" / "MangoDefend_Restored"
        if not desktop_dir.exists():
            desktop_dir.mkdir(parents=True, exist_ok=True)
            
        target_path = desktop_dir / original_name
        
        reply = QMessageBox.question(
            self, "Restore File", 
            f"This will move the file to:\n{target_path}\n\nAre you sure you want to restore this potentially dangerous file?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                shutil.move(filepath, str(target_path))
                QMessageBox.information(self, "Success", f"File restored to {target_path}")
                self.load_quarantine_items()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to restore file: {e}")
                
    def empty_quarantine(self):
        reply = QMessageBox.question(
            self, "Empty Quarantine", 
            "Are you sure you want to permanently delete all isolated files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for file_path in self.quarantine_dir.glob("*.quarantined"):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            self.load_quarantine_items()
            
    def set_theme(self, is_dark: bool):
        """Update theme."""
        self.is_dark = is_dark
        self.title_label.setStyleSheet(f"color: {self._tp()}; font-size: 28px; font-weight: bold; font-family: {Typography.FONT_FAMILY};")
        self.table.setStyleSheet(self._table_style())
        self.card.setStyleSheet(f"""
            QFrame.glassCard {{
                background: {self._card_bg()};
                border: 1px solid {self._card_border()};
                border-radius: 24px;
            }}
        """)
