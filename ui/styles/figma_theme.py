"""
Sistem Tema MangoDefend — berdasarkan desain Figma.

File ini adalah sumber kebenaran tunggal (single source of truth) untuk:
  - Palet warna (Colors)
  - Tipografi / font (Typography)
  - Ukuran dan jarak (Sizes)
  - Pembantu stylesheet (StyleHelper) — metode yang menghasilkan CSS berulang
  - Stylesheet lengkap mode gelap (DARK_THEME) dan terang (LIGHT_THEME)
  - Fungsi pemilih tema (get_theme_stylesheet)

Aturan: jangan letakkan warna atau CSS berulang di dalam file tampilan.
Semua harus didefinisikan di sini dan diimpor dari sini.
"""

# ============================================================
# PALET WARNA — warna-warna dari desain Figma
# ============================================================

class Colors:
    """
    Kumpulan konstanta warna yang digunakan di seluruh aplikasi.

    Kenapa menggunakan konstanta?
      Jika warna ingin diubah, cukup ubah satu baris di sini.
      Semua komponen yang menggunakannya akan ikut berubah secara otomatis.
    """

    # ── Warna Utama (gradasi Oranye → Merah) ──
    # Warna-warna ini digunakan untuk tombol utama, logo, dan aksen interaktif.

    ORANGE_500 = "#FFA500"  # Oranye utama — warna identitas aplikasi
    ORANGE_400 = "#FFB732"  # Oranye lebih terang — untuk hover tombol
    ORANGE_300 = "#FFC04C"  # Oranye paling terang — untuk aksen ringan

    RED_500 = "#FF6B35"     # Merah-oranye utama — pasangan gradasi ORANGE_500
    RED_400 = "#FF8C00"     # Oranye tua — untuk hover merah
    RED_600 = "#E64A19"     # Merah lebih gelap — untuk tombol ditekan / destruktif

    # ── Warna Aksen Status ──
    # Digunakan untuk menunjukkan kondisi: aman, berhasil, atau terpantau.

    GREEN_500  = "#32CD32"  # Hijau cerah — menunjukkan status "Terlindungi / Aman"
    GREEN_400  = "#90EE90"  # Hijau muda — untuk elemen status yang lebih ringan
    EMERALD_500 = "#10b981" # Hijau emerald — untuk statistik "proses dipantau"

    # ── Warna Netral Mode Gelap ──
    # Latar belakang dan teks untuk mode gelap (dark mode).

    DARK_BG_PRIMARY   = "#0B0B0F"  # Latar belakang utama aplikasi — hampir hitam
    DARK_BG_SECONDARY = "#1A1A1A"  # Latar kartu — sedikit lebih terang dari primary
    DARK_BG_TERTIARY  = "#252525"  # Elemen terangkat (elevated) — paling terang di dark mode

    DARK_BORDER        = "rgba(255, 255, 255, 0.1)"  # Garis tepi halus — putih sangat transparan
    DARK_TEXT_PRIMARY  = "#FFFFFF"   # Teks utama — putih penuh
    DARK_TEXT_SECONDARY = "#CCCCCC"  # Teks sekunder — putih abu-abu
    DARK_TEXT_MUTED    = "#6B7280"   # Teks muted/samar — abu-abu sedang (untuk deskripsi)

    # ── Warna Netral Mode Terang ──
    # Latar belakang dan teks untuk mode terang (light mode).

    LIGHT_BG_PRIMARY   = "#FFFFFF"   # Latar belakang utama — putih bersih
    LIGHT_BG_SECONDARY = "#F9FAFB"   # Latar kartu — putih tulang sangat terang
    LIGHT_BG_TERTIARY  = "#FFF5E6"   # Latar terangkat — sedikit oranye pucat

    LIGHT_BORDER        = "#E5E7EB"  # Garis tepi — abu-abu muda (border kartu)
    LIGHT_TEXT_PRIMARY  = "#1F2937"  # Teks utama — hitam keabuan (mudah dibaca di putih)
    LIGHT_TEXT_SECONDARY = "#444444" # Teks sekunder — abu-abu gelap
    LIGHT_TEXT_MUTED    = "#6B7280"  # Teks muted — sama dengan dark mode (netral di keduanya)


# ============================================================
# TIPOGRAFI — pengaturan font
# ============================================================

