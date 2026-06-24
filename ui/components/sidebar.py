"""
Komponen Navigasi Sidebar — Menu samping dengan logo, tab navigasi, dan kontrol bawah.

File ini bertanggung jawab membuat panel kiri aplikasi MangoDefend yang berisi:
- Logo dan nama aplikasi
- Badge status sistem (terlindungi / tidak)
- Lima tombol navigasi (Dashboard, Scan, Protection, Quarantine, Update)
- Kartu jumlah ancaman yang diblokir
- Tombol untuk berganti tema (gelap/terang)
"""

import os
import sys

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QButtonGroup, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFont

# Widget kartu bergaya kustom dan palet warna dari tema aplikasi
from ui.widgets import SoftCard
from ui.styles.figma_theme import Colors


def _asset(relative: str) -> str:
    """
    Mencari lokasi file aset (gambar, ikon) yang benar.

    Ketika aplikasi dikemas menjadi file .exe (frozen), aset ada di folder sementara
    yang disebut _MEIPASS. Ketika sedang dikembangkan, aset dicari dari folder root
    proyek dengan naik dua level dari file ini.

    Args:
        relative: Jalur file relatif dari folder root, misalnya 'assets/mango_icon.png'.

    Returns:
        Jalur file lengkap (absolut) yang siap digunakan.
    """
    # Jika aplikasi sudah dikemas sebagai .exe, gunakan folder sementara PyInstaller
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        # sidebar.py berada di ui/components/ — naik 2 level ke root aplikasi
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, relative)


