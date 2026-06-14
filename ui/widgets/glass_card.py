"""
Reusable dashboard card widgets.
"""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient
from ui.styles.figma_theme import Colors
from ui.core.anim_timer import AdaptiveTimer


class GlassCard(QFrame):
    """
    Glassmorphism card with smooth hover border transition.
    Border animates white → orange as the mouse enters.
    """

    def __init__(self, parent=None, hover_effect=True):
        """Siapkan kartu kaca dengan animasi border saat mouse diarahkan ke kartu."""
        super().__init__(parent)
        self.hover_effect = hover_effect
        self._hovered = False
        self._hover_t = 0.0   # 0.0 = idle, 1.0 = fully hovered
        self.setObjectName("glassCard")
        self.setProperty("class", "glassCard")

        self._hover_timer = AdaptiveTimer(target_fps=60, parent=self)
        self._hover_timer.tick.connect(self._on_hover_tick)

    # ── Animation ─────────────────────────────────────────────────────────────

    def _on_hover_tick(self, dt: float):
        """Smoothly interpolate _hover_t toward target (0 or 1). Stops when settled."""
        target = 1.0 if self._hovered else 0.0
        speed  = 5.5 if self._hovered else 4.5
        diff   = target - self._hover_t
        if abs(diff) < 0.005:
            self._hover_t = target
            self._hover_timer.stop()
        else:
            self._hover_t += diff * (1.0 - pow(0.01, dt * speed))
        self.update()

    # ── Mouse events ──────────────────────────────────────────────────────────

    def enterEvent(self, event):
        """Start hover animation on mouse enter."""
        if self.hover_effect:
            self._hovered = True
            if not self._hover_timer.is_active():
                self._hover_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Reverse hover animation on mouse leave."""
        if self.hover_effect:
            self._hovered = False
            if not self._hover_timer.is_active():
                self._hover_timer.start()
        super().leaveEvent(event)

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        """Draw frosted glass fill and animated border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect   = self.rect()
        radius = 24.0
        t      = self._hover_t

        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), radius, radius)

        # Semi-transparent white fill
        painter.setClipPath(path)
        painter.fillPath(path, QBrush(QColor(255, 255, 255, 13)))

        # Border: white at idle → orange at hover
        painter.setClipping(False)
        border_alpha = int(26 + (77 - 26) * t)
        border_r     = int(255 * t)
        border_g     = int(255 * (1.0 - t) + 165 * t)
        border_b     = int(255 * (1.0 - t))
        border_color = QColor(border_r, border_g, border_b, border_alpha)
        painter.setPen(QPen(border_color, 1.0 + 0.5 * t))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(
            rect.x() + 0.5, rect.y() + 0.5,
            rect.width() - 1, rect.height() - 1,
            radius, radius,
        )
        painter.end()


