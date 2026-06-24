"""
Timer Adaptif untuk Animasi — berbasis delta waktu.

Masalah yang diselesaikan:
  Jika animasi bergerak sejumlah piksel tetap setiap 'tick', maka di komputer
  lambat (30 fps) animasi akan terasa lambat, dan di komputer cepat (144 fps)
  akan terasa sangat cepat.

Solusinya:
  Setiap kali timer berbunyi, ia melaporkan BERAPA DETIK yang sudah berlalu
  sejak bunyi terakhir (disebut 'delta time' atau dt). Dengan mengalikan
  kecepatan animasi dengan dt, hasilnya selalu sama di komputer manapun.

Contoh pemakaian:
    timer = AdaptiveTimer(target_fps=60)
    timer.tick.connect(lambda dt: self._update(dt))
    timer.start()

    def _update(self, dt: float):
        # Sudut berputar 270 derajat per detik, di FPS berapapun
        self.angle = (self.angle + 270 * dt) % 360
        self.update()
"""

from __future__ import annotations
import time  # Digunakan untuk mengukur waktu nyata dengan presisi tinggi
from PySide6.QtCore import QObject, QTimer, Signal, Qt


class AdaptiveTimer(QObject):
    """
    Pembungkus QTimer yang mengirimkan sinyal 'tick(dt)' di mana dt adalah
    waktu nyata yang berlalu (dalam detik) sejak tick sebelumnya.

    Kenapa ini penting:
      QTimer biasa hanya berkata "waktunya!" tanpa memberitahu berapa lama
      sebenarnya. AdaptiveTimer mengukur waktu nyata menggunakan jam presisi
      tinggi (time.perf_counter), sehingga animasi tetap mulus di semua perangkat.

    Parameter:
        target_fps : Jumlah tick yang diinginkan per detik (default 60).
        max_dt     : Batas maksimum selisih waktu per tick (default 0.1 detik).
                     Berguna agar animasi tidak 'melompat' tiba-tiba saat
                     komputer baru kembali dari mode tidur atau tab ganti.
    """

    # Sinyal yang dikirim setiap tick, membawa nilai dt (selisih waktu dalam detik)
    tick = Signal(float)

    def __init__(self, target_fps: int = 60, max_dt: float = 0.1,
                 parent: QObject | None = None):
        """
        Siapkan timer adaptif.

        target_fps : Berapa kali per detik timer harus berbunyi (biasanya 60).
        max_dt     : Batas atas dt agar animasi tidak loncat saat komputer sibuk.
        parent     : Widget induk agar timer ikut dihapus saat induk ditutup.
        """
        super().__init__(parent)

        # Simpan batas dt agar lonjakan waktu tidak merusak animasi
        self._max_dt = max_dt

        # Waktu kapan tick terakhir terjadi; None berarti timer belum pernah jalan
        self._last_t: float | None = None

        # Hitung interval dalam milidetik dari target fps
        # Contoh: 60 fps → interval 16 ms; 30 fps → interval 33 ms
        interval_ms = max(1, int(1000 / target_fps))

        # Buat QTimer internal yang akan memanggil _on_tick secara berkala
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)

        # PreciseTimer meminta OS untuk akurasi tinggi (mengurangi jitter)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)

        # Hubungkan timer internal ke metode pengolah tick
        self._timer.timeout.connect(self._on_tick)

    def start(self):
        """
        Mulai timer: catat waktu saat ini sebagai titik awal,
        lalu aktifkan QTimer agar tick mulai berjalan.
        """
        # Simpan waktu sekarang agar tick pertama punya titik referensi
        self._last_t = time.perf_counter()
        self._timer.start()

    def stop(self):
        """
        Hentikan timer dan hapus waktu referensi.
        Setelah ini, sinyal tick tidak akan dikirim sampai start() dipanggil lagi.
        """
        self._timer.stop()
        self._last_t = None  # Reset agar tick pertama setelah start ulang tidak salah hitung

    def is_active(self) -> bool:
        """
        Kembalikan True jika timer sedang aktif (berdetak), False jika berhenti.
        Berguna agar kode luar tidak memanggil start() berkali-kali.
        """
        return self._timer.isActive()

    def _on_tick(self):
        """
        Dipanggil otomatis setiap kali interval QTimer habis.

        Tugasnya:
          1. Ukur berapa detik berlalu sejak tick terakhir.
          2. Batasi nilai agar tidak lebih dari max_dt (hindari lompatan besar).
          3. Kirim sinyal tick dengan nilai dt tersebut ke semua penerimanya.

        Penerima sinyal (misalnya animasi) tinggal mengalikan dt dengan kecepatan
        mereka untuk mendapatkan gerakan yang konsisten di semua komputer.
        """
        now = time.perf_counter()  # Waktu sekarang dalam detik (presisi tinggi)

        # Jika ini tick pertama sejak start(), gunakan waktu sekarang sebagai acuan
        if self._last_t is None:
            self._last_t = now

        # Hitung selisih waktu dan batasi agar tidak terlalu besar
        dt = min(now - self._last_t, self._max_dt)

        # Simpan waktu sekarang untuk dibandingkan di tick berikutnya
        self._last_t = now

        # Kirim sinyal dengan dt ke semua penerima yang sudah terhubung
        self.tick.emit(dt)
