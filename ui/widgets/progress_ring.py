"""
Progress Ring Widget — delta-time based for smooth rendering on any device.
"""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QColor, QConicalGradient

from ui.core.anim_timer import AdaptiveTimer


class ProgressRing(QWidget):
    """
    Circular progress indicator with smooth, device-adaptive animation.
    Progress animates at a fixed perceived speed (easing toward target)
    regardless of frame rate.
    """

    def __init__(self, diameter=120, line_width=12, parent=None):
        """Initialize the ring with a fixed size and start the adaptive animation timer."""
        super().__init__(parent)
        self.diameter = diameter
        self.line_width = line_width
        self.progress = 0.0        # current rendered value  0.0–1.0
        self.target_progress = 1.0
        self.is_dark = True

        self.setFixedSize(diameter, diameter)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._timer = AdaptiveTimer(target_fps=60, parent=self)
        self._timer.tick.connect(self._on_tick)

    def set_progress(self, value: float, animate: bool = True):
        """Set the target progress value and optionally animate toward it."""
        self.target_progress = max(0.0, min(1.0, value))
        if animate:
            if not self._timer.is_active():
                self._timer.start()
        else:
            self.progress = self.target_progress
            self._timer.stop()
            self.update()

    def _on_tick(self, dt: float):
        """Advance the rendered progress toward the target using exponential easing."""
        diff = self.target_progress - self.progress
        if abs(diff) < 0.002:
            self.progress = self.target_progress
            self._timer.stop()
        else:
            # Exponential ease: ~95% of gap closed per second
            self.progress += diff * (1.0 - pow(0.05, dt))
        self.update()

    def paintEvent(self, event):
        """Draw the background track, the progress arc, and the centered percentage label."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        cx = rect.width() / 2
        cy = rect.height() / 2
        radius = (min(rect.width(), rect.height()) - self.line_width) / 2

        # Background track
        bg_pen = QPen(QColor(255, 255, 255, 20), self.line_width)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(
            int(cx - radius), int(cy - radius),
            int(radius * 2), int(radius * 2),
            90 * 16, -360 * 16,
        )

        # Progress arc
        if self.progress > 0:
            gradient = QConicalGradient(cx, cy, 90)
            gradient.setColorAt(0.0, QColor(34, 197, 94))
            gradient.setColorAt(1.0, QColor(16, 185, 129))

            arc_pen = QPen(gradient, self.line_width)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            painter.drawArc(
                int(cx - radius), int(cy - radius),
                int(radius * 2), int(radius * 2),
                90 * 16, int(-360 * 16 * self.progress),
            )

        # Center text — theme-aware
        text_color = QColor(255, 255, 255) if self.is_dark else QColor(31, 41, 55)
        painter.setPen(text_color)
        font = painter.font()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter,
                         f"{int(self.progress * 100)}%")

        painter.end()
