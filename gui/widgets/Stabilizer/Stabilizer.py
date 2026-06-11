import asyncio
from datetime import datetime
import time
import gui.crate as crate
from gui import compiler
from typing import Optional
from PySide6.QtCore import QTimer, Qt
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from gui.widgets.Stabilizer.pid_kai_receiver import ReceiverState, UdpReceiverProtocol, parse_pid_datagram_to_batches
from gui.widgets.Stabilizer.UpdateWidget import UpdateWidget
from gui.widgets.Stabilizer import set_stabilizer


DEFAULT_DEVICE_PORT = 2177

FULL_SCALE_CODE = 32768
FULL_SCALE_VOLTS = 10.24
CODE_PER_VOLT = FULL_SCALE_CODE / FULL_SCALE_VOLTS

def _indicator_stylesheet(color_hex: str) -> str:
    return (
        "QLabel {"
        f"background-color: {color_hex};"
        "border: 1px solid #333;"
        "border-radius: 6px;"
        "}"
    )
class StabilizerDock(QDockWidget):
    def __init__(self, gui, parent: QWidget | None = None):
        super().__init__("Stabilizer pid_kai", parent)
        self.setObjectName("StabilizerDock")

        self.gui = gui

        # Track start/stop tasks so we can cancel them during shutdown.
        self._receiver_op_task: Optional[asyncio.Task] = None

        app = QCoreApplication.instance()
        if app is not None:
            try:
                app.aboutToQuit.connect(self._on_app_about_to_quit)
            except Exception:
                pass

        self._state = ReceiverState()

        self._port_edit = QLineEdit(str(DEFAULT_DEVICE_PORT))
        self._port_edit.setPlaceholderText("UDP port")
        self._receive_button = QPushButton("Receive")
        self._receive_button.clicked.connect(self._on_receive_clicked)

        self._rx_indicator = QLabel()
        self._rx_indicator.setFixedSize(14, 14)
        self._rx_indicator.setToolTip("UDP activity: green = packet within last 0.1s")
        self._last_packet_monotonic = 0.0
        self._set_rx_indicator_recent(False)

        self._rx_indicator_timer = QTimer(self)
        self._rx_indicator_timer.setInterval(25)
        self._rx_indicator_timer.timeout.connect(self._update_rx_indicator)
        self._rx_indicator_timer.start()

        self._scope_box = self._build_scope_box()
        self._display_box = self._build_display_box()
        self._update_widget = UpdateWidget(self)
        self._set_parameters_box = self._build_set_parameters_box()
        self._build_layout()

        # Sync initial slider values to the scope (if available).
        self._apply_dot_alpha(self._dot_alpha_slider.value())
        self._apply_fade_alpha(self._fade_alpha_slider.value())
        self._apply_x_offset(self._x_offset_slider.value())
        self._apply_x_zoom(self._x_zoom_slider.value())
        self._apply_y_offset(self._y_offset_slider.value())
        self._apply_y_zoom(self._y_zoom_slider.value())

    def _set_rx_indicator_recent(self, recent: bool) -> None:
        if recent:
            self._rx_indicator.setStyleSheet(_indicator_stylesheet("#2ecc71"))
        else:
            self._rx_indicator.setStyleSheet(_indicator_stylesheet("#e74c3c"))

    def _update_rx_indicator(self) -> None:
        if not self._state.is_receiving:
            self._set_rx_indicator_recent(False)
            return
        now = time.monotonic()
        recent = (self._last_packet_monotonic > 0.0) and ((now - self._last_packet_monotonic) <= 0.1)
        self._set_rx_indicator_recent(recent)

    def _build_display_box(self) -> QWidget:
        box = QGroupBox("Display")
        layout = QGridLayout(box)

        self._ch1_checkbox = QCheckBox("CH1")
        self._ch2_checkbox = QCheckBox("CH2")
        self._ch1_checkbox.setChecked(True)
        self._ch2_checkbox.setChecked(True)
        self._ch1_checkbox.toggled.connect(lambda enabled: self._apply_channel_enabled(1, enabled))
        self._ch2_checkbox.toggled.connect(lambda enabled: self._apply_channel_enabled(2, enabled))

        self._dot_alpha_slider = QSlider()
        self._dot_alpha_slider.setOrientation(Qt.Orientation.Horizontal)
        self._dot_alpha_slider.setRange(0, 255)
        self._dot_alpha_slider.setValue(50)
        self._dot_alpha_value = QLabel("50")
        self._dot_alpha_slider.valueChanged.connect(self._apply_dot_alpha)

        self._fade_alpha_slider = QSlider()
        self._fade_alpha_slider.setOrientation(Qt.Orientation.Horizontal)
        self._fade_alpha_slider.setRange(0, 255)
        self._fade_alpha_slider.setValue(18)
        self._fade_alpha_value = QLabel("18")
        self._fade_alpha_slider.valueChanged.connect(self._apply_fade_alpha)

        self._x_offset_slider = QSlider()
        self._x_offset_slider.setOrientation(Qt.Orientation.Horizontal)
        # Use millivolts so the UI is in volts but still precise.
        self._x_offset_slider.setRange(-10240, 10240)
        self._x_offset_slider.setValue(0)
        self._x_offset_value = QLabel("0.000 V")
        self._x_offset_slider.valueChanged.connect(self._apply_x_offset)

        self._x_zoom_slider = QSlider()
        self._x_zoom_slider.setOrientation(Qt.Orientation.Horizontal)
        self._x_zoom_slider.setRange(100, 10000)
        self._x_zoom_slider.setValue(100)
        self._x_zoom_value = QLabel("1.00x")
        self._x_zoom_slider.valueChanged.connect(self._apply_x_zoom)

        self._y_offset_slider = QSlider()
        self._y_offset_slider.setOrientation(Qt.Orientation.Horizontal)
        self._y_offset_slider.setRange(-10240, 10240)
        self._y_offset_slider.setValue(0)
        self._y_offset_value = QLabel("0.000 V")
        self._y_offset_slider.valueChanged.connect(self._apply_y_offset)

        self._y_zoom_slider = QSlider()
        self._y_zoom_slider.setOrientation(Qt.Orientation.Horizontal)
        self._y_zoom_slider.setRange(100, 10000)
        self._y_zoom_slider.setValue(100)
        self._y_zoom_value = QLabel("1.00x")
        self._y_zoom_slider.valueChanged.connect(self._apply_y_zoom)

        layout.addWidget(self._ch1_checkbox, 0, 0)
        layout.addWidget(self._ch2_checkbox, 0, 1)

        layout.addWidget(QLabel("Dot alpha:"), 1, 0)
        layout.addWidget(self._dot_alpha_slider, 1, 1)
        layout.addWidget(self._dot_alpha_value, 1, 2)

        layout.addWidget(QLabel("Fade alpha:"), 2, 0)
        layout.addWidget(self._fade_alpha_slider, 2, 1)
        layout.addWidget(self._fade_alpha_value, 2, 2)

        layout.addWidget(QLabel("X offset:"), 3, 0)
        layout.addWidget(self._x_offset_slider, 3, 1)
        layout.addWidget(self._x_offset_value, 3, 2)

        layout.addWidget(QLabel("X zoom:"), 4, 0)
        layout.addWidget(self._x_zoom_slider, 4, 1)
        layout.addWidget(self._x_zoom_value, 4, 2)

        layout.addWidget(QLabel("Y offset:"), 5, 0)
        layout.addWidget(self._y_offset_slider, 5, 1)
        layout.addWidget(self._y_offset_value, 5, 2)

        layout.addWidget(QLabel("Y zoom:"), 6, 0)
        layout.addWidget(self._y_zoom_slider, 6, 1)
        layout.addWidget(self._y_zoom_value, 6, 2)

        layout.setColumnStretch(1, 1)
        return box

    def _build_set_parameters_box(self) -> QWidget:
        box = QGroupBox("Set Parameters")
        layout = QGridLayout(box)

        layout.addWidget(QLabel("SPI Device:"), 0, 0)

        self._set_parameters_combo = QComboBox()
        devices: list[str] = []
        try:
            device_db = getattr(crate, "device_db", {})
            if isinstance(device_db, dict):
                for device_name, info in device_db.items():
                    module = None
                    if isinstance(info, dict):
                        module = info.get("module")
                    else:
                        module = getattr(info, "module", None)
                    if module == "artiq.coredevice.spi2" and "stab" in device_name.lower():
                        devices.append(str(device_name))
        except Exception:
            devices = []

        devices = sorted(set(devices))
        if devices:
            self._set_parameters_combo.addItems(devices)
            self._set_parameters_combo.setEnabled(True)
        else:
            self._set_parameters_combo.addItem("(no spi2 devices)")
            self._set_parameters_combo.setEnabled(False)

        layout.addWidget(self._set_parameters_combo, 0, 1)
        layout.setColumnStretch(1, 1)

        self._send_to_device_button = QPushButton("Send to Device")
        self._send_to_device_button.clicked.connect(self._on_send_to_device_clicked)
        layout.addWidget(self._send_to_device_button, 1, 0, 1, 2)

        layout.addWidget(self._update_widget, 2, 0, 1, 2)
        layout.setRowStretch(2, 1)

        return box

    def _on_send_to_device_clicked(self) -> None:
        try:
            if not self._set_parameters_combo.isEnabled():
                QMessageBox.warning(self, "Send to Device", "No SPI device available (no spi2 devices in device_db).")
                return

            stabilizer_device_name = self._set_parameters_combo.currentText().strip()
            if not stabilizer_device_name or stabilizer_device_name.startswith("("):
                QMessageBox.warning(self, "Send to Device", "Please select a valid SPI device.")
                return

            updates = self._update_widget.visible_updates()

            codeID = int(datetime.now().strftime("%Y%m%d%H%M%S%f"))
            code = set_stabilizer.build_script(stabilizer_device_name, updates, codeID)
            compiler.submit_generated_code(
                code=code,
                codeID=codeID,
                class_name="StabilizerPidKaiSpi",
                arguments={},
                duration=None,
                filename_prefix="stabilizer_",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Send to Device", f"Failed to build script: {exc}")

    def _apply_channel_enabled(self, channel: int, enabled: bool) -> None:
        try:
            if self._scope_widget is not None:
                self._scope_widget.set_channel_enabled(int(channel), bool(enabled))
        except Exception:
            pass

    def _apply_dot_alpha(self, value: int) -> None:
        self._dot_alpha_value.setText(str(int(value)))
        try:
            if self._scope_widget is not None:
                self._scope_widget.set_dot_alpha(int(value))
        except Exception:
            pass

    def _apply_fade_alpha(self, value: int) -> None:
        self._fade_alpha_value.setText(str(int(value)))
        try:
            if self._scope_widget is not None:
                self._scope_widget.set_fade_alpha(int(value))
        except Exception:
            pass

    def _apply_x_offset(self, value: int) -> None:
        volts = float(value) / 1000.0
        self._x_offset_value.setText(f"{volts:.3f} V")
        try:
            if self._scope_widget is not None:
                self._scope_widget.set_x_offset_code(int(round(volts * CODE_PER_VOLT)))
        except Exception:
            pass

    def _apply_x_zoom(self, value: int) -> None:
        zoom = float(value) / 100.0
        self._x_zoom_value.setText(f"{zoom:.2f}x")
        try:
            if self._scope_widget is not None:
                self._scope_widget.set_x_zoom(zoom)
        except Exception:
            pass

    def _apply_y_offset(self, value: int) -> None:
        volts = float(value) / 1000.0
        self._y_offset_value.setText(f"{volts:.3f} V")
        try:
            if self._scope_widget is not None:
                self._scope_widget.set_y_offset_code(int(round(volts * CODE_PER_VOLT)))
        except Exception:
            pass

    def _apply_y_zoom(self, value: int) -> None:
        zoom = float(value) / 100.0
        self._y_zoom_value.setText(f"{zoom:.2f}x")
        try:
            if self._scope_widget is not None:
                self._scope_widget.set_y_zoom(zoom)
        except Exception:
            pass

    def _build_scope_box(self) -> QWidget:
        box = QGroupBox("XY Scope")
        layout = QVBoxLayout(box)

        self._scope_widget = None
        try:
            from gui.widgets.Stabilizer.xy_scope_widget import XyScopeWidget

            scope = XyScopeWidget()
            scope.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            layout.addWidget(scope)

            # Ensure the requested full-scale mapping.
            scope.set_full_scale(code=32768, volts=10.24)
            self._scope_widget = scope

            # If display checkboxes exist already, sync to current state.
            try:
                if hasattr(self, "_ch1_checkbox"):
                    scope.set_channel_enabled(1, self._ch1_checkbox.isChecked())
                if hasattr(self, "_ch2_checkbox"):
                    scope.set_channel_enabled(2, self._ch2_checkbox.isChecked())
            except Exception:
                pass
        except Exception as exc:
            label = QLabel(f"XY scope unavailable: {exc}")
            label.setWordWrap(True)
            layout.addWidget(label)

        return box

    def _build_layout(self) -> None:
        controls = QGroupBox("Receiver")
        controls_layout = QGridLayout(controls)
        controls_layout.addWidget(QLabel("Port:"), 0, 0)
        controls_layout.addWidget(self._port_edit, 0, 1)
        controls_layout.addWidget(self._receive_button, 0, 2)
        controls_layout.addWidget(self._rx_indicator, 0, 3)
        controls_layout.setColumnStretch(1, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(controls)
        left_layout.addWidget(self._display_box)
        left_layout.addWidget(self._set_parameters_box)
        left_layout.addStretch(1)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setWidget(left)
        left_scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        splitter = QSplitter()
        splitter.addWidget(left_scroll)
        splitter.addWidget(self._scope_box)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 2)

        root = QWidget(self)
        root_layout = QHBoxLayout(root)
        root_layout.addWidget(splitter)
        self.setWidget(root)

    def closeEvent(self, event):  # type: ignore[override]
        self._cancel_receiver_op_task()
        self._stop_receiver_sync()
        super().closeEvent(event)

    def _on_receive_clicked(self) -> None:
        # Avoid overlapping start/stop operations which can leave transports open.
        if self._state.is_receiving:
            self._start_receiver_op(self._stop_receiver())
        else:
            self._start_receiver_op(self._start_receiver())

    def _start_receiver_op(self, coro) -> None:
        self._cancel_receiver_op_task()
        try:
            task = asyncio.create_task(coro)
        except RuntimeError:
            # No running event loop (e.g. during shutdown). Fall back to sync stop.
            self._stop_receiver_sync()
            return

        self._receiver_op_task = task
        task.add_done_callback(lambda _t: setattr(self, "_receiver_op_task", None))

    def _cancel_receiver_op_task(self) -> None:
        task = self._receiver_op_task
        if task is not None and not task.done():
            try:
                task.cancel()
            except Exception:
                pass
        self._receiver_op_task = None

    def _on_app_about_to_quit(self) -> None:
        # Ensure the UDP transport is closed even if the dock was never explicitly closed.
        self._cancel_receiver_op_task()
        self._stop_receiver_sync()

    async def _start_receiver(self) -> None:
        port_text = self._port_edit.text().strip()
        try:
            port = int(port_text)
            if not (1 <= port <= 65535):
                raise ValueError("port out of range")
        except Exception:
            QMessageBox.warning(self, "Invalid Port", f"Invalid UDP port: {port_text!r}")
            return

        await self._stop_receiver()

        loop = asyncio.get_running_loop()
        self._last_packet_monotonic = 0.0
        self._update_rx_indicator()

        def on_datagram(data: bytes, addr) -> None:
            self._last_packet_monotonic = time.monotonic()
            batches = parse_pid_datagram_to_batches(data)
            if batches is None:
                return

            try:
                if self._scope_widget is None:
                    return

                # Enqueue ALL samples from ALL batches.
                # Channel mapping: CH1=(adc0,dac0), CH2=(adc1,dac1)
                for pkt in batches:
                    adc0 = pkt.get("adc0")
                    adc1 = pkt.get("adc1")
                    dac0 = pkt.get("dac0")
                    dac1 = pkt.get("dac1")

                    if isinstance(adc0, list) and isinstance(dac0, list) and adc0 and dac0:
                        self._scope_widget.enqueue_channel_xy_codes(1, dac0, adc0)
                    if isinstance(adc1, list) and isinstance(dac1, list) and adc1 and dac1:
                        self._scope_widget.enqueue_channel_xy_codes(2, dac1, adc1)
            except Exception:
                return

        try:
            transport, protocol = await loop.create_datagram_endpoint(
                lambda: UdpReceiverProtocol(on_datagram),
                local_addr=("0.0.0.0", port),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Bind Failed", f"Failed to bind UDP port {port}: {exc}")
            return

        self._state.transport = transport
        self._state.protocol = protocol
        self._state.is_receiving = True
        self._receive_button.setText("Stop")
        self._update_rx_indicator()

    async def _stop_receiver(self) -> None:
        transport = self._state.transport
        if transport is not None:
            try:
                # On Windows (Proactor), abort() is often required to cancel pending receives cleanly.
                abort = getattr(transport, "abort", None)
                if callable(abort):
                    abort()
                else:
                    transport.close()
            except Exception:
                pass

        # Give the event loop a chance to process the close/abort.
        try:
            await asyncio.sleep(0)
        except Exception:
            pass
        self._state = ReceiverState()
        self._receive_button.setText("Receive")
        self._last_packet_monotonic = 0.0
        self._update_rx_indicator()

    def _stop_receiver_sync(self) -> None:
        transport = self._state.transport
        if transport is not None:
            try:
                abort = getattr(transport, "abort", None)
                if callable(abort):
                    abort()
                else:
                    transport.close()
            except Exception:
                pass
        self._state = ReceiverState()
        self._receive_button.setText("Receive")
        self._last_packet_monotonic = 0.0
        self._update_rx_indicator()

    async def shutdown_async(self) -> None:
        await self._stop_receiver()
