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
    QPushButton, QMessageBox,
)
from PySide6.QtCore import Qt

from ui.widgets import SoftCard
from ui.styles.figma_theme import Colors, Typography, StyleHelper


class QuarantineView(QWidget):
    """Quarantine manager that lists, restores, and deletes quarantined files."""

    def __init__(self, parent=None):
        """Initialize quarantine directory and build the UI."""
        super().__init__(parent)
        self.is_dark = True
        self.quarantine_dir = Path.home() / ".Mangodefend" / "Karintina"
        self._soft_cards: list[SoftCard] = []

        # Create quarantine directory if it does not exist yet
        if not self.quarantine_dir.exists():
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        self.setup_ui()
        self.load_quarantine_items()

    # ------------------------------------------------------------------
    # BUILD UI
    # ------------------------------------------------------------------

    def setup_ui(self):
        """Build the header, action buttons, and quarantine table."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 32)
        layout.setSpacing(24)

        # Header
        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)

        self.title_label = QLabel("Quarantine Manager")
        self.title_label.setStyleSheet(
            f"color: {self._tp()}; font-size: 28px; font-weight: bold;"
            f" font-family: {Typography.FONT_FAMILY};"
        )

        self.subtitle_label = QLabel("Manage isolated threats to protect your system.")
        self.subtitle_label.setStyleSheet(StyleHelper.muted_body())

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setFixedSize(52, 40)
        self.refresh_btn.setStyleSheet(StyleHelper.pill_button_outline(36))
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setToolTip("Refresh daftar karantina")
        self.refresh_btn.clicked.connect(self.load_quarantine_items)
        header_layout.addWidget(self.refresh_btn)

        self.restore_all_btn = QPushButton("Restore All")
        self.restore_all_btn.setFixedHeight(40)
        self.restore_all_btn.setMinimumWidth(142)
        self.restore_all_btn.setStyleSheet(StyleHelper.pill_button_outline(36))
        self.restore_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.restore_all_btn.setToolTip("Pulihkan semua file dari karantina")
        self.restore_all_btn.clicked.connect(self.restore_all_files)
        header_layout.addWidget(self.restore_all_btn)

        self.clear_all_btn = QPushButton("Empty Quarantine")
        self.clear_all_btn.setFixedHeight(40)
        self.clear_all_btn.setMinimumWidth(168)
        self.clear_all_btn.setStyleSheet(StyleHelper.pill_button_danger(36))
        self.clear_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_all_btn.clicked.connect(self.empty_quarantine)
        header_layout.addWidget(self.clear_all_btn)

        layout.addLayout(header_layout)

        # Table card
        self.card = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_400)
        self._soft_cards.append(self.card)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Date", "Original File", "Status", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 230)
        self.table.verticalHeader().setDefaultSectionSize(56)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setStyleSheet(self._table_style())

        card_layout.addWidget(self.table)
        layout.addWidget(self.card)

    # ------------------------------------------------------------------
    # THEME HELPERS
    # ------------------------------------------------------------------

    def _tp(self) -> str:
        """Return primary text color for the current theme."""
        return Colors.DARK_TEXT_PRIMARY if self.is_dark else Colors.LIGHT_TEXT_PRIMARY

    def _card_bg(self) -> str:
        """Return card background color for the current theme."""
        return "rgba(255, 255, 255, 0.05)" if self.is_dark else "rgba(255, 255, 255, 0.6)"

    def _card_border(self) -> str:
        """Return card border color for the current theme."""
        return "rgba(255, 165, 0, 0.3)" if self.is_dark else Colors.LIGHT_BORDER

    def _table_style(self) -> str:
        """Build and return the full QSS stylesheet for the quarantine table."""
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

    def _action_button_style(self, danger: bool = False) -> str:
        """Return compact, table-safe action button styling."""
        bg = Colors.RED_500 if danger else Colors.ORANGE_500
        bg_hover = Colors.RED_600 if danger else Colors.ORANGE_400
        border = Colors.RED_600 if danger else Colors.ORANGE_500
        return f"""
            QPushButton {{
                background: {bg};
                color: white;
                border: 1px solid {border};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 700;
                font-family: {Typography.FONT_FAMILY};
            }}
            QPushButton:hover {{
                background: {bg_hover};
                border-color: {bg_hover};
            }}
            QPushButton:pressed {{
                background: {border};
            }}
        """

    # ------------------------------------------------------------------
    # DATA LOADING
    # ------------------------------------------------------------------

    def load_quarantine_items(self):
        """Scan the quarantine directory and populate the table with current items."""
        self.table.setRowCount(0)

        if not self.quarantine_dir.exists():
            return

        files = []
        for file_path in self.quarantine_dir.glob("*.quarantined"):
            # Expected filename format: <timestamp>_<original_name>.quarantined
            parts = file_path.name.split("_", 1)
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
                    "name": original_name,
                })

        # Show newest entries first
        files.sort(key=lambda x: x["date"], reverse=True)

        self.table.setRowCount(len(files))
        for row, item in enumerate(files):
            self.table.setRowHeight(row, 56)
            self.table.setItem(row, 0, QTableWidgetItem(item["date"]))
            self.table.setItem(row, 1, QTableWidgetItem(item["name"]))

            # Status badge widget
            status_lbl = QLabel("Quarantined")
            status_lbl.setStyleSheet(StyleHelper.tag_badge())
            status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            status_widget = QWidget()
            s_layout = QHBoxLayout(status_widget)
            s_layout.setContentsMargins(10, 4, 10, 4)
            s_layout.addWidget(status_lbl)
            self.table.setCellWidget(row, 2, status_widget)

            # Action buttons widget
            action_widget = QWidget()
            a_layout = QHBoxLayout(action_widget)
            a_layout.setContentsMargins(8, 8, 8, 8)
            a_layout.setSpacing(8)

            btn_restore = QPushButton("Restore")
            btn_restore.setFixedSize(92, 34)
            btn_restore.setStyleSheet(self._action_button_style())
            btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_restore.clicked.connect(
                lambda checked, p=item["path"], n=item["name"]: self.restore_file(p, n)
            )

            btn_del = QPushButton("Delete")
            btn_del.setFixedSize(86, 34)
            btn_del.setStyleSheet(self._action_button_style(danger=True))
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.clicked.connect(lambda checked, p=item["path"]: self.delete_file(p))

            a_layout.addWidget(btn_restore)
            a_layout.addWidget(btn_del)
            self.table.setCellWidget(row, 3, action_widget)

    # ------------------------------------------------------------------
    # FILE ACTIONS
    # ------------------------------------------------------------------

    def delete_file(self, filepath: str):
        """Permanently remove a quarantined file and refresh the table."""
        try:
            os.remove(filepath)
            self.load_quarantine_items()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to delete file: {e}")

    def restore_file(self, filepath: str, original_name: str):
        """Move a quarantined file back to the Desktop after user confirmation."""
        desktop_dir = Path.home() / "Desktop" / "MangoDefend_Restored"
        if not desktop_dir.exists():
            desktop_dir.mkdir(parents=True, exist_ok=True)

        target_path = desktop_dir / original_name

        reply = QMessageBox.question(
            self,
            "Restore File",
            f"This will move the file to:\n{target_path}\n\n"
            "Are you sure you want to restore this potentially dangerous file?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                shutil.move(filepath, str(target_path))
                QMessageBox.information(self, "Success", f"File restored to {target_path}")
                self.load_quarantine_items()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to restore file: {e}")

    def restore_all_files(self):
        """Move all quarantined files back to the Desktop restore folder."""
        files = list(self.quarantine_dir.glob("*.quarantined"))
        if not files:
            QMessageBox.information(self, "Restore All", "Tidak ada file di karantina.")
            return

        desktop_dir = Path.home() / "Desktop" / "MangoDefend_Restored"
        desktop_dir.mkdir(parents=True, exist_ok=True)

        reply = QMessageBox.question(
            self,
            "Restore All Files",
            f"Ini akan memulihkan {len(files)} file ke:\n{desktop_dir}\n\n"
            "File karantina mungkin berbahaya. Lanjutkan?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success, failed = 0, 0
        for file_path in files:
            parts = file_path.name.split("_", 1)
            original_name = parts[1].replace(".quarantined", "") if len(parts) == 2 else file_path.stem
            target_path = desktop_dir / original_name

            if target_path.exists():
                stem = target_path.stem
                suffix = target_path.suffix
                counter = 1
                while target_path.exists():
                    target_path = desktop_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

            try:
                shutil.move(str(file_path), str(target_path))
                success += 1
            except Exception:
                failed += 1

        self.load_quarantine_items()
        message = f"Berhasil memulihkan {success} file ke:\n{desktop_dir}"
        if failed:
            message += f"\n\nGagal: {failed} file"
        QMessageBox.information(self, "Restore All Selesai", message)

    def empty_quarantine(self):
        """Delete all quarantined files after user confirmation."""
        reply = QMessageBox.question(
            self,
            "Empty Quarantine",
            "Are you sure you want to permanently delete all isolated files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            for file_path in self.quarantine_dir.glob("*.quarantined"):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            self.load_quarantine_items()

    # ------------------------------------------------------------------
    # THEME
    # ------------------------------------------------------------------

    def set_theme(self, is_dark: bool):
        """Switch theme and reapply styles to the title label and table."""
        self.is_dark = is_dark
        self.title_label.setStyleSheet(
            f"color: {self._tp()}; font-size: 28px; font-weight: bold;"
            f" font-family: {Typography.FONT_FAMILY};"
        )
        self.table.setStyleSheet(self._table_style())
        for card in self._soft_cards:
            card.set_theme(self.is_dark)
