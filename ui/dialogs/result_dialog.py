"""
Result dialogs — single-file scan result and batch scan summary overlays.
"""
import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QFrame, QGraphicsOpacityEffect,
    QSizePolicy
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal
from ui.styles.figma_theme import Colors, Typography, StyleHelper


# ── Shared animated overlay base ──────────────────────────────────────────────

class _BaseOverlay(QWidget):
    """
    Full-screen dark scrim that fades in/out and sizes itself to the parent widget.
    Subclasses build their own card UI on top of this.
    """

    def __init__(self, parent=None):
        """Buat lapisan gelap fullscreen dan animasi fade untuk dialog turunan."""
        super().__init__(parent)
        self.setObjectName("baseOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QWidget#baseOverlay{background:rgba(5,5,10,0.82);}")

        # Opacity effect drives fade animations
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(0)

        # Fade in animation
        self._fade_in = QPropertyAnimation(self._opacity, b"opacity")
        self._fade_in.setDuration(260)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Fade out animation — destroys widget when done
        self._fade_out = QPropertyAnimation(self._opacity, b"opacity")
        self._fade_out.setDuration(180)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self._destroy)

    # ── Public ────────────────────────────────────────────────────────────────

    def show_dialog(self):
        """Expand to parent size, show, and fade in."""
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()
        self._fade_in.start()

    def close_dialog(self):
        """Fade out and schedule deletion."""
        self._fade_out.start()

    def _destroy(self):
        """Hide and delete this widget after fade-out completes."""
        self.hide()
        self.deleteLater()

    # ── Card & widget factories ────────────────────────────────────────────────

    @staticmethod
    def _card(min_w=540, max_w=600, radius=24) -> tuple["QFrame", "QVBoxLayout"]:
        """Create and return a centered dialog card with zero-margin layout."""
        card = QFrame()
        card.setObjectName("dialogCard")
        card.setMinimumWidth(min_w)
        card.setMaximumWidth(max_w)
        card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        card.setStyleSheet(f"""
            QFrame#dialogCard {{
                background: #131317;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: {radius}px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        return card, lay

    @staticmethod
    def _divider() -> QFrame:
        """Return a 1px horizontal divider line."""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background:rgba(255,255,255,0.07);max-height:1px;border:none;")
        return line

    @staticmethod
    def _micro_label(text: str) -> QLabel:
        """Return a small uppercase section header label."""
        lbl = QLabel(text)
        lbl.setStyleSheet(f"""
            color: {Colors.DARK_TEXT_MUTED};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.2px;
            background: transparent;
            font-family: {Typography.FONT_FAMILY};
        """)
        return lbl

    @staticmethod
    def _value_label(text: str, size="14px", color=Colors.DARK_TEXT_PRIMARY,
                     bold=False) -> QLabel:
        """Return a standard value label with configurable size, color, and weight."""
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"""
            color: {color};
            font-size: {size};
            font-weight: {'700' if bold else '400'};
            background: transparent;
            font-family: {Typography.FONT_FAMILY};
        """)
        return lbl


# ── Single-file scan result dialog ────────────────────────────────────────────

class ResultDialog(_BaseOverlay):
    """Full-screen overlay showing the result of a single-file scan."""

    def __init__(self, result_data: dict, parent=None):
        """Terima data hasil scan satu file lalu bangun dialog hasilnya."""
        super().__init__(parent)
        self.result_data = result_data
        self._build_ui()

    # ── Data parsing ──────────────────────────────────────────────────────────

    def _parse(self):
        """
        Extract is_safe, confidence, result_type, and is_full from result_data.
        Handles both single-file and batch-style result dicts.
        """
        rd      = self.result_data
        is_full = rd.get("is_full_scan", False) or ("result" not in rd)

        if is_full:
            is_safe     = not rd.get("is_malware", False)
            confidence  = rd.get("confidence", 100) / 100.0
            result_type = "Benign" if is_safe else "Malware"
        else:
            result_type = rd["result"]
            is_safe     = result_type == "Benign"
            po          = rd["model"]["predicted_output"]
            # Normalize predicted output to a 2-element probability list
            if isinstance(po, list):
                probs = po if len(po) == 2 else (po[0] if isinstance(po[0], list) else po)
            else:
                probs = [po, 1 - po]
            # Softmax-style confidence from raw logits
            exp_p      = [math.exp(min(p, 100)) for p in probs]
            tot        = sum(exp_p)
            confidence = min(max(exp_p) / tot if tot else 0.5, 1.0)

        return is_safe, confidence, result_type, is_full

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        """Build the full dialog: header, file info block, result block, footer."""
        is_safe, confidence, result_type, is_full = self._parse()
        rd = self.result_data

        accent        = Colors.GREEN_500 if is_safe else Colors.ORANGE_500
        accent_dim    = "rgba(50,205,50,0.15)"  if is_safe else "rgba(255,165,0,0.12)"
        accent_border = "rgba(50,205,50,0.35)"  if is_safe else "rgba(255,165,0,0.35)"
        status_icon   = "✓" if is_safe else "✕"
        status_text   = "File Aman" if is_safe else "Ancaman Terdeteksi"
        header_grad   = (
            "stop:0 rgba(50,205,50,0.25), stop:1 rgba(16,185,129,0.12)"
            if is_safe else
            "stop:0 rgba(255,140,0,0.25), stop:1 rgba(255,107,53,0.12)"
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card, card_lay = self._card(min_w=520, max_w=580)

        card_lay.addWidget(self._build_header(
            accent, accent_border, header_grad,
            status_icon, status_text, confidence
        ))

        card_lay.addWidget(self._build_body(rd, is_safe, is_full, accent_dim, accent_border, result_type))
        card_lay.addWidget(self._divider())
        card_lay.addWidget(self._build_footer(rd))

        root_layout.addWidget(card)

    def _build_header(self, accent, accent_border, header_grad,
                      status_icon, status_text, confidence) -> QFrame:
        """Build the colored header with status icon, title, and confidence bar."""
        header = QFrame()
        header.setObjectName("resultHeader")
        header.setStyleSheet(f"""
            QFrame#resultHeader {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, {header_grad});
                border-radius: 24px 24px 0 0;
                border-bottom: 1px solid {accent_border};
            }}
        """)
        lay = QVBoxLayout(header)
        lay.setContentsMargins(36, 32, 36, 28)
        lay.setSpacing(10)

        # Icon + title row
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        icon_lbl = QLabel(status_icon)
        icon_lbl.setFixedSize(52, 52)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            font-size: 26px; font-weight: 900; color: white;
            background: {accent}; border-radius: 26px;
        """)
        top_row.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel(status_text)
        title_lbl.setStyleSheet(f"""
            color: white; font-size: 22px; font-weight: 700;
            background: transparent; font-family: {Typography.FONT_FAMILY};
        """)
        sub_lbl = QLabel(f"Keyakinan model: {confidence:.0%}")
        sub_lbl.setStyleSheet(f"""
            color: rgba(255,255,255,0.65); font-size: 12px;
            background: transparent; font-family: {Typography.FONT_FAMILY};
        """)
        title_col.addWidget(title_lbl)
        title_col.addWidget(sub_lbl)
        top_row.addLayout(title_col)
        top_row.addStretch()
        lay.addLayout(top_row)

        # Confidence progress bar
        conf_bar = QProgressBar()
        conf_bar.setRange(0, 100)
        conf_bar.setValue(int(confidence * 100))
        conf_bar.setTextVisible(False)
        conf_bar.setFixedHeight(6)
        conf_bar.setStyleSheet(f"""
            QProgressBar{{background:rgba(255,255,255,0.15);border-radius:3px;border:none;}}
            QProgressBar::chunk{{background:{accent};border-radius:3px;}}
        """)
        lay.addWidget(conf_bar)
        return header

    def _build_body(self, rd, is_safe, is_full, accent_dim, accent_border, result_type) -> QWidget:
        """Build the body section with file info, detection result, and warning strip."""
        body = QWidget()
        lay  = QVBoxLayout(body)
        lay.setContentsMargins(36, 24, 36, 24)
        lay.setSpacing(16)

        # File information block
        file_name = rd.get("file_name", "Unknown") if is_full else rd["file"]["file_name"]
        file_path = "" if is_full else rd["file"].get("file_path", "")
        file_size = None if is_full else rd["file"].get("file_size")
        lay.addWidget(self._info_block(
            "INFORMASI FILE",
            [
                ("Nama",    file_name),
                ("Lokasi",  file_path or "—"),
                ("Ukuran",  f"{file_size / 1024:.1f} KB" if file_size else "—"),
            ]
        ))

        # Detection result block
        detect_color = Colors.GREEN_500 if is_safe else Colors.ORANGE_500
        model_name   = "—" if is_full else rd.get("model", {}).get("model", "Modelv3.onnx")
        device_name  = "—" if is_full else rd.get("device", {}).get("device", "CPU")
        lay.addWidget(self._result_block(
            result_type, detect_color, accent_dim, model_name, device_name
        ))

        return body

    def _build_footer(self, rd) -> QWidget:
        """Build the footer with timestamp and close button."""
        footer = QWidget()
        lay    = QHBoxLayout(footer)
        lay.setContentsMargins(36, 16, 36, 20)

        ts = rd.get("timestamp", "")
        if ts:
            ts_lbl = QLabel(f" {ts}")
            ts_lbl.setStyleSheet(f"""
                color:{Colors.DARK_TEXT_MUTED};font-size:11px;
                background:transparent;font-family:{Typography.FONT_FAMILY};
            """)
            lay.addWidget(ts_lbl)
        lay.addStretch()

        close_btn = QPushButton("Selesai")
        close_btn.setFixedSize(110, 40)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close_dialog)
        close_btn.setStyleSheet(StyleHelper.pill_button_primary(40))
        lay.addWidget(close_btn)
        return footer

    # ── Sub-builders ──────────────────────────────────────────────────────────

    def _info_block(self, title: str, rows: list) -> QFrame:
        """Build a key-value information block with a section title."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame{background:rgba(255,255,255,0.04);border:none;border-radius:14px;}
        """)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)
        lay.addWidget(self._micro_label(title))

        for label, val in rows:
            row = QHBoxLayout()
            row.setSpacing(8)
            k = QLabel(label)
            k.setFixedWidth(60)
            k.setStyleSheet(f"""
                color:{Colors.DARK_TEXT_MUTED};font-size:12px;
                background:transparent;font-family:{Typography.FONT_FAMILY};
            """)
            v = QLabel(val)
            v.setWordWrap(True)
            v.setStyleSheet(f"""
                color:{Colors.DARK_TEXT_PRIMARY};font-size:12px;
                background:transparent;font-family:{Typography.FONT_FAMILY};
            """)
            row.addWidget(k)
            row.addWidget(v, 1)
            lay.addLayout(row)
        return frame

    def _result_block(self, result_type, color, bg, model_name, device_name) -> QFrame:
        """Build the detection result block showing BENIGN or MALWARE."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame{{background:{bg};border:none;border-radius:14px;}}
        """)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(6)
        lay.addWidget(self._micro_label("HASIL DETEKSI"))

        res_lbl = QLabel(result_type.upper())
        res_lbl.setStyleSheet(f"""
            color:{color};font-size:28px;font-weight:900;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        lay.addWidget(res_lbl)

        # Model and device metadata
        meta = QHBoxLayout()
        meta.setSpacing(16)
        for txt in [f"Model: {model_name}", f"Device: {device_name}"]:
            lbl = QLabel(txt)
            lbl.setStyleSheet(f"""
                color:{Colors.DARK_TEXT_MUTED};font-size:11px;
                background:transparent;font-family:{Typography.FONT_FAMILY};
            """)
            meta.addWidget(lbl)
        meta.addStretch()
        lay.addLayout(meta)
        return frame

    def _warning_strip(self) -> QFrame:
        """Build the orange warning strip shown for malware detections."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame{background:rgba(255,107,53,0.1);
                   border-left:3px solid #FF6B35;
                   border-radius:10px;}
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)

        icon = QLabel("⚠")
        icon.setStyleSheet("font-size:20px;color:#FF6B35;background:transparent;")
        txt = QLabel("Segera hapus atau karantina file ini untuk melindungi perangkat Anda.")
        txt.setWordWrap(True)
        txt.setStyleSheet(f"""
            color:#FFAA80;font-size:12px;font-weight:600;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        lay.addWidget(icon)
        lay.addWidget(txt, 1)
        return frame


# ── Batch scan summary dialog ─────────────────────────────────────────────────

class BatchResultDialog(_BaseOverlay):
    """
    Full-screen overlay showing a summary after a batch or device scan.
    Emits quarantine_requested(list) when the user clicks 'Karantina Semua'.
    """

    quarantine_requested = Signal(list)

    def __init__(self, summary: dict, parent=None):
        """Terima ringkasan scan banyak file lalu bangun dialog rekapnya."""
        super().__init__(parent)
        self._summary = summary
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        """Build header, stat pills, notes, and footer from scan summary data."""
        s       = self._summary
        total   = s.get("scanned", 0)
        malware = s.get("malware", 0)
        clean   = s.get("clean", 0)
        errors  = s.get("errors", 0)
        results = s.get("results", [])
        beyond  = s.get("continued_beyond_limit", False)
        is_safe = malware == 0

        accent        = Colors.GREEN_500 if is_safe else Colors.ORANGE_500
        accent_border = "rgba(50,205,50,0.30)" if is_safe else "rgba(255,165,0,0.30)"
        header_grad   = (
            "stop:0 rgba(50,205,50,0.22), stop:1 rgba(16,185,129,0.10)"
            if is_safe else
            "stop:0 rgba(255,140,0,0.22), stop:1 rgba(255,107,53,0.10)"
        )
        status_icon = "✓" if is_safe else "✕"
        status_text = "Perangkat Aman" if is_safe else f"{malware} Ancaman Ditemukan"

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card, card_lay = self._card(min_w=500, max_w=560)

        card_lay.addWidget(self._build_header(
            accent, accent_border, header_grad, status_icon, status_text
        ))
        card_lay.addWidget(self._build_stats(total, clean, malware, errors))
        card_lay.addWidget(self._build_notes(malware, errors, beyond))
        card_lay.addWidget(self._divider())
        card_lay.addWidget(self._build_footer(malware, results))

        root_layout.addWidget(card)

    def _build_header(self, accent, accent_border, header_grad,
                      status_icon, status_text) -> QFrame:
        """Build the colored header with status icon and scan result title."""
        header = QFrame()
        header.setObjectName("batchResultHeader")
        header.setStyleSheet(f"""
            QFrame#batchResultHeader {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,{header_grad});
                border-radius: 24px 24px 0 0;
                border-bottom: 1px solid {accent_border};
            }}
        """)
        lay = QVBoxLayout(header)
        lay.setContentsMargins(36, 30, 36, 26)
        lay.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        icon_lbl = QLabel(status_icon)
        icon_lbl.setFixedSize(52, 52)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            font-size: 26px; font-weight: 900; color: white;
            background: {accent}; border-radius: 26px;
        """)
        top_row.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        t1 = QLabel("Hasil Pemindaian")
        t1.setStyleSheet(f"""
            color:rgba(255,255,255,0.55);font-size:11px;font-weight:700;
            letter-spacing:1px;background:transparent;
            font-family:{Typography.FONT_FAMILY};
        """)
        t2 = QLabel(status_text)
        t2.setStyleSheet(f"""
            color:white;font-size:20px;font-weight:700;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        title_col.addWidget(t1)
        title_col.addWidget(t2)
        top_row.addLayout(title_col)
        top_row.addStretch()
        lay.addLayout(top_row)
        return header

    def _build_stats(self, total, clean, malware, errors) -> QWidget:
        """Build the row of stat pills showing totals, clean, malware, and error counts."""
        row = QHBoxLayout()
        row.setContentsMargins(36, 20, 36, 0)
        row.setSpacing(10)

        row.addWidget(self._stat_pill(total,   "TOTAL",   Colors.DARK_TEXT_SECONDARY, "rgba(255,255,255,0.05)"))
        row.addWidget(self._stat_pill(clean,   "AMAN",    Colors.GREEN_500,            "rgba(50,205,50,0.10)"))
        row.addWidget(self._stat_pill(malware, "MALWARE", Colors.ORANGE_500,           "rgba(255,165,0,0.10)"))
        if errors:
            row.addWidget(self._stat_pill(errors, "GAGAL", Colors.RED_500, "rgba(255,107,53,0.10)"))

        container = QWidget()
        container.setStyleSheet("background:transparent;")
        container.setLayout(row)
        return container

    def _stat_pill(self, val, label, color, bg) -> QFrame:
        """Build a single rounded stat pill with a large number and label."""
        pill = QFrame()
        pill.setStyleSheet(f"QFrame{{background:{bg};border:none;border-radius:14px;}}")
        lay = QVBoxLayout(pill)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        v = QLabel(str(val))
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setStyleSheet(f"""
            color:{color};font-size:26px;font-weight:900;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"""
            color:rgba(255,255,255,0.45);font-size:10px;font-weight:600;
            letter-spacing:0.5px;background:transparent;
            font-family:{Typography.FONT_FAMILY};
        """)
        lay.addWidget(v)
        lay.addWidget(lbl)
        return pill

    def _build_notes(self, malware, errors, beyond) -> QWidget:
        """Build contextual note rows below the stat pills."""
        notes = QWidget()
        notes.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(notes)
        lay.setContentsMargins(36, 14, 36, 10)
        lay.setSpacing(6)

        if beyond:
            self._add_note(lay, "", "Scan dilanjutkan melewati batas default.", "rgba(255,255,255,0.35)")
        if malware > 0:
            self._add_note(lay, "⚠",
                f"{malware} file berbahaya ditemukan. Segera karantina untuk melindungi perangkat.",
                Colors.ORANGE_400)
        if not malware and not errors:
            self._add_note(lay, "✓", "Tidak ada ancaman yang terdeteksi pada perangkat Anda.", Colors.GREEN_500)

        return notes

    def _add_note(self, layout, icon: str, text: str, color: str):
        """Add an icon + text note row to a layout."""
        row = QHBoxLayout()
        row.setSpacing(8)
        if icon:
            ic = QLabel(icon)
            ic.setFixedWidth(20)
            ic.setStyleSheet(f"font-size:14px;color:{color};background:transparent;")
            row.addWidget(ic)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"""
            color:{color};font-size:12px;background:transparent;
            font-family:{Typography.FONT_FAMILY};
        """)
        row.addWidget(lbl, 1)
        layout.addLayout(row)

    def _build_footer(self, malware: int, results: list) -> QWidget:
        """Build the footer with close and optional quarantine buttons."""
        footer = QWidget()
        lay    = QHBoxLayout(footer)
        lay.setContentsMargins(36, 14, 36, 20)
        lay.setSpacing(10)
        lay.addStretch()

        close_btn = QPushButton("Tutup")
        close_btn.setFixedSize(100, 40)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close_dialog)
        close_btn.setStyleSheet(StyleHelper.pill_button_outline(40))
        lay.addWidget(close_btn)

        if malware > 0:
            q_btn = QPushButton(f"Karantina {malware} File")
            q_btn.setFixedHeight(40)
            q_btn.setMinimumWidth(150)
            q_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            q_btn.clicked.connect(lambda: self._on_quarantine(results))
            q_btn.setStyleSheet(StyleHelper.pill_button_primary(40))
            lay.addWidget(q_btn)

        return footer

    def _on_quarantine(self, results: list):
        """Emit quarantine_requested with the malware results list and close."""
        self.quarantine_requested.emit(results)
        self.close_dialog()