class SoftCard(QFrame):
    """
    Softer, denser card with solid fill, drop shadow, and animated hover/press states.

    States:
    - Idle:   subtle fill + thin border
    - Hover:  orange border glow (smooth transition)
    - Press:  orange fill flash + bright border (if set_interactive(True))
    """

    clicked = Signal()

    def __init__(self, parent=None, is_dark=True, accent=None, hover_effect=True):
        """Siapkan kartu umum aplikasi yang bisa diberi tema, aksen, hover, dan klik."""
        super().__init__(parent)
        self.is_dark      = is_dark
        self.hover_effect = hover_effect
        self._hovered     = False
        self._pressed     = False
        self._hover_t     = 0.0   # 0.0 = idle, 1.0 = fully hovered
        self._press_t     = 0.0   # 0.0 = idle, 1.0 = fully pressed
        self._interactive = False
        self._radius      = 18.0
        self._accent      = QColor(accent) if accent else None

        self.setObjectName("softCard")
        self.setProperty("class", "softCard")

        # Drop shadow
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(34)
        self._shadow.setOffset(0, 12)
        self.setGraphicsEffect(self._shadow)
        self._apply_shadow()

        # Single timer drives both hover and press fade animations
        self._hover_timer = AdaptiveTimer(target_fps=60, parent=self)
        self._hover_timer.tick.connect(self._on_hover_tick)

    # ── Theme & appearance ────────────────────────────────────────────────────

    def _apply_shadow(self):
        """Update drop shadow color to match current theme."""
        self._shadow.setColor(
            QColor(0, 0, 0, 95) if self.is_dark else QColor(15, 23, 42, 28)
        )

    def set_theme(self, is_dark: bool):
        """Switch dark/light theme and refresh shadow + paint."""
        self.is_dark = is_dark
        self._apply_shadow()
        self.update()

    def set_accent(self, accent):
        """Set an optional accent color tint on the card fill."""
        self._accent = QColor(accent) if accent else None
        self.update()

    def set_interactive(self, enabled: bool):
        """Enable click interaction — shows press feedback and emits clicked signal."""
        self._interactive = enabled
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor
        )

    # ── Animation ─────────────────────────────────────────────────────────────

    def _on_hover_tick(self, dt: float):
        """Advance hover and press fade animations. Stops timer when both settled."""
        target = 1.0 if self._hovered else 0.0
        speed  = 5.5 if self._hovered else 4.5
        diff   = target - self._hover_t
        if abs(diff) >= 0.005:
            self._hover_t += diff * (1.0 - pow(0.01, dt * speed))
        else:
            self._hover_t = target

        # Press highlight fades out after mouse release
        if not self._pressed and self._press_t > 0.005:
            self._press_t -= self._press_t * (1.0 - pow(0.01, dt * 6.0))
        elif not self._pressed:
            self._press_t = 0.0

        done_hover = abs(self._hover_t - target) < 0.005
        done_press = not self._pressed and self._press_t < 0.005
        if done_hover and done_press:
            self._hover_timer.stop()
        self.update()

    # ── Mouse events ──────────────────────────────────────────────────────────

    def enterEvent(self, event):
        """Start hover animation."""
        if self.hover_effect:
            self._hovered = True
            if not self._hover_timer.is_active():
                self._hover_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Reverse hover animation."""
        if self.hover_effect:
            self._hovered = False
            if not self._hover_timer.is_active():
                self._hover_timer.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Trigger press flash if card is interactive."""
        if self._interactive and event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._press_t = 1.0
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Emit clicked signal and start press fade-out."""
        if self._interactive and event.button() == Qt.MouseButton.LeftButton:
            self._pressed = False
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit()
            if not self._hover_timer.is_active():
                self._hover_timer.start()
        super().mouseReleaseEvent(event)

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        """Draw card fill, optional accent tint, sheen, press overlay, and border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), self._radius, self._radius)

        # Base fill colors per theme
        if self.is_dark:
            top_color       = QColor(Colors.DARK_BG_TERTIARY);  top_color.setAlpha(244)
            bottom_color    = QColor(Colors.DARK_BG_SECONDARY); bottom_color.setAlpha(244)
            border_color    = QColor(Colors.DARK_TEXT_PRIMARY);  border_color.setAlpha(28)
            highlight_color = QColor(Colors.DARK_TEXT_PRIMARY);  highlight_color.setAlpha(22)
            hover_color     = QColor(Colors.ORANGE_500);         hover_color.setAlpha(85)
        else:
            top_color       = QColor(Colors.LIGHT_BG_PRIMARY);  top_color.setAlpha(250)
            bottom_color    = QColor(Colors.LIGHT_BG_SECONDARY);bottom_color.setAlpha(250)
            border_color    = QColor(Colors.LIGHT_BORDER);      border_color.setAlpha(210)
            highlight_color = QColor(Colors.LIGHT_BG_PRIMARY);  highlight_color.setAlpha(140)
            hover_color     = QColor(Colors.ORANGE_500);        hover_color.setAlpha(70)

        # Base gradient fill
        fill_gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        fill_gradient.setColorAt(0.0, top_color)
        fill_gradient.setColorAt(1.0, bottom_color)
        painter.fillPath(path, QBrush(fill_gradient))

        # Optional accent color tint
        if self._accent:
            r, g, b = self._accent.red(), self._accent.green(), self._accent.blue()
            ag = QLinearGradient(rect.topLeft(), rect.bottomRight())
            ag.setColorAt(0.0,  QColor(r, g, b, 26 if self.is_dark else 18))
            ag.setColorAt(0.55, QColor(r, g, b, 10 if self.is_dark else 6))
            ag.setColorAt(1.0,  QColor(r, g, b, 0))
            painter.fillPath(path, QBrush(ag))

        # Top sheen highlight
        painter.save()
        painter.setClipPath(path)
        sheen_rect = rect.adjusted(0, 0, 0, -rect.height() * 0.45)
        sg = QLinearGradient(sheen_rect.topLeft(), sheen_rect.bottomLeft())
        sg.setColorAt(0.0, highlight_color)
        sg.setColorAt(1.0, QColor(highlight_color.red(), highlight_color.green(), highlight_color.blue(), 0))
        painter.fillRect(sheen_rect, sg)
        painter.restore()

        def _lerp_color(a: QColor, b: QColor, f: float) -> QColor:
            """Linear interpolation between two QColors."""
            return QColor(
                int(a.red()   + (b.red()   - a.red())   * f),
                int(a.green() + (b.green() - a.green()) * f),
                int(a.blue()  + (b.blue()  - a.blue())  * f),
                int(a.alpha() + (b.alpha() - a.alpha()) * f),
            )

        # Press overlay — orange flash on click
        pt = self._press_t
        if pt > 0.001:
            press_fill = QColor(Colors.ORANGE_500)
            press_fill.setAlpha(int(55 * pt))
            painter.fillPath(path, QBrush(press_fill))

        # Border: idle → hover orange → press bright orange
        t             = self._hover_t
        press_border  = QColor(Colors.ORANGE_500); press_border.setAlpha(220)
        blended       = _lerp_color(border_color, hover_color, t)
        if pt > 0.001:
            blended = _lerp_color(blended, press_border, pt)

        painter.setPen(QPen(blended, 1.0 + 0.4 * t + 0.6 * pt))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, self._radius, self._radius)

        painter.end()


