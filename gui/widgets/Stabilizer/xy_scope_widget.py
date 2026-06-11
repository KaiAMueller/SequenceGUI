from __future__ import annotations

from collections import deque

from PySide6.QtCore import Qt
from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QPainter, QPen

try:
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
except Exception as exc:  # pragma: no cover
    raise ImportError("PySide6 QtOpenGLWidgets is not available") from exc


class XyScopeWidget(QOpenGLWidget):
    """Minimal XY scope widget.

    For now it renders a dot at (0,0) for each enabled channel.
    Coordinates are in "scope space" where origin maps to the widget center.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ch1_enabled = True
        self._ch2_enabled = True
        self._ch1_color_base = QColor(255, 80, 80)
        self._ch2_color_base = QColor(80, 200, 255)
        self._dot_alpha = 50
        self._ch1_color = QColor(self._ch1_color_base)
        self._ch2_color = QColor(self._ch2_color_base)
        self._ch1_color.setAlpha(self._dot_alpha)
        self._ch2_color.setAlpha(self._dot_alpha)
        self._dot_radius_px = 4

        # Preserve the previous framebuffer contents so we can do phosphor-like fade.
        try:
            self.setUpdateBehavior(QOpenGLWidget.UpdateBehavior.PartialUpdate)
        except Exception:
            pass

        # Fade strength: each frame overlays a translucent background.
        # Smaller alpha -> longer persistence.
        self._fade_alpha = 18

        # Full-scale ranges (code units and volts). The GUI maps code units linearly.
        # Requested: -32768..32768 corresponds to -10.24..10.24 V.
        self._full_scale_code = 32768
        self._full_scale_volts = 10.24

        # View transform (applied in code-unit space):
        # offset shifts the origin; zoom scales normalized coordinates.
        self._x_offset_code = 0
        self._y_offset_code = 0
        self._x_zoom = 1.0
        self._y_zoom = 1.0

        # Queue of incoming samples to be drawn once.
        # Items: (channel, x_code, y_code)
        self._queue_capacity = 20000
        self._pending_points: deque[tuple[int, int, int]] = deque(maxlen=self._queue_capacity)
        self._update_pending = False

        # Keep repainting so the fade continues even if data pauses.
        self._decay_timer = QTimer(self)
        self._decay_timer.setInterval(16)  # ~60 Hz
        self._decay_timer.timeout.connect(self._on_decay_tick)
        self._decay_timer.start()

    def set_channel_enabled(self, channel: int, enabled: bool) -> None:
        if channel == 1:
            self._ch1_enabled = enabled
        elif channel == 2:
            self._ch2_enabled = enabled
        self._request_update()

    def set_channel_xy_code(self, channel: int, x_code: int, y_code: int) -> None:
        x = int(max(-self._full_scale_code, min(self._full_scale_code, x_code)))
        y = int(max(-self._full_scale_code, min(self._full_scale_code, y_code)))
        self._pending_points.append((int(channel), x, y))
        self._request_update()

    def enqueue_channel_xy_codes(self, channel: int, x_codes: list[int], y_codes: list[int]) -> None:
        """Enqueue many samples for one channel with a single repaint request."""
        ch = int(channel)
        fs = int(self._full_scale_code)
        n = min(len(x_codes), len(y_codes))
        if n <= 0:
            return

        append = self._pending_points.append
        for i in range(n):
            x = int(x_codes[i])
            y = int(y_codes[i])
            if x > fs:
                x = fs
            elif x < -fs:
                x = -fs
            if y > fs:
                y = fs
            elif y < -fs:
                y = -fs
            append((ch, x, y))

        self._request_update()

    def set_full_scale(self, *, code: int = 32768, volts: float = 10.24) -> None:
        self._full_scale_code = int(code)
        self._full_scale_volts = float(volts)
        self._request_update()

    def set_fade_alpha(self, alpha: int) -> None:
        self._fade_alpha = int(max(0, min(255, alpha)))
        self._request_update()

    def set_dot_alpha(self, alpha: int) -> None:
        """Set alpha (opacity) for both channel dot colors."""
        self._dot_alpha = int(max(0, min(255, alpha)))
        self._ch1_color = QColor(self._ch1_color_base)
        self._ch2_color = QColor(self._ch2_color_base)
        self._ch1_color.setAlpha(self._dot_alpha)
        self._ch2_color.setAlpha(self._dot_alpha)
        self._request_update()

    def set_queue_capacity(self, capacity: int) -> None:
        capacity = int(max(1, capacity))
        if capacity == self._queue_capacity:
            return
        self._queue_capacity = capacity
        old = list(self._pending_points)
        self._pending_points = deque(old[-capacity:], maxlen=capacity)

    def set_x_offset_code(self, offset_code: int) -> None:
        self._x_offset_code = int(offset_code)
        self._request_update()

    def set_y_offset_code(self, offset_code: int) -> None:
        self._y_offset_code = int(offset_code)
        self._request_update()

    def set_x_zoom(self, zoom: float) -> None:
        self._x_zoom = float(max(1e-6, zoom))
        self._request_update()

    def set_y_zoom(self, zoom: float) -> None:
        self._y_zoom = float(max(1e-6, zoom))
        self._request_update()

    def _request_update(self) -> None:
        if not self._update_pending:
            self._update_pending = True
            self.update()

    def _on_decay_tick(self) -> None:
        # Always repaint for decay; cheap when nothing changes.
        self.update()

    def paintGL(self) -> None:  # type: ignore[override]
        self._update_pending = False
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            # Phosphor fade: overlay a translucent dark rect.
            painter.fillRect(self.rect(), QColor(12, 12, 14, self._fade_alpha))

            w = self.width()
            h = self.height()
            cx = w // 2
            cy = h // 2

            radius = max(1, self._dot_radius_px)
            pad = 10 + radius
            span = max(1, min(w, h) // 2 - pad)

            def map_code_to_px(x_code: int, y_code: int) -> tuple[int, int] | None:
                fs = float(self._full_scale_code) if self._full_scale_code else 32768.0
                x_norm = (float(x_code) + float(self._x_offset_code)) / fs
                y_norm = (float(y_code) + float(self._y_offset_code)) / fs
                x_norm *= float(self._x_zoom)
                y_norm *= float(self._y_zoom)
                # If the point is outside the current view, don't draw it.
                if x_norm < -1.0 or x_norm > 1.0 or y_norm < -1.0 or y_norm > 1.0:
                    return None
                x_px = int(round(cx + x_norm * span))
                y_px = int(round(cy - y_norm * span))
                return x_px, y_px

            grid_pen = QPen(QColor(60, 60, 65))
            grid_pen.setWidth(1)
            painter.setPen(grid_pen)
            painter.drawLine(0, cy, w, cy)
            painter.drawLine(cx, 0, cx, h)

            # Light border.
            painter.setPen(QPen(QColor(40, 40, 45)))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

            # Axis labels (minimal).
            painter.setPen(QColor(150, 150, 155))
            fs_code = float(self._full_scale_code) if self._full_scale_code else 32768.0
            fs_v = float(self._full_scale_volts)
            x_zoom = float(self._x_zoom) if self._x_zoom else 1.0
            y_zoom = float(self._y_zoom) if self._y_zoom else 1.0

            # Visible window in code units (inverse of the mapping), then convert to volts.
            x_min_code = (-fs_code / x_zoom) - float(self._x_offset_code)
            x_max_code = (fs_code / x_zoom) - float(self._x_offset_code)
            y_min_code = (-fs_code / y_zoom) - float(self._y_offset_code)
            y_max_code = (fs_code / y_zoom) - float(self._y_offset_code)

            x_min_v = x_min_code / fs_code * fs_v
            x_max_v = x_max_code / fs_code * fs_v
            y_min_v = y_min_code / fs_code * fs_v
            y_max_v = y_max_code / fs_code * fs_v

            painter.drawText(8, 16, f"X: {x_min_v:.2f} .. {x_max_v:.2f} V")
            painter.drawText(8, 32, f"Y: {y_min_v:.2f} .. {y_max_v:.2f} V")

            # Drain and render all queued points once.
            while self._pending_points:
                ch, x_code, y_code = self._pending_points.popleft()
                if ch == 1:
                    if not self._ch1_enabled:
                        continue
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(self._ch1_color)
                elif ch == 2:
                    if not self._ch2_enabled:
                        continue
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(self._ch2_color)
                else:
                    continue

                mapped = map_code_to_px(x_code, y_code)
                if mapped is None:
                    continue
                x_px, y_px = mapped
                painter.drawEllipse(x_px - radius, y_px - radius, 2 * radius, 2 * radius)
        finally:
            painter.end()