class Typography:
    """
    Konstanta tipografi yang digunakan di seluruh aplikasi.

    FONT_FAMILY memuat daftar font cadangan:
      - 'Inter'     : Font modern yang bersih, digunakan jika tersedia.
      - 'Segoe UI'  : Font bawaan Windows, cadangan utama.
      - 'sans-serif': Font bawaan sistem sebagai cadangan terakhir.
    """

    # Font utama dengan daftar cadangan agar tampilan tetap rapi di semua OS
    FONT_FAMILY      = "'Inter', 'Segoe UI', sans-serif"

    # Font monospace untuk tampilan kode atau nama file
    FONT_FAMILY_MONO = "'Inter', 'Segoe UI', monospace"

    # ── Ukuran Font ──
    # Hierarki ukuran: H1 (judul besar) → TINY (catatan kaki kecil)

    SIZE_H1    = "32px"  # Judul halaman utama
    SIZE_H2    = "24px"  # Subjudul / nama bagian besar
    SIZE_H3    = "20px"  # Subjudul kartu
    SIZE_BODY  = "14px"  # Teks isi utama — ukuran yang nyaman dibaca
    SIZE_SMALL = "12px"  # Teks keterangan / badge
    SIZE_TINY  = "11px"  # Teks sangat kecil — catatan, tooltip


# ============================================================
# UKURAN & JARAK — satu tempat untuk semua dimensi
# ============================================================

class Sizes:
    """
    Konstanta ukuran dan jarak yang digunakan di seluruh aplikasi.

    Kenapa satu tempat?
      Memastikan semua komponen menggunakan ukuran yang sama.
      Jika ingin mengubah tinggi tombol, cukup ubah di sini.
    """

    BTN_HEIGHT_SM = 36   # Tinggi tombol kecil (misalnya tombol ikon di toolbar)
    BTN_HEIGHT_MD = 48   # Tinggi tombol sedang — ukuran default
    BTN_HEIGHT_LG = 52   # Tinggi tombol besar — tombol aksi utama di halaman

    CARD_RADIUS    = 24  # Sudut melengkung kartu dalam piksel
    CARD_PADDING_H = 28  # Jarak dalam kartu arah horizontal (kiri-kanan)
    CARD_PADDING_V = 24  # Jarak dalam kartu arah vertikal (atas-bawah)


# ============================================================
# PEMBANTU STYLESHEET — metode yang menghasilkan CSS berulang
# ============================================================

