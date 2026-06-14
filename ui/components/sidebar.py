"""
Sidebar Navigation Component
Modern sidebar with logo, navigation tabs, and bottom controls.
"""
import os
import sys

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QButtonGroup, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFont

from ui.widgets import SoftCard
from ui.styles.figma_theme import Colors


def _asset(relative: str) -> str:
    """Resolve asset path for both dev and PyInstaller frozen mode."""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        # sidebar.py lives in ui/components/ — go up 2 levels to app root
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, relative)


class Sidebar(QWidget):
    """
    Modern sidebar navigation matching Figma design.

    Features:
    - Logo section with branding
    - Protection status badge
    - 5 navigation tabs
    - Threats counter card
    - Theme toggle button

    Signals:
        tab_changed(str): Emitted when a navigation tab is clicked.
        theme_toggled(bool): Emitted when the theme toggle button is clicked.
    """

    tab_changed = Signal(str)    # tab_id: 'dashboard' | 'scan' | 'protection' | 'quarantine' | 'update'
    theme_toggled = Signal(bool) # is_dark

    def __init__(self, is_dark: bool = True, parent=None):
        """Set fixed width, initial theme, and build the sidebar."""
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(264)
        self.is_dark = is_dark
        self.threats_count = 0

        self.setup_ui()

    # ------------------------------------------------------------------
    # BUILD UI
    # ------------------------------------------------------------------

    def setup_ui(self):
        """Assemble all sidebar sections into the main layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(self._create_logo_section())
        layout.addSpacing(12)
        layout.addWidget(self._create_status_badge())
        layout.addSpacing(16)
        layout.addLayout(self._create_navigation())
        layout.addLayout(self._create_bottom_section())
        layout.addStretch()

    def _create_logo_section(self) -> QWidget:
        """Build the logo area with app icon and brand name."""
        container = QWidget()
        container.setMinimumHeight(64)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        logo_wrap = QWidget()
        logo_wrap.setFixedSize(56, 56)
        logo_wrap.setStyleSheet("background: transparent;")
        logo_wrap_layout = QVBoxLayout(logo_wrap)
        logo_wrap_layout.setContentsMargins(4, 4, 4, 4)
        logo_wrap_layout.setSpacing(0)
        logo_wrap_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_path = _asset(os.path.join("assets", "mango_icon.png"))
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            scaled = pixmap.scaled(
                42, 42,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_label.setPixmap(scaled)
        else:
            logo_label.setStyleSheet("font-size: 48px;")

        logo_label.setFixedSize(44, 44)
        logo_wrap_layout.addWidget(logo_label)
        layout.addWidget(logo_wrap)

        text_container = QWidget()
        text_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        text_container.setMinimumWidth(0)
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        title = QLabel("MANGO DEFEND")
        title.setObjectName("logoTitle")
        title.setWordWrap(False)
        text_layout.addWidget(title)

        subtitle = QLabel("Mango Defends")
        subtitle.setObjectName("logoSubtitle")
        subtitle.setWordWrap(False)
        text_layout.addWidget(subtitle)

        layout.addWidget(text_container, 1)

        return container

    def _create_status_badge(self) -> QFrame:
        """Build the system status badge with a label, color indicator, and progress bar."""
        badge = QFrame()
        badge.setObjectName("statusBadge")

        layout = QVBoxLayout(badge)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        status_label = QLabel("System Status")
        status_label.setStyleSheet(f"color: {Colors.GREEN_500}; font-size: 11px; font-weight: 600;")
        text_layout.addWidget(status_label)

        self.status_text = QLabel("Unprotected")
        self.status_text.setStyleSheet(f"color: {Colors.RED_500}; font-size: 18px; font-weight: bold;")
        text_layout.addWidget(self.status_text)

        header_row.addWidget(text_container, 1)

        # Pulse dot — saved so update_status() can change its color
        self.pulse_indicator = QLabel("●")
        self.pulse_indicator.setStyleSheet(f"color: {Colors.RED_500}; font-size: 12px;")
        header_row.addWidget(self.pulse_indicator)

        layout.addLayout(header_row)

        # Decorative progress bar (visual only)
        progress_bg = QFrame()
        progress_bg.setFixedHeight(6)
        progress_bg.setStyleSheet("background: rgba(0, 0, 0, 0.3); border-radius: 3px;")

        progress_fill = QFrame(progress_bg)
        progress_fill.setGeometry(0, 0, int(badge.width() * 0.95), 6)
        progress_fill.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {Colors.GREEN_500}, stop:1 {Colors.EMERALD_500});
            border-radius: 3px;
        """)

        layout.addWidget(progress_bg)

        return badge

    def _create_navigation(self) -> QVBoxLayout:
        """Build navigation buttons with an exclusive button group."""
        layout = QVBoxLayout()
        layout.setSpacing(8)

        nav_items = [
            ("dashboard",  "Dashboard"),
            ("scan",       "Scan"),
            ("protection", "Protection"),
            ("quarantine", "Quarantine"),
            ("update",     "Update"),
        ]

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        for tab_id, label in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setProperty("tab_id", tab_id)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(50)
            btn.clicked.connect(lambda checked, tid=tab_id: self.tab_changed.emit(tid))
            self.nav_group.addButton(btn)
            layout.addWidget(btn)

        # Dashboard is active by default
        self.nav_group.buttons()[0].setChecked(True)

        return layout

    def _create_bottom_section(self) -> QVBoxLayout:
        """Build the bottom area with a threats counter card and a theme toggle button."""
        layout = QVBoxLayout()
        layout.setSpacing(12)

        self.threats_card = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_500, hover_effect=False)
        self.threats_card.setMinimumHeight(96)

        threats_layout = QVBoxLayout(self.threats_card)
        threats_layout.setContentsMargins(18, 16, 18, 16)
        threats_layout.setSpacing(8)

        self._threats_title_lbl = QLabel("Threats Blocked")
        threats_layout.addWidget(self._threats_title_lbl)

        self.threats_label = QLabel("0")
        self.threats_label.setStyleSheet(f"""
            color: {Colors.ORANGE_500};
            font-size: 34px;
            font-weight: bold;
            background: transparent;
        """)
        threats_layout.addWidget(self.threats_label)

        self._threats_meta_lbl = QLabel("Sesi ini")
        threats_layout.addWidget(self._threats_meta_lbl)
        self._apply_threats_card_theme()

        layout.addWidget(self.threats_card)

        # Label reflects the current theme state
        theme_label = " Dark Mode" if self.is_dark else " Light Mode"
        self.theme_btn = QPushButton(theme_label)
        self.theme_btn.setObjectName("secondaryButton")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.setMinimumHeight(44)
        self.theme_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self.theme_btn)

        return layout

    def _apply_threats_card_theme(self):
        """Update subtitle/meta label colors inside the threats card to match the theme."""
        ts = Colors.DARK_TEXT_SECONDARY if self.is_dark else Colors.LIGHT_TEXT_SECONDARY
        tm = Colors.DARK_TEXT_MUTED if self.is_dark else Colors.LIGHT_TEXT_MUTED
        self._threats_title_lbl.setStyleSheet(
            f"color: {ts}; font-size: 12px; font-weight: 500; background: transparent;"
        )
        self._threats_meta_lbl.setStyleSheet(
            f"color: {tm}; font-size: 11px; background: transparent;"
        )

    # ------------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------------

    def _toggle_theme(self):
        """Flip the theme state, update button label, and emit theme_toggled."""
        self.is_dark = not self.is_dark
        if hasattr(self, "threats_card"):
            self.threats_card.set_theme(self.is_dark)
        self._apply_threats_card_theme()

        self.theme_btn.setText(" Dark Mode" if self.is_dark else " Light Mode")
        self.theme_toggled.emit(self.is_dark)

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def set_active_tab(self, tab_id: str):
        """Programmatically activate a navigation tab by its ID."""
        for btn in self.nav_group.buttons():
            if btn.property("tab_id") == tab_id:
                btn.setChecked(True)
                break

    def update_threats_count(self, count: int):
        """Update the threats blocked counter displayed in the sidebar."""
        self.threats_count = count
        self.threats_label.setText(str(count))

    def update_status(self, status: str, is_protected: bool = True):
        """Update the protection status label and pulse indicator color.

        Args:
            status: Status text to display.
            is_protected: If True, use green; if False, use red.
        """
        self.status_text.setText(status)
        color = Colors.GREEN_500 if is_protected else Colors.RED_500
        self.status_text.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        self.pulse_indicator.setStyleSheet(f"color: {color}; font-size: 12px;")