class SpotlightCard(QFrame):
    """
    Dark showcase card with thick border and strong contrast.
    Best for compact KPI tiles that need a premium focal look.
    """

    def __init__(self, parent=None, is_dark=True, hover_effect=True):
        """Siapkan kartu sorotan untuk informasi penting dengan border kuat."""
        super().__init__(parent)
        self.is_dark      = is_dark
        self.hover_effect = hover_effect
        self._hovered     = False
        self._radius      = 30.0

        self.setObjectName("spotlightCard")
        self.setProperty("class", "spotlightCard")

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(24)
        self._shadow.setOffset(0, 10)
        self.setGraphicsEffect(self._shadow)
        self._apply_shadow()

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _apply_shadow(self):
        """Update shadow color for current theme."""
        self._shadow.setColor(
            QColor(0, 0, 0, 90) if self.is_dark else QColor(15, 23, 42, 26)
        )

    def set_theme(self, is_dark: bool):
        """Switch theme and repaint."""
        self.is_dark = is_dark
        self._apply_shadow()
        self.update()

    # ── Mouse events ──────────────────────────────────────────────────────────

    def enterEvent(self, event):
        """Thicken border on hover."""
        if self.hover_effect:
            self._hovered = True
            self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Restore border on leave."""
        if self.hover_effect:
            self._hovered = False
            self.update()
        super().leaveEvent(event)

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        """Draw gradient fill, top sheen, thick outer border, and thin inner border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(rect, self._radius, self._radius)

        if self.is_dark:
            start_color  = QColor(Colors.DARK_BG_TERTIARY)
            end_color    = QColor(Colors.DARK_BG_SECONDARY)
            top_sheen    = QColor(Colors.DARK_TEXT_PRIMARY); top_sheen.setAlpha(20)
            border_color = QColor(Colors.DARK_BG_PRIMARY)
            inner_color  = QColor(Colors.DARK_TEXT_PRIMARY); inner_color.setAlpha(18)
        else:
            start_color  = QColor(Colors.LIGHT_BG_PRIMARY)
            end_color    = QColor(Colors.LIGHT_BG_SECONDARY)
            top_sheen    = QColor(Colors.ORANGE_500); top_sheen.setAlpha(18)
            border_color = QColor(Colors.LIGHT_BORDER)
            inner_color  = QColor(Colors.ORANGE_500); inner_color.setAlpha(28)

        # Base gradient
        base_gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        base_gradient.setColorAt(0.0, start_color)
        base_gradient.setColorAt(1.0, end_color)
        painter.fillPath(path, QBrush(base_gradient))

        # Top sheen
        painter.save()
        painter.setClipPath(path)
        sheen_rect = rect.adjusted(0, 0, 0, -int(rect.height() * 0.54))
        sg = QLinearGradient(sheen_rect.topLeft(), sheen_rect.bottomLeft())
        sg.setColorAt(0.0, top_sheen)
        sg.setColorAt(1.0, QColor(Colors.DARK_TEXT_PRIMARY if self.is_dark else Colors.ORANGE_500, 0))
        painter.fillRect(sheen_rect, sg)
        painter.restore()

        # Outer border (thickens slightly on hover)
        painter.setPen(QPen(border_color, 4 if not self._hovered else 4.6))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, self._radius, self._radius)

        # Inner border accent line
        painter.setPen(QPen(inner_color, 1))
        painter.drawRoundedRect(rect.adjusted(4, 4, -4, -4), self._radius - 4, self._radius - 4)

        painter.end()


class StatCard(QFrame):
    """
    Minimal stat card with orange tint background and border.
    Used for small KPI numbers in the dashboard.
    """

    def __init__(self, parent=None, is_dark=True):
        """Siapkan kartu statistik kecil yang hanya perlu menggambar background sendiri."""
        super().__init__(parent)
        self.is_dark = is_dark
        self.setObjectName("statCard")

    def paintEvent(self, event):
        """Draw orange-tinted rounded background and border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect   = self.rect()
        radius = 20.0

        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), radius, radius)

        # Orange tint fill
        painter.fillPath(path, QBrush(QColor(255, 165, 0, 25)))

        # Orange border
        painter.setPen(QPen(QColor(255, 165, 0, 51), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(
            rect.x() + 0.5, rect.y() + 0.5,
            rect.width() - 1, rect.height() - 1,
            radius, radius
        )

        painter.end()
