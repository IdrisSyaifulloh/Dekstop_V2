"""
Tampilan Karantina — Kelola file berbahaya yang telah dikarantina.

File ini mengelola halaman Quarantine pada MangoDefend yang berfungsi untuk:
- Menampilkan daftar file berbahaya yang sudah diisolasi (dikarantina)
- Memungkinkan pengguna memulihkan file ke Desktop (jika yakin aman)
- Memungkinkan pengguna menghapus file secara permanen dari karantina

Folder karantina disimpan di:
    C:/Users/<nama_pengguna>/.Mangodefend/Karintina/

File di karantina memiliki ekstensi .quarantined dengan format nama:
    <timestamp>_<nama_asli>.quarantined
Contoh: 1750000000.0_contoh.exe.quarantined
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QMessageBox,
)
from PySide6.QtCore import Qt

# Widget kartu kustom dan sistem warna/gaya
from ui.widgets import SoftCard
from ui.styles.figma_theme import Colors, Typography, StyleHelper


class QuarantineView(QWidget):
    """
    Halaman manajemen karantina — tempat file-file berbahaya yang telah diisolasi.

    Ketika MangoDefend mendeteksi file berbahaya, file tersebut dipindahkan ke
    folder karantina dan tidak bisa lagi dieksekusi oleh sistem. Di halaman ini,
    pengguna bisa melihat daftar file tersebut dan memutuskan:
    1. Restore — kembalikan file ke Desktop (gunakan dengan hati-hati!)
    2. Delete — hapus file secara permanen dari karantina
    """

    def __init__(self, parent=None):
        """
        Menyiapkan folder karantina dan membangun tampilan halaman.

        Jika folder karantina belum ada, folder tersebut dibuat secara otomatis.

        Args:
            parent: Widget induk (biasanya area konten utama jendela).
        """
        super().__init__(parent)

        # Tema awal: gelap
        self.is_dark = True

        # Jalur folder karantina di folder home pengguna
        # Contoh: C:/Users/Budi/.Mangodefend/Karintina/
        self.quarantine_dir = Path.home() / ".Mangodefend" / "Karintina"

        # Daftar kartu soft card untuk diperbarui saat tema berubah
        self._soft_cards: list[SoftCard] = []

        # Buat folder karantina jika belum ada (parents=True: buat folder induk juga jika perlu)
        if not self.quarantine_dir.exists():
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        # Bangun tampilan halaman
        self.setup_ui()

        # Muat dan tampilkan file-file karantina yang sudah ada
        self.load_quarantine_items()

    # ------------------------------------------------------------------
    # MEMBANGUN TAMPILAN
    # ------------------------------------------------------------------

    def setup_ui(self):
        """
        Membangun header, tombol-tombol aksi, dan tabel daftar file karantina.

        Tata letak halaman:
        1. Header: judul halaman + tombol Refresh, Restore All, Empty Quarantine
        2. Kartu berisi tabel dengan kolom: Tanggal | Nama File | Status | Aksi
        """
        # Tata letak vertikal utama halaman
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 32)
        layout.setSpacing(24)

        # --- 1. Header halaman ---
        header_layout = QHBoxLayout()

        # Kolom judul (vertikal): judul besar + subtitle kecil
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)

        # Judul besar "Quarantine Manager"
        self.title_label = QLabel("Quarantine Manager")
        self.title_label.setStyleSheet(
            f"color: {self._tp()}; font-size: 28px; font-weight: bold;"
            f" font-family: {Typography.FONT_FAMILY};"
        )

        # Subtitle penjelasan singkat fungsi halaman
        self.subtitle_label = QLabel("Manage isolated threats to protect your system.")
        self.subtitle_label.setStyleSheet(StyleHelper.muted_body())

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)
        header_layout.addLayout(title_layout)

        # Dorong tombol-tombol ke sisi kanan header
        header_layout.addStretch()

        # Tombol refresh (↻): membaca ulang folder karantina dan memperbarui tabel
        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setFixedSize(52, 40)
        self.refresh_btn.setStyleSheet(StyleHelper.pill_button_outline(36))
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setToolTip("Refresh daftar karantina")
        # Ketika diklik: muat ulang daftar file dari folder karantina
        self.refresh_btn.clicked.connect(self.load_quarantine_items)
        header_layout.addWidget(self.refresh_btn)

        # Tombol "Restore All": memulihkan SEMUA file ke Desktop
        self.restore_all_btn = QPushButton("Restore All")
        self.restore_all_btn.setFixedHeight(40)
        self.restore_all_btn.setMinimumWidth(142)
        self.restore_all_btn.setStyleSheet(StyleHelper.pill_button_outline(36))
        self.restore_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.restore_all_btn.setToolTip("Pulihkan semua file dari karantina")
        # Ketika diklik: panggil fungsi restore_all_files() dengan konfirmasi
        self.restore_all_btn.clicked.connect(self.restore_all_files)
        header_layout.addWidget(self.restore_all_btn)

        # Tombol "Empty Quarantine": menghapus SEMUA file secara permanen (tombol merah/berbahaya)
        self.clear_all_btn = QPushButton("Empty Quarantine")
        self.clear_all_btn.setFixedHeight(40)
        self.clear_all_btn.setMinimumWidth(168)
        self.clear_all_btn.setStyleSheet(StyleHelper.pill_button_danger(36))  # Gaya merah = aksi berbahaya
        self.clear_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Ketika diklik: hapus semua file dengan konfirmasi terlebih dahulu
        self.clear_all_btn.clicked.connect(self.empty_quarantine)
        header_layout.addWidget(self.clear_all_btn)

        layout.addLayout(header_layout)

        # --- 2. Kartu yang berisi tabel daftar file karantina ---
        self.card = SoftCard(is_dark=self.is_dark, accent=Colors.ORANGE_400)
        self._soft_cards.append(self.card)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        # Tabel dengan 4 kolom: Tanggal, Nama File Asli, Status, Aksi
        self.table = QTableWidget(0, 4)  # 0 baris awal, 4 kolom

        # Header kolom
        self.table.setHorizontalHeaderLabels(["Date", "Original File", "Status", "Actions"])

        # Kolom nama file (kolom 1) melebar mengisi sisa ruang yang tersedia
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # Kolom tanggal (kolom 0) menyesuaikan lebar konten
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        # Kolom status dan aksi memiliki lebar tetap
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 150)   # Lebar kolom Status: 150 piksel
        self.table.setColumnWidth(3, 250)   # Lebar kolom Aksi: 250 piksel agar tombol tidak terpotong

        # Tinggi setiap baris: 64 piksel agar tombol aksi tidak terpotong
        self.table.verticalHeader().setDefaultSectionSize(64)

        # Mode seleksi: pilih satu baris penuh (bukan sel individual)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Nonaktifkan pengeditan sel — tabel hanya untuk menampilkan data
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Sembunyikan garis grid tabel agar terlihat lebih bersih
        self.table.setShowGrid(False)

        # Sembunyikan nomor baris di sisi kiri tabel
        self.table.verticalHeader().setVisible(False)

        # Nonaktifkan fokus keyboard agar tabel tidak terlihat "aktif"
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Terapkan gaya warna tabel
        self.table.setStyleSheet(self._table_style())

        card_layout.addWidget(self.table)
        layout.addWidget(self.card)

    # ------------------------------------------------------------------
    # PEMBANTU WARNA TEMA
    # ------------------------------------------------------------------

    def _tp(self) -> str:
        """Mengembalikan warna teks utama sesuai tema saat ini (gelap atau terang)."""
        return Colors.DARK_TEXT_PRIMARY if self.is_dark else Colors.LIGHT_TEXT_PRIMARY

    def _card_bg(self) -> str:
        """Mengembalikan warna latar belakang kartu sesuai tema saat ini."""
        return "rgba(255, 255, 255, 0.05)" if self.is_dark else "rgba(255, 255, 255, 0.6)"

    def _card_border(self) -> str:
        """Mengembalikan warna garis tepi kartu sesuai tema saat ini."""
        return "rgba(255, 165, 0, 0.3)" if self.is_dark else Colors.LIGHT_BORDER

    def _table_style(self) -> str:
        """
        Membuat dan mengembalikan stylesheet lengkap untuk tampilan tabel karantina.

        Mengatur warna latar, teks, header, baris, dan kondisi terpilih
        agar konsisten dengan tema aktif.

        Returns:
            String stylesheet CSS untuk QTableWidget.
        """
        bg = "transparent"  # Latar tabel transparan agar latar kartu terlihat
        text = self._tp()   # Warna teks sel tabel

        # Warna latar header kolom: oranye transparan
        header_bg = "rgba(255, 165, 0, 0.1)" if self.is_dark else "rgba(255, 165, 0, 0.05)"

        return f"""
            QTableWidget {{
                background-color: {bg};
                color: {text};
                border: none;
                font-family: {Typography.FONT_FAMILY};
                font-size: 13px;
            }}
            QHeaderView::section {{
                background-color: {header_bg};    /* Latar belakang header oranye transparan */
                color: {Colors.ORANGE_500};        /* Teks header berwarna oranye */
                padding: 10px;
                border: none;
                font-weight: bold;
                font-family: {Typography.FONT_FAMILY};
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 12px 10px;                /* Padding dalam setiap sel */
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);  /* Garis pemisah tipis */
            }}
            QTableWidget::item:selected {{
                background-color: rgba(255, 165, 0, 0.1);  /* Latar oranye tipis saat baris dipilih */
            }}
        """

    def _action_button_style(self, danger: bool = False) -> str:
        """
        Mengembalikan stylesheet untuk tombol aksi kompak di dalam sel tabel.

        Tombol normal: warna oranye (aksi aman seperti Restore)
        Tombol bahaya: warna merah (aksi permanen seperti Delete)

        Args:
            danger: True untuk tombol merah (aksi berbahaya), False untuk oranye (default).

        Returns:
            String stylesheet CSS untuk QPushButton.
        """
        # Tentukan warna berdasarkan tingkat bahaya aksi
        bg = Colors.RED_500 if danger else Colors.ORANGE_500           # Warna latar tombol
        bg_hover = Colors.RED_600 if danger else Colors.ORANGE_400     # Warna saat hover
        border = Colors.RED_600 if danger else Colors.ORANGE_500       # Warna garis tepi

        return f"""
            QPushButton {{
                background: {bg};
                color: white;
                border: 1px solid {border};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 700;
                font-family: {Typography.FONT_FAMILY};
            }}
            QPushButton:hover {{
                background: {bg_hover};    /* Sedikit lebih gelap saat mouse hover */
                border-color: {bg_hover};
            }}
            QPushButton:pressed {{
                background: {border};     /* Lebih gelap lagi saat ditekan */
            }}
        """

    # ------------------------------------------------------------------
    # MEMUAT DATA DARI FOLDER KARANTINA
    # ------------------------------------------------------------------

    def load_quarantine_items(self):
        """
        Membaca folder karantina dan mengisi tabel dengan daftar file yang ada.

        Proses:
        1. Kosongkan tabel terlebih dahulu
        2. Cari semua file dengan ekstensi .quarantined di folder karantina
        3. Parse nama file untuk mendapatkan tanggal karantina dan nama asli
        4. Urutkan berdasarkan tanggal (terbaru di atas)
        5. Isi tabel: tanggal, nama file, badge status, dan tombol aksi

        Format nama file karantina: <timestamp>_<nama_asli>.quarantined
        Contoh: 1750000000.0_dokumen.pdf.quarantined
        """
        # Kosongkan semua baris tabel sebelum mengisi ulang
        self.table.setRowCount(0)

        # Hentikan jika folder karantina belum ada
        if not self.quarantine_dir.exists():
            return

        # Kumpulkan informasi semua file karantina
        files = []
        for file_path in self.quarantine_dir.glob("*.quarantined"):
            # Pisahkan timestamp dan nama asli berdasarkan pemisah underscore pertama
            # Format: "<timestamp>_<nama_asli>.quarantined"
            parts = file_path.name.split("_", 1)

            if len(parts) == 2:
                timestamp_str = parts[0]   # Bagian timestamp (misalnya "1750000000.0")
                original_name = parts[1].replace(".quarantined", "")  # Nama file asli

                try:
                    # Konversi timestamp (detik Unix) menjadi tanggal dan waktu yang terbaca manusia
                    ts = float(timestamp_str)
                    date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    # Jika timestamp tidak valid, tampilkan "Unknown" sebagai fallback
                    date_str = "Unknown"
                    original_name = file_path.name  # Gunakan nama file lengkap sebagai pengganti

                # Tambahkan informasi file ke daftar
                files.append({
                    "path": str(file_path),  # Jalur lengkap file karantina
                    "date": date_str,         # Tanggal dikarantina
                    "name": original_name,    # Nama file asli
                })

        # Urutkan: file yang paling baru dikarantina muncul di bagian atas tabel
        files.sort(key=lambda x: x["date"], reverse=True)

        # Isi tabel dengan data yang sudah dikumpulkan
        self.table.setRowCount(len(files))  # Atur jumlah baris sesuai jumlah file

        for row, item in enumerate(files):
            # Atur tinggi baris agar tombol Restore/Delete terlihat penuh
            self.table.setRowHeight(row, 64)

            # Kolom 0: Tanggal dikarantina
            self.table.setItem(row, 0, QTableWidgetItem(item["date"]))

            # Kolom 1: Nama file asli
            self.table.setItem(row, 1, QTableWidgetItem(item["name"]))

            # Kolom 2: Badge status "Quarantined" — dibuat sebagai widget kustom
            status_lbl = QLabel("Quarantined")
            status_lbl.setStyleSheet(StyleHelper.tag_badge())  # Gaya badge berwarna oranye
            status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Bungkus badge dalam widget agar bisa diatur padding-nya
            status_widget = QWidget()
            s_layout = QHBoxLayout(status_widget)
            s_layout.setContentsMargins(10, 4, 10, 4)
            s_layout.addWidget(status_lbl)
            self.table.setCellWidget(row, 2, status_widget)

            # Kolom 3: Dua tombol aksi (Restore dan Delete) untuk setiap baris
            action_widget = QWidget()
            a_layout = QHBoxLayout(action_widget)
            a_layout.setContentsMargins(8, 6, 8, 6)
            a_layout.setSpacing(8)  # Jarak antara dua tombol
            a_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Tombol "Restore" — warna oranye (aksi tidak permanen, masih bisa dibatalkan)
            btn_restore = QPushButton("Restore")
            btn_restore.setFixedSize(92, 34)
            btn_restore.setStyleSheet(self._action_button_style())  # Oranye
            btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
            # Ketika diklik: panggil restore_file dengan jalur dan nama file baris ini
            # Gunakan default argument (p=..., n=...) untuk menangkap nilai saat ini dalam loop
            btn_restore.clicked.connect(
                lambda checked, p=item["path"], n=item["name"]: self.restore_file(p, n)
            )

            # Tombol "Delete" — warna merah (aksi permanen, tidak bisa dibatalkan)
            btn_del = QPushButton("Delete")
            btn_del.setFixedSize(86, 34)
            btn_del.setStyleSheet(self._action_button_style(danger=True))  # Merah
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            # Ketika diklik: panggil delete_file dengan jalur file baris ini
            btn_del.clicked.connect(lambda checked, p=item["path"]: self.delete_file(p))

            a_layout.addWidget(btn_restore)
            a_layout.addWidget(btn_del)
            self.table.setCellWidget(row, 3, action_widget)

    # ------------------------------------------------------------------
    # AKSI FILE — Fungsi-fungsi untuk mengelola file karantina
    # ------------------------------------------------------------------

    def delete_file(self, filepath: str):
        """
        Menghapus satu file karantina secara permanen dari disk.

        File yang dihapus tidak bisa dipulihkan. Setelah penghapusan,
        tabel diperbarui untuk mencerminkan perubahan.

        Args:
            filepath: Jalur lengkap file karantina yang akan dihapus.
        """
        try:
            # Hapus file dari disk secara permanen
            os.remove(filepath)

            # Muat ulang tabel agar baris file yang dihapus hilang dari tampilan
            self.load_quarantine_items()

        except Exception as e:
            # Tampilkan pesan error jika penghapusan gagal (misalnya file sedang digunakan)
            QMessageBox.warning(self, "Error", f"Failed to delete file: {e}")

    def restore_file(self, filepath: str, original_name: str):
        """
        Memindahkan satu file karantina kembali ke folder pemulihan di Desktop.

        Sebelum memindahkan, pengguna dimintai konfirmasi karena file tersebut
        mungkin masih berbahaya. File dipindahkan ke:
            Desktop/MangoDefend_Restored/<nama_asli>

        Args:
            filepath: Jalur lengkap file .quarantined yang akan dipulihkan.
            original_name: Nama file asli (tanpa ekstensi .quarantined).
        """
        # Tentukan folder tujuan pemulihan di Desktop
        desktop_dir = Path.home() / "Desktop" / "MangoDefend_Restored"

        # Buat folder tujuan jika belum ada
        if not desktop_dir.exists():
            desktop_dir.mkdir(parents=True, exist_ok=True)

        # Tentukan jalur lengkap file setelah dipulihkan
        target_path = desktop_dir / original_name

        # Minta konfirmasi pengguna sebelum memulihkan file berbahaya
        reply = QMessageBox.question(
            self,
            "Restore File",
            f"This will move the file to:\n{target_path}\n\n"
            "Are you sure you want to restore this potentially dangerous file?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        # Lanjutkan hanya jika pengguna menekan "Yes"
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Pindahkan file dari karantina ke folder pemulihan
                shutil.move(filepath, str(target_path))

                # Tampilkan pesan sukses dengan jalur tujuan
                QMessageBox.information(self, "Success", f"File restored to {target_path}")

                # Muat ulang tabel agar baris file yang dipulihkan hilang dari tampilan
                self.load_quarantine_items()

            except Exception as e:
                # Tampilkan pesan error jika pemindahan gagal
                QMessageBox.warning(self, "Error", f"Failed to restore file: {e}")

    def restore_all_files(self):
        """
        Memindahkan SEMUA file karantina ke folder pemulihan di Desktop.

        Proses:
        1. Cek apakah ada file di karantina
        2. Minta konfirmasi pengguna
        3. Pindahkan setiap file satu per satu
        4. Jika nama file sudah ada di tujuan, tambahkan nomor urut (_1, _2, dst.)
        5. Tampilkan ringkasan hasil (berhasil dan gagal)
        """
        # Kumpulkan semua file karantina
        files = list(self.quarantine_dir.glob("*.quarantined"))

        # Jika tidak ada file, beri tahu pengguna dan berhenti
        if not files:
            QMessageBox.information(self, "Restore All", "Tidak ada file di karantina.")
            return

        # Tentukan folder tujuan
        desktop_dir = Path.home() / "Desktop" / "MangoDefend_Restored"
        desktop_dir.mkdir(parents=True, exist_ok=True)

        # Minta konfirmasi — sertakan jumlah file dan jalur tujuan
        reply = QMessageBox.question(
            self,
            "Restore All Files",
            f"Ini akan memulihkan {len(files)} file ke:\n{desktop_dir}\n\n"
            "File karantina mungkin berbahaya. Lanjutkan?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        # Hentikan jika pengguna membatalkan
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Hitung file yang berhasil dan gagal dipindahkan
        success, failed = 0, 0

        for file_path in files:
            # Parse nama asli dari nama file karantina
            parts = file_path.name.split("_", 1)
            original_name = parts[1].replace(".quarantined", "") if len(parts) == 2 else file_path.stem
            target_path = desktop_dir / original_name

            # Hindari menimpa file yang sudah ada di tujuan
            # Jika sudah ada, tambahkan nomor: file.exe → file_1.exe → file_2.exe, dst.
            if target_path.exists():
                stem = target_path.stem      # Nama tanpa ekstensi
                suffix = target_path.suffix  # Ekstensi saja (misalnya ".exe")
                counter = 1
                # Cari nomor yang belum dipakai
                while target_path.exists():
                    target_path = desktop_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

            try:
                # Pindahkan file ke folder tujuan
                shutil.move(str(file_path), str(target_path))
                success += 1  # Catat sebagai berhasil

            except Exception:
                failed += 1  # Catat sebagai gagal (jangan crash, lanjut ke file berikutnya)

        # Muat ulang tabel setelah semua file diproses
        self.load_quarantine_items()

        # Tampilkan ringkasan hasil
        message = f"Berhasil memulihkan {success} file ke:\n{desktop_dir}"
        if failed:
            message += f"\n\nGagal: {failed} file"  # Tambahkan info file yang gagal jika ada
        QMessageBox.information(self, "Restore All Selesai", message)

    def empty_quarantine(self):
        """
        Menghapus SEMUA file di folder karantina secara permanen.

        Ini adalah aksi yang tidak bisa dibatalkan, sehingga pengguna
        dimintai konfirmasi terlebih dahulu sebelum penghapusan dilakukan.

        Setiap file dihapus satu per satu — jika ada yang gagal (misalnya
        sedang digunakan), file tersebut dilewati dan yang lain tetap dihapus.
        """
        # Minta konfirmasi pengguna sebelum menghapus semua file
        reply = QMessageBox.question(
            self,
            "Empty Quarantine",
            "Are you sure you want to permanently delete all isolated files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        # Lanjutkan hanya jika pengguna menekan "Yes"
        if reply == QMessageBox.StandardButton.Yes:
            # Hapus setiap file karantina satu per satu
            for file_path in self.quarantine_dir.glob("*.quarantined"):
                try:
                    os.remove(file_path)  # Hapus file dari disk secara permanen
                except Exception:
                    pass  # Lewati file yang gagal dihapus, lanjut ke berikutnya

            # Muat ulang tabel — seharusnya sekarang kosong
            self.load_quarantine_items()

    # ------------------------------------------------------------------
    # TEMA
    # ------------------------------------------------------------------

    def set_theme(self, is_dark: bool):
        """
        Mengganti tema dan memperbarui tampilan semua elemen halaman.

        Dipanggil dari luar (misalnya tombol tema di Sidebar) untuk
        menyinkronkan tampilan halaman karantina dengan pilihan tema pengguna.

        Args:
            is_dark: True untuk tema gelap, False untuk tema terang.
        """
        # Simpan pilihan tema baru
        self.is_dark = is_dark

        # Perbarui warna judul halaman
        self.title_label.setStyleSheet(
            f"color: {self._tp()}; font-size: 28px; font-weight: bold;"
            f" font-family: {Typography.FONT_FAMILY};"
        )

        # Perbarui gaya tabel dengan warna yang sesuai tema baru
        self.table.setStyleSheet(self._table_style())

        # Perbarui tema semua kartu soft card
        for card in self._soft_cards:
            card.set_theme(self.is_dark)
