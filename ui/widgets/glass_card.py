"""
Widget Kartu Dasbor yang Bisa Digunakan Ulang.

Berisi tiga jenis kartu yang digunakan di seluruh aplikasi MangoDefend:

1. GlassCard    — Kartu kaca (glassmorphism) dengan animasi border saat diarahkan mouse.
2. SoftCard     — Kartu umum yang lebih padat, mendukung tema, aksen warna, hover, dan klik.
3. SpotlightCard — Kartu showcase gelap dengan border tebal dan kontras tinggi.
4. StatCard     — Kartu statistik mini untuk angka-angka di dashboard.

Semua kartu menggambar dirinya sendiri menggunakan paintEvent (bukan CSS stylesheet)
agar animasi hover/klik bisa dikendalikan dengan presisi tinggi.
"""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient
from ui.styles.figma_theme import Colors  # Konstanta warna dari design system
from ui.core.anim_timer import AdaptiveTimer  # Timer berbasis delta waktu untuk animasi


class GlassCard(QFrame):
    """
    Kartu bergaya 'kaca' (glassmorphism): latar transparan dengan border yang
    berubah warna secara mulus dari putih ke oranye saat mouse diarahkan ke kartu.

    Cara kerja animasi hover:
      - self._hover_t adalah angka 0.0 (idle) hingga 1.0 (fully hovered).
      - Saat mouse masuk, _hover_t bergerak menuju 1.0.
      - Saat mouse pergi, _hover_t kembali ke 0.0.
      - Warna border diinterpolasi antara putih dan oranye berdasarkan _hover_t.
      - Timer dihentikan otomatis saat animasi selesai untuk menghemat CPU.
    """

    def __init__(self, parent=None, hover_effect=True):
        """
        Siapkan kartu kaca dengan animasi border hover.

        hover_effect : Jika True, border beranimasi saat mouse diarahkan ke kartu.
        """
        super().__init__(parent)
        self.hover_effect = hover_effect

        # Status apakah mouse sedang berada di atas kartu
        self._hovered = False

        # Nilai animasi hover: 0.0 = idle, 1.0 = mouse di atas kartu
        self._hover_t = 0.0

        # Nama objek untuk penargetan CSS dari luar
        self.setObjectName("glassCard")
        self.setProperty("class", "glassCard")

        # Timer adaptif yang menggerakkan animasi border ~60 kali per detik
        # Timer hanya berjalan saat animasi sedang berlangsung, hemat CPU
        self._hover_timer = AdaptiveTimer(target_fps=60, parent=self)
        self._hover_timer.tick.connect(self._on_hover_tick)

    # ── Animasi ─────────────────────────────────────────────────────────────

    def _on_hover_tick(self, dt: float):
        """
        Jalankan satu langkah animasi hover setiap tick.

        Menggeser _hover_t menuju nilai target (1.0 saat hover, 0.0 saat tidak).
        Saat sudah sangat dekat ke target, timer dihentikan otomatis.

        Kecepatan: 5.5 saat masuk (cepat muncul), 4.5 saat keluar (lebih lambat).
        dt : Waktu nyata yang berlalu sejak tick terakhir (detik).
        """
        target = 1.0 if self._hovered else 0.0

        # Kecepatan saat mouse masuk lebih tinggi dari saat mouse pergi
        speed  = 5.5 if self._hovered else 4.5
        diff   = target - self._hover_t

        if abs(diff) < 0.005:
            # Animasi selesai — paskan tepat ke target dan hentikan timer
            self._hover_t = target
            self._hover_timer.stop()
        else:
            # Gerakkan _hover_t mendekati target secara eksponensial
            self._hover_t += diff * (1.0 - pow(0.01, dt * speed))

        # Minta Qt untuk menggambar ulang kartu dengan nilai _hover_t terbaru
        self.update()

    # ── Peristiwa Mouse ──────────────────────────────────────────────────────

    def enterEvent(self, event):
        """Mulai animasi border saat mouse memasuki area kartu."""
        if self.hover_effect:
            self._hovered = True
            # Mulai timer hanya jika belum berjalan (hindari mulai ulang yang tidak perlu)
            if not self._hover_timer.is_active():
                self._hover_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Balik animasi border saat mouse meninggalkan area kartu."""
        if self.hover_effect:
            self._hovered = False
            if not self._hover_timer.is_active():
                self._hover_timer.start()
        super().leaveEvent(event)

    # ── Menggambar ─────────────────────────────────────────────────────────

    def paintEvent(self, event):
        """
        Gambar kartu kaca: latar transparan + border yang berubah warna sesuai hover.

        Latar: isian putih sangat transparan (efek 'kaca').
        Border: interpolasi warna dari putih (idle) ke oranye (hover penuh).
                Ketebalan border juga sedikit bertambah saat hover.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect   = self.rect()  # Area gambar seluruh widget
        radius = 24.0         # Sudut melengkung kartu dalam piksel
        t      = self._hover_t  # Nilai animasi saat ini (0.0–1.0)

        # Buat path dengan sudut melengkung untuk dijadikan bentuk kartu
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), radius, radius)

        # ── Latar belakang transparan (efek kaca) ──
        # Alpha 13/255 ≈ 5% — sangat transparan, tampak seperti kaca
        painter.setClipPath(path)
        painter.fillPath(path, QBrush(QColor(255, 255, 255, 13)))

        # ── Border yang beranimasi ──
        painter.setClipping(False)

        # Hitung alpha border: dari 26 (idle, samar) ke 77 (hover, lebih jelas)
        border_alpha = int(26 + (77 - 26) * t)

        # Interpolasi warna border dari putih (255,255,255) ke oranye (255,165,0)
        # t=0.0 → putih, t=1.0 → oranye
        border_r = int(255 * t)                      # Merah: 0 → 255
        border_g = int(255 * (1.0 - t) + 165 * t)   # Hijau: 255 → 165
        border_b = int(255 * (1.0 - t))              # Biru: 255 → 0

        border_color = QColor(border_r, border_g, border_b, border_alpha)

        # Ketebalan border sedikit bertambah saat hover: 1.0px → 1.5px
        painter.setPen(QPen(border_color, 1.0 + 0.5 * t))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Gambar border di dalam batas widget (0.5px offset agar tidak terpotong)
        painter.drawRoundedRect(
            rect.x() + 0.5, rect.y() + 0.5,
            rect.width() - 1, rect.height() - 1,
            radius, radius,
        )
        painter.end()


