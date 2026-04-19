import sys
import time
import serial
import serial.tools.list_ports
import pandas as pd
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QLabel,
    QFrame,
    QSizePolicy,
    QComboBox,
    QLineEdit,
    QGridLayout,
    QInputDialog,
)
from PyQt6.QtCore import Qt, QTimer, QTime
from PyQt6.QtGui import QFont, QPixmap, QColor, QPalette

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ─── CONFIG ──────────────────────────────────────────────────────────────────
WINDOW_SIZE = 60
ANIMATION_SPEED = 33
LOGO_FILENAME = "logo.jpeg"
DEFAULT_BAUD = 9600
DEFAULT_FORMAT = "pressure"

# ─── PALETTE ─────────────────────────────────────────────────────────────────
C_BG = "#F0F4F8"
C_CARD = "#FFFFFF"
C_CARD2 = "#F7F9FC"
C_BORDER = "#D1D9E0"
C_TEXT = "#1A202C"
C_SUBTEXT = "#64748B"
C_ACCENT = "#1D6FEB"
C_GREEN = "#16A34A"
C_RED = "#DC2626"
C_PURPLE = "#7C3AED"
C_TEAL = "#0891B2"
C_ORANGE = "#EA580C"
C_DIVIDER = "#E2E8F0"
GRAPH_BG = "#F8FAFC"
GRAPH_GRID = "#CBD5E1"