class StyleHelper:
    """
    Kumpulan metode statis yang menghasilkan string CSS (QSS) untuk
    komponen-komponen yang sering digunakan.

    Tujuan:
      Menghindari duplikasi CSS yang tersebar di banyak file tampilan.
      Jika gaya tombol ingin diubah, cukup ubah metode di sini.

    Cara penggunaan:
        btn.setStyleSheet(StyleHelper.pill_button_primary())
        label.setStyleSheet(StyleHelper.status_badge(Colors.GREEN_500))

    Aturan: setiap blok CSS yang diulang lebih dari satu kali harus ada di sini.
    """

    # ── Tombol ──────────────────────────────────────────────────────────────

    @staticmethod
    def pill_button_primary(height: int = Sizes.BTN_HEIGHT_MD) -> str:
        """
        Hasilkan CSS untuk tombol berbentuk kapsul (pill) dengan gradasi oranye→merah.
        Digunakan untuk aksi utama (misalnya: 'Scan File', 'Aktifkan Perlindungan').

        height : Tinggi tombol dalam piksel; border-radius dihitung otomatis (= height/2).
        """
        r = height // 2  # Border-radius = setengah tinggi → menghasilkan bentuk kapsul
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.ORANGE_500}, stop:1 {Colors.RED_500});
                color: white;
                border: none;
                border-radius: {r}px;
                padding: 0 20px;
                font-weight: 700;
                font-size: 14px;
                font-family: {Typography.FONT_FAMILY};
            }}
            QPushButton:hover {{
                /* Saat diarahkan mouse: gradasi bergeser ke warna lebih terang */
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.ORANGE_400}, stop:1 {Colors.RED_400});
            }}
            QPushButton:pressed {{
                /* Saat ditekan: gradasi bergeser ke warna lebih gelap */
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.RED_400}, stop:1 {Colors.RED_600});
            }}
            QPushButton:disabled {{
                /* Saat dinonaktifkan: tampilan pudar agar terlihat tidak bisa diklik */
                background: rgba(255,255,255,0.1);
                color: rgba(255,255,255,0.3);
            }}
        """

    @staticmethod
    def pill_button_danger(height: int = Sizes.BTN_HEIGHT_MD) -> str:
        """
        Hasilkan CSS untuk tombol kapsul merah — untuk aksi berbahaya/destruktif.
        Digunakan misalnya untuk tombol 'Nonaktifkan Perlindungan' atau 'Hapus'.

        Warna merah memberi isyarat visual: "hati-hati, ini aksi berbahaya".

        height : Tinggi tombol dalam piksel.
        """
        r = height // 2
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.RED_500}, stop:1 {Colors.RED_600});
                color: white;
                border: none;
                border-radius: {r}px;
                padding: 0 20px;
                font-weight: 700;
                font-size: 14px;
                font-family: {Typography.FONT_FAMILY};
            }}
            QPushButton:hover {{
                background: {Colors.RED_600};
            }}
            QPushButton:pressed {{
                background: {Colors.RED_600};
                opacity: 0.9;
            }}
        """

    @staticmethod
    def pill_button_outline(height: int = Sizes.BTN_HEIGHT_MD) -> str:
        """
        Hasilkan CSS untuk tombol kapsul dengan hanya outline oranye (tanpa isian penuh).
        Digunakan untuk aksi sekunder yang tidak terlalu mendesak.

        Tampilan: latar transparan + border oranye + teks oranye.

        height : Tinggi tombol dalam piksel.
        """
        r = height // 2
        return f"""
            QPushButton {{
                background: rgba(255, 165, 0, 0.1);  /* Isian sangat tipis */
                color: {Colors.ORANGE_400};
                border: 2px solid {Colors.ORANGE_500};
                border-radius: {r}px;
                padding: 0 20px;
                font-weight: 700;
                font-size: 14px;
                font-family: {Typography.FONT_FAMILY};
            }}
            QPushButton:hover {{
                background: rgba(255, 165, 0, 0.2);  /* Sedikit lebih terlihat saat hover */
                border: 2px solid {Colors.ORANGE_400};
            }}
            QPushButton:pressed {{
                background: rgba(255, 165, 0, 0.3);  /* Lebih solid saat ditekan */
            }}
        """

    # ── Label ───────────────────────────────────────────────────────────────

    @staticmethod
    def section_header(is_dark: bool = True) -> str:
        """
        Hasilkan CSS untuk label judul bagian (section header) ukuran 18px tebal.
        Warna menyesuaikan tema aktif.

        is_dark : True = teks putih, False = teks hitam keabuan.
        """
        color = Colors.DARK_TEXT_PRIMARY if is_dark else Colors.LIGHT_TEXT_PRIMARY
        return f"""
            color: {color};
            font-size: 18px;
            font-weight: bold;
            background: transparent;
            font-family: {Typography.FONT_FAMILY};
        """

    @staticmethod
    def muted_body(size: str = "13px") -> str:
        """
        Hasilkan CSS untuk teks deskripsi/keterangan yang lebih redup.
        Selalu menggunakan warna DARK_TEXT_MUTED (abu-abu) yang dibaca di semua tema.

        size : Ukuran font, default "13px".
        """
        return f"""
            color: {Colors.DARK_TEXT_MUTED};
            font-size: {size};
            background: transparent;
            font-family: {Typography.FONT_FAMILY};
        """

    # ── Badge ────────────────────────────────────────────────────────────────

    @staticmethod
    def status_badge(color: str) -> str:
        """
        Hasilkan CSS untuk badge status berbentuk pil dengan border berwarna.
        Warna teks dan border menggunakan parameter 'color' yang diberikan.

        Digunakan untuk menampilkan status seperti "Protected" atau "Malware".

        color : String warna hex, misalnya Colors.GREEN_500 atau Colors.ORANGE_500.
        """
        return f"""
            color: {color};
            font-size: 13px;
            font-weight: 700;
            background: transparent;
            border: 2px solid {color};   /* Border berwarna sama dengan teks */
            border-radius: 9999px;        /* 9999px = selalu bulat sempurna */
            padding: 6px 20px;
            font-family: {Typography.FONT_FAMILY};
        """

    @staticmethod
    def tag_badge() -> str:
        """
        Hasilkan CSS untuk tag/label kecil berwarna oranye.
        Digunakan untuk label teknis seperti 'Pseudo-Blocking', 'ONNX Runtime', dsb.

        Ukuran lebih kecil dari status_badge, dengan latar oranye samar.
        """
        return f"""
            color: {Colors.ORANGE_400};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.5px;         /* Sedikit jarak antar huruf agar mudah dibaca */
            background: rgba(255, 165, 0, 0.15);  /* Latar oranye sangat tipis */
            border: 1px solid rgba(255, 165, 0, 0.3);  /* Border oranye tipis */
            border-radius: 9999px;
            padding: 3px 10px;
            font-family: {Typography.FONT_FAMILY};
        """


