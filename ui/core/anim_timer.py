"""
Adaptive animation timer — delta-time based.

Instead of firing at a fixed interval and moving a fixed amount per tick,
every tick reports how many *seconds* actually elapsed since the last tick.
Callers multiply their speed by that delta so animation runs at the same
perceived speed regardless of how fast or slow the host machine is.

Usage:
    timer = AdaptiveTimer(target_fps=60)
    timer.tick.connect(lambda dt: self._update(dt))
    timer.start()

    def _update(self, dt: float):
        self.angle = (self.angle + 270 * dt) % 360   # 270 deg/sec always
        self.update()
"""

from __future__ import annotations
import time
from PySide6.QtCore import QObject, QTimer, Signal, Qt


class AdaptiveTimer(QObject):
    """
    QTimer wrapper that emits a `tick(dt)` signal where dt is the real
    elapsed time in seconds since the previous tick.

    - target_fps: desired tick rate (default 60). The QTimer interval is set
      to 1000/target_fps ms, but the actual dt is measured with time.perf_counter
      so late/early ticks are automatically compensated.
    - max_dt: clamp to avoid huge jumps after tab-switches / suspends (default 0.1s).
    """

    tick = Signal(float)  # dt in seconds

    def __init__(self, target_fps: int = 60, max_dt: float = 0.1,
                 parent: QObject | None = None):
        """Initialize the adaptive timer with a target frame rate and maximum delta clamp."""
        super().__init__(parent)
        self._max_dt = max_dt
        self._last_t: float | None = None

        interval_ms = max(1, int(1000 / target_fps))
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._on_tick)

    def start(self):
        """Record the start time and begin emitting tick signals."""
        self._last_t = time.perf_counter()
        self._timer.start()

    def stop(self):
        """Stop emitting tick signals and reset the last timestamp."""
        self._timer.stop()
        self._last_t = None

    def is_active(self) -> bool:
        """Return True if the underlying QTimer is currently running."""
        return self._timer.isActive()

    def _on_tick(self):
        """Compute the delta time since the last tick, clamp it, and emit the tick signal."""
        now = time.perf_counter()
        if self._last_t is None:
            self._last_t = now
        dt = min(now - self._last_t, self._max_dt)
        self._last_t = now
        self.tick.emit(dt)
