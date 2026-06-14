"""
Animated activity bar chart widget for the dashboard.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QBrush, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ui.styles.figma_theme import Colors
from ui.core.anim_timer import AdaptiveTimer


class ActivityChart(QWidget):
    """
    Rounded animated bar chart with a ghost backdrop layer.

    Visual behavior:
    - Bars grow in with a staggered ease-out animation on first render.
    - A soft glow pulses on the selected (clicked) bar.
    - Hovering a bar shows a thin orange outline without changing fill.
    - The last bar is selected by default.
    """

    def __init__(self, parent=None):
        """Siapkan chart aktivitas 7 hari dan animasi bar yang bergerak halus."""
        super().__init__(parent)
        self.setMinimumHeight(250)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        # Theme
        self.is_dark = True

        # Chart data is provided by DashboardView from real scan activity.
        self.labels       = self._default_labels()
        self.values       = [0.0] * len(self.labels)
        self.ghost_values = [0.0] * len(self.labels)
        self.max_value    = 1.0
        self.avg_line     = 0.0

        # Interaction state
        self._hovered_index  = -1
        self._selected_index = len(self.values) - 1  # last bar selected by default

        # Animation state
        self.animation_progress = 0.0   # 0→1 bar grow-in
        self.sweep_phase        = 0.0   # 0→1 glow pulse cycle

        self._timer = AdaptiveTimer(target_fps=60, parent=self)
        self._timer.tick.connect(self._tick)
        self._timer.start()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_theme(self, is_dark: bool):
        """Switch between dark and light color palette."""
        self.is_dark = is_dark
        self.update()

    def set_activity_data(self, labels: list[str], values: list[float], ghost_values: list[float] | None = None):
        """Replace chart data with scan activity counts."""
        if not labels or not values:
            labels = self._default_labels()
            values = [0.0] * len(labels)

        count = min(len(labels), len(values))
        self.labels = [str(label) for label in labels[:count]]
        self.values = [max(0.0, float(value)) for value in values[:count]]

        if ghost_values:
            self.ghost_values = [max(0.0, float(value)) for value in ghost_values[:count]]
            if len(self.ghost_values) < count:
                self.ghost_values.extend([0.0] * (count - len(self.ghost_values)))
        else:
            self.ghost_values = [0.0] * count

        highest = max(self.values + self.ghost_values + [1.0])
        self.max_value = max(1.0, math.ceil(highest * 1.2))
        self.avg_line = sum(self.values) / len(self.values) if self.values else 0.0
        self._selected_index = max(0, len(self.values) - 1)
        self.update()

    @staticmethod
    def _default_labels() -> list[str]:
        """Return day labels for the last seven days."""
        today = datetime.now().date()
        return [(today - timedelta(days=offset)).strftime("%d") for offset in range(6, -1, -1)]

    @staticmethod
    def _format_axis(value: float) -> str:
        """Format axis values as compact integers when possible."""
        return str(int(value)) if float(value).is_integer() else f"{value:.1f}"

    # ── Mouse interaction ─────────────────────────────────────────────────────

    def _bar_index_at(self, x_pos: float) -> int:
        """Return the bar index under x_pos, or -1 if outside the plot area."""
        rect = self.rect().adjusted(12, 8, -12, -8)
        plot = QRectF(rect.left() + 12, rect.top() + 8, rect.width() - 58, rect.height() - 48)
        if not plot.contains(x_pos, plot.center().y()):
            return -1
        bar_slot = plot.width() / max(1, len(self.values))
        index = int((x_pos - plot.left()) / bar_slot)
        return index if 0 <= index < len(self.values) else -1

    def mouseMoveEvent(self, event):
        """Update hover highlight as mouse moves across bars."""
        index = self._bar_index_at(event.position().x())
        if index != self._hovered_index:
            self._hovered_index = index
            self.update()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """Select the clicked bar (persists orange fill until another is clicked)."""
        if event.button() == Qt.MouseButton.LeftButton:
            index = self._bar_index_at(event.position().x())
            if index >= 0:
                self._selected_index = index
                self.update()
        super().mousePressEvent(event)

    def leaveEvent(self, event):
        """Clear hover when mouse leaves the widget."""
        self._hovered_index = -1
        self.update()
        super().leaveEvent(event)

    # ── Animation ─────────────────────────────────────────────────────────────

    def _tick(self, dt: float):
        """Advance bar grow-in and glow pulse animations each frame."""
        # Grow-in: 0→1 over ~1.2 seconds
        if self.animation_progress < 1.0:
            self.animation_progress = min(1.0, self.animation_progress + dt / 1.2)
        # Glow pulse: one full cycle every ~5 seconds
        self.sweep_phase = (self.sweep_phase + dt / 5.0) % 1.0
        self.update()

    # ── Color palette ─────────────────────────────────────────────────────────

    def _palette(self) -> dict[str, QColor]:
        """Return the color palette for the current theme (dark or light)."""
        if self.is_dark:
            return {
                "grid":         QColor(255, 255, 255, 18),
                "label":        QColor(107, 114, 128),
                "axis":         QColor(204, 204, 204, 88),
                "avg":          QColor(255, 255, 255, 72),
                "ghost_top":    QColor(255, 255, 255, 42),
                "ghost_bottom": QColor(255, 255, 255, 10),
                "bar_top":      QColor(255, 255, 255, 210),
                "bar_bottom":   QColor(214, 214, 214, 168),
                "accent_top":   QColor(255, 183, 50, 238),
                "accent_bottom":QColor(255, 165, 0,  188),
                "glow":         QColor(255, 165, 0,  78),
            }
        return {
            "grid":         QColor(31, 41, 55,  20),
            "label":        QColor(107, 114, 128),
            "axis":         QColor(68, 68, 68,  100),
            "avg":          QColor(68, 68, 68,  72),
            "ghost_top":    QColor(31, 41, 55,  28),
            "ghost_bottom": QColor(31, 41, 55,  10),
            "bar_top":      QColor(255, 255, 255, 238),
            "bar_bottom":   QColor(229, 231, 235, 224),
            "accent_top":   QColor(255, 183, 50, 235),
            "accent_bottom":QColor(255, 165, 0,  180),
            "glow":         QColor(255, 165, 0,  56),
        }

    # ── Drawing helpers ───────────────────────────────────────────────────────

    def _draw_bar(self, painter: QPainter, rect: QRectF, radius: float,
                  top_color: QColor, bottom_color: QColor):
        """Draw a single rounded gradient bar."""
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0.0, top_color)
        gradient.setColorAt(1.0, bottom_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(rect, radius, radius)

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        """Render grid, average line, ghost bars, live bars, and axis labels."""
        super().paintEvent(event)
        if not self.values:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self._palette()

        rect = self.rect().adjusted(12, 8, -12, -8)
        plot = QRectF(rect.left() + 12, rect.top() + 8, rect.width() - 58, rect.height() - 48)

        self._paint_grid(painter, palette, plot)
        self._paint_bars(painter, palette, plot)
        self._paint_labels(painter, palette, plot)

        painter.end()

    def _paint_grid(self, painter: QPainter, palette: dict, plot: QRectF):
        """Draw horizontal grid lines and the dashed average line."""
        # Horizontal grid lines (5 evenly spaced)
        painter.setPen(QPen(palette["grid"], 1))
        for step in range(5):
            y = plot.bottom() - (plot.height() / 4.0) * step
            painter.drawLine(plot.left(), y, plot.right(), y)

        # Dashed average reference line
        avg_y   = plot.bottom() - (self.avg_line / self.max_value) * plot.height()
        avg_pen = QPen(palette["avg"], 1)
        avg_pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(avg_pen)
        painter.drawLine(plot.left(), avg_y, plot.right(), avg_y)

        # Store avg_y so label painter can reuse it
        self._avg_y = avg_y

    def _paint_bars(self, painter: QPainter, palette: dict, plot: QRectF):
        """Draw ghost (previous period) bars and animated live bars."""
        bar_slot    = plot.width() / max(1, len(self.values))
        ghost_width = min(42.0, bar_slot * 0.72)
        live_width  = min(42.0, bar_slot * 0.60)

        # Ghost bars (previous period backdrop)
        for index, value in enumerate(self.ghost_values):
            x_center     = plot.left() + bar_slot * index + bar_slot * 0.5
            ghost_height = (value / max(1.0, self.max_value)) * plot.height()
            ghost_rect   = QRectF(
                x_center - ghost_width / 2.0,
                plot.bottom() - ghost_height,
                ghost_width, ghost_height,
            )
            self._draw_bar(painter, ghost_rect, 9.0, palette["ghost_top"], palette["ghost_bottom"])

        # Live bars with staggered ease-out grow-in
        for index, value in enumerate(self.values):
            local_progress = max(0.0, min(1.0, self.animation_progress * 1.2 - index * 0.08))
            eased          = 1.0 - math.pow(1.0 - local_progress, 2.8)
            live_height    = (value / max(1.0, self.max_value)) * plot.height() * eased
            x_center       = plot.left() + bar_slot * index + bar_slot * 0.5
            live_rect      = QRectF(
                x_center - live_width / 2.0,
                plot.bottom() - live_height,
                live_width, live_height,
            )

            is_selected = index == self._selected_index
            is_hovered  = index == self._hovered_index and not is_selected

            if is_selected:
                # Pulsing orange glow behind selected bar
                glow = 10.0 + 8.0 * (0.5 + 0.5 * math.sin(self.sweep_phase * math.tau))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(palette["glow"])
                painter.drawRoundedRect(
                    QRectF(live_rect.left()  - glow * 0.4, live_rect.top()    - glow * 0.3,
                           live_rect.width() + glow * 0.8, live_rect.height() + glow * 0.6),
                    14.0, 14.0,
                )
                self._draw_bar(painter, live_rect, 8.0, palette["accent_top"], palette["accent_bottom"])
            else:
                self._draw_bar(painter, live_rect, 8.0, palette["bar_top"], palette["bar_bottom"])

            # Hover: thin orange outline only, no fill change
            if is_hovered:
                painter.setPen(QPen(palette["accent_top"], 1.5))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(live_rect.adjusted(-2, -2, 2, 2), 10.0, 10.0)

    def _paint_labels(self, painter: QPainter, palette: dict, plot: QRectF):
        """Draw x-axis date labels and y-axis value labels."""
        bar_slot = plot.width() / max(1, len(self.values))

        # X-axis labels (dates)
        font = painter.font()
        font.setFamily("Inter")
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(palette["label"])
        for index, label in enumerate(self.labels):
            x_center = plot.left() + bar_slot * index + bar_slot * 0.5
            painter.drawText(
                QRectF(x_center - 18, plot.bottom() + 8, 36, 18),
                Qt.AlignmentFlag.AlignCenter,
                label,
            )

        # Y-axis labels (values)
        axis_font = painter.font()
        axis_font.setPointSize(8)
        painter.setFont(axis_font)
        painter.setPen(palette["axis"])
        avg_y       = getattr(self, "_avg_y", plot.center().y())
        axis_labels = [
            (self._format_axis(self.max_value), plot.top()),
            (self._format_axis(self.avg_line), avg_y),
            ("0", plot.bottom() - 4),
        ]
        for text, y in axis_labels:
            painter.drawText(
                QRectF(plot.right() + 10, y - 10, 24, 20),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                text,
            )