class SoftCard(QFrame):
    """
    Kartu umum yang lebih padat dengan bayangan, hover, dan efek tekan.

    Digunakan untuk sebagian besar kartu di halaman Protection, Scan, dan Update.

    Status visual:
      - Idle   : Isian solid tipis + border samar
      - Hover  : Border oranye bersinar (transisi mulus)
      - Tekan  : Kilatan isian oranye + border terang (jika set_interactive(True))

    Sinyal:
      clicked : Dikirim saat kartu ditekan dan dilepas (jika mode interaktif aktif).
    """

    # Sinyal yang dikirim saat kartu diklik (hanya jika set_interactive(True))
    clicked = Signal()

    def __init__(self, parent=None, is_dark=True, accent=None, hover_effect=True):
        """
        Siapkan kartu lunak dengan opsi tema, warna aksen, dan efek interaksi.

        is_dark      : True = mode gelap, False = mode terang.
        accent       : Warna aksen opsional (string hex, misal '#FF6B35').
                       Jika diisi, memberikan tint warna pada sudut kiri atas kartu.
        hover_effect : Jika True, border beranimasi oranye saat mouse di atas kartu.
        """
        super().__init__(parent)
        self.is_dark      = is_dark
        self.hover_effect = hover_effect

        # Status mouse dan interaksi
        self._hovered     = False   # Apakah mouse di atas kartu
        self._pressed     = False   # Apakah kartu sedang ditekan

        # Nilai animasi: 0.0 = idle, 1.0 = sepenuhnya hover/tekan
        self._hover_t     = 0.0
        self._press_t     = 0.0

        # Mode interaktif: jika False, kartu tidak merespons klik
        self._interactive = False

        # Jari-jari sudut melengkung kartu dalam piksel
        self._radius      = 18.0

        # Simpan warna aksen sebagai objek QColor (atau None jika tidak ada)
        self._accent      = QColor(accent) if accent else None

        # Nama objek untuk identifikasi
        self.setObjectName("softCard")
        self.setProperty("class", "softCard")

        # ── Bayangan jatuh (drop shadow) ──
        # Memberikan kesan kartu melayang sedikit di atas latar
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(34)  # Seberapa lebar/kabur bayangan (lebih besar = lebih halus)
        self._shadow.setOffset(0, 12)   # Bayangan jatuh 12px ke bawah (kesan cahaya dari atas)
        self.setGraphicsEffect(self._shadow)
        self._apply_shadow()  # Atur warna bayangan sesuai tema

        # Timer adaptif yang menggerakkan animasi hover DAN tekan sekaligus
        # Satu timer cukup untuk kedua animasi, lebih hemat sumber daya
        self._hover_timer = AdaptiveTimer(target_fps=60, parent=self)
        self._hover_timer.tick.connect(self._on_hover_tick)

    # ── Tema & Tampilan ──────────────────────────────────────────────────────

    def _apply_shadow(self):
        """
        Perbarui warna bayangan sesuai tema aktif.
        Mode gelap: bayangan hitam lebih kuat.
        Mode terang: bayangan biru gelap lebih tipis agar tidak terlalu berat.
        """
        self._shadow.setColor(
            QColor(0, 0, 0, 95) if self.is_dark else QColor(15, 23, 42, 28)
        )

    def set_theme(self, is_dark: bool):
        """
        Ganti tema gelap/terang dan perbarui tampilan kartu.
        Dipanggil dari induk saat pengguna mengganti tema.
        """
        self.is_dark = is_dark
        self._apply_shadow()  # Warna bayangan harus ikut berubah
        self.update()         # Minta gambar ulang dengan warna tema baru

    def set_accent(self, accent):
        """
        Atur warna aksen pada tint isian kartu.
        Warna aksen memberikan sedikit warna khas di sudut kartu
        (misalnya: merah untuk peringatan, hijau untuk status aman).

        accent : String hex warna (misalnya '#FF6B35') atau None untuk menghapus aksen.
        """
        self._accent = QColor(accent) if accent else None
        self.update()

    def set_interactive(self, enabled: bool):
        """
        Aktifkan atau nonaktifkan mode interaktif (klik).
        Saat aktif: kursor berubah menjadi tangan dan kartu merespons klik.
        Saat nonaktif: kartu hanya menampilkan visual, tidak bisa diklik.
        """
        self._interactive = enabled
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor
        )

    # ── Animasi ─────────────────────────────────────────────────────────────

    def _on_hover_tick(self, dt: float):
        """
        Jalankan satu langkah animasi hover DAN tekan setiap tick.

        Hover  : _hover_t bergerak ke 1.0 saat mouse di atas, kembali ke 0.0 saat pergi.
        Tekan  : _press_t memudar ke 0.0 setelah mouse dilepas (kilatan oranye).
        Timer dihentikan saat kedua animasi sudah selesai.

        dt : Waktu nyata yang berlalu sejak tick terakhir (detik).
        """
        # ── Animasi hover ──
        target = 1.0 if self._hovered else 0.0
        speed  = 5.5 if self._hovered else 4.5
        diff   = target - self._hover_t

        if abs(diff) >= 0.005:
            # Masih perlu bergerak — gunakan rumus eksponensial
            self._hover_t += diff * (1.0 - pow(0.01, dt * speed))
        else:
            # Sudah sampai target
            self._hover_t = target

        # ── Animasi kilatan tekan (press flash) ──
        # Setelah mouse dilepas, nilai _press_t memudar perlahan ke 0
        if not self._pressed and self._press_t > 0.005:
            # Kurangi _press_t secara eksponensial (cepat di awal, lambat di akhir)
            self._press_t -= self._press_t * (1.0 - pow(0.01, dt * 6.0))
        elif not self._pressed:
            # Sudah sangat kecil — langsung nolkan
            self._press_t = 0.0

        # ── Cek apakah semua animasi sudah selesai ──
        done_hover = abs(self._hover_t - target) < 0.005
        done_press = not self._pressed and self._press_t < 0.005

        if done_hover and done_press:
            # Kedua animasi selesai — hentikan timer untuk hemat CPU
            self._hover_timer.stop()

        self.update()  # Minta gambar ulang

    # ── Peristiwa Mouse ──────────────────────────────────────────────────────

    def enterEvent(self, event):
        """Mulai animasi border oranye saat mouse memasuki kartu."""
        if self.hover_effect:
            self._hovered = True
            if not self._hover_timer.is_active():
                self._hover_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Balik animasi border saat mouse meninggalkan kartu."""
        if self.hover_effect:
            self._hovered = False
            if not self._hover_timer.is_active():
                self._hover_timer.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Picu kilatan oranye saat kartu ditekan (hanya dalam mode interaktif)."""
        if self._interactive and event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._press_t = 1.0  # Set kilatan ke penuh
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Lepaskan status tekan, mulai pudar efek kilatan, dan kirim sinyal klik
        jika mouse masih berada di dalam kartu saat dilepas.
        """
        if self._interactive and event.button() == Qt.MouseButton.LeftButton:
            self._pressed = False

            # Hanya kirim sinyal 'clicked' jika mouse tidak keluar sebelum dilepas
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit()

            # Mulai animasi pudar kilatan
            if not self._hover_timer.is_active():
                self._hover_timer.start()
        super().mouseReleaseEvent(event)

    # ── Menggambar ─────────────────────────────────────────────────────────

    def paintEvent(self, event):
        """
        Gambar kartu dengan semua lapisan visual secara berurutan:

          1. Isian gradasi dasar (warna berbeda untuk gelap/terang)
          2. Tint aksen warna di sudut kiri atas (jika ada)
          3. Kilap (sheen) terang di bagian atas kartu
          4. Kilatan oranye saat kartu ditekan
          5. Border yang beranimasi (idle → hover → tekan)
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Area gambar dikecilkan 1px dari tepi agar border tidak terpotong
        rect = self.rect().adjusted(1, 1, -1, -1)

        # Path bentuk kartu dengan sudut melengkung
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), self._radius, self._radius)

        # ── Tentukan warna berdasarkan tema ──
        if self.is_dark:
            # Mode gelap: warna abu-abu gelap dengan sedikit transparansi
            top_color       = QColor(Colors.DARK_BG_TERTIARY);  top_color.setAlpha(244)
            bottom_color    = QColor(Colors.DARK_BG_SECONDARY); bottom_color.setAlpha(244)
            border_color    = QColor(Colors.DARK_TEXT_PRIMARY);  border_color.setAlpha(28)    # Border putih samar
            highlight_color = QColor(Colors.DARK_TEXT_PRIMARY);  highlight_color.setAlpha(22) # Kilap putih samar
            hover_color     = QColor(Colors.ORANGE_500);         hover_color.setAlpha(85)     # Hover oranye
        else:
            # Mode terang: warna putih bersih
            top_color       = QColor(Colors.LIGHT_BG_PRIMARY);  top_color.setAlpha(250)
            bottom_color    = QColor(Colors.LIGHT_BG_SECONDARY);bottom_color.setAlpha(250)
            border_color    = QColor(Colors.LIGHT_BORDER);      border_color.setAlpha(210)
            highlight_color = QColor(Colors.LIGHT_BG_PRIMARY);  highlight_color.setAlpha(140)
            hover_color     = QColor(Colors.ORANGE_500);        hover_color.setAlpha(70)

        # ── Lapisan 1: Isian gradasi dasar ──
        # Gradasi dari kiri-atas (lebih terang) ke kanan-bawah (lebih gelap)
        fill_gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        fill_gradient.setColorAt(0.0, top_color)
        fill_gradient.setColorAt(1.0, bottom_color)
        painter.fillPath(path, QBrush(fill_gradient))

        # ── Lapisan 2: Tint aksen warna (opsional) ──
        # Memberikan sedikit warna khas di sudut kiri-atas kartu
        if self._accent:
            r, g, b = self._accent.red(), self._accent.green(), self._accent.blue()
            ag = QLinearGradient(rect.topLeft(), rect.bottomRight())
            # Alpha lebih tinggi di sudut atas, memudar ke 0 di sudut bawah
            ag.setColorAt(0.0,  QColor(r, g, b, 26 if self.is_dark else 18))
            ag.setColorAt(0.55, QColor(r, g, b, 10 if self.is_dark else 6))
            ag.setColorAt(1.0,  QColor(r, g, b, 0))
            painter.fillPath(path, QBrush(ag))

        # ── Lapisan 3: Kilap (sheen) di bagian atas ──
        # Efek permukaan mengkilap — hanya separuh atas kartu yang diberi kilap
        painter.save()
        painter.setClipPath(path)  # Batasi gambar dalam bentuk kartu
        sheen_rect = rect.adjusted(0, 0, 0, -rect.height() * 0.45)  # Hanya 55% atas
        sg = QLinearGradient(sheen_rect.topLeft(), sheen_rect.bottomLeft())
        sg.setColorAt(0.0, highlight_color)                                   # Terang di atas
        sg.setColorAt(1.0, QColor(highlight_color.red(), highlight_color.green(), highlight_color.blue(), 0))  # Transparan di bawah
        painter.fillRect(sheen_rect, sg)
        painter.restore()

        # ── Fungsi interpolasi warna (digunakan untuk border animasi) ──
        def _lerp_color(a: QColor, b: QColor, f: float) -> QColor:
            """
            Campurkan dua warna berdasarkan faktor f (0.0 = warna a, 1.0 = warna b).
            Digunakan untuk transisi warna border idle→hover→tekan.
            """
            return QColor(
                int(a.red()   + (b.red()   - a.red())   * f),
                int(a.green() + (b.green() - a.green()) * f),
                int(a.blue()  + (b.blue()  - a.blue())  * f),
                int(a.alpha() + (b.alpha() - a.alpha()) * f),
            )

        # ── Lapisan 4: Kilatan isian saat ditekan ──
        pt = self._press_t
        if pt > 0.001:
            # Isian oranye semi-transparan yang memudar setelah dilepas
            press_fill = QColor(Colors.ORANGE_500)
            press_fill.setAlpha(int(55 * pt))  # Semakin kecil pt, semakin transparan
            painter.fillPath(path, QBrush(press_fill))

        # ── Lapisan 5: Border beranimasi ──
        t             = self._hover_t
        press_border  = QColor(Colors.ORANGE_500); press_border.setAlpha(220)

        # Campurkan warna border idle → hover oranye
        blended = _lerp_color(border_color, hover_color, t)

        # Jika sedang/baru ditekan, campurkan lagi dengan warna tekan yang lebih terang
        if pt > 0.001:
            blended = _lerp_color(blended, press_border, pt)

        # Ketebalan border bertambah saat hover dan tekan
        painter.setPen(QPen(blended, 1.0 + 0.4 * t + 0.6 * pt))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, self._radius, self._radius)

        painter.end()