# ─── GRAPH ───────────────────────────────────────────────────────────────────
class PressureGraphCanvas(FigureCanvas):
    def __init__(self):
        self.fig = Figure(facecolor=C_CARD)
        self.ax = self.fig.add_subplot(111)
        self._style()
        self.fig.subplots_adjust(left=0.07, right=0.97, top=0.90, bottom=0.10)
        super().__init__(self.fig)
        self.setStyleSheet("background: transparent;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _style(self):
        self.ax.set_facecolor(GRAPH_BG)
        for s in self.ax.spines.values():
            s.set_color(C_BORDER)
        self.ax.grid(True, alpha=0.5, color=GRAPH_GRID, linestyle="--", linewidth=0.7)
        self.ax.tick_params(colors=C_SUBTEXT, labelsize=8)
        self.ax.set_title(
            "Real-Time Volume Monitor",
            color=C_TEXT,
            fontsize=11,
            fontweight="bold",
            pad=6,
        )
        self.ax.set_ylabel("Volume (ml)", color=C_SUBTEXT, fontsize=9)

    def update_plot(self, x, y):
        self.ax.clear()
        self._style()
        if y:
            self.ax.plot(x, y, color=C_TEAL, linewidth=2.2, zorder=3)
            self.ax.fill_between(x, y, alpha=0.10, color=C_TEAL, zorder=2)
            if len(y) > 1:
                self.ax.axhline(
                    max(y), color=C_RED, linestyle=":", alpha=0.45, linewidth=1
                )
                self.ax.axhline(
                    min(y), color=C_GREEN, linestyle=":", alpha=0.45, linewidth=1
                )
        self.draw()


# ─── HELPERS ─────────────────────────────────────────────────────────────────
def card(radius=12, bg=None):
    f = QFrame()
    f.setStyleSheet(
        f"QFrame{{background:{bg or C_CARD};border-radius:{radius}px;border:1px solid {C_BORDER};}}"
    )
    return f


def hdiv():
    d = QFrame()
    d.setFrameShape(QFrame.Shape.HLine)
    d.setFixedHeight(1)
    d.setStyleSheet(f"background:{C_DIVIDER};border:none;max-height:1px;")
    return d


def sublabel(text, size=10, bold=False):
    l = QLabel(text)
    w = QFont.Weight.Bold if bold else QFont.Weight.Normal
    l.setFont(QFont("Segoe UI", size, w))
    l.setStyleSheet(f"color:{C_SUBTEXT};background:transparent;border:none;")
    return l


def vallabel(text, color, size=13, bold=True):
    l = QLabel(text)
    w = QFont.Weight.Bold if bold else QFont.Weight.Normal
    l.setFont(QFont("Segoe UI", size, w))
    l.setStyleSheet(f"color:{color};background:transparent;border:none;")
    return l


# ─── INLINE-EDITABLE PATIENT CELL ────────────────────────────────────────────
# Shared style strings
_GHOST = (  # unfocused: looks like plain text
    "QLineEdit, QComboBox {"
    f"  background: transparent;"
    f"  color: {C_TEXT};"
    f"  border: none;"
    f"  border-bottom: 1.5px dashed transparent;"
    f"  border-radius: 0px;"
    f"  padding: 0px 2px;"
    f"  font-size: 13px; font-weight: bold;"
    "}"
    "QComboBox::drop-down { border: none; width: 0px; }"
    "QComboBox::down-arrow { image: none; width: 0px; }"
)
_ACTIVE = (  # focused: proper input appearance
    "QLineEdit, QComboBox {"
    f"  background: {C_CARD2};"
    f"  color: {C_TEXT};"
    f"  border: 1.5px solid {C_ACCENT};"
    f"  border-radius: 6px;"
    f"  padding: 2px 7px;"
    f"  font-size: 13px; font-weight: bold;"
    "}"
    f"QComboBox::drop-down {{ border: none; padding-right: 6px; }}"
)


class PatientCell(QWidget):
    """
    One patient field rendered as  [icon]  [label]  [inline input]
    horizontally in a single row.  The input looks like plain text when
    unfocused and becomes a proper QLineEdit / QComboBox on focus/click.
    Changes are written to *info_dict* in real-time.
    """

    def __init__(
        self,
        icon: str,
        field_key: str,
        info_dict: dict,
        choices: list = None,
        placeholder: str = "",
    ):
        super().__init__()
        self._key = field_key
        self._info = info_dict
        self._is_combo = choices is not None
        self.setStyleSheet("background: transparent;")

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 8, 14, 8)
        row.setSpacing(6)

        # icon
        ico = QLabel(icon)
        ico.setFont(QFont("Segoe UI", 11))
        ico.setStyleSheet("background: transparent; border: none; color: #94A3B8;")
        ico.setFixedWidth(20)
        row.addWidget(ico)

        # label
        lbl = QLabel(field_key)
        lbl.setFont(QFont("Segoe UI", 10))
        lbl.setStyleSheet(f"color: {C_SUBTEXT}; background: transparent; border: none;")
        lbl.setFixedWidth(110)
        row.addWidget(lbl)

        # input widget
        if self._is_combo:
            self.widget = QComboBox()
            self.widget.addItems(choices)
            saved = info_dict.get(field_key, "")
            idx = self.widget.findText(saved)
            self.widget.setCurrentIndex(max(0, idx))
            self.widget.setStyleSheet(_GHOST)
            # show/hide drop-down arrow via focus
            self.widget.activated.connect(self._on_combo_change)
            self.widget.installEventFilter(self)
        else:
            self.widget = QLineEdit()
            self.widget.setText(info_dict.get(field_key, ""))
            self.widget.setPlaceholderText(placeholder)
            self.widget.setStyleSheet(_GHOST)
            self.widget.installEventFilter(self)
            self.widget.textChanged.connect(self._on_text_change)

        self.widget.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.widget.setFixedHeight(28)
        row.addWidget(self.widget, stretch=1)

    # ── real-time sync ────────────────────────────────────────────────────────
    def _on_text_change(self, text):
        self._info[self._key] = text.strip()

    def _on_combo_change(self, _index):
        self._info[self._key] = self.widget.currentText()

    # ── ghost ↔ active style swap ─────────────────────────────────────────────
    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent

        if obj is self.widget:
            if event.type() == QEvent.Type.FocusIn:
                self.widget.setStyleSheet(_ACTIVE)
                if self._is_combo:
                    # re-enable drop-down arrow
                    self.widget.setStyleSheet(
                        _ACTIVE
                        + "QComboBox::drop-down { border: none; padding-right: 6px; }"
                    )
            elif event.type() == QEvent.Type.FocusOut:
                self.widget.setStyleSheet(_GHOST)
                if self._is_combo:
                    self._info[self._key] = self.widget.currentText()
        return super().eventFilter(obj, event)

    def enterEvent(self, event):
        self.setStyleSheet(f"background: #EFF6FF; border-radius: 8px;")

    def leaveEvent(self, event):
        self.setStyleSheet("background: transparent;")


