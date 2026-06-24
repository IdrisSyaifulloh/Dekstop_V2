"""
Startup Manager — Mengatur apakah MangoDefend otomatis berjalan saat Windows menyala.

Cara kerja:
Windows punya daftar program yang otomatis dijalankan saat login pengguna.
Daftar ini tersimpan di registry Windows di lokasi:
  HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run

Kita cukup tambahkan atau hapus entri di sana untuk mengatur auto-start.
Tidak perlu hak Administrator — HKCU (Current User) bisa diakses tanpa admin.
"""

import sys   # Untuk cek platform (Windows atau bukan)
import os    # Untuk mendapatkan path executable aplikasi
import logging

# Logger khusus untuk modul ini
logger = logging.getLogger(__name__)

# Nama entri di registry — ini yang akan muncul di Task Manager > Startup
_REG_APP_NAME = "MangoDefend"

# Lokasi registry tempat program auto-start disimpan per-user
_REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _get_exe_path() -> str:
    """
    Mendapatkan path lengkap executable MangoDefend yang sedang berjalan.

    Kenapa ada dua kondisi?
    - Saat dikemas dengan PyInstaller: sys.frozen = True, path ada di sys.executable
    - Saat dijalankan langsung sebagai skrip Python: pakai 'pythonw.exe main.py'
      (pythonw = python tanpa console window yang mengganggu)
    """
    if getattr(sys, "frozen", False):
        # Aplikasi sudah dikemas sebagai .exe oleh PyInstaller
        return f'"{sys.executable}"'
    else:
        # Dijalankan sebagai skrip Python biasa
        # Gunakan pythonw.exe agar tidak muncul jendela console hitam saat startup
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        main_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "main.py")
        )
        return f'"{pythonw}" "{main_path}"'


def enable_startup() -> bool:
    """
    Daftarkan MangoDefend ke registry agar otomatis jalan saat Windows menyala.

    Mengembalikan True jika berhasil, False jika gagal (mis. bukan Windows).
    """
    if sys.platform != "win32":
        logger.warning("Auto-start hanya didukung di Windows")
        return False

    try:
        import winreg  # Modul bawaan Python untuk akses registry Windows

        # Buka kunci registry Run dengan izin tulis
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,  # Per-user, tidak butuh admin
            _REG_KEY_PATH,
            0,
            winreg.KEY_SET_VALUE  # Izin untuk menulis nilai
        )

        # Tulis entri: nama = "MangoDefend", nilai = path executable
        exe_path = _get_exe_path()
        winreg.SetValueEx(key, _REG_APP_NAME, 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)

        logger.info(f"✅ Auto-start diaktifkan: {exe_path}")
        return True

    except Exception as e:
        logger.error(f"Gagal mengaktifkan auto-start: {e}")
        return False


def disable_startup() -> bool:
    """
    Hapus MangoDefend dari registry sehingga tidak lagi otomatis jalan saat Windows menyala.

    Mengembalikan True jika berhasil atau memang sudah tidak terdaftar.
    """
    if sys.platform != "win32":
        return False

    try:
        import winreg

        # Buka kunci registry Run dengan izin hapus
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REG_KEY_PATH,
            0,
            winreg.KEY_SET_VALUE
        )

        try:
            winreg.DeleteValue(key, _REG_APP_NAME)  # Hapus entri MangoDefend
            logger.info("✅ Auto-start dinonaktifkan")
        except FileNotFoundError:
            pass  # Entri memang tidak ada — tidak perlu dihapus
        finally:
            winreg.CloseKey(key)

        return True

    except Exception as e:
        logger.error(f"Gagal menonaktifkan auto-start: {e}")
        return False


def is_startup_enabled() -> bool:
    """
    Cek apakah MangoDefend sudah terdaftar di auto-start Windows atau belum.

    Mengembalikan True jika terdaftar, False jika tidak.
    """
    if sys.platform != "win32":
        return False

    try:
        import winreg

        # Buka kunci registry Run dengan izin baca saja
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REG_KEY_PATH,
            0,
            winreg.KEY_READ
        )

        try:
            winreg.QueryValueEx(key, _REG_APP_NAME)  # Coba baca entri
            return True   # Entri ada → auto-start aktif
        except FileNotFoundError:
            return False  # Entri tidak ada → auto-start tidak aktif
        finally:
            winreg.CloseKey(key)

    except Exception:
        return False