class SpotlightCard(QFrame):
    """
    Kartu showcase gelap dengan border tebal dan kontras tinggi.
    Paling cocok untuk tile KPI kecil yang membutuhkan tampilan premium dan menonjol.

    Berbeda dari SoftCard, SpotlightCard menggunakan border tebal (4px) di luar
    dan border tipis di dalam, memberi kesan bingkai seperti foto.
    Hover hanya mempertebal border luar sedikit — tidak ada animasi timer.
    """

    def __init__(self, parent=None, is_dark=True, hover_effect=True):
        """
        Siapkan kartu sorotan premium.

        is_dark      : True = mode gelap, False = mode terang.
        hover_effect : Jika True, border sedikit menebal saat mouse di atas.
        """
        super().__init__(parent)
        self.is_dark      = is_dark
        self.hover_effect = hover_effect
        self._hovered     = False
        self._radius      = 30.0  # Sudut lebih bulat dari SoftCard untuk kesan premium

        self.setObjectName("spotlightCard")
        self.setProperty("class", "spotlightCard")

        # Bayangan jatuh untuk kesan melayang
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(24)
        self._shadow.setOffset(0, 10)
        self.setGraphicsEffect(self._shadow)
        self._apply_shadow()

    # ── Tema ────────────────────────────────────────────────────────────────

    def _apply_shadow(self):
        """Perbarui warna bayangan sesuai tema aktif."""
        self._shadow.setColor(
            QColor(0, 0, 0, 90) if self.is_dark else QColor(15, 23, 42, 26)
        )

    def set_theme(self, is_dark: bool):
        """Ganti tema dan minta gambar ulang."""
        self.is_dark = is_dark
        self._apply_shadow()
        self.update()

    # ── Peristiwa Mouse ──────────────────────────────────────────────────────

    def enterEvent(self, event):
        """Pertebal border saat mouse masuk (efek hover sederhana, tanpa timer)."""
        if self.hover_effect:
            self._hovered = True
            self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Kembalikan border ke ukuran normal saat mouse pergi."""
        if self.hover_effect:
            self._hovered = False
            self.update()
        super().leaveEvent(event)

    # ── Menggambar ─────────────────────────────────────────────────────────

    def paintEvent(self, event):
        """
        Gambar kartu spotlight dengan:
          1. Isian gradasi gelap dari sudut kiri-atas ke kanan-bawah.
          2. Kilap terang tipis di bagian atas (kesan cahaya dari atas).
          3. Border luar tebal (sedikit menebal saat hover).
          4. Border dalam tipis sebagai garis aksen tambahan.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Perkecil area 2px dari tepi untuk ruang border tebal
        rect = self.rect().adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(rect, self._radius, self._radius)

        # Tentukan warna sesuai tema
        if self.is_dark:
            start_color  = QColor(Colors.DARK_BG_TERTIARY)   # Abu-abu agak terang
            end_color    = QColor(Colors.DARK_BG_SECONDARY)   # Abu-abu lebih gelap
            top_sheen    = QColor(Colors.DARK_TEXT_PRIMARY); top_sheen.setAlpha(20)   # Kilap putih samar
            border_color = QColor(Colors.DARK_BG_PRIMARY)     # Border gelap pekat
            inner_color  = QColor(Colors.DARK_TEXT_PRIMARY); inner_color.setAlpha(18) # Border dalam putih samar
        else:
            start_color  = QColor(Colors.LIGHT_BG_PRIMARY)
            end_color    = QColor(Colors.LIGHT_BG_SECONDARY)
            top_sheen    = QColor(Colors.ORANGE_500); top_sheen.setAlpha(18)   # Kilap oranye samar
            border_color = QColor(Colors.LIGHT_BORDER)
            inner_color  = QColor(Colors.ORANGE_500); inner_color.setAlpha(28) # Border dalam oranye samar

        # ── Lapisan 1: Isian gradasi ──
        base_gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        base_gradient.setColorAt(0.0, start_color)
        base_gradient.setColorAt(1.0, end_color)
        painter.fillPath(path, QBrush(base_gradient))

        # ── Lapisan 2: Kilap di bagian atas ──
        painter.save()
        painter.setClipPath(path)
        sheen_rect = rect.adjusted(0, 0, 0, -int(rect.height() * 0.54))
        sg = QLinearGradient(sheen_rect.topLeft(), sheen_rect.bottomLeft())
        sg.setColorAt(0.0, top_sheen)
        sg.setColorAt(1.0, QColor(Colors.DARK_TEXT_PRIMARY if self.is_dark else Colors.ORANGE_500, 0))
        painter.fillRect(sheen_rect, sg)
        painter.restore()

        # ── Lapisan 3: Border luar tebal ──
        # Saat hover border sedikit menebal: 4.0px → 4.6px
        painter.setPen(QPen(border_color, 4 if not self._hovered else 4.6))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, self._radius, self._radius)

        # ── Lapisan 4: Border dalam tipis (garis aksen) ──
        # Digambar 4px lebih ke dalam dari border luar untuk kesan bingkai ganda
        painter.setPen(QPen(inner_color, 1))
        painter.drawRoundedRect(rect.adjusted(4, 4, -4, -4), self._radius - 4, self._radius - 4)

        painter.end()