# ============================================================
# STYLESHEET LENGKAP MODE GELAP
# ============================================================

DARK_THEME = f"""
/* ========================================
   MODE GELAP — sesuai desain Figma
   ======================================== */

QMainWindow {{
    /* Latar jendela utama: gradasi diagonal dari hitam ke abu-abu sangat gelap */
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {Colors.DARK_BG_PRIMARY},
        stop:1 rgb(17, 17, 25));
}}

/* ========================================
   SIDEBAR (Panel Navigasi Kiri)
   ======================================== */

QWidget#sidebar {{
    /* Sidebar lebih transparan dari konten — efek kaca gelap */
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(0, 0, 0, 0.4),
        stop:0.5 rgba(0, 0, 0, 0.3),
        stop:1 rgba(0, 0, 0, 0.4));
    /* Garis tipis di kanan sidebar sebagai pemisah dari area konten */
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}}

QLabel#logoTitle {{
    /* Nama aplikasi "MangoDefend" di atas sidebar — warna oranye brand */
    color: {Colors.ORANGE_400};
    font-size: 18px;
    font-weight: bold;
    font-family: {Typography.FONT_FAMILY};
    background: transparent;
}}

QLabel#logoSubtitle {{
    /* Tagline kecil di bawah nama aplikasi */
    color: {Colors.DARK_TEXT_MUTED};
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1px;  /* Jarak antar huruf agar terbaca meski kecil */
    font-family: {Typography.FONT_FAMILY};
}}

/* Badge status "Protected" / "Unprotected" di sidebar */
QFrame#statusBadge {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(50, 205, 50, 0.1),   /* Hijau transparan di atas */
        stop:1 rgba(16, 185, 129, 0.05)); /* Emerald transparan di bawah */
    border: 1px solid rgba(50, 205, 50, 0.2);
    border-radius: 9999px;  /* Badge berbentuk pil */
}}

/* ── Tombol Navigasi Sidebar ── */
QPushButton#navButton {{
    /* Status normal: transparan, teks abu-abu samar */
    background: transparent;
    color: {Colors.DARK_TEXT_MUTED};
    border: 2px solid transparent;  /* Border ada tapi transparan (siap berubah saat active) */
    border-radius: 9999px;
    padding: 12px 20px;
    text-align: left;
    font-size: 14px;
    font-weight: 600;
    font-family: {Typography.FONT_FAMILY};
}}

QPushButton#navButton:hover {{
    /* Hover: teks lebih terang, latar putih sangat samar */
    color: {Colors.DARK_TEXT_PRIMARY};
    background: rgba(255, 255, 255, 0.05);
}}

QPushButton#navButton:checked {{
    /* Aktif/terpilih: latar oranye samar + border oranye */
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(255, 165, 0, 0.2),
        stop:1 rgba(255, 107, 53, 0.2));
    color: {Colors.ORANGE_400};
    border: 2px solid rgba(255, 165, 0, 0.3);
}}

/* ========================================
   KARTU (Glassmorphism)
   ======================================== */

QFrame.glassCard {{
    /* Kartu kaca: latar putih sangat transparan dengan border oranye */
    background: rgba(255, 255, 255, 0.05);  /* 5% putih = efek kaca */
    border-radius: 24px;
    border: 1px solid rgba(255, 165, 0, 0.3);
    padding: 24px;
}}

QFrame.glassCard:hover {{
    border: 1px solid rgba(255, 165, 0, 0.3);
}}

/* ========================================
   KARTU STATISTIK
   ======================================== */

QFrame#statCard {{
    /* Kartu statistik: gradasi oranye sangat tipis */
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(255, 165, 0, 0.1),
        stop:1 rgba(255, 107, 53, 0.05));
    border: 1px solid rgba(255, 165, 0, 0.2);
    border-radius: 20px;
}}

QLabel.statValue {{
    /* Angka statistik besar — putih bold */
    color: {Colors.DARK_TEXT_PRIMARY};
    font-size: 48px;
    font-weight: bold;
    font-family: {Typography.FONT_FAMILY};
}}

QLabel.statLabel {{
    /* Label di bawah angka statistik */
    color: {Colors.DARK_TEXT_SECONDARY};
    font-size: 13px;
    font-family: {Typography.FONT_FAMILY};
}}

/* ========================================
   TOMBOL
   ======================================== */

QPushButton#primaryButton {{
    /* Tombol utama: gradasi oranye→merah */
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {Colors.ORANGE_500},
        stop:1 {Colors.RED_500});
    color: white;
    border: none;
    border-radius: 9999px;
    padding: 14px 28px;
    font-weight: 600;
    font-size: 14px;
    font-family: {Typography.FONT_FAMILY};
}}

QPushButton#primaryButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {Colors.ORANGE_400},
        stop:1 {Colors.RED_400});
}}

QPushButton#primaryButton:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {Colors.RED_400},
        stop:1 {Colors.RED_600});
}}

QPushButton#secondaryButton {{
    /* Tombol sekunder: latar transparan dengan border oranye */
    background: rgba(255, 255, 255, 0.05);
    color: {Colors.ORANGE_400};
    border: 2px solid {Colors.ORANGE_500};
    border-radius: 9999px;
    padding: 12px 24px;
    font-weight: 600;
    font-size: 14px;
    font-family: {Typography.FONT_FAMILY};
}}

QPushButton#secondaryButton:hover {{
    background: rgba(255, 165, 0, 0.1);
    border: 2px solid {Colors.ORANGE_400};
}}

/* ========================================
   PROGRESS BAR (Bilah Kemajuan)
   ======================================== */

QProgressBar {{
    border: none;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.1);  /* Latar transparan sebagai trek */
    text-align: center;
    color: {Colors.DARK_TEXT_PRIMARY};
    font-weight: 600;
    font-size: 12px;
}}

QProgressBar::chunk {{
    /* Bagian yang sudah terisi: gradasi oranye→merah */
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {Colors.ORANGE_500},
        stop:1 {Colors.RED_500});
    border-radius: 6px;
}}

/* ========================================
   SCROLLBAR (Bilah Gulir Vertikal)
   ======================================== */

QScrollBar:vertical {{
    border: none;
    background: rgba(255, 255, 255, 0.05);  /* Trek gulir: hampir tak terlihat */
    width: 10px;
    margin: 0;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    /* Handle (pegangan) gulir berwarna oranye transparan */
    background: rgba(255, 165, 0, 0.3);
    border-radius: 5px;
    min-height: 30px;  /* Tinggi minimum agar mudah diklik */
}}

QScrollBar::handle:vertical:hover {{
    /* Handle lebih terlihat saat diarahkan mouse */
    background: rgba(255, 165, 0, 0.5);
}}

/* ========================================
   LABEL TEKS
   ======================================== */

QLabel.heading {{
    /* Judul halaman besar */
    color: {Colors.DARK_TEXT_PRIMARY};
    font-size: 28px;
    font-weight: bold;
    font-family: {Typography.FONT_FAMILY};
}}

QLabel.subheading {{
    /* Subjudul / deskripsi singkat di bawah judul */
    color: {Colors.DARK_TEXT_SECONDARY};
    font-size: 14px;
    font-family: {Typography.FONT_FAMILY};
}}

QLabel.caption {{
    /* Teks keterangan kecil — metadata, waktu, dsb */
    color: {Colors.DARK_TEXT_MUTED};
    font-size: 12px;
    font-family: {Typography.FONT_FAMILY};
}}

QToolTip {{
    /* Tooltip saat mouse diarahkan ke elemen */
    background: {Colors.DARK_BG_TERTIARY};
    color: {Colors.DARK_TEXT_PRIMARY};
    border: 1px solid rgba(255, 165, 0, 0.35);
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
    font-family: {Typography.FONT_FAMILY};
}}
"""


