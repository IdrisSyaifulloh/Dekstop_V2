"""
Splash screen with logo animation shown during app startup.
"""
import os
import sys
import math

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QColor, QPainter, QPixmap, QBrush, QLinearGradient,
    QRadialGradient, QPen, QPainterPath
)
from PySide6.QtWidgets import QWidget, QApplication

from ui.styles.figma_theme import Colors, Typography


def _asset(relative: str) -> str:
    """Resolve asset path — works both frozen (PyInstaller) and dev mode."""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


class SplashScreen(QWidget):
    """
    Frameless splash screen with logo, animated ring, and fade-in/out.

    Animation phases (total ~2.2s):
      0.0 – 0.4s  fade in
      0.4 – 1.6s  pulse ring + logo animation
      1.6 – 2.2s  fade out → emits finished signal
    """

    finished = Signal()

    # Animation timing constants (seconds)
    _TOTAL          = 2.2
    _FADE_IN        = 0.4
    _FADE_OUT_START = 1.6

    # Fixed widget size in logical pixels
    _SIZE = 320

    def __init__(self):
        """Siapkan splash screen kecil yang tampil saat aplikasi sedang membuka service awal."""
        super().__init__(None)
        # Frameless + always-on-top + bypass window manager for correct centering
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Animation state
        self._t      = 0.0   # elapsed time in seconds
        self._opacity = 0.0  # master opacity 0..1
        self._ring_t  = 0.0  # ring pulse progress 0..1

        # Load app logo — falls back gracefully if file missing
        logo_path = _asset(os.path.join("assets", "mango_icon.png"))
        self._logo = QPixmap(logo_path) if os.path.exists(logo_path) else QPixmap()

        self.setFixedSize(self._SIZE, self._SIZE)
        self._center()

        # 60fps animation timer
        self._tick_ms = 16
        self._timer = QTimer(self)
        self._timer.setInterval(self._tick_ms)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ── Positioning ───────────────────────────────────────────────────────────

    def _center(self):
        """Move splash to exact center of the primary screen."""
        screen = QApplication.primaryScreen().geometry()
        self.move(
            screen.x() + (screen.width()  - self._SIZE) // 2,
            screen.y() + (screen.height() - self._SIZE) // 2,
        )

    def showEvent(self, event):
        """Re-center on show in case screen geometry changed since __init__."""
        self._center()
        super().showEvent(event)

    # ── Animation tick ────────────────────────────────────────────────────────

    def _tick(self):
        """Advance animation by one frame (~16ms). Closes and emits when done."""
        dt = self._tick_ms / 1000.0
        self._t += dt
        t = self._t

        # Opacity envelope: fade in → hold → fade out
        if t < self._FADE_IN:
            self._opacity = t / self._FADE_IN
        elif t < self._FADE_OUT_START:
            self._opacity = 1.0
        elif t < self._TOTAL:
            self._opacity = 1.0 - (t - self._FADE_OUT_START) / (self._TOTAL - self._FADE_OUT_START)
        else:
            self._timer.stop()
            self.close()
            self.finished.emit()
            return

        # Ring pulse progress: 0→1 during the hold phase
        if t > self._FADE_IN:
            self._ring_t = min(1.0, (t - self._FADE_IN) / (self._FADE_OUT_START - self._FADE_IN))

        self.update()

    # ── Painting ──────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        """Draw background card, animated ring, logo, app name, and tagline."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(max(0.0, min(1.0, self._opacity)))

        w, h  = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0

        self._draw_card(painter, w, h)
        self._draw_ring(painter, cx, cy)
        self._draw_logo(painter, cx, cy, w)
        self._draw_text(painter, cx, cy, w)

        painter.end()

    def _draw_card(self, painter: QPainter, w: float, h: float):
        """Draw the rounded dark background card with orange tint and border."""
        card_r = 48.0
        card_w = w - 48
        card_h = h - 48
        card_x = (w - card_w) / 2.0
        card_y = (h - card_h) / 2.0

        path = QPainterPath()
        path.addRoundedRect(card_x, card_y, card_w, card_h, card_r, card_r)

        # Dark gradient background
        bg_grad = QLinearGradient(QPointF(card_x, card_y), QPointF(card_x + card_w, card_y + card_h))
        bg_grad.setColorAt(0.0, QColor(18, 18, 26, 245))
        bg_grad.setColorAt(1.0, QColor(12, 12, 20, 245))
        painter.fillPath(path, QBrush(bg_grad))

        # Subtle orange radial tint in top-left
        tint = QRadialGradient(QPointF(card_x + card_w * 0.25, card_y + card_h * 0.25), card_w * 0.7)
        tint.setColorAt(0.0, QColor(255, 165, 0, 28))
        tint.setColorAt(1.0, QColor(255, 165, 0, 0))
        painter.fillPath(path, QBrush(tint))

        # Thin orange border
        painter.setPen(QPen(QColor(255, 165, 0, 55), 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(
            QRectF(card_x + 0.6, card_y + 0.6, card_w - 1.2, card_h - 1.2),
            card_r, card_r
        )

    def _draw_ring(self, painter: QPainter, cx: float, cy: float):
        """Draw the expanding pulse ring and rotating arc around the logo."""
        ring_t     = self._ring_t
        ring_r     = 52.0 + (80.0 - 52.0) * ring_t       # expands 52→80px
        ring_alpha = int(180 * (1.0 - ring_t))             # fades out as it expands

        # Outer soft glow
        painter.setPen(QPen(QColor(255, 165, 0, ring_alpha // 3), ring_r * 0.18))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), ring_r + 6, ring_r + 6)

        # Main ring
        painter.setPen(QPen(QColor(255, 183, 50, ring_alpha), 2.5))
        painter.drawEllipse(QPointF(cx, cy), ring_r, ring_r)

        # Rotating bright arc
        arc_angle = int(ring_t * 720) % 360
        arc_rect  = QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)
        painter.setPen(QPen(QColor(255, 220, 100, min(255, ring_alpha + 60)), 3.0))
        painter.drawArc(arc_rect, arc_angle * 16, 90 * 16)

    def _draw_logo(self, painter: QPainter, cx: float, cy: float, w: float):
        """Draw the app logo with a subtle scale pulse animation."""
        logo_size = 96
        if not self._logo.isNull():
            # Pulse scale: 1.0 → 1.04 → 1.0
            pulse       = 1.0 + 0.04 * math.sin(self._ring_t * math.pi)
            scaled_size = int(logo_size * pulse)
            logo_scaled = self._logo.scaled(
                scaled_size, scaled_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            lx = int(cx - logo_scaled.width()  / 2)
            ly = int(cy - logo_scaled.height() / 2) - 16
            painter.drawPixmap(lx, ly, logo_scaled)
        else:
            # Fallback: draw "M" letter if logo file is missing
            painter.setPen(QColor(255, 165, 0))
            f = painter.font()
            f.setPointSize(42)
            f.setBold(True)
            painter.setFont(f)
            painter.drawText(QRectF(0, cy - 60, w, 80), Qt.AlignmentFlag.AlignCenter, "M")

    def _draw_text(self, painter: QPainter, cx: float, cy: float, w: float):
        """Draw app name and tagline, fading in during the animation."""
        name_alpha = int(255 * min(1.0, self._ring_t * 2.5))

        # App name
        painter.setPen(QColor(255, 255, 255, name_alpha))
        f = painter.font()
        f.setFamily(Typography.FONT_FAMILY)
        f.setPointSize(15)
        f.setBold(True)
        f.setLetterSpacing(f.SpacingType.AbsoluteSpacing, 2.5)
        painter.setFont(f)
        painter.drawText(QRectF(0, cy + 52, w, 30), Qt.AlignmentFlag.AlignCenter, "MANGO DEFEND")

        # Tagline
        painter.setPen(QColor(255, 165, 0, name_alpha * 2 // 3))
        f2 = painter.font()
        f2.setFamily(Typography.FONT_FAMILY)
        f2.setPointSize(9)
        f2.setBold(False)
        f2.setLetterSpacing(f2.SpacingType.AbsoluteSpacing, 1.5)
        painter.setFont(f2)
        painter.drawText(QRectF(0, cy + 82, w, 20), Qt.AlignmentFlag.AlignCenter, "AI Malware Protection")