class StatCard(QFrame):
    """
    Kartu statistik mini dengan tint oranye.
    Digunakan untuk menampilkan angka-angka kunci kecil di dashboard.

    Desainnya sederhana: hanya latar belakang bergradasi oranye samar
    dengan border oranye tipis. Konten (teks angka) ditambahkan dari luar.
    """

    def __init__(self, parent=None, is_dark=True):
        """
        Siapkan kartu statistik kecil.

        is_dark : Disimpan untuk konsistensi API, belum digunakan secara aktif.
        """
        super().__init__(parent)
        self.is_dark = is_dark
        self.setObjectName("statCard")  # Nama untuk penargetan CSS jika diperlukan

    def paintEvent(self, event):
        """
        Gambar kartu statistik: latar oranye samar + border oranye tipis.

        Sederhana dan ringan: tidak ada animasi, hanya satu lapisan fill dan satu border.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect   = self.rect()
        radius = 20.0  # Sudut lebih bulat dari widget lain untuk tampilan kompak

        # Buat path bentuk kartu
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), radius, radius)

        # ── Isian oranye samar ──
        # Alpha 25/255 ≈ 10% — sangat tipis, hanya warna khas saja
        painter.fillPath(path, QBrush(QColor(255, 165, 0, 25)))

        # ── Border oranye tipis ──
        # Alpha 51/255 ≈ 20% — sedikit lebih jelas dari isian
        painter.setPen(QPen(QColor(255, 165, 0, 51), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(
            rect.x() + 0.5, rect.y() + 0.5,     # Offset 0.5px agar border tidak terpotong
            rect.width() - 1, rect.height() - 1,
            radius, radius
        )

        painter.end()