# ============================================================
# STYLESHEET LENGKAP MODE TERANG
# ============================================================

LIGHT_THEME = f"""
/* ========================================
   MODE TERANG — sesuai desain Figma
   ======================================== */

QMainWindow {{
    /* Latar jendela utama: gradasi putih ke krem oranye muda */
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgb(255, 250, 245),
        stop:0.5 white,
        stop:1 rgb(255, 240, 230));
}}

/* ========================================
   SIDEBAR (Panel Navigasi Kiri)
   ======================================== */

QWidget#sidebar {{
    /* Sidebar terang: putih semi-transparan */
    background: rgba(255, 255, 255, 0.6);
    border-right: 1px solid rgba(255, 165, 0, 0.2);
}}

QLabel#logoTitle {{
    /* Nama aplikasi dengan oranye yang lebih tegas di latar terang */
    color: {Colors.ORANGE_500};
    font-size: 18px;
    font-weight: bold;
    font-family: {Typography.FONT_FAMILY};
    background: transparent;
}}

QLabel#logoSubtitle {{
    color: {Colors.LIGHT_TEXT_MUTED};
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1px;
    font-family: {Typography.FONT_FAMILY};
}}

/* Badge status di sidebar (mode terang) */
QFrame#statusBadge {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgb(240, 253, 244),  /* Hijau muda sangat terang */
        stop:1 rgb(220, 252, 231)); /* Hijau muda */
    border: 1px solid rgb(167, 243, 208);
    border-radius: 9999px;
}}

/* ── Tombol Navigasi Sidebar (Mode Terang) ── */
QPushButton#navButton {{
    background: transparent;
    color: {Colors.LIGHT_TEXT_SECONDARY};
    border: 2px solid transparent;
    border-radius: 9999px;
    padding: 12px 20px;
    text-align: left;
    font-size: 14px;
    font-weight: 600;
    font-family: {Typography.FONT_FAMILY};
}}

QPushButton#navButton:hover {{
    color: {Colors.ORANGE_500};
    background: rgba(255, 165, 0, 0.05);
}}

QPushButton#navButton:checked {{
    /* Aktif: latar oranye pastel + border oranye */
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgb(255, 237, 213),  /* Peach sangat terang */
        stop:1 rgb(254, 215, 170)); /* Peach muda */
    color: {Colors.ORANGE_500};
    border: 2px solid {Colors.ORANGE_400};
}}

/* ========================================
   KARTU (Mode Terang)
   ======================================== */

QFrame.glassCard {{
    /* Kartu mode terang: putih semi-transparan dengan border abu-abu */
    background: rgba(255, 255, 255, 0.6);
    border: 1px solid {Colors.LIGHT_BORDER};
    border-radius: 24px;
    padding: 24px;
}}

QFrame.glassCard:hover {{
    border: 1px solid rgba(255, 165, 0, 0.4);
}}

/* ========================================
   KARTU STATISTIK (Mode Terang)
   ======================================== */

QFrame#statCard {{
    /* Gradasi krem-oranye sangat terang */
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgb(255, 247, 237),
        stop:1 rgb(254, 226, 226));
    border: 1px solid rgb(253, 186, 116);
    border-radius: 20px;
}}

QLabel.statValue {{
    color: {Colors.LIGHT_TEXT_PRIMARY};
    font-size: 48px;
    font-weight: bold;
    font-family: {Typography.FONT_FAMILY};
}}

QLabel.statLabel {{
    color: {Colors.LIGHT_TEXT_SECONDARY};
    font-size: 13px;
    font-family: {Typography.FONT_FAMILY};
}}

/* ========================================
   TOMBOL (Mode Terang)
   ======================================== */

QPushButton#primaryButton {{
    /* Sama dengan mode gelap — oranye→merah selalu kontras */
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {Colors.ORANGE_500},
        stop:1 {Colors.RED_500});
    color: white;
    border: none;
    border-radius: 9999px;
    padding: 14px 28px;
    font-weight: 600;
    font-size: 14px;
    font-family: {Typography.FONT_FAMILY};
}}

QPushButton#primaryButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {Colors.ORANGE_400},
        stop:1 {Colors.RED_400});
}}

QPushButton#primaryButton:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {Colors.RED_400},
        stop:1 {Colors.RED_600});
}}

QPushButton#secondaryButton {{
    /* Mode terang: latar putih bersih dengan border oranye */
    background: white;
    color: {Colors.ORANGE_500};
    border: 2px solid {Colors.ORANGE_500};
    border-radius: 9999px;
    padding: 12px 24px;
    font-weight: 600;
    font-size: 14px;
    font-family: {Typography.FONT_FAMILY};
}}

QPushButton#secondaryButton:hover {{
    background: rgb(255, 247, 237);  /* Krem oranye muda saat hover */
    border: 2px solid {Colors.ORANGE_400};
}}

/* ========================================
   PROGRESS BAR (Mode Terang)
   ======================================== */

QProgressBar {{
    border: none;
    border-radius: 6px;
    background: {Colors.LIGHT_BG_SECONDARY};  /* Trek abu-abu terang */
    text-align: center;
    color: {Colors.LIGHT_TEXT_PRIMARY};
    font-weight: 600;
    font-size: 12px;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {Colors.ORANGE_500},
        stop:1 {Colors.RED_500});
    border-radius: 6px;
}}

/* ========================================
   SCROLLBAR (Mode Terang)
   ======================================== */

QScrollBar:vertical {{
    border: none;
    background: {Colors.LIGHT_BG_SECONDARY};
    width: 10px;
    margin: 0;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background: rgba(255, 165, 0, 0.4);
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: rgba(255, 165, 0, 0.6);
}}

/* ========================================
   LABEL TEKS (Mode Terang)
   ======================================== */

QLabel.heading {{
    color: {Colors.LIGHT_TEXT_PRIMARY};
    font-size: 28px;
    font-weight: bold;
    font-family: {Typography.FONT_FAMILY};
}}

QLabel.subheading {{
    color: {Colors.LIGHT_TEXT_SECONDARY};
    font-size: 14px;
    font-family: {Typography.FONT_FAMILY};
}}

QLabel.caption {{
    color: {Colors.LIGHT_TEXT_MUTED};
    font-size: 12px;
    font-family: {Typography.FONT_FAMILY};
}}

QToolTip {{
    background: {Colors.LIGHT_BG_PRIMARY};
    color: {Colors.LIGHT_TEXT_PRIMARY};
    border: 1px solid rgba(255, 165, 0, 0.4);
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
    font-family: {Typography.FONT_FAMILY};
}}
"""