class Sidebar(QWidget):
    """
    Navigasi sidebar utama aplikasi MangoDefend.

    Panel ini berada di sisi kiri layar dan selalu terlihat selama aplikasi berjalan.
    Berisi logo, badge status sistem, lima tombol navigasi,
    penghitung ancaman yang berhasil diblokir, dan tombol ganti tema.

    Sinyal yang dikirim ke luar:
        tab_changed(str): Dikirim ketika pengguna mengklik salah satu tab navigasi.
                          Isinya adalah ID tab, misalnya 'dashboard' atau 'scan'.
        theme_toggled(bool): Dikirim ketika pengguna menekan tombol ganti tema.
                             Isinya True jika tema gelap aktif, False jika tema terang.
    """

    # Sinyal: memberi tahu tampilan utama halaman mana yang harus ditampilkan
    tab_changed = Signal(str)    # nilai: 'dashboard' | 'scan' | 'protection' | 'quarantine' | 'update'

    # Sinyal: memberi tahu aplikasi bahwa pengguna ingin ganti tema
    theme_toggled = Signal(bool) # nilai: True = tema gelap, False = tema terang

    def __init__(self, is_dark: bool = True, parent=None):
        """
        Menyiapkan sidebar dengan tema awal dan membangun semua elemennya.

        Args:
            is_dark: Jika True, sidebar menggunakan tema gelap (default).
                     Jika False, menggunakan tema terang.
            parent: Widget induk dari sidebar ini (biasanya jendela utama).
        """
        super().__init__(parent)

        # Beri nama unik pada widget ini agar bisa ditargetkan oleh stylesheet
        self.setObjectName("sidebar")

        # Kunci lebar sidebar agar tidak melebar/menyempit saat jendela diubah ukurannya
        self.setFixedWidth(264)

        # Simpan status tema saat ini
        self.is_dark = is_dark

        # Penghitung ancaman yang diblokir sejak aplikasi dibuka
        self.threats_count = 0

        # Bangun semua elemen tampilan sidebar
        self.setup_ui()

    # ------------------------------------------------------------------
    # MEMBANGUN TAMPILAN
    # ------------------------------------------------------------------

    def setup_ui(self):
        """
        Menyusun semua bagian sidebar ke dalam tata letak vertikal utama.

        Urutan dari atas ke bawah:
        1. Logo + nama aplikasi
        2. Badge status sistem
        3. Tombol-tombol navigasi
        4. Kartu ancaman + tombol ganti tema
        5. Ruang kosong fleksibel di bawah
        """
        # Tata letak vertikal: elemen disusun dari atas ke bawah
        layout = QVBoxLayout(self)

        # Jarak tepi: 24 piksel di semua sisi agar tidak terlalu rapat
        layout.setContentsMargins(24, 24, 24, 24)

        # Jarak antar elemen
        layout.setSpacing(16)

        # Tambahkan bagian logo di paling atas
        layout.addWidget(self._create_logo_section())

        # Beri sedikit ruang ekstra antara logo dan badge status
        layout.addSpacing(12)

        # Tambahkan badge yang menampilkan status keamanan sistem
        layout.addWidget(self._create_status_badge())

        # Ruang antar badge dan tombol navigasi
        layout.addSpacing(16)

        # Tambahkan kelompok tombol navigasi
        layout.addLayout(self._create_navigation())

        # Tambahkan bagian bawah (kartu ancaman + tombol tema)
        layout.addLayout(self._create_bottom_section())

        # Ruang kosong yang fleksibel: mendorong semua konten ke atas
        layout.addStretch()

    def _create_logo_section(self) -> QWidget:
        """
        Membangun area logo di bagian paling atas sidebar.

        Berisi ikon mango di sisi kiri dan dua baris teks di sisi kanan:
        - Baris atas: nama aplikasi 'MANGO DEFEND'
        - Baris bawah: tagline 'Mango Defends'

        Returns:
            Widget yang berisi logo dan teks merek.
        """
        # Container utama area logo
        container = QWidget()
        container.setMinimumHeight(64)  # Tinggi minimum agar logo tidak terpotong

        # Tata letak horizontal: ikon di kiri, teks di kanan
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)  # Tidak ada jarak tepi tambahan
        layout.setSpacing(12)  # Jarak antara ikon dan teks
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # Sejajarkan vertikal ke tengah

        # --- Area ikon logo ---
        # Kotak kecil yang membungkus gambar ikon
        logo_wrap = QWidget()
        logo_wrap.setFixedSize(56, 56)  # Ukuran tetap 56x56 piksel
        logo_wrap.setStyleSheet("background: transparent;")  # Latar belakang transparan

        logo_wrap_layout = QVBoxLayout(logo_wrap)
        logo_wrap_layout.setContentsMargins(4, 4, 4, 4)  # Sedikit padding agar ikon tidak mepet
        logo_wrap_layout.setSpacing(0)
        logo_wrap_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Ikon di tengah kotak

        # Label yang menampilkan gambar ikon
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Cari file gambar ikon aplikasi
        icon_path = _asset(os.path.join("assets", "mango_icon.png"))

        if os.path.exists(icon_path):
            # Jika file gambar ditemukan, muat dan skalakan ke 42x42 piksel
            pixmap = QPixmap(icon_path)
            scaled = pixmap.scaled(
                42, 42,
                Qt.AspectRatioMode.KeepAspectRatio,      # Jaga proporsi gambar
                Qt.TransformationMode.SmoothTransformation, # Penskalaan halus (anti-alias)
            )
            logo_label.setPixmap(scaled)
        else:
            # Jika file tidak ditemukan, tampilkan emoji mango sebagai pengganti
            logo_label.setStyleSheet("font-size: 48px;")

        logo_label.setFixedSize(44, 44)  # Ukuran tetap untuk label ikon
        logo_wrap_layout.addWidget(logo_label)
        layout.addWidget(logo_wrap)

        # --- Area teks nama aplikasi ---
        text_container = QWidget()
        # Boleh melebar mengikuti sisa ruang yang tersedia
        text_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        text_container.setMinimumWidth(0)

        # Tata letak vertikal untuk dua baris teks
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)  # Jarak kecil antara nama dan tagline

        # Baris pertama: nama aplikasi utama
        title = QLabel("MANGO DEFEND")
        title.setObjectName("logoTitle")  # ID untuk styling via stylesheet
        title.setWordWrap(False)  # Jangan bungkus ke baris baru
        text_layout.addWidget(title)

        # Baris kedua: tagline/deskripsi singkat
        subtitle = QLabel("Mango Defends")
        subtitle.setObjectName("logoSubtitle")
        subtitle.setWordWrap(False)
        text_layout.addWidget(subtitle)

        # Tambahkan area teks ke tata letak, beri bobot 1 agar bisa melebar
        layout.addWidget(text_container, 1)

        return container

    def _create_status_badge(self) -> QFrame:
        """
        Membangun badge status sistem di bawah logo.

        Badge ini menunjukkan apakah komputer sedang terlindungi atau tidak,
        dengan indikator warna (hijau = aman, merah = tidak terlindungi)
        dan sebuah progress bar dekoratif.

        Returns:
            Frame yang berisi semua elemen badge status.
        """
        # Gunakan QFrame sebagai wadah dengan gaya khusus via stylesheet
        badge = QFrame()
        badge.setObjectName("statusBadge")  # ID untuk styling via stylesheet

        # Tata letak vertikal dalam badge
        layout = QVBoxLayout(badge)
        layout.setContentsMargins(20, 16, 20, 16)  # Padding dalam kartu
        layout.setSpacing(12)  # Jarak antar baris

        # --- Baris atas: teks status dan indikator titik ---
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        # Kontainer untuk dua baris teks status
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        # Label kecil "System Status" di atas
        status_label = QLabel("System Status")
        status_label.setStyleSheet(f"color: {Colors.GREEN_500}; font-size: 11px; font-weight: 600;")
        text_layout.addWidget(status_label)

        # Teks status utama — diawali dengan "Unprotected", akan diperbarui lewat update_status()
        self.status_text = QLabel("Unprotected")
        self.status_text.setStyleSheet(f"color: {Colors.RED_500}; font-size: 18px; font-weight: bold;")
        text_layout.addWidget(self.status_text)

        # Tambahkan teks ke baris header, beri bobot 1 agar bisa melebar
        header_row.addWidget(text_container, 1)

        # Titik bulat (●) sebagai indikator visual — disimpan agar warnanya bisa diubah
        self.pulse_indicator = QLabel("●")
        self.pulse_indicator.setStyleSheet(f"color: {Colors.RED_500}; font-size: 12px;")
        header_row.addWidget(self.pulse_indicator)

        layout.addLayout(header_row)

        # --- Progress bar dekoratif (hanya visual, tidak merepresentasikan data nyata) ---
        # Latar belakang progress bar (abu-abu gelap)
        progress_bg = QFrame()
        progress_bg.setFixedHeight(6)  # Tinggi sangat kecil agar terlihat seperti garis tipis
        progress_bg.setStyleSheet("background: rgba(0, 0, 0, 0.3); border-radius: 3px;")

        # Isian hijau yang melapisi latar belakang, meniru tampilan loading yang hampir penuh
        progress_fill = QFrame(progress_bg)
        progress_fill.setGeometry(0, 0, int(badge.width() * 0.95), 6)  # Lebar 95% sebagai dekorasi
        progress_fill.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {Colors.GREEN_500}, stop:1 {Colors.EMERALD_500});
            border-radius: 3px;
        """)

        layout.addWidget(progress_bg)

        return badge

    def _create_navigation(self) -> QVBoxLayout:
        """
        Membangun deretan tombol navigasi di tengah sidebar.

        Lima tombol dibuat dan dikelompokkan agar hanya satu yang aktif pada satu waktu
        (seperti radio button). Ketika tombol diklik, sinyal tab_changed dikirim dengan
        ID tab yang sesuai.

        Returns:
            Tata letak vertikal berisi lima tombol navigasi.
        """
        # Tata letak vertikal dengan jarak kecil antar tombol
        layout = QVBoxLayout()
        layout.setSpacing(8)

        # Daftar tab: (ID internal, teks yang ditampilkan)
        nav_items = [
            ("dashboard",  "Dashboard"),    # Halaman ringkasan utama
            ("scan",       "Scan"),         # Halaman pemindaian malware
            ("protection", "Protection"),   # Halaman proteksi realtime
            ("quarantine", "Quarantine"),   # Halaman file karantina
            ("update",     "Update"),       # Halaman pembaruan model AI
        ]

        # QButtonGroup memastikan hanya satu tombol yang aktif/terpilih pada satu waktu
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)  # Mode eksklusif: satu klik = yang lain non-aktif

        # Buat tombol untuk setiap item navigasi
        for tab_id, label in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("navButton")   # ID untuk styling via stylesheet
            btn.setCheckable(True)           # Tombol bisa dalam keadaan aktif/tidak aktif
            btn.setProperty("tab_id", tab_id)  # Simpan ID tab di properti tombol
            btn.setCursor(Qt.CursorShape.PointingHandCursor)  # Kursor berubah jadi tangan saat hover
            btn.setMinimumHeight(50)         # Tinggi minimum agar mudah diklik

            # Ketika tombol diklik: kirim sinyal tab_changed dengan ID tab yang sesuai
            btn.clicked.connect(lambda checked, tid=tab_id: self.tab_changed.emit(tid))

            # Tambahkan tombol ke grup dan ke tata letak
            self.nav_group.addButton(btn)
            layout.addWidget(btn)

        # Aktifkan tombol pertama (Dashboard) secara otomatis saat aplikasi dibuka
        self.nav_group.buttons()[0].setChecked(True)

        return layout

    def _create_bottom_section(self) -> QVBoxLayout:
        """
        Membangun bagian bawah sidebar dengan dua elemen:
        1. Kartu yang menampilkan jumlah ancaman yang berhasil diblokir
        2. Tombol untuk beralih antara tema gelap dan terang

        Returns:
            Tata letak vertikal berisi kartu ancaman dan tombol tema.
        """
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # --- Kartu penghitung ancaman ---
        # SoftCard adalah kartu kustom dengan efek bayangan dan warna aksen
        self.threats_card = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_500, hover_effect=False)
        self.threats_card.setMinimumHeight(96)

        # Tata letak dalam kartu
        threats_layout = QVBoxLayout(self.threats_card)
        threats_layout.setContentsMargins(18, 16, 18, 16)
        threats_layout.setSpacing(8)

        # Label judul "Threats Blocked"
        self._threats_title_lbl = QLabel("Threats Blocked")
        threats_layout.addWidget(self._threats_title_lbl)

        # Angka besar yang menampilkan jumlah ancaman — diawali dengan "0"
        self.threats_label = QLabel("0")
        self.threats_label.setStyleSheet(f"""
            color: {Colors.ORANGE_500};
            font-size: 34px;
            font-weight: bold;
            background: transparent;
        """)
        threats_layout.addWidget(self.threats_label)

        # Label kecil "Sesi ini" yang menjelaskan konteks angka tersebut
        self._threats_meta_lbl = QLabel("Sesi ini")
        threats_layout.addWidget(self._threats_meta_lbl)

        # Terapkan warna teks sesuai tema saat ini
        self._apply_threats_card_theme()

        layout.addWidget(self.threats_card)

        # --- Tombol ganti tema ---
        # Label tombol mencerminkan tema yang SEDANG aktif (bukan yang akan aktif)
        theme_label = " Dark Mode" if self.is_dark else " Light Mode"
        self.theme_btn = QPushButton(theme_label)
        self.theme_btn.setObjectName("secondaryButton")  # ID untuk styling via stylesheet
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)  # Kursor tangan saat hover
        self.theme_btn.setMinimumHeight(44)

        # Ketika diklik, jalankan fungsi _toggle_theme untuk membalik tema
        self.theme_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self.theme_btn)

        return layout

    def _apply_threats_card_theme(self):
        """
        Memperbarui warna teks judul dan keterangan di kartu ancaman sesuai tema saat ini.

        Warna teks berbeda antara tema gelap dan terang agar tetap terbaca dengan baik.
        """
        # Pilih warna teks sekunder dan redup berdasarkan tema aktif
        ts = Colors.DARK_TEXT_SECONDARY if self.is_dark else Colors.LIGHT_TEXT_SECONDARY
        tm = Colors.DARK_TEXT_MUTED if self.is_dark else Colors.LIGHT_TEXT_MUTED

        # Terapkan warna ke label judul kartu
        self._threats_title_lbl.setStyleSheet(
            f"color: {ts}; font-size: 12px; font-weight: 500; background: transparent;"
        )
        # Terapkan warna ke label keterangan "Sesi ini"
        self._threats_meta_lbl.setStyleSheet(
            f"color: {tm}; font-size: 11px; background: transparent;"
        )

    # ------------------------------------------------------------------
    # AKSI / LOGIKA
    # ------------------------------------------------------------------

    def _toggle_theme(self):
        """
        Membalik tema antara gelap dan terang ketika pengguna menekan tombol tema.

        Langkah-langkah:
        1. Balik nilai tema (gelap → terang, atau sebaliknya)
        2. Perbarui tampilan kartu ancaman
        3. Perbarui teks tombol tema
        4. Kirim sinyal theme_toggled agar seluruh aplikasi mengikuti perubahan ini
        """
        # Balik nilai tema: True → False, atau False → True
        self.is_dark = not self.is_dark

        # Perbarui tampilan kartu ancaman jika sudah dibuat
        if hasattr(self, "threats_card"):
            self.threats_card.set_theme(self.is_dark)

        # Perbarui warna teks dalam kartu ancaman
        self._apply_threats_card_theme()

        # Perbarui teks tombol agar mencerminkan tema yang baru aktif
        self.theme_btn.setText(" Dark Mode" if self.is_dark else " Light Mode")

        # Kirim sinyal ke seluruh aplikasi untuk mengganti tema
        self.theme_toggled.emit(self.is_dark)

    # ------------------------------------------------------------------
    # API PUBLIK — Fungsi yang bisa dipanggil dari luar kelas ini
    # ------------------------------------------------------------------

    def set_active_tab(self, tab_id: str):
        """
        Mengaktifkan (menyorot) tab navigasi tertentu secara programatis.

        Digunakan ketika kode lain ingin mengubah halaman aktif tanpa klik pengguna,
        misalnya saat kartu di Dashboard diklik dan navigasi berpindah ke halaman lain.

        Args:
            tab_id: ID tab yang ingin diaktifkan, misalnya 'scan' atau 'protection'.
        """
        # Cari tombol yang memiliki ID tab yang cocok
        for btn in self.nav_group.buttons():
            if btn.property("tab_id") == tab_id:
                # Aktifkan tombol ini (yang lain akan otomatis non-aktif karena mode eksklusif)
                btn.setChecked(True)
                break  # Hentikan pencarian begitu ditemukan

    def update_threats_count(self, count: int):
        """
        Memperbarui angka yang ditampilkan di kartu penghitung ancaman.

        Dipanggil setiap kali ancaman baru berhasil diblokir oleh mesin deteksi.

        Args:
            count: Jumlah total ancaman yang sudah diblokir dalam sesi ini.
        """
        # Simpan nilai terbaru
        self.threats_count = count
        # Perbarui teks label angka besar
        self.threats_label.setText(str(count))

    def update_status(self, status: str, is_protected: bool = True):
        """
        Memperbarui teks dan warna indikator pada badge status sistem.

        Ketika proteksi aktif, badge ditampilkan dengan warna hijau.
        Ketika proteksi tidak aktif, badge ditampilkan dengan warna merah.

        Args:
            status: Teks status yang akan ditampilkan, misalnya 'Protected' atau 'Unprotected'.
            is_protected: True jika sistem sedang terlindungi, False jika tidak.
        """
        # Perbarui teks status
        self.status_text.setText(status)

        # Pilih warna berdasarkan kondisi proteksi
        color = Colors.GREEN_500 if is_protected else Colors.RED_500

        # Terapkan warna ke teks status utama
        self.status_text.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")

        # Terapkan warna yang sama ke titik indikator di sebelah kanan
        self.pulse_indicator.setStyleSheet(f"color: {color}; font-size: 12px;")
