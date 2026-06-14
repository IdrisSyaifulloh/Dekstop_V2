"""
Animated Spinner Component — delta-time based for smooth rendering on any device.
"""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QColor, QConicalGradient

from ui.core.anim_timer import AdaptiveTimer


class AnimatedSpinner(QWidget):
    """
    Smooth arc spinner.  Speed is expressed in degrees-per-second so it
    looks identical on a 30 fps budget laptop and a 144 Hz gaming machine.
    """

    # degrees per second — tweak freely
    _SPEED_DEG_S = 300.0

    def __init__(self, diameter=80, line_width=6, parent=None):
        """Initialize the spinner with a fixed size and start the animation timer immediately."""
        super().__init__(parent)
        self.diameter = diameter
        self.line_width = line_width
        self._angle = 0.0  # float for sub-degree precision
        self.setFixedSize(diameter, diameter)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._timer = AdaptiveTimer(target_fps=60, parent=self)
        self._timer.tick.connect(self._on_tick)
        self._timer.start()

    def _on_tick(self, dt: float):
        """Advance the spinner angle by speed * dt degrees and request a repaint."""
        self._angle = (self._angle + self._SPEED_DEG_S * dt) % 360.0
        self.update()

    def paintEvent(self, event):
        """Draw the static background track and the rotating gradient arc."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        margin = self.line_width
        draw_rect = rect.adjusted(margin, margin, -margin, -margin)

        # Background track — adapts to parent bg
        back_pen = QPen(QColor(100, 100, 100, 60), self.line_width)
        back_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(back_pen)
        painter.drawArc(draw_rect, 0, 360 * 16)

        # Animated arc with gradient-ish look
        arc_pen = QPen(QColor(255, 140, 0), self.line_width)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)
        painter.drawArc(draw_rect, int(self._angle * 16), 120 * 16)

        painter.end()