# ============================================================
# FUNGSI PEMBANTU
# ============================================================

def get_theme_stylesheet(is_dark: bool = True) -> str:
    """
    Kembalikan stylesheet lengkap sesuai tema yang dipilih.

    Fungsi ini dipanggil oleh ModernWindow.apply_theme() setiap kali
    pengguna mengganti tema atau tema OS berubah.

    is_dark : True = kembalikan DARK_THEME, False = kembalikan LIGHT_THEME.

    Contoh penggunaan:
        window.setStyleSheet(get_theme_stylesheet(is_dark=True))
    """
    return DARK_THEME if is_dark else LIGHT_THEME


def get_gradient_style(color1: str, color2: str, direction: str = "x") -> str:
    """
    Hasilkan string gradasi QSS dari dua warna.

    Berguna saat komponen perlu gradasi kustom yang tidak ada di StyleHelper.

    color1    : Warna awal gradasi (string hex, misal "#FFA500").
    color2    : Warna akhir gradasi.
    direction : Arah gradasi:
                  'x'        = horizontal (kiri ke kanan)
                  'y'        = vertikal (atas ke bawah)
                  'diagonal' = diagonal (kiri-atas ke kanan-bawah)

    Contoh:
        btn.setStyleSheet(f"background: {get_gradient_style('#FFA500', '#FF6B35', 'x')};")
    """
    if direction == "x":
        # Gradasi horizontal: kiri (x1=0) ke kanan (x2=1)
        return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color1}, stop:1 {color2})"
    elif direction == "y":
        # Gradasi vertikal: atas (y1=0) ke bawah (y2=1)
        return f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {color1}, stop:1 {color2})"
    else:
        # Gradasi diagonal: kiri-atas ke kanan-bawah
        return f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {color1}, stop:1 {color2})"
