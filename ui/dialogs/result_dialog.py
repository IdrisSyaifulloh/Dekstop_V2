"""
MangoDefend - Dialog Hasil Scan
Overlay layar penuh yang menampilkan hasil pemindaian satu file maupun banyak file (batch).
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGraphicsOpacityEffect,
    QSizePolicy
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal
from ui.styles.figma_theme import Colors, Typography, StyleHelper


class _BaseOverlay(QWidget):
    """
    Kelas dasar untuk semua dialog hasil scan.
    Menyediakan lapisan gelap yang menutupi seluruh layar dengan efek muncul (fade in)
    dan menghilang (fade out) yang halus.

    Kelas ini tidak dipakai langsung — kelas ResultDialog dan BatchResultDialog
    mewarisi (extends) kelas ini dan menambahkan konten tampilan masing-masing.
    """

    def __init__(self, parent=None):
        """
        Buat lapisan gelap transparan dan siapkan dua animasi: muncul dan menghilang.

        Yang disiapkan di sini:
        1. Widget overlay gelap yang menutupi seluruh jendela induk
        2. Efek transparansi (QGraphicsOpacityEffect) yang bisa dianimasikan
        3. Animasi fade in  — overlay muncul perlahan dalam 260 ms
        4. Animasi fade out — overlay menghilang perlahan dalam 180 ms,
           lalu widget dihapus dari memori setelah animasi selesai
        """
        # Panggil konstruktor kelas induk QWidget
        super().__init__(parent)

        # Nama unik untuk styling CSS — meskipun tidak dipakai stylesheet di sini,
        # nama ini memudahkan debugging
        self.setObjectName("baseOverlay")

        # Aktifkan dukungan warna latar dari stylesheet
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Warna latar overlay: hitam sangat pekat (opacity 82%) untuk memblur konten di belakang
        self.setStyleSheet("QWidget#baseOverlay{background:rgba(5,5,10,0.82);}")

        # ── EFEK TRANSPARANSI ────────────────────────────────────────────────────
        # QGraphicsOpacityEffect memungkinkan widget ini memiliki tingkat transparansi
        # yang bisa diubah secara program. Nilai 0.0 = tidak terlihat, 1.0 = penuh terlihat.
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)

        # Mulai dengan transparansi penuh (tidak terlihat) agar bisa dilakukan fade in
        self._opacity.setOpacity(0)

        # ── ANIMASI FADE IN (MUNCUL) ─────────────────────────────────────────────
        # Animasi ini mengubah nilai opacity dari 0.0 ke 1.0 selama 260 ms.
        # QPropertyAnimation bekerja dengan mengubah "properti" Python secara bertahap.
        # b"opacity" adalah nama properti yang diubah (ditulis dalam bytes untuk Qt).
        self._fade_in = QPropertyAnimation(self._opacity, b"opacity")
        self._fade_in.setDuration(260)                           # durasi 260 ms = cukup cepat tapi halus
        self._fade_in.setStartValue(0.0)                         # mulai dari tidak terlihat
        self._fade_in.setEndValue(1.0)                           # akhir penuh terlihat
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic) # percepatan di awal, melambat di akhir

        # ── ANIMASI FADE OUT (MENGHILANG) ───────────────────────────────────────
        # Animasi ini mengubah opacity dari 1.0 ke 0.0 selama 180 ms (lebih cepat dari fade in).
        # Setelah animasi selesai, sinyal finished memanggil _destroy() untuk membersihkan memori.
        self._fade_out = QPropertyAnimation(self._opacity, b"opacity")
        self._fade_out.setDuration(180)                           # durasi 180 ms — cepat saat menutup
        self._fade_out.setStartValue(1.0)                         # mulai dari penuh terlihat
        self._fade_out.setEndValue(0.0)                           # akhir tidak terlihat
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic) # lambat di awal, percepat di akhir
        # Setelah fade out selesai, langsung hapus widget dari memori untuk menghemat RAM
        self._fade_out.finished.connect(self._destroy)

    def show_dialog(self):
        """
        Tampilkan dialog dengan efek muncul (fade in).
        Urutan langkah:
        1. Sesuaikan ukuran overlay agar sama dengan ukuran jendela parent
        2. Tampilkan widget (tanpa animasi dulu — opacity masih 0 dari inisialisasi)
        3. Pindahkan ke paling depan agar tidak tertutup widget lain
        4. Mulai animasi fade in yang mengubah opacity dari 0 ke 1
        """
        # Langkah 1: perluas overlay agar pas dengan jendela parent
        if self.parent():
            self.setGeometry(self.parent().rect())

        # Langkah 2: tampilkan widget (masih transparan di awal karena opacity=0)
        self.show()

        # Langkah 3: bawa ke depan agar terlihat di atas semua widget lain
        self.raise_()

        # Langkah 4: mulai animasi muncul
        self._fade_in.start()

    def close_dialog(self):
        """
        Tutup dialog dengan efek menghilang (fade out).
        Animasi mengubah opacity dari 1 ke 0, lalu _destroy() dipanggil otomatis.
        """
        self._fade_out.start()  # mulai animasi menghilang

    def _destroy(self):
        """
        Dipanggil otomatis setelah animasi fade out selesai.
        Sembunyikan widget dan hapus dari memori agar tidak ada kebocoran memori (memory leak).
        deleteLater() adalah cara aman Qt untuk menghapus widget — penghapusan ditunda
        sampai event loop selesai memproses event yang sedang berjalan.
        """
        self.hide()          # sembunyikan dari layar
        self.deleteLater()   # tandai untuk dihapus dari memori di akhir siklus event

    @staticmethod
    def _card(min_w=540, max_w=600, radius=24) -> tuple["QFrame", "QVBoxLayout"]:
        """
        Buat kotak kartu dialog yang tampil di tengah layar dengan sudut melengkung.
        Kartu ini yang berisi semua informasi hasil scan.

        Parameter:
            min_w  — lebar minimum kartu dalam piksel (default 540)
            max_w  — lebar maksimum kartu dalam piksel (default 600)
            radius — radius sudut melengkung dalam piksel (default 24)

        Mengembalikan tuple (kartu, layout) agar pemanggil bisa langsung menambahkan widget.
        """
        card = QFrame()
        card.setObjectName("dialogCard")                         # nama untuk styling
        card.setMinimumWidth(min_w)                              # jangan lebih kecil dari min_w
        card.setMaximumWidth(max_w)                              # jangan lebih besar dari max_w
        card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        card.setStyleSheet(f"""
            QFrame#dialogCard {{
                background: #131317;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: {radius}px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)  # konten menempel ke tepi kartu (bagian dalam mengatur margin sendiri)
        lay.setSpacing(0)                    # tidak ada jarak ekstra antar bagian kartu
        return card, lay

    @staticmethod
    def _divider() -> QFrame:
        """
        Buat garis pemisah horizontal tipis antara bagian-bagian dialog.
        Garis ini nyaris transparan untuk tampilan yang elegan.
        """
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)  # garis horizontal
        line.setStyleSheet("background:rgba(255,255,255,0.07);max-height:1px;border:none;")
        return line

    @staticmethod
    def _micro_label(text: str) -> QLabel:
        """
        Buat label judul seksi kecil dengan huruf kapital dan jarak antar huruf.
        Digunakan sebagai penanda kelompok informasi (contoh: "INFORMASI FILE", "HASIL DETEKSI").
        """
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
        """
        Buat label teks nilai dengan ukuran, warna, dan ketebalan yang bisa dikonfigurasi.
        Digunakan untuk menampilkan nilai-nilai informasi dalam kartu.

        Parameter:
            text  — teks yang ditampilkan
            size  — ukuran font CSS (contoh: "14px", "18px")
            color — warna teks dalam format hex atau rgba
            bold  — True untuk cetak tebal, False untuk normal
        """
        lbl = QLabel(text)
        lbl.setWordWrap(True)  # izinkan teks panjang ke baris bawah
        lbl.setStyleSheet(f"""
            color: {color};
            font-size: {size};
            font-weight: {'700' if bold else '400'};
            background: transparent;
            font-family: {Typography.FONT_FAMILY};
        """)
        return lbl