# ─── MAIN WINDOW ─────────────────────────────────────────────────────────────
class MedicalDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.live_data = []
        self.vol_history = []      #  to track (time_ms, volume) for calculus
        self.smoothed_flow = 0.0   # ADD THIS: for the EMA filter
        self.serial_port = None
        self.is_connected = False
        self.patient_info = {
            k: ""
            for k in [
                "Name",
                "Age",
                "Gender",
                "Height (cm)",
                "Weight (kg)",
                "Smoker",
                "Phone",
                "Clinical Condition",
                "Email",
            ]
        }

        self.setWindowTitle("Medical Pressure Dashboard")
        self.resize(1440, 900)
        self.setStyleSheet(f"QMainWindow{{background:{C_BG};}}")

        root = QWidget()
        root.setStyleSheet(f"background:{C_BG};")
        self.setCentralWidget(root)
        RL = QVBoxLayout(root)
        RL.setContentsMargins(14, 14, 14, 14)
        RL.setSpacing(10)

        # ── 1. HEADER
        RL.addWidget(self._header())

        # ── 2. PATIENT INFO GRID
        RL.addWidget(self._patient_grid())

        # ── 3. BOTTOM ROW: graph (left) + stat cards (right)  [max vertical space]
        RL.addLayout(self._bottom_row(), stretch=1)

        # ── 4. COMBINED BOTTOM BAR: port/baud/connect/disconnect + export CSV
        RL.addWidget(self._conn_bar())

        # status bar (hidden, kept for _ui_connected/_ui_disconnected logic)
        self.lbl_status_bar = QLabel("  Ready — connect a device to begin recording.")
        self.lbl_status_bar.setFont(QFont("Segoe UI", 10))
        self.lbl_status_bar.hide()

        # Timers
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self._tick)
        self.clock_timer.start(1000)
        self._tick()
        self.serial_timer = QTimer()
        self.serial_timer.timeout.connect(self._read_serial)

    # ── HEADER ────────────────────────────────────────────────────────────────
    def _header(self):
        h = card(12)
        h.setFixedHeight(68)
        L = QHBoxLayout(h)
        L.setContentsMargins(18, 0, 18, 0)

        logo = QLabel()
        logo.setFixedSize(120, 50)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(
            f"background:{C_CARD2};border-radius:7px;border:1px solid {C_BORDER};color:{C_SUBTEXT};font-weight:bold;"
        )
        try:
            px = QPixmap(LOGO_FILENAME)
            if not px.isNull():
                logo.setPixmap(
                    px.scaled(
                        logo.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                logo.setText("LOGO")
        except:
            logo.setText("LOGO")
        L.addWidget(logo)
        L.addStretch()

        t = QLabel("Urine Flow Monitoring System")
        t.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        t.setStyleSheet(
            f"color:{C_TEXT};background:transparent;border:none;letter-spacing:2px;"
        )
        L.addWidget(t)
        L.addStretch()

        self.badge = QLabel("● DISCONNECTED")
        self.badge.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.badge.setStyleSheet(
            f"color:{C_RED};background:transparent;border:none;letter-spacing:1px;"
        )
        L.addWidget(self.badge)
        return h

    # ── PATIENT INFO GRID ─────────────────────────────────────────────────────
    def _patient_grid(self):
        outer = card(12)
        outer.setFixedHeight(200)
        OL = QVBoxLayout(outer)
        OL.setContentsMargins(0, 0, 0, 0)
        OL.setSpacing(0)

        # Header row
        top_bar = QWidget()
        top_bar.setStyleSheet("background:transparent;")
        tb = QHBoxLayout(top_bar)
        tb.setContentsMargins(16, 8, 16, 4)
        tb.setSpacing(0)
        title = QLabel("Patient Information")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{C_TEXT};background:transparent;border:none;")
        tb.addWidget(title)
        hint = QLabel("  · click any field to edit inline")
        hint.setFont(QFont("Segoe UI", 9))
        hint.setStyleSheet(f"color:{C_SUBTEXT};background:transparent;border:none;")
        tb.addWidget(hint)
        tb.addStretch()
        OL.addWidget(top_bar)
        OL.addWidget(hdiv())

        # 3-column × 3-row grid of inline-editable cells
        grid_w = QWidget()
        grid_w.setStyleSheet("background:transparent;")
        G = QGridLayout(grid_w)
        G.setContentsMargins(0, 0, 0, 0)
        G.setSpacing(0)

        # (icon, key, choices_or_None, placeholder, grid_row, grid_col)
        fields = [
            ("👤", "Name", None, "Full name", 0, 0),
            ("📏", "Height (cm)", None, "e.g. 172", 0, 1),
            ("🎂", "Age", None, "e.g. 34", 0, 2),
            ("⚥", "Gender", ["", "Male", "Female", "Other"], "", 1, 0),
            ("⚖", "Weight (kg)", None, "e.g. 70", 1, 1),
            ("🚬", "Smoker", ["", "Yes", "No"], "", 1, 2),
            ("📞", "Phone", None, "+91 XXXXX XXXXX", 2, 0),
            ("🩺", "Clinical Condition", ["", "Yes", "No"], "", 2, 1),
            ("✉", "Email", None, "example@email.com", 2, 2),
        ]

        for icon, key, choices, placeholder, r, c in fields:
            cell = PatientCell(
                icon, key, self.patient_info, choices=choices, placeholder=placeholder
            )
            # vertical separator between columns
            if c > 0:
                vsep = QFrame()
                vsep.setFrameShape(QFrame.Shape.VLine)
                vsep.setStyleSheet(
                    f"color:{C_DIVIDER};background:{C_DIVIDER};border:none;max-width:1px;"
                )
                G.addWidget(vsep, r, c * 2 - 1)
            G.addWidget(cell, r, c * 2)

        for ci in [0, 2, 4]:
            G.setColumnStretch(ci, 1)
        for ci in [1, 3]:
            G.setColumnMinimumWidth(ci, 1)

        OL.addWidget(grid_w, stretch=1)
        return outer

    # ── CONNECTION BAR ────────────────────────────────────────────────────────
    def _conn_bar(self):
        bar = card(10)
        bar.setFixedHeight(56)
        L = QHBoxLayout(bar)
        L.setContentsMargins(18, 0, 18, 0)
        L.setSpacing(10)

        inp = (
            f"background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};"
            f"border-radius:6px;padding:5px 9px;font-size:12px;"
        )

        def lbl(t):
            w = QLabel(t)
            w.setStyleSheet(
                f"color:{C_SUBTEXT};font-weight:bold;font-size:11px;background:transparent;border:none;"
            )
            return w

        # PORT
        L.addWidget(lbl("PORT"))
        self.combo_ports = QComboBox()
        self.combo_ports.setFixedWidth(145)
        self.combo_ports.setStyleSheet(inp)
        self.refresh_ports()
        L.addWidget(self.combo_ports)
        rb = QPushButton("↻")
        rb.setFixedSize(28, 28)
        rb.clicked.connect(self.refresh_ports)
        rb.setStyleSheet(
            f"background:{C_CARD2};color:{C_TEXT};border:1px solid {C_BORDER};border-radius:6px;font-size:14px;"
        )
        L.addWidget(rb)

        # BAUD
        L.addSpacing(8)
        L.addWidget(lbl("BAUD"))
        self.input_baud = QLineEdit(str(DEFAULT_BAUD))
        self.input_baud.setFixedWidth(75)
        self.input_baud.setStyleSheet(inp)
        L.addWidget(self.input_baud)

        L.addSpacing(12)
        self.input_format = QLineEdit(
            DEFAULT_FORMAT
        )  # kept for serial logic, not shown

        # CONNECT
        self.btn_connect = QPushButton("  CONNECT")
        self.btn_connect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_connect.setFixedHeight(36)
        self.btn_connect.setStyleSheet(self._bstyle(C_ACCENT))
        self.btn_connect.clicked.connect(self.toggle_connection)
        L.addWidget(self.btn_connect)

        # DISCONNECT (separate button as per sketch)
        self.btn_disconnect = QPushButton("  DISCONNECT")
        self.btn_disconnect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_disconnect.setFixedHeight(36)
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.setStyleSheet(self._bstyle(C_RED))
        self.btn_disconnect.clicked.connect(self.toggle_connection)
        L.addWidget(self.btn_disconnect)

        L.addStretch()

        # EXPORT CSV — rightmost
        self.btn_export = QPushButton("⬇  EXPORT CSV")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setFixedHeight(36)
        self.btn_export.setStyleSheet(self._bstyle(C_GREEN))
        self.btn_export.clicked.connect(self.export_csv)
        L.addWidget(self.btn_export)

        return bar

    # ── BOTTOM ROW ────────────────────────────────────────────────────────────
    def _bottom_row(self):
        row = QHBoxLayout()
        row.setSpacing(12)

        # LEFT: graph (expanded now, takes most space)
        graph_card = card()
        GL = QVBoxLayout(graph_card)
        GL.setContentsMargins(8, 8, 8, 8)
        self.graph = PressureGraphCanvas()
        GL.addWidget(self.graph)
        row.addWidget(graph_card, stretch=1)

        # RIGHT: vertical stack of stat cards (no CURRENT card)
        stat_col = QVBoxLayout()
        stat_col.setSpacing(10)
        self.card_clock, self.lbl_clock = self._stat_card(
            "🕐", "TIME", "--:--:--", C_PURPLE
        )
        self.card_max, self.lbl_max = self._stat_card("↑", "VOLUME (ml)", "--", C_RED)
        self.card_min, self.lbl_min = self._stat_card(
            "↓", "VOLUMETRIC FLOW RATE", "--", C_GREEN
        )

        # unit sub-labels
        self._add_unit(self.card_max, "ml")
        self._add_unit(self.card_min, "ml/s")

        for c in [self.card_clock, self.card_max, self.card_min]:
            stat_col.addWidget(c, stretch=1)

        stat_w = QWidget()
        stat_w.setStyleSheet("background:transparent;")
        stat_w.setLayout(stat_col)
        stat_w.setFixedWidth(210)
        row.addWidget(stat_w)

        return row

    def _add_unit(self, card_widget, unit_text):
        """Append a small unit label inside an existing stat card."""
        layout = card_widget.layout()
        u = QLabel(unit_text)
        u.setFont(QFont("Segoe UI", 9))
        u.setStyleSheet(f"color:{C_SUBTEXT};background:transparent;border:none;")
        layout.insertWidget(layout.count() - 1, u)  # before the colour bar

    def _stat_card(self, icon, title, default, color):
        c = card()
        c.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        L = QVBoxLayout(c)
        L.setContentsMargins(16, 12, 16, 10)
        L.setSpacing(2)

        top = QHBoxLayout()
        ico = QLabel(icon)
        ico.setFont(QFont("Segoe UI", 13))
        ico.setStyleSheet(f"color:{color};background:transparent;border:none;")
        ttl = QLabel(title)
        ttl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        ttl.setStyleSheet(
            f"color:{C_SUBTEXT};background:transparent;border:none;letter-spacing:1px;"
        )
        top.addWidget(ico)
        top.addSpacing(5)
        top.addWidget(ttl)
        top.addStretch()
        L.addLayout(top)

        v = QLabel(default)
        v.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        v.setStyleSheet(f"color:{color};background:transparent;border:none;")
        L.addWidget(v)
        L.addStretch()

        bar = QFrame()
        bar.setFixedHeight(4)
        bar.setStyleSheet(
            f"QFrame{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {color},stop:1 transparent);border-radius:2px;border:none;}}"
        )
        L.addWidget(bar)
        return c, v

    def _bstyle(self, bg, fg="white"):
        return (
            f"QPushButton{{background:{bg};color:{fg};font-weight:bold;"
            f"padding:7px 18px;border-radius:7px;font-size:12px;border:none;}}"
            f"QPushButton:hover{{opacity:0.85;}}"
            f"QPushButton:disabled{{background:#CBD5E1;color:#94A3B8;}}"
        )

    # ── CLOCK ─────────────────────────────────────────────────────────────────
    def _tick(self):
        self.lbl_clock.setText(QTime.currentTime().toString("HH:mm:ss"))

    def refresh_ports(self):
        self.combo_ports.clear()
        for p in serial.tools.list_ports.comports():
            self.combo_ports.addItem(p.device)

    # ── CONNECTION ────────────────────────────────────────────────────────────
    def toggle_connection(self):
        if not self.is_connected:
            # 1. Validate inputs before touching hardware
            port = self.combo_ports.currentText()
            if not port:
                QMessageBox.warning(self, "No Port", "Please select a serial port.")
                return

            try:
                baud = int(self.input_baud.text())
            except ValueError:
                QMessageBox.warning(
                    self, "Invalid Baud", "Baud rate must be a whole number."
                )
                return

            # 2. Open the serial port
            try:
                self.serial_port = serial.Serial(
                    port,
                    baud,
                    timeout=1,
                    write_timeout=2,
                )
            except Exception as e:
                QMessageBox.critical(self, "Connection Error", str(e))
                return

            # 3. Wait for MCU to finish booting after DTR reset, then clear
            #    any garbage it sent during the bootloader splash
            time.sleep(2)
            self.serial_port.reset_input_buffer()

            # 4. Show popup — device is ready by the time the user types
            t_value, ok = QInputDialog.getText(
                self,
                "Initialise Device",
                "Please put the container in place.\n\nEnter value of T:",
            )

            # 5. Cancel or blank → abort cleanly
            if not ok or not t_value.strip():
                self.serial_port.close()
                self.serial_port = None
                return

            # 6. Try sending T command, wait for any ack, retry once if needed
            ack = self._send_T_and_wait_ack(t_value.strip())

            if not ack:
                # First attempt got no response — retry once with a fresh send
                QMessageBox.information(
                    self, "Retrying", "No response from device. Retrying once…"
                )
                ack = self._send_T_and_wait_ack(t_value.strip())

            if not ack:
                # Both attempts failed — disconnect and tell the user
                QMessageBox.critical(
                    self,
                    "No Acknowledgement",
                    "The device did not respond after two attempts.\n"
                    "Check the connection and try again.",
                )
                self.serial_port.close()
                self.serial_port = None
                return

            # 7. Ack received — go LIVE and start reading data
            self.serial_port.reset_input_buffer()  # discard the ack line itself
            self.live_data = []
            self.is_connected = True
            self._ui_connected(port)
            self.serial_timer.start(ANIMATION_SPEED)

        else:
            # Disconnect
            self.serial_timer.stop()
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.serial_port = None
            self.is_connected = False
            self._ui_disconnected()

    def _send_T_and_wait_ack(self, t_value: str, timeout_s: float = 5.0) -> bool:
        """
        Send  T<value>\r\n  over the open serial port, then block (in a
        tight Qt-friendly loop) for up to *timeout_s* seconds waiting for
        any non-empty line back from the device.

        Returns True if a response arrived, False if the timeout expired.
        """
        command = f"T{t_value}\r\n"
        try:
            self.serial_port.reset_input_buffer()
            self.serial_port.write(command.encode("utf-8"))
            self.serial_port.flush()
        except Exception as e:
            QMessageBox.critical(self, "Write Error", f"Failed to send command:\n{e}")
            return False

        deadline = time.time() + timeout_s
        while time.time() < deadline:
            # Process pending Qt events so the window doesn't freeze
            QApplication.processEvents()
            try:
                if self.serial_port.in_waiting > 0:
                    line = (
                        self.serial_port.readline()
                        .decode("utf-8", errors="ignore")
                        .strip()
                    )
                    if line:  # any non-empty response counts as ack
                        return True
            except Exception:
                return False
            time.sleep(0.05)  # 50 ms poll — light on CPU

        return False  # timed out

    def _ui_connected(self, port):
        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)
        self.combo_ports.setEnabled(False)
        self.input_baud.setEnabled(False)
        self.badge.setText("● LIVE")
        self.badge.setStyleSheet(
            f"color:{C_GREEN};background:transparent;border:none;font-weight:bold;letter-spacing:1px;"
        )
        ts = datetime.now().strftime("%d %b %Y  %H:%M:%S")
        self.lbl_status_bar.setText(
            f"  ▶  Session started  {ts}  ·  Connected to {port}"
        )
        self.lbl_status_bar.setStyleSheet(
            f"color:{C_GREEN};background:#F0FDF4;border-radius:8px;"
            f"border:1px solid {C_GREEN};padding:6px 14px;font-weight:bold;font-size:10px;"
        )

    def _ui_disconnected(self):
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.combo_ports.setEnabled(True)
        self.input_baud.setEnabled(True)
        self.badge.setText("● DISCONNECTED")
        self.badge.setStyleSheet(
            f"color:{C_RED};background:transparent;border:none;font-weight:bold;letter-spacing:1px;"
        )
        self.lbl_status_bar.setText("  Ready — connect a device to begin recording.")
        self.lbl_status_bar.setStyleSheet(
            f"color:{C_SUBTEXT};background:{C_CARD};border-radius:8px;"
            f"border:1px solid {C_BORDER};padding:6px 14px;font-size:10px;"
        )

    # ── SERIAL ────────────────────────────────────────────────────────────────
    def _read_serial(self):
        if not (self.serial_port and self.serial_port.is_open):
            return

        latest_volume = None
        latest_flow_rate = None

        try:
            # Drain the entire serial buffer to eliminate visual lag
            while self.serial_port.in_waiting > 0:
                raw = self.serial_port.readline().decode("utf-8", errors="ignore").strip()
                if not raw:
                    continue

                # Parse: "Timestamp_ms, Volume" from Arduino
                parts = [p.strip() for p in raw.split(",")]
                if len(parts) < 2:
                    continue

                try:
                    t_ms = float(parts[0])
                    volume = float(parts[1])
                except ValueError:
                    continue 

                # --- SCIENTIFIC CALCULUS LOGIC ---
                self.vol_history.append((t_ms, volume))
                
                # Keep a 2-second rolling buffer
                while self.vol_history and (t_ms - self.vol_history[0][0]) > 2000:
                    self.vol_history.pop(0)

                flow_rate = 0.0
                if len(self.vol_history) > 1:
                    # Look back ~500ms to calculate dV/dt (mitigates drop impact noise)
                    past_t, past_v = self.vol_history[0]
                    for i in range(len(self.vol_history)-1, -1, -1):
                        if (t_ms - self.vol_history[i][0]) >= 500:
                            past_t, past_v = self.vol_history[i]
                            break

                    dt_s = (t_ms - past_t) / 1000.0  # Convert ms to seconds
                    if dt_s > 0:
                        raw_q = (volume - past_v) / dt_s
                        raw_q = max(0.0, raw_q) # Uroflowmetry flow cannot be negative

                        # Apply Exponential Moving Average (EMA) to smooth the curve
                        # Alpha of 0.15 is standard for hardware noise reduction without extreme lag
                        self.smoothed_flow = (0.15 * raw_q) + (0.85 * self.smoothed_flow)
                        flow_rate = self.smoothed_flow

                # Store for logging/export
                row = {
                    "Timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                    "Arduino_ms": t_ms,
                    "_volume": volume,
                    "_flow_rate": flow_rate,
                }
                self.live_data.append(row)

                latest_volume = volume
                latest_flow_rate = flow_rate

            # Update UI once with the most recent smoothed data
            if latest_volume is not None:
                self._update_ui(latest_volume, latest_flow_rate)

        except Exception as e:
            print(f"Serial: {e}")

    def _update_ui(self, volume: float, flow_rate: float):
        # Display real-time volume (not max)
        self.lbl_max.setText(f"{volume:.1f}")

        # Display actual flow rate from Arduino (not min)
        self.lbl_min.setText(f"{flow_rate:.1f}")

        # Update graph with volume data
        w = self.live_data[-WINDOW_SIZE:]
        self.graph.update_plot(
            list(range(len(w))), [d["_volume"] for d in w if "_volume" in d]
        )

    # ── EXPORT ────────────────────────────────────────────────────────────────
    def export_csv(self):
        if not self.live_data:
            QMessageBox.warning(self, "No Data", "No sensor data recorded yet.")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", f"medical_session_{ts}.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            import csv
            with open(path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # --- 1. Write Patient Info (Row 1 & 2) ---
                patient_keys = list(self.patient_info.keys())
                patient_values = list(self.patient_info.values())
                
                writer.writerow(patient_keys)
                writer.writerow(patient_values)

                # --- 2. Write Empty Row (Row 3) ---
                writer.writerow([])

                # --- 3. Write Sensor Data Headers (Row 4) ---
                writer.writerow(["Timestamp", "volume", "volumetric rate"])

                # --- 4. Write Sensor Data Values (Row 5+) ---
                for d in self.live_data:
                    t = d.get("Timestamp", "")
                    v = d.get("_volume", 0)
                    r = d.get("_flow_rate", 0)
                    writer.writerow([t, v, r])

            QMessageBox.information(
                self, "Exported", f"✓  Saved data to:\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

# ─── ENTRY ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(C_BG))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(C_TEXT))
    pal.setColor(QPalette.ColorRole.Base, QColor(C_CARD))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(C_CARD2))
    pal.setColor(QPalette.ColorRole.Text, QColor(C_TEXT))
    pal.setColor(QPalette.ColorRole.Button, QColor(C_CARD))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(C_TEXT))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(C_ACCENT))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(pal)

    win = MedicalDashboard()
    win.show()
    sys.exit(app.exec())