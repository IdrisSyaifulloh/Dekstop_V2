"""
Dashboard View - System Overview
Cockpit-inspired dashboard panel for MangoDefend.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

import psutil
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.styles.figma_theme import Colors, Typography
from ui.widgets import ActivityChart, SoftCard


def _asset(relative: str) -> str:
    """Resolve asset path for both dev and PyInstaller frozen mode."""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, relative)


_LOGO_PATH = _asset(os.path.join("assets", "mango_icon.png"))


class DashboardView(QWidget):
    """Cockpit-style dashboard with compact security stats."""

    navigate_requested = Signal(str)

    def __init__(self, parent=None):
        """Initialize state, start the resource polling timer, and build UI."""
        super().__init__(parent)
        self.is_dark = True
        self.realtime_enabled = True
        self.last_scan = datetime.now()
        self.threats_detected = 0
        self.scan_activity_by_day: dict = {}

        self._soft_cards: list[SoftCard] = []
        self._metric_cards: dict[str, SoftCard] = {}
        self._summary_cards: list[SoftCard] = []
        self.activity_chart: ActivityChart | None = None

        self._resource_timer = QTimer(self)
        self._resource_timer.timeout.connect(self._update_resources)
        self._resource_timer.setInterval(3000)
        self._resource_timer.start()

        self.setup_ui()

    # ------------------------------------------------------------------
    # THEME HELPERS
    # ------------------------------------------------------------------

    def _tp(self) -> str:
        """Return primary text color for the current theme."""
        return Colors.DARK_TEXT_PRIMARY if self.is_dark else Colors.LIGHT_TEXT_PRIMARY

    def _ts(self) -> str:
        """Return secondary text color for the current theme."""
        return Colors.DARK_TEXT_SECONDARY if self.is_dark else Colors.LIGHT_TEXT_SECONDARY

    def _tm(self) -> str:
        """Return muted text color for the current theme."""
        return Colors.DARK_TEXT_MUTED if self.is_dark else Colors.LIGHT_TEXT_MUTED

    def _badge_bg(self, color: str, dark_alpha: int = 22, light_alpha: int = 18) -> str:
        """Compute a semi-transparent rgba background from a hex accent color."""
        q = color.lstrip("#")
        r, g, b = int(q[0:2], 16), int(q[2:4], 16), int(q[4:6], 16)
        alpha = dark_alpha if self.is_dark else light_alpha
        return f"rgba({r}, {g}, {b}, {alpha / 255:.3f})"

    # ------------------------------------------------------------------
    # BUILD UI
    # ------------------------------------------------------------------

    def setup_ui(self):
        """Construct the full dashboard layout inside a scroll area."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        scroll.setWidget(content)

        outer = QVBoxLayout(content)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(14)

        self.main_panel = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_500, hover_effect=False)
        self._soft_cards.append(self.main_panel)
        self.main_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        panel_layout = QVBoxLayout(self.main_panel)
        panel_layout.setContentsMargins(20, 18, 20, 20)
        panel_layout.setSpacing(14)

        panel_layout.addLayout(self._create_panel_header())

        top_grid = QGridLayout()
        top_grid.setHorizontalSpacing(10)
        top_grid.setVerticalSpacing(10)
        top_grid.addWidget(self._create_identity_card(), 0, 0, 2, 1)
        top_grid.addWidget(
            self._create_metric_card(
                key="threats",
                title="Threats blocked",
                stamp=self._panel_stamp(),
                value="0",
                subtitle="Realtime neutralization active",
                accent=Colors.ORANGE_500,
                footer_glyph="▂▃▅▇▆",
                value_color=Colors.ORANGE_500,
            ),
            0, 1,
        )
        top_grid.addWidget(
            self._create_metric_card(
                key="last_scan",
                title="Last scan",
                stamp=self.last_scan.strftime("%H:%M"),
                value=self.last_scan.strftime("%H:%M"),
                subtitle="No threats found",
                accent=Colors.GREEN_500,
                footer_glyph="◦─◦─◦",
                value_color=self._tp(),
            ),
            0, 2,
        )
        top_grid.addWidget(
            self._create_metric_card(
                key="memory",
                title="Memory usage",
                stamp="Live",
                value="128 MB",
                subtitle="Runtime footprint",
                accent=Colors.EMERALD_500,
                footer_glyph="▁▂▂▃▂",
                value_color=self._tp(),
            ),
            1, 1,
        )
        top_grid.addWidget(
            self._create_metric_card(
                key="cpu",
                title="CPU load",
                stamp="Live",
                value="2.3%",
                subtitle="Background processing",
                accent=Colors.ORANGE_400,
                footer_glyph="▁▄▂▅▃",
                value_color=self._tp(),
            ),
            1, 2,
        )
        top_grid.setColumnStretch(0, 1)
        top_grid.setColumnStretch(1, 1)
        top_grid.setColumnStretch(2, 1)
        panel_layout.addLayout(top_grid)

        divider = QFrame()
        divider.setFixedHeight(1)
        self.divider = divider
        panel_layout.addWidget(divider)

        panel_layout.addWidget(self._create_section_label("Protection stats"))
        panel_layout.addLayout(self._create_summary_row())

        chart_header = QHBoxLayout()
        chart_header.setSpacing(10)
        self.chart_title = QLabel("Recent activity")
        chart_header.addWidget(self.chart_title)
        chart_header.addStretch()

        self.chart_badge = QLabel("7D")
        self.chart_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_badge.setFixedHeight(28)
        self.chart_badge.setMinimumWidth(44)
        chart_header.addWidget(self.chart_badge)
        panel_layout.addLayout(chart_header)

        self.activity_chart = ActivityChart()
        self.activity_chart.set_theme(self.is_dark)
        self.activity_chart.setToolTip("Hover bar untuk lihat detail aktivitas")
        panel_layout.addWidget(self.activity_chart)
        self._refresh_activity_chart()

        outer.addWidget(self.main_panel)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        self._apply_theme()
        self._update_resources()
        self._wire_interactions()

    def _create_panel_header(self) -> QHBoxLayout:
        """Build the top header row with mode chip, title, and timestamp."""
        layout = QHBoxLayout()
        layout.setSpacing(12)

        self.mode_chip = QLabel("Security pulse")
        self.mode_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_chip.setFixedHeight(34)
        self.mode_chip.setMinimumWidth(118)
        layout.addWidget(self.mode_chip)

        layout.addStretch()

        self.header_title = QLabel("MangoDefend Overview")
        self.header_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.header_title)

        layout.addStretch()

        self.header_stamp = QLabel(self._panel_stamp())
        self.header_stamp.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.header_stamp)
        return layout

    def _create_identity_card(self) -> SoftCard:
        """Build the large identity card showing logo, model info, and status."""
        card = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_500, hover_effect=True)
        self._soft_cards.append(card)
        card.set_interactive(True)
        card.setToolTip("Buka halaman Update")
        self.identity_card = card
        card.setMinimumHeight(284)
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        logo_frame = QFrame()
        logo_frame.setFixedSize(54, 54)
        self.logo_frame = logo_frame
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(7, 7, 7, 7)
        logo_layout.setSpacing(0)

        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = QPixmap(_LOGO_PATH)
        if not pix.isNull():
            self.logo_label.setPixmap(
                pix.scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
        else:
            self.logo_label.setText("MD")
        logo_layout.addWidget(self.logo_label)
        top_row.addWidget(logo_frame)
        top_row.addStretch()

        self.state_chip = QLabel("Realtime ready")
        self.state_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_chip.setFixedHeight(28)
        self.state_chip.setMinimumWidth(112)
        top_row.addWidget(self.state_chip)
        layout.addLayout(top_row)

        self.identity_title = QLabel("MangoDefend")
        layout.addWidget(self.identity_title)

        self.identity_subtitle = QLabel("Desktop threat telemetry")
        layout.addWidget(self.identity_subtitle)

        self.identity_status = QLabel("Layered protection status")
        layout.addWidget(self.identity_status)

        self.identity_value = QLabel("Public scan lane")
        layout.addWidget(self.identity_value)

        info_grid = QGridLayout()
        info_grid.setHorizontalSpacing(8)
        info_grid.setVerticalSpacing(10)

        self.identity_keys: list[QLabel] = []
        self.identity_vals: list[QLabel] = []
        rows = [
            ("Model", "CNN v3 ONNX"),
            ("Mode", "Local core"),
            ("Window", "Desktop"),
        ]
        for row, (key_text, value_text) in enumerate(rows):
            key = QLabel(key_text)
            val = QLabel(value_text)
            key.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.identity_keys.append(key)
            self.identity_vals.append(val)
            info_grid.addWidget(key, row, 0)
            info_grid.addWidget(val, row, 1)

        layout.addLayout(info_grid)
        return card

    def _create_metric_card(
        self,
        *,
        key: str,
        title: str,
        stamp: str,
        value: str,
        subtitle: str,
        accent: str,
        footer_glyph: str,
        value_color: str,
    ) -> SoftCard:
        """Build a single metric card and register its labels under the given key."""
        card = SoftCard(is_dark=self.is_dark, accent=accent, hover_effect=True)
        self._soft_cards.append(card)
        self._metric_cards[key] = card
        card.set_interactive(True)
        card.setMinimumHeight(138)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(4)

        title_stamp_col = QVBoxLayout()
        title_stamp_col.setSpacing(2)
        title_stamp_col.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(title)
        stamp_label = QLabel(stamp)
        title_stamp_col.addWidget(title_label)
        title_stamp_col.addWidget(stamp_label)
        header.addLayout(title_stamp_col)
        header.addStretch()
        layout.addLayout(header)

        value_label = QLabel(value)
        layout.addWidget(value_label)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        subtitle_label = QLabel(subtitle)
        footer.addWidget(subtitle_label)
        footer.addStretch()
        glyph_label = QLabel(footer_glyph)
        footer.addWidget(glyph_label)
        layout.addLayout(footer)

        # Store label references via dynamic attributes for later updates
        setattr(self, f"{key}_title_label", title_label)
        setattr(self, f"{key}_stamp_label", stamp_label)
        setattr(self, f"{key}_value_label", value_label)
        setattr(self, f"{key}_subtitle_label", subtitle_label)
        setattr(self, f"{key}_glyph_label", glyph_label)
        setattr(self, f"{key}_accent", accent)
        setattr(self, f"{key}_value_color", value_color)
        return card

    def _create_section_label(self, text: str) -> QLabel:
        """Create a styled section header label."""
        label = QLabel(text)
        label.setText(text)
        self.summary_header = label
        return label

    def _create_summary_row(self) -> QHBoxLayout:
        """Build the three summary stat cards (threats, layers, latest scan)."""
        layout = QHBoxLayout()
        layout.setSpacing(8)

        self.summary_items: dict[str, tuple[QLabel, QLabel, QLabel]] = {}
        items = [
            ("blocked", "Threats neutralized", "0", Colors.ORANGE_500, "Session total"),
            ("layers", "Layers online", "3 / 3", Colors.GREEN_500, "Monitor state"),
            ("latest", "Latest scan", self.last_scan.strftime("%H:%M"), self._tp(), "Updated just now"),
        ]

        for key, title_text, value_text, accent, caption_text in items:
            card = SoftCard(is_dark=self.is_dark, accent=accent, hover_effect=True)
            card.setMinimumHeight(92)
            self._soft_cards.append(card)
            self._summary_cards.append(card)
            card.set_interactive(True)

            col = QVBoxLayout(card)
            col.setContentsMargins(14, 12, 14, 12)
            col.setSpacing(2)

            title = QLabel(title_text)
            value = QLabel(value_text)
            caption = QLabel(caption_text)
            col.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
            col.addWidget(value, alignment=Qt.AlignmentFlag.AlignCenter)
            col.addWidget(caption, alignment=Qt.AlignmentFlag.AlignCenter)

            layout.addWidget(card, 1)
            self.summary_items[key] = (title, value, caption)

        return layout

    def _panel_stamp(self) -> str:
        """Format the last scan time as a human-readable panel timestamp."""
        return self.last_scan.strftime("%d %b %Y  %H:%M")

    def _wire_interactions(self):
        """Connect card click signals to navigation requests and set tooltips."""
        self.identity_card.clicked.connect(lambda: self.navigate_requested.emit("update"))
        self._metric_cards["threats"].clicked.connect(lambda: self.navigate_requested.emit("quarantine"))
        self._metric_cards["last_scan"].clicked.connect(lambda: self.navigate_requested.emit("scan"))
        self._metric_cards["memory"].clicked.connect(lambda: self.navigate_requested.emit("protection"))
        self._metric_cards["cpu"].clicked.connect(lambda: self.navigate_requested.emit("protection"))
        self._summary_cards[0].clicked.connect(lambda: self.navigate_requested.emit("quarantine"))
        self._summary_cards[1].clicked.connect(lambda: self.navigate_requested.emit("protection"))
        self._summary_cards[2].clicked.connect(lambda: self.navigate_requested.emit("scan"))

        self._metric_cards["threats"].setToolTip("Buka halaman Quarantine")
        self._metric_cards["last_scan"].setToolTip("Buka halaman Scan")
        self._metric_cards["memory"].setToolTip("Buka halaman Protection")
        self._metric_cards["cpu"].setToolTip("Buka halaman Protection")
        self._summary_cards[0].setToolTip("Lihat file yang diblokir")
        self._summary_cards[1].setToolTip("Lihat lapisan proteksi")
        self._summary_cards[2].setToolTip("Buka riwayat scan")
        self.main_panel.setToolTip("Ringkasan proteksi MangoDefend")

    # ------------------------------------------------------------------
    # THEME APPLICATION
    # ------------------------------------------------------------------

    def _apply_theme(self):
        """Apply current theme colors to all cards, labels, and widgets."""
        for card in self._soft_cards:
            card.set_theme(self.is_dark)

        tp = self._tp()
        ts = self._ts()
        tm = self._tm()
        success = Colors.GREEN_500 if self.is_dark else Colors.EMERALD_500

        self.main_panel.set_accent(Colors.ORANGE_500 if self.is_dark else Colors.ORANGE_400)
        self.divider.setStyleSheet(
            f"background: {'rgba(255,255,255,0.08)' if self.is_dark else 'rgba(31,41,55,0.10)'}; border: none;"
        )

        self.mode_chip.setStyleSheet(
            f"""
            background: {self._badge_bg(Colors.ORANGE_500, 30, 22)};
            color: {Colors.ORANGE_500};
            border: 1px solid {self._badge_bg(Colors.ORANGE_500, 80, 50)};
            border-radius: 17px;
            font-size: 11px;
            font-weight: 600;
            font-family: {Typography.FONT_FAMILY};
            padding: 0 12px;
            """
        )
        self.header_title.setStyleSheet(
            f"color: {tp}; font-size: 22px; font-weight: 600; background: transparent;"
            f" font-family: {Typography.FONT_FAMILY};"
        )
        self.header_stamp.setStyleSheet(
            f"color: {tm}; font-size: 12px; background: transparent; font-family: {Typography.FONT_FAMILY};"
        )

        self.logo_frame.setStyleSheet(
            f"""
            background: {self._badge_bg(Colors.ORANGE_500, 26, 18)};
            border: 1px solid {self._badge_bg(Colors.ORANGE_500, 72, 46)};
            border-radius: 16px;
            """
        )
        self.logo_label.setStyleSheet(
            f"color: {Colors.ORANGE_500}; background: transparent; font-size: 16px; font-weight: 700;"
        )
        self.state_chip.setStyleSheet(
            f"""
            background: {self._badge_bg(success, 24, 18)};
            color: {success};
            border: 1px solid {self._badge_bg(success, 84, 48)};
            border-radius: 14px;
            font-size: 11px;
            font-weight: 600;
            padding: 0 10px;
            """
        )
        self.identity_title.setStyleSheet(
            f"color: {tp}; font-size: 28px; font-weight: 600; background: transparent;"
            f" font-family: {Typography.FONT_FAMILY};"
        )
        self.identity_subtitle.setStyleSheet(
            f"color: {Colors.ORANGE_500}; font-size: 13px; font-weight: 500; background: transparent;"
            f" font-family: {Typography.FONT_FAMILY};"
        )
        self.identity_status.setStyleSheet(
            f"color: {tm}; font-size: 11px; letter-spacing: 0.4px; background: transparent;"
            f" font-family: {Typography.FONT_FAMILY};"
        )
        self.identity_value.setStyleSheet(
            f"color: {tp}; font-size: 18px; font-weight: 500; background: transparent;"
            f" font-family: {Typography.FONT_FAMILY};"
        )
        for key in self.identity_keys:
            key.setStyleSheet(
                f"color: {tm}; font-size: 11px; background: transparent; font-family: {Typography.FONT_FAMILY};"
            )
        for val in self.identity_vals:
            val.setStyleSheet(
                f"color: {ts}; font-size: 11px; font-weight: 500; background: transparent;"
                f" font-family: {Typography.FONT_FAMILY};"
            )

        for key in ("threats", "last_scan", "memory", "cpu"):
            title_label = getattr(self, f"{key}_title_label")
            stamp_label = getattr(self, f"{key}_stamp_label")
            value_label = getattr(self, f"{key}_value_label")
            subtitle_label = getattr(self, f"{key}_subtitle_label")
            glyph_label = getattr(self, f"{key}_glyph_label")
            accent = getattr(self, f"{key}_accent")
            value_color = getattr(self, f"{key}_value_color")

            title_label.setStyleSheet(
                f"color: {ts}; font-size: 11px; font-weight: 500; background: transparent;"
                f" font-family: {Typography.FONT_FAMILY};"
            )
            stamp_label.setStyleSheet(
                f"color: {tm}; font-size: 11px; background: transparent; font-family: {Typography.FONT_FAMILY};"
            )
            value_label.setStyleSheet(
                f"color: {value_color}; font-size: 21px; font-weight: 600; background: transparent;"
                f" font-family: {Typography.FONT_FAMILY};"
            )
            subtitle_label.setStyleSheet(
                f"color: {success if key == 'last_scan' else tm}; font-size: 12px; background: transparent;"
                f" font-family: {Typography.FONT_FAMILY};"
            )
            glyph_label.setStyleSheet(
                f"color: {accent}; font-size: 18px; background: transparent;"
                f" font-family: {Typography.FONT_FAMILY_MONO};"
            )

        self.summary_header.setStyleSheet(
            f"color: {tp}; font-size: 20px; font-weight: 500; background: transparent;"
            f" font-family: {Typography.FONT_FAMILY};"
        )
        for key, (title, value, caption) in self.summary_items.items():
            value_color = tp
            if key == "blocked":
                value_color = Colors.ORANGE_500
            elif key == "layers":
                value_color = success
            title.setStyleSheet(
                f"color: {tm}; font-size: 11px; font-weight: 500; background: transparent;"
                f" font-family: {Typography.FONT_FAMILY};"
            )
            value.setStyleSheet(
                f"color: {value_color}; font-size: 22px; font-weight: 600; background: transparent;"
                f" font-family: {Typography.FONT_FAMILY};"
            )
            caption.setStyleSheet(
                f"color: {tm}; font-size: 11px; background: transparent; font-family: {Typography.FONT_FAMILY};"
            )

        self.chart_title.setStyleSheet(
            f"color: {tp}; font-size: 18px; font-weight: 500; background: transparent;"
            f" font-family: {Typography.FONT_FAMILY};"
        )
        self.chart_badge.setStyleSheet(
            f"""
            background: {self._badge_bg(Colors.ORANGE_400, 24, 16)};
            color: {Colors.ORANGE_500};
            border: 1px solid {self._badge_bg(Colors.ORANGE_400, 74, 42)};
            border-radius: 14px;
            font-size: 11px;
            font-weight: 600;
            padding: 0 10px;
            """
        )

        if self.activity_chart:
            self.activity_chart.set_theme(self.is_dark)

    # ------------------------------------------------------------------
    # LIVE DATA UPDATES
    # ------------------------------------------------------------------

    def _update_resources(self):
        """Poll CPU and memory usage and refresh the corresponding metric cards."""
        try:
            cpu = psutil.cpu_percent(interval=0)
            proc = psutil.Process()
            mem_mb = proc.memory_info().rss / (1024 * 1024)

            self.cpu_value_label.setText(f"{cpu:.1f}%")
            self.memory_value_label.setText(f"{mem_mb:.0f} MB")
        except Exception:
            pass

    def update_threats(self, count: int):
        """Update threats count on the metric card and summary row."""
        self.threats_detected = count
        self.threats_value_label.setText(str(count))
        self.summary_items["blocked"][1].setText(str(count))

    def update_threats_count(self, count: int):
        """Alias for update_threats — kept for backward compatibility."""
        self.update_threats(count)

    def update_last_scan(self, scan_time: datetime):
        """Refresh all scan-time labels with the latest scan timestamp."""
        self.last_scan = scan_time
        stamp = scan_time.strftime("%H:%M")
        self.last_scan_stamp_label.setText(stamp)
        self.last_scan_value_label.setText(stamp)
        self.summary_items["latest"][1].setText(stamp)
        self.summary_items["latest"][2].setText("Updated just now")
        self.header_stamp.setText(self._panel_stamp())

    def record_scan_activity(self, count: int = 1, scan_time: datetime | None = None):
        """Record scan activity for the recent activity chart."""
        if count <= 0:
            return
        when = scan_time or datetime.now()
        day = when.date()
        self.scan_activity_by_day[day] = self.scan_activity_by_day.get(day, 0) + count
        self._trim_activity_days()
        self._refresh_activity_chart()

    def _trim_activity_days(self):
        """Keep only the current seven-day activity window."""
        start_day = datetime.now().date() - timedelta(days=6)
        self.scan_activity_by_day = {
            day: count
            for day, count in self.scan_activity_by_day.items()
            if day >= start_day
        }

    def _refresh_activity_chart(self):
        """Push the latest seven-day scan activity into the chart widget."""
        if not self.activity_chart:
            return
        today = datetime.now().date()
        days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
        labels = [day.strftime("%d") for day in days]
        values = [self.scan_activity_by_day.get(day, 0) for day in days]
        self.activity_chart.set_activity_data(labels, values)

    def set_realtime_state(self, enabled: bool):
        """Update identity card and summary row to reflect realtime on/off state."""
        self.realtime_enabled = enabled
        self.state_chip.setText("Realtime active" if enabled else "Realtime standby")
        self.identity_value.setText("Public scan lane" if enabled else "Protection paused")
        self.summary_items["layers"][1].setText("3 / 3" if enabled else "0 / 3")
        self.summary_items["layers"][2].setText("Monitor state" if enabled else "Protection paused")
        self._apply_theme()

    def set_theme(self, is_dark: bool):
        """Switch between dark and light theme and redraw all styled widgets."""
        self.is_dark = is_dark
        self._apply_theme()