class ResultDialog(_BaseOverlay):
    """
    Overlay layar penuh yang menampilkan hasil pemindaian SATU file.
    Menampilkan: status aman/berbahaya, tingkat keyakinan, informasi file, dan detail model ML.
    """

    def __init__(self, result_data: dict, parent=None):
        """
        Terima data hasil scan satu file lalu bangun tampilan dialog hasilnya.

        Parameter:
            result_data — kamus berisi semua data hasil scan (nama file, ukuran, hasil ML, dsb.)
            parent      — jendela induk tempat overlay ditampilkan
        """
        # Panggil konstruktor kelas dasar untuk menyiapkan overlay dan animasi
        super().__init__(parent)

        # Simpan data hasil scan untuk digunakan oleh metode-metode pembangunan tampilan
        self.result_data = result_data

        # Bangun seluruh tampilan dialog
        self._build_ui()

    def _parse(self):
        """
        Urai (parse) data hasil scan menjadi nilai-nilai yang siap ditampilkan.

        Mengembalikan tuple berisi:
        - is_safe     : True jika file aman, False jika malware
        - result_type : label hasil ("Benign" atau "Malware")
        - is_full     : True jika ini hasil scan penuh (dari format berbeda)

        Perbedaan is_full vs single (scan tunggal):
        - Scan TUNGGAL (is_full=False): data menggunakan kunci "result"
          Contoh: {"result": "Malware", "model": {"predicted_output": [-1.2, 3.5]}}
        - Scan PENUH/BATCH (is_full=True): data menggunakan kunci "is_malware"
          Contoh: {"is_malware": True, "confidence": 95}
        """
        rd = self.result_data

        # Tentukan apakah ini format scan penuh atau scan tunggal
        is_full = rd.get("is_full_scan", False) or ("result" not in rd)

        if is_full:
            is_safe     = not rd.get("is_malware", False)
            result_type = "Benign" if is_safe else "Malware"
        else:
            result_type = rd["result"]
            is_safe     = result_type == "Benign"

        return is_safe, result_type, is_full

    def _build_ui(self):
        """
        Bangun keseluruhan dialog hasil scan satu file:
        1. Tentukan warna dan ikon berdasarkan hasil (aman=hijau, malware=oranye)
        2. Buat kartu tengah
        3. Tambahkan header, body (informasi), garis pemisah, dan footer
        """
        # Urai data untuk mendapatkan nilai-nilai yang dibutuhkan
        is_safe, result_type, is_full = self._parse()
        rd = self.result_data

        # ── PILIHAN WARNA BERDASARKAN HASIL ─────────────────────────────────────
        accent        = Colors.GREEN_500 if is_safe else Colors.ORANGE_500
        accent_dim    = "rgba(50,205,50,0.15)"  if is_safe else "rgba(255,165,0,0.12)"   # latar transparan
        accent_border = "rgba(50,205,50,0.35)"  if is_safe else "rgba(255,165,0,0.35)"   # border transparan
        status_icon   = "✓" if is_safe else "✕"                  # tanda centang hijau atau silang oranye
        status_text   = "File Aman" if is_safe else "Ancaman Terdeteksi"
        header_grad   = (
            "stop:0 rgba(50,205,50,0.25), stop:1 rgba(16,185,129,0.12)"    # gradient hijau
            if is_safe else
            "stop:0 rgba(255,140,0,0.25), stop:1 rgba(255,107,53,0.12)"    # gradient oranye
        )

        # ── LAYOUT UTAMA OVERLAY ─────────────────────────────────────────────────
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)   # pusatkan kartu di tengah layar

        # Buat kartu dialog (kotak gelap di tengah)
        card, card_lay = self._card(min_w=520, max_w=580)

        # Tambahkan bagian-bagian dialog ke dalam kartu
        card_lay.addWidget(self._build_header(
            accent, accent_border, header_grad,
            status_icon, status_text
        ))
        card_lay.addWidget(self._build_body(rd, is_safe, is_full, accent_dim, result_type))
        card_lay.addWidget(self._divider())       # garis pemisah tipis antara body dan footer
        card_lay.addWidget(self._build_footer(rd))

        # Tambahkan kartu ke layout overlay
        root_layout.addWidget(card)

    def _build_header(self, accent, accent_border, header_grad,
                      status_icon, status_text) -> QFrame:
        """
        Bangun bagian atas dialog berisi:
        - Ikon bulat (centang atau silang) di sebelah kiri
        - Judul status ("File Aman" atau "Ancaman Terdeteksi")
        - Keterangan keyakinan model dalam persen
        - Bar kemajuan tipis yang menunjukkan persentase keyakinan
        """
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

        # ── BARIS ATAS: IKON + JUDUL ─────────────────────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        # Ikon bulat berwarna aksen berisi tanda centang atau silang
        icon_lbl = QLabel(status_icon)
        icon_lbl.setFixedSize(52, 52)                               # ukuran lingkaran tetap
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            font-size: 26px; font-weight: 900; color: white;
            background: {accent}; border-radius: 26px;
        """)
        top_row.addWidget(icon_lbl)

        # Kolom berisi dua baris teks: judul besar dan keterangan kecil
        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        # Judul status yang besar
        title_lbl = QLabel(status_text)
        title_lbl.setStyleSheet(f"""
            color: white; font-size: 22px; font-weight: 700;
            background: transparent; font-family: {Typography.FONT_FAMILY};
        """)

        title_col.addWidget(title_lbl)
        top_row.addLayout(title_col)
        top_row.addStretch()   # dorong ikon dan judul ke kiri
        lay.addLayout(top_row)

        return header

    def _build_body(self, rd, is_safe, is_full, accent_dim, result_type) -> QWidget:
        """
        Bangun bagian tengah dialog berisi dua blok informasi:
        1. INFORMASI FILE — nama, lokasi, ukuran, durasi scan
        2. HASIL DETEKSI  — label BENIGN/MALWARE, nama model, nama perangkat
        """
        body = QWidget()
        lay  = QVBoxLayout(body)
        lay.setContentsMargins(36, 24, 36, 24)
        lay.setSpacing(16)

        # ── BLOK INFORMASI FILE ──────────────────────────────────────────────────
        # Ambil data file berdasarkan format (full scan vs scan tunggal)
        file_name = rd.get("file_name", "Unknown") if is_full else rd["file"]["file_name"]
        file_path = "" if is_full else rd["file"].get("file_path", "")
        file_size = None if is_full else rd["file"].get("file_size")  # ukuran dalam byte
        duration  = rd.get("scan_duration_seconds")

        # Format durasi: tampilkan hingga 3 angka desimal (milidetik tetap terlihat)
        dur_str   = f"{duration:.3f} detik" if duration is not None else "—"

        lay.addWidget(self._info_block(
            "INFORMASI FILE",
            [
                ("Nama",    file_name),
                ("Lokasi",  file_path or "—"),
                # Ubah ukuran dari byte ke KB dengan 1 angka desimal
                ("Ukuran",  f"{file_size / 1024:.1f} KB" if file_size else "—"),
                ("Durasi",  dur_str),
            ]
        ))

        # ── BLOK HASIL DETEKSI ───────────────────────────────────────────────────
        detect_color = Colors.GREEN_500 if is_safe else Colors.ORANGE_500  # hijau=aman, oranye=malware
        model_name   = "—" if is_full else rd.get("model", {}).get("model", "Modelv3.onnx")
        device_name  = "—" if is_full else rd.get("device", {}).get("device", "CPU")

        lay.addWidget(self._result_block(
            result_type, detect_color, accent_dim, model_name, device_name
        ))

        return body

    def _build_footer(self, rd) -> QWidget:
        """
        Bangun bagian bawah dialog berisi:
        - Kiri: timestamp (waktu scan dilakukan)
        - Kanan: tombol "Selesai" yang menutup dialog dengan animasi fade out
        """
        footer = QWidget()
        lay    = QHBoxLayout(footer)
        lay.setContentsMargins(36, 16, 36, 20)

        # Tampilkan waktu scan jika tersedia (format dari server/model)
        ts = rd.get("timestamp", "")
        if ts:
            ts_lbl = QLabel(f" {ts}")
            ts_lbl.setStyleSheet(f"""
                color:{Colors.DARK_TEXT_MUTED};font-size:11px;
                background:transparent;font-family:{Typography.FONT_FAMILY};
            """)
            lay.addWidget(ts_lbl)

        # Ruang kosong untuk mendorong tombol ke kanan
        lay.addStretch()

        # Tombol Selesai — menutup dialog dengan animasi menghilang
        close_btn = QPushButton("Selesai")
        close_btn.setFixedSize(110, 40)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close_dialog)  # panggil fade out saat diklik
        close_btn.setStyleSheet(StyleHelper.pill_button_primary(40))
        lay.addWidget(close_btn)
        return footer

    def _info_block(self, title: str, rows: list) -> QFrame:
        """
        Buat kotak berwarna transparan yang menampilkan beberapa pasang kunci-nilai
        dengan judul seksi di bagian atas.

        Parameter:
            title — judul seksi (contoh: "INFORMASI FILE")
            rows  — daftar tuple (kunci, nilai) yang akan ditampilkan
        """
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame{background:rgba(255,255,255,0.04);border:none;border-radius:14px;}
        """)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)

        # Label judul seksi di atas
        lay.addWidget(self._micro_label(title))

        # Buat satu baris untuk setiap pasang kunci-nilai
        for label, val in rows:
            row = QHBoxLayout()
            row.setSpacing(8)

            # Teks kunci (lebih redup dan lebar tetap 60px agar semua kunci sejajar)
            k = QLabel(label)
            k.setFixedWidth(60)  # lebar tetap agar nilai-nilai di kanan selalu rata
            k.setStyleSheet(f"""
                color:{Colors.DARK_TEXT_MUTED};font-size:12px;
                background:transparent;font-family:{Typography.FONT_FAMILY};
            """)

            # Teks nilai (lebih terang, bisa memanjang ke baris bawah)
            v = QLabel(val)
            v.setWordWrap(True)
            v.setStyleSheet(f"""
                color:{Colors.DARK_TEXT_PRIMARY};font-size:12px;
                background:transparent;font-family:{Typography.FONT_FAMILY};
            """)

            row.addWidget(k)
            row.addWidget(v, 1)  # nilai mendapat ruang sisa (stretch factor=1)
            lay.addLayout(row)

        return frame

    def _result_block(self, result_type, color, bg, model_name, device_name) -> QFrame:
        """
        Buat kotak yang menampilkan label hasil deteksi dalam huruf besar
        beserta detail model ML yang digunakan dan perangkat komputasi.

        Parameter:
            result_type — "BENIGN" atau "MALWARE" (ditampilkan sangat besar)
            color       — warna aksen (hijau atau oranye)
            bg          — warna latar transparan kotak
            model_name  — nama file model ONNX yang digunakan
            device_name — nama perangkat komputasi (contoh: "CPU", "GPU")
        """
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame{{background:{bg};border:none;border-radius:14px;}}
        """)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(6)

        # Judul seksi kecil
        lay.addWidget(self._micro_label("HASIL DETEKSI"))

        # Teks hasil yang sangat besar — ini yang paling pertama dilihat pengguna
        res_lbl = QLabel(result_type.upper())  # pastikan huruf besar
        res_lbl.setStyleSheet(f"""
            color:{color};font-size:28px;font-weight:900;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        lay.addWidget(res_lbl)

        # Baris informasi model dan perangkat yang digunakan
        meta = QHBoxLayout()
        meta.setSpacing(16)
        for txt in [f"Model: {model_name}", f"Device: {device_name}"]:
            lbl = QLabel(txt)
            lbl.setStyleSheet(f"""
                color:{Colors.DARK_TEXT_MUTED};font-size:11px;
                background:transparent;font-family:{Typography.FONT_FAMILY};
            """)
            meta.addWidget(lbl)
        meta.addStretch()  # dorong info ke kiri
        lay.addLayout(meta)
        return frame

    def _warning_strip(self) -> QFrame:
        """
        Buat strip peringatan oranye yang muncul khusus saat file terdeteksi sebagai malware.
        Berisi ikon segitiga peringatan dan teks anjuran untuk segera mengkarantina file.
        """
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame{background:rgba(255,107,53,0.1);
                   border-left:3px solid #FF6B35;
                   border-radius:10px;}
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)

        # Ikon peringatan oranye
        icon = QLabel("⚠")
        icon.setStyleSheet("font-size:20px;color:#FF6B35;background:transparent;")

        # Teks anjuran tindakan
        txt = QLabel("Segera hapus atau karantina file ini untuk melindungi perangkat Anda.")
        txt.setWordWrap(True)
        txt.setStyleSheet(f"""
            color:#FFAA80;font-size:12px;font-weight:600;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)
        lay.addWidget(icon)
        lay.addWidget(txt, 1)
        return frame


class BatchResultDialog(_BaseOverlay):
    """
    Overlay layar penuh yang menampilkan ringkasan hasil scan BANYAK file sekaligus
    (scan folder atau scan seluruh perangkat).

    Menampilkan statistik: total file dipindai, aman, malware, dan gagal.
    Jika ada malware, muncul tombol "Karantina N File" yang mengirim sinyal
    ke parent agar bisa memproses karantina file-file tersebut.
    """

    # Sinyal yang dikirim saat tombol Karantina ditekan.
    # Membawa daftar file malware yang perlu dikarantina.
    quarantine_requested = Signal(list)

    def __init__(self, summary: dict, parent=None, scan_duration: float = None):
        """
        Terima ringkasan hasil scan banyak file lalu bangun tampilan rekapitulasinya.

        Parameter:
            summary       — kamus berisi statistik scan (jumlah file, malware, aman, dsb.)
            parent        — jendela induk tempat overlay ditampilkan
            scan_duration — total durasi scan dalam detik (opsional, untuk ditampilkan di footer)
        """
        # Siapkan overlay dasar dan animasi
        super().__init__(parent)

        # Simpan ringkasan scan untuk digunakan saat membangun tampilan
        self._summary = summary

        # Simpan durasi scan untuk ditampilkan di footer (bisa None jika tidak tersedia)
        self._scan_duration = scan_duration

        # Bangun seluruh tampilan dialog
        self._build_ui()

    def _build_ui(self):
        """
        Bangun keseluruhan dialog batch scan:
        1. Ekstrak angka statistik dari ringkasan
        2. Tentukan warna (hijau=aman, oranye=ada malware)
        3. Buat kartu dengan header, statistik, catatan, garis pemisah, dan footer
        """
        s = self._summary

        # Ekstrak angka-angka statistik dari ringkasan
        total   = s.get("scanned", 0)    # total file yang dipindai
        malware = s.get("malware", 0)    # jumlah file malware yang ditemukan
        clean   = s.get("clean", 0)      # jumlah file yang aman
        errors  = s.get("errors", 0)     # jumlah file yang gagal dipindai (error)
        results = s.get("results", [])   # daftar detail setiap file hasil scan
        beyond  = s.get("continued_beyond_limit", False)  # apakah scan melewati batas default

        # Tentukan apakah semua file aman (tidak ada malware sama sekali)
        is_safe = malware == 0

        # ── PILIHAN WARNA BERDASARKAN HASIL ─────────────────────────────────────
        accent        = Colors.GREEN_500 if is_safe else Colors.ORANGE_500
        accent_border = "rgba(50,205,50,0.30)" if is_safe else "rgba(255,165,0,0.30)"
        header_grad   = (
            "stop:0 rgba(50,205,50,0.22), stop:1 rgba(16,185,129,0.10)"
            if is_safe else
            "stop:0 rgba(255,140,0,0.22), stop:1 rgba(255,107,53,0.10)"
        )
        status_icon = "✓" if is_safe else "✕"
        # Teks judul: "Perangkat Aman" atau "N Ancaman Ditemukan"
        status_text = "Perangkat Aman" if is_safe else f"{malware} Ancaman Ditemukan"

        # ── LAYOUT UTAMA OVERLAY ─────────────────────────────────────────────────
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Buat kartu dialog sedikit lebih kecil dari dialog satu file
        card, card_lay = self._card(min_w=500, max_w=560)

        # Tambahkan bagian-bagian dialog ke dalam kartu
        card_lay.addWidget(self._build_header(
            accent, accent_border, header_grad, status_icon, status_text
        ))
        card_lay.addWidget(self._build_stats(total, clean, malware, errors))  # pil statistik
        card_lay.addWidget(self._build_notes(malware, errors, beyond))         # catatan kontekstual
        card_lay.addWidget(self._divider())                                    # garis pemisah
        card_lay.addWidget(self._build_footer(malware, results))               # tombol aksi

        root_layout.addWidget(card)

    def _build_header(self, accent, accent_border, header_grad,
                      status_icon, status_text) -> QFrame:
        """
        Bangun bagian atas dialog berisi:
        - Label kecil "Hasil Pemindaian"
        - Ikon status bulat (centang hijau atau silang oranye)
        - Judul besar yang menampilkan status keseluruhan ("Perangkat Aman" atau "N Ancaman")
        """
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

        # Baris horizontal: ikon + kolom teks
        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        # Ikon bulat berisi centang atau silang
        icon_lbl = QLabel(status_icon)
        icon_lbl.setFixedSize(52, 52)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            font-size: 26px; font-weight: 900; color: white;
            background: {accent}; border-radius: 26px;
        """)
        top_row.addWidget(icon_lbl)

        # Kolom dua baris: label kecil di atas, judul besar di bawah
        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        # Label kecil "HASIL PEMINDAIAN" dengan jarak antar huruf
        t1 = QLabel("Hasil Pemindaian")
        t1.setStyleSheet(f"""
            color:rgba(255,255,255,0.55);font-size:11px;font-weight:700;
            letter-spacing:1px;background:transparent;
            font-family:{Typography.FONT_FAMILY};
        """)

        # Judul besar yang langsung terlihat oleh pengguna
        t2 = QLabel(status_text)
        t2.setStyleSheet(f"""
            color:white;font-size:20px;font-weight:700;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)

        title_col.addWidget(t1)
        title_col.addWidget(t2)
        top_row.addLayout(title_col)
        top_row.addStretch()  # dorong ikon dan teks ke kiri
        lay.addLayout(top_row)
        return header

    def _build_stats(self, total, clean, malware, errors) -> QWidget:
        """
        Bangun baris pil statistik yang menampilkan angka-angka penting secara visual.
        Setiap statistik ditampilkan sebagai "pil" kotak kecil dengan angka besar di atas
        dan label di bawahnya.

        Urutan pil: TOTAL | AMAN | MALWARE | GAGAL (hanya jika ada error)
        """
        row = QHBoxLayout()
        row.setContentsMargins(36, 20, 36, 0)
        row.setSpacing(10)

        # Pil TOTAL: angka abu-abu netral menunjukkan semua file yang dipindai
        row.addWidget(self._stat_pill(total,   "TOTAL",   Colors.DARK_TEXT_SECONDARY, "rgba(255,255,255,0.05)"))

        # Pil AMAN: angka hijau menunjukkan file yang bersih
        row.addWidget(self._stat_pill(clean,   "AMAN",    Colors.GREEN_500,            "rgba(50,205,50,0.10)"))

        # Pil MALWARE: angka oranye menunjukkan file berbahaya yang ditemukan
        row.addWidget(self._stat_pill(malware, "MALWARE", Colors.ORANGE_500,           "rgba(255,165,0,0.10)"))

        # Pil GAGAL: hanya tampil jika ada file yang gagal dipindai karena error
        if errors:
            row.addWidget(self._stat_pill(errors, "GAGAL", Colors.RED_500, "rgba(255,107,53,0.10)"))

        # Bungkus layout dalam widget agar bisa ditambahkan ke layout lain
        container = QWidget()
        container.setStyleSheet("background:transparent;")
        container.setLayout(row)
        return container

    def _stat_pill(self, val, label, color, bg) -> QFrame:
        """
        Buat satu pil statistik — kotak kecil dengan:
        - Angka besar di atas (warna aksen sesuai jenis statistik)
        - Label kecil di bawah (contoh: "TOTAL", "AMAN", "MALWARE")

        Parameter:
            val   — angka yang ditampilkan (contoh: 42)
            label — nama statistik (contoh: "TOTAL")
            color — warna teks angka
            bg    — warna latar kotak (transparan berwarna aksen)
        """
        pill = QFrame()
        pill.setStyleSheet(f"QFrame{{background:{bg};border:none;border-radius:14px;}}")
        lay = QVBoxLayout(pill)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Angka besar yang langsung terlihat
        v = QLabel(str(val))
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setStyleSheet(f"""
            color:{color};font-size:26px;font-weight:900;
            background:transparent;font-family:{Typography.FONT_FAMILY};
        """)

        # Label kecil di bawah angka — deskripsi angka tersebut
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
        """
        Bangun baris catatan kontekstual di bawah statistik.
        Catatan yang ditampilkan bergantung pada kondisi hasil scan:
        - Jika scan melewati batas file: tampilkan keterangan
        - Jika ada malware: tampilkan peringatan dan anjuran karantina
        - Jika semua aman dan tidak ada error: tampilkan pesan positif
        """
        notes = QWidget()
        notes.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(notes)
        lay.setContentsMargins(36, 14, 36, 10)
        lay.setSpacing(6)

        # Catatan jika scan dilanjutkan melewati batas file default
        if beyond:
            self._add_note(lay, "", "Scan dilanjutkan melewati batas default.", "rgba(255,255,255,0.35)")

        # Peringatan oranye jika ada file malware yang ditemukan
        if malware > 0:
            self._add_note(lay, "⚠",
                f"{malware} file berbahaya ditemukan. Segera karantina untuk melindungi perangkat.",
                Colors.ORANGE_400)

        # Pesan sukses hijau jika tidak ada malware dan tidak ada error
        if not malware and not errors:
            self._add_note(lay, "✓", "Tidak ada ancaman yang terdeteksi pada perangkat Anda.", Colors.GREEN_500)

        return notes

    def _add_note(self, layout, icon: str, text: str, color: str):
        """
        Tambahkan satu baris catatan ke dalam layout yang diberikan.
        Setiap catatan terdiri dari ikon kecil (opsional) di sebelah kiri dan teks di sebelah kanan.

        Parameter:
            layout — layout QVBoxLayout tempat catatan akan ditambahkan
            icon   — karakter Unicode untuk ikon (contoh: "⚠", "✓"), bisa kosong ""
            text   — teks isi catatan
            color  — warna teks dan ikon
        """
        row = QHBoxLayout()
        row.setSpacing(8)

        # Tambahkan ikon jika ada
        if icon:
            ic = QLabel(icon)
            ic.setFixedWidth(20)  # lebar tetap agar teks selalu sejajar
            ic.setStyleSheet(f"font-size:14px;color:{color};background:transparent;")
            row.addWidget(ic)

        # Teks catatan — bisa memanjang ke baris bawah
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"""
            color:{color};font-size:12px;background:transparent;
            font-family:{Typography.FONT_FAMILY};
        """)
        row.addWidget(lbl, 1)  # teks mendapat ruang sisa
        layout.addLayout(row)

    def _build_footer(self, malware: int, results: list) -> QWidget:
        """
        Bangun bagian bawah dialog berisi:
        - Kiri: durasi total scan (jika tersedia)
        - Kanan: tombol "Tutup" dan (jika ada malware) tombol "Karantina N File"

        Tombol Karantina hanya muncul jika ada file malware yang perlu ditangani.
        Saat ditekan, tombol ini mengirim sinyal quarantine_requested ke parent
        agar parent bisa memproses karantina file-file tersebut.
        """
        footer = QWidget()
        lay    = QHBoxLayout(footer)
        lay.setContentsMargins(36, 14, 36, 20)
        lay.setSpacing(10)

        # Tampilkan durasi scan jika data tersedia
        if self._scan_duration is not None:
            dur_lbl = QLabel(f"⏱ Selesai dalam {self._scan_duration:.1f} detik")
            dur_lbl.setStyleSheet(f"""
                color:{Colors.DARK_TEXT_MUTED};font-size:11px;
                background:transparent;font-family:{Typography.FONT_FAMILY};
            """)
            lay.addWidget(dur_lbl)

        # Ruang kosong untuk mendorong tombol ke kanan
        lay.addStretch()

        # Tombol Tutup — hanya menutup dialog tanpa tindakan lain
        close_btn = QPushButton("Tutup")
        close_btn.setFixedSize(100, 40)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close_dialog)  # fade out dan hapus widget
        close_btn.setStyleSheet(StyleHelper.pill_button_outline(40))
        lay.addWidget(close_btn)

        # Tombol Karantina — hanya muncul jika ada malware yang perlu ditangani
        if malware > 0:
            q_btn = QPushButton(f"Karantina {malware} File")
            q_btn.setFixedHeight(40)
            q_btn.setMinimumWidth(150)
            q_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # Saat diklik: panggil _on_quarantine dengan daftar file malware
            q_btn.clicked.connect(lambda: self._on_quarantine(results))
            q_btn.setStyleSheet(StyleHelper.pill_button_primary(40))
            lay.addWidget(q_btn)

        return footer

    def _on_quarantine(self, results: list):
        """
        Dipanggil saat pengguna menekan tombol "Karantina N File".
        Kirim sinyal quarantine_requested ke parent berisi daftar file malware,
        lalu tutup dialog dengan animasi menghilang.

        Parent yang menerima sinyal ini bertanggung jawab memindahkan
        file-file berbahaya ke folder karantina dan menghapusnya dari lokasi asli.
        """
        # Kirim sinyal ke parent dengan daftar semua hasil scan (termasuk file malware)
        self.quarantine_requested.emit(results)

        # Tutup dialog setelah sinyal dikirim
        self.close_dialog()
