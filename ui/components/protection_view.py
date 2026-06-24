"""
Tampilan Halaman Proteksi Realtime — kontrol dan statistik perlindungan aktif.

Halaman ini menampilkan:
  1. Kartu status utama dengan ikon perisai + tombol aktifkan/nonaktifkan.
  2. Empat kartu statistik: file discan, ancaman diblokir, dikarantina, proses dipantau.
  3. Tiga kartu penjelasan lapisan proteksi teknis (Layer 1, 2, 3).

Statistik diperbarui setiap 2 detik selama proteksi aktif menggunakan QTimer.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QScrollArea, QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QTimer

from ui.widgets import SoftCard                                    # Kartu umum aplikasi
from ui.styles.figma_theme import Colors, Typography, StyleHelper, Sizes  # Design system


class ProtectionView(QWidget):
    """
    Halaman kontrol proteksi realtime.

    Menampilkan status aktif/tidak aktif perlindungan, statistik file yang dipindai,
    ancaman yang diblokir, serta penjelasan tiga lapisan proteksi yang digunakan.

    Sinyal:
        protection_toggled(bool): Dikirim ketika tombol proteksi ditekan.
                                  True = pengguna meminta aktifkan, False = nonaktifkan.
    """

    # Sinyal yang dikirim ke ModernWindow saat tombol proteksi ditekan
    protection_toggled = Signal(bool)

    def __init__(self, parent=None):
        """
        Siapkan data internal dan bangun seluruh tampilan halaman proteksi.
        """
        super().__init__(parent)

        # Status tema saat ini (True = gelap)
        self.is_dark = True

        # Status proteksi saat ini (False = belum aktif saat pertama dibuka)
        self.protection_enabled = False

        # Daftar semua SoftCard di halaman ini — digunakan untuk ganti tema sekaligus
        self._soft_cards: list[SoftCard] = []

        # Daftar semua label + peran temanya — digunakan untuk ganti warna teks sekaligus
        # Format: (widget_label, nama_peran)
        self._theme_labels: list[tuple[QLabel, str]] = []

        # Timer yang secara berkala mengambil statistik dari sistem proteksi
        # Interval 2000ms = setiap 2 detik — cukup sering tanpa terlalu membebani CPU
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._update_live_stats)
        self._stats_timer.setInterval(2000)
        # Timer TIDAK dimulai di sini — hanya berjalan saat proteksi aktif

        # Bangun tampilan halaman
        self.setup_ui()

    # ------------------------------------------------------------------
    # MEMBANGUN TAMPILAN
    # ------------------------------------------------------------------

    def setup_ui(self):
        """
        Bangun seluruh tata letak halaman proteksi di dalam area gulir (scroll).

        Menggunakan QScrollArea agar konten yang panjang bisa digulir ke bawah
        tanpa mengubah ukuran jendela utama.
        """
        # ── Area gulir ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)   # Konten mengisi lebar scroll otomatis
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Konten di dalam scroll
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(32, 24, 32, 32)
        layout.setSpacing(24)

        # ── Kartu Status Utama ──
        # Menampilkan ikon perisai, teks status, dan tombol aktifkan/nonaktifkan
        self.status_card = SoftCard(is_dark=self.is_dark, accent=Colors.RED_500)
        self._soft_cards.append(self.status_card)
        status_layout = QVBoxLayout(self.status_card)
        status_layout.setContentsMargins(40, 36, 40, 36)
        status_layout.setSpacing(16)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Wadah ikon perisai dengan efek cahaya melingkar (radial glow) di belakangnya
        self.shield_container = QFrame()
        self.shield_container.setFixedSize(100, 100)
        self.shield_container.setStyleSheet("""
            QFrame {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    stop:0 rgba(255, 107, 53, 0.3),
                    stop:1 rgba(255, 107, 53, 0.0));
                border-radius: 50px;
            }
        """)

        # Ikon perisai (emoji karakter) di tengah wadah
        shield_icon_layout = QVBoxLayout(self.shield_container)
        shield_icon_layout.setContentsMargins(0, 0, 0, 0)
        self.shield_icon = QLabel("")
        self.shield_icon.setStyleSheet("font-size: 56px; background: transparent;")
        self.shield_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shield_icon_layout.addWidget(self.shield_icon)

        # Pusatkan wadah ikon secara horizontal
        shield_row = QHBoxLayout()
        shield_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shield_row.addWidget(self.shield_container)
        status_layout.addLayout(shield_row)

        # Judul kartu "Real-time Protection"
        self._rt_title = QLabel("Real-time Protection")
        self._rt_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._theme_labels.append((self._rt_title, "primary_large"))
        status_layout.addWidget(self._rt_title)

        # ── Badge Status (menampilkan "TIDAK AKTIF" atau "On") ──
        # Warna badge berubah merah/hijau sesuai status proteksi
        self.status_badge = QFrame()
        self.status_badge.setFixedHeight(32)
        badge_layout = QHBoxLayout(self.status_badge)
        badge_layout.setContentsMargins(16, 0, 16, 0)
        badge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Label teks di dalam badge
        self.status_label = QLabel("TIDAK AKTIF")
        self.status_label.setStyleSheet(f"""
            color: {Colors.RED_500};
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1.5px;
            background: transparent;
            font-family: {Typography.FONT_FAMILY};
        """)
        badge_layout.addWidget(self.status_label)

        # Latar badge merah samar (akan berubah hijau saat aktif)
        self.status_badge.setStyleSheet("""
            QFrame {
                background: rgba(255, 107, 53, 0.15);
                border: none;
                border-radius: 16px;
            }
        """)

        # Pusatkan badge secara horizontal
        badge_row = QHBoxLayout()
        badge_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_row.addWidget(self.status_badge)
        status_layout.addLayout(badge_row)

        # Deskripsi singkat fungsi halaman ini
        self._rt_desc = QLabel(
            "Memantau dan melindungi sistem Anda secara real-time\ndari ancaman malware menggunakan AI"
        )
        self._rt_desc.setWordWrap(True)
        self._rt_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._theme_labels.append((self._rt_desc, "muted"))
        status_layout.addWidget(self._rt_desc)

        status_layout.addSpacing(8)

        # ── Tombol Utama Aktifkan/Nonaktifkan ──
        self.toggle_btn = QPushButton("Aktifkan Perlindungan")
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)  # Kursor tangan saat hover
        self.toggle_btn.setFixedWidth(260)
        self.toggle_btn.setFixedHeight(52)
        self.toggle_btn.setStyleSheet(StyleHelper.pill_button_primary(Sizes.BTN_HEIGHT_LG))
        self.toggle_btn.clicked.connect(self._toggle_protection)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.addWidget(self.toggle_btn)
        status_layout.addLayout(btn_row)

        layout.addWidget(self.status_card)

        # ── Judul Bagian Statistik ──
        stats_header = QLabel("Statistik Real-time")
        self._theme_labels.append((stats_header, "section_header"))
        layout.addWidget(stats_header)

        # ── Grid 2×2 Kartu Statistik ──
        # Menampilkan empat angka statistik utama dari sistem proteksi
        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)

        # Buat empat kartu statistik dengan warna aksen berbeda-beda
        self.stat_scanned    = self._create_stat_card("0", "File Discan",        Colors.ORANGE_500)
        self.stat_threats    = self._create_stat_card("0", "Ancaman Diblokir",   Colors.RED_500)
        self.stat_quarantine = self._create_stat_card("0", "Dikarantina",        Colors.ORANGE_300)
        self.stat_processes  = self._create_stat_card("0", "Proses Dipantau",    Colors.EMERALD_500)

        # Tata letak 2 kolom × 2 baris
        stats_grid.addWidget(self.stat_scanned["card"],    0, 0)
        stats_grid.addWidget(self.stat_threats["card"],    0, 1)
        stats_grid.addWidget(self.stat_quarantine["card"], 1, 0)
        stats_grid.addWidget(self.stat_processes["card"],  1, 1)

        layout.addLayout(stats_grid)

        # ── Judul Bagian Lapisan Proteksi ──
        layers_header = QLabel("Lapisan Perlindungan")
        self._theme_labels.append((layers_header, "section_header"))
        layout.addWidget(layers_header)

        # Data tiga lapisan proteksi:
        # (ikon_emoji, judul, deskripsi, badge_teknis)
        layers = [
            (
                "", "Layer 1 — File Monitor",
                "Memantau file baru di Downloads, Desktop, Documents. "
                "File langsung dikunci dan discan sebelum bisa dibuka.",
                "Pseudo-Blocking",  # Nama teknis metode proteksi ini
            ),
            (
                "", "Layer 2 — Process Guard",
                "Memantau setiap program yang dijalankan. "
                "Proses di-suspend dan discan sebelum diizinkan berjalan.",
                "Scan-on-Execute",
            ),
            (
                "", "Layer 3 — Click Shield",
                "Memindai file yang dibuka pengguna, termasuk file lama. "
                "Mendeteksi malware dari argument command-line proses.",
                "Scan-on-Click",
            ),
        ]

        # Buat kartu penjelasan untuk setiap lapisan proteksi
        for icon, title, desc, badge_text in layers:
            layout.addWidget(self._create_layer_card(icon, title, desc, badge_text))

        # Ruang kosong di bawah agar konten tidak menempel di tepi bawah
        layout.addStretch()

        # Pasang konten ke scroll
        scroll.setWidget(scroll_content)

        # Layout utama halaman
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        # Terapkan warna tema ke semua label
        self._apply_label_theme()

    def _create_stat_card(self, value: str, label: str, accent_color: str) -> dict:
        """
        Buat satu kartu statistik yang menampilkan angka besar dengan label berwarna.

        value        : Nilai awal yang ditampilkan (misalnya "0").
        label        : Keterangan di bawah angka (misalnya "File Discan").
        accent_color : Warna aksen untuk teks angka dan ikon (hex color).

        Mengembalikan dict berisi:
          'card'  : Widget QFrame kartu lengkap.
          'value' : QLabel angka — bisa diperbarui langsung untuk update statistik.
        """
        card = SoftCard(is_dark=self.is_dark, accent=accent_color)
        self._soft_cards.append(card)
        card.setMinimumHeight(100)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        # Kotak ikon kecil dengan latar warna aksen transparan (20% opacity)
        # '{accent_color}20' = warna hex + alpha 32/255 dalam format ARGB
        icon_frame = QFrame()
        icon_frame.setFixedSize(40, 40)
        icon_frame.setStyleSheet(f"QFrame {{ background: {accent_color}20; border-radius: 10px; }}")

        # Label angka besar berwarna aksen — ini yang diperbarui setiap 2 detik
        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            color: {accent_color};
            font-size: 32px;
            font-weight: bold;
            font-family: {Typography.FONT_FAMILY};
            background: transparent;
        """)
        top_row.addWidget(value_label)
        top_row.addStretch()  # Dorong angka ke kiri

        card_layout.addLayout(top_row)

        # Label keterangan di bawah angka (warna muted sesuai tema)
        label_widget = QLabel(label)
        self._theme_labels.append((label_widget, "muted"))
        card_layout.addWidget(label_widget)

        # Kembalikan dict dengan referensi ke kartu dan label angka
        return {"card": card, "value": value_label}

    def _create_layer_card(self, icon: str, title: str, desc: str, badge_text: str) -> SoftCard:
        """
        Buat kartu penjelasan untuk satu lapisan proteksi.

        icon       : Emoji yang ditampilkan di kiri kartu.
        title      : Nama lapisan (misalnya "Layer 1 — File Monitor").
        desc       : Penjelasan cara kerja lapisan ini.
        badge_text : Label teknis singkat (misalnya "Pseudo-Blocking").

        Tata letak kartu: [ikon] [judul + badge] [deskripsi]
        """
        card = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_400)
        self._soft_cards.append(card)

        # Tata letak horizontal: ikon di kiri, teks di kanan
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(16)

        # ── Ikon di kiri ──
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 32px; background: transparent;")
        icon_label.setFixedWidth(40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        card_layout.addWidget(icon_label)

        # ── Area teks di kanan ──
        text_container = QWidget()
        text_container.setStyleSheet("background: transparent;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(6)

        # Baris judul + badge teknis (keduanya sejajar horizontal)
        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        # Judul lapisan proteksi
        title_label = QLabel(title)
        self._theme_labels.append((title_label, "primary"))
        title_row.addWidget(title_label)

        # Badge teknis kecil (contoh: "Pseudo-Blocking")
        badge = QLabel(badge_text)
        badge.setStyleSheet(StyleHelper.tag_badge())
        title_row.addWidget(badge)

        title_row.addStretch()  # Dorong badge tetap di kiri, tidak meregang ke kanan
        text_layout.addLayout(title_row)

        # Deskripsi cara kerja di bawah judul
        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)
        desc_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._theme_labels.append((desc_label, "muted_small"))
        text_layout.addWidget(desc_label)

        card_layout.addWidget(text_container, 1)  # '1' = biarkan area teks mengisi ruang tersisa

        return card

    # ------------------------------------------------------------------
    # LOGIKA TOMBOL PROTEKSI
    # ------------------------------------------------------------------

    def _toggle_protection(self):
        """
        Dipanggil saat pengguna menekan tombol "Aktifkan / Nonaktifkan Perlindungan".

        Cara kerja:
          1. Balik status internal (True ↔ False).
          2. Perbarui tampilan sesuai status baru.
          3. Kirim sinyal ke ModernWindow agar sistem proteksi nyata ikut berubah.
        """
        self.protection_enabled = not self.protection_enabled  # Balik status
        self._update_ui_state()                                # Perbarui tampilan
        self.protection_toggled.emit(self.protection_enabled)  # Beritahu parent window


    def _update_ui_state(self):
        """
        Perbarui semua elemen visual sesuai status proteksi saat ini.

        Jika AKTIF:
          - Kartu berwarna hijau, badge "On", tombol menjadi merah "Nonaktifkan".
          - Timer statistik dijalankan.

        Jika TIDAK AKTIF:
          - Kartu berwarna merah, badge "TIDAK AKTIF", tombol menjadi oranye "Aktifkan".
          - Timer statistik dihentikan.
        """
        if self.protection_enabled:
            # ── Status AKTIF ──

            # Warna aksen kartu status berubah ke hijau
            self.status_card.set_accent(Colors.GREEN_500)

            # Teks badge berubah ke "On" dengan warna hijau
            self.status_label.setText("On")
            self.status_label.setStyleSheet(f"""
                color: {Colors.GREEN_500};
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1.5px;
                background: transparent;
                font-family: {Typography.FONT_FAMILY};
            """)

            # Latar badge berubah ke hijau samar
            self.status_badge.setStyleSheet("""
                QFrame {
                    background: rgba(50, 205, 50, 0.12);
                    border: none;
                    border-radius: 16px;
                }
            """)

            # Tombol berubah menjadi merah "Nonaktifkan Perlindungan"
            self.toggle_btn.setText("Nonaktifkan Perlindungan")
            self.toggle_btn.setStyleSheet(StyleHelper.pill_button_danger(Sizes.BTN_HEIGHT_LG))

            # Mulai timer statistik — memperbarui angka setiap 2 detik
            self._stats_timer.start()

        else:
            # ── Status TIDAK AKTIF ──

            # Warna aksen kartu status kembali ke merah
            self.status_card.set_accent(Colors.RED_500)

            # Kembalikan ikon perisai ke emoji default
            self.shield_icon.setText("")

            # Kembalikan glow di belakang perisai ke warna merah
            self.shield_container.setStyleSheet("""
                QFrame {
                    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                        stop:0 rgba(255, 107, 53, 0.3),
                        stop:1 rgba(255, 107, 53, 0.0));
                    border-radius: 50px;
                }
            """)

            # Teks badge kembali ke "TIDAK AKTIF" dengan warna merah
            self.status_label.setText("TIDAK AKTIF")
            self.status_label.setStyleSheet(f"""
                color: {Colors.RED_500};
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1.5px;
                background: transparent;
                font-family: {Typography.FONT_FAMILY};
            """)

            # Latar badge kembali ke merah samar
            self.status_badge.setStyleSheet("""
                QFrame {
                    background: rgba(255, 107, 53, 0.15);
                    border: none;
                    border-radius: 16px;
                }
            """)

            # Tombol kembali ke oranye "Aktifkan Perlindungan"
            self.toggle_btn.setText("Aktifkan Perlindungan")
            self.toggle_btn.setStyleSheet(StyleHelper.pill_button_primary(Sizes.BTN_HEIGHT_LG))

            # Hentikan timer statistik saat proteksi tidak aktif
            self._stats_timer.stop()

    def _update_live_stats(self):
        """
        Ambil data statistik terbaru dari objek realtime_protection dan
        tampilkan angkanya di keempat kartu statistik.

        Dipanggil otomatis oleh _stats_timer setiap 2 detik.

        Cara mengambil data:
          - self.window() mengembalikan ModernWindow (jendela induk teratas).
          - ModernWindow menyimpan objek realtime_protection.
          - realtime_protection.stats adalah dict berisi angka-angka statistik.
        """
        window = self.window()  # Dapatkan referensi ke ModernWindow
        rp = getattr(window, "realtime_protection", None)  # Ambil objek proteksi

        if rp and hasattr(rp, "stats"):
            stats = rp.stats  # Dict statistik langsung dari engine proteksi

            # Perbarui angka di setiap kartu statistik
            self.stat_scanned["value"].setText(str(stats.get("files_scanned", 0)))
            self.stat_threats["value"].setText(str(stats.get("malware_detected", 0)))
            self.stat_quarantine["value"].setText(str(stats.get("files_quarantined", 0)))
            self.stat_processes["value"].setText(str(stats.get("processes_suspended", 0)))

    # ------------------------------------------------------------------
    # API PUBLIK — dipanggil dari ModernWindow
    # ------------------------------------------------------------------

    def set_protection_state(self, enabled: bool):
        """
        Atur status proteksi dari kode luar TANPA mengirim sinyal protection_toggled.

        Digunakan oleh ModernWindow.initialize_protection() untuk menyinkronkan
        tampilan tombol dengan status proteksi nyata saat aplikasi pertama dibuka.

        enabled : True = tampilkan sebagai aktif, False = tampilkan sebagai tidak aktif.
        """
        self.protection_enabled = enabled
        self._update_ui_state()  # Perbarui tampilan saja, tanpa sinyal

    def set_theme(self, is_dark: bool):
        """
        Ganti tema dan terapkan ulang gaya pada semua kartu dan label.
        Dipanggil oleh ModernWindow.apply_theme() saat pengguna mengganti tema.

        is_dark : True = mode gelap, False = mode terang.
        """
        self.is_dark = is_dark

        # Perbarui tema semua kartu lunak
        for card in self._soft_cards:
            card.set_theme(self.is_dark)

        # Perbarui warna semua label teks
        self._apply_label_theme()

    def _apply_label_theme(self):
        """
        Terapkan warna stylesheet yang sesuai pada setiap label berdasarkan 'peran' temanya.

        Peran yang ada:
          - 'section_header' : Judul bagian besar (18px, tebal)
          - 'primary_large'  : Teks utama ukuran besar (28px, tebal)
          - 'primary'        : Teks utama ukuran normal (15px, tebal)
          - 'muted'          : Teks deskripsi redup (13px)
          - 'muted_small'    : Teks keterangan kecil (12px)

        Menggunakan warna dari Colors sesuai tema aktif.
        """
        # Pilih warna teks utama dan teks muted sesuai tema
        tp = Colors.DARK_TEXT_PRIMARY if self.is_dark else Colors.LIGHT_TEXT_PRIMARY
        tm = Colors.DARK_TEXT_MUTED   if self.is_dark else Colors.LIGHT_TEXT_MUTED
        f  = Typography.FONT_FAMILY

        # Peta peran → string CSS
        styles = {
            "section_header": f"color:{tp};font-size:18px;font-weight:bold;font-family:{f};background:transparent;",
            "primary_large":  f"color:{tp};font-size:28px;font-weight:bold;font-family:{f};background:transparent;",
            "primary":        f"color:{tp};font-size:15px;font-weight:700;font-family:{f};background:transparent;",
            "muted":          f"color:{tm};font-size:13px;font-family:{f};background:transparent;",
            "muted_small":    f"color:{tm};font-size:12px;font-family:{f};background:transparent;",
        }

        # Terapkan CSS ke setiap label sesuai perannya
        for lbl, role in self._theme_labels:
            if role in styles:
                lbl.setStyleSheet(styles[role])
