"""
MangoDefend Installer - Tkinter based (no VC++ dependency)
"""
# Tutup PyInstaller built-in splash screen
try:
    import pyi_splash
    pyi_splash.close()
except Exception:
    pass

import sys
import os
import subprocess
import shutil
import threading
import ctypes
import winreg
import urllib.request
import tkinter as tk
from tkinter import ttk
from pathlib import Path


INSTALL_DIR   = Path("C:/Program Files/MangoDefend")
APP_NAME      = "MangoDefend"
APP_VERSION   = "1.0.0"
VC_REDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
VC_REDIST_KEY = r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"

BG       = "#12121C"
ACCENT   = "#FFA500"
FG       = "#FFFFFF"
FG_DIM   = "#888888"
FG_GREEN = "#2ecc71"


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def vc_redist_installed() -> bool:
    try:
        winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, VC_REDIST_KEY)
        return True
    except FileNotFoundError:
        return False


def create_shortcut(target: Path):
    try:
        import win32com.client
        shell    = win32com.client.Dispatch("WScript.Shell")
        desktop  = Path(shell.SpecialFolders("Desktop"))
        sc       = shell.CreateShortcut(str(desktop / f"{APP_NAME}.lnk"))
        sc.TargetPath       = str(target)
        sc.WorkingDirectory = str(target.parent)
        sc.IconLocation     = str(target)
        sc.save()
    except Exception:
        pass


def register_app():
    try:
        key = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key) as k:
            winreg.SetValueEx(k, "DisplayName",     0, winreg.REG_SZ, APP_NAME)
            winreg.SetValueEx(k, "DisplayVersion",  0, winreg.REG_SZ, APP_VERSION)
            winreg.SetValueEx(k, "Publisher",       0, winreg.REG_SZ, "MangoDefend")
            winreg.SetValueEx(k, "InstallLocation", 0, winreg.REG_SZ, str(INSTALL_DIR))
    except Exception:
        pass


# ── Installer Window ──────────────────────────────────────────────────────────

class InstallerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MangoDefend Setup")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        self.root.overrideredirect(True)  # frameless

        self._drag_x = 0
        self._drag_y = 0
        self._build_ui()
        self._center()

    def _center(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = (sw - 500) // 2
        y  = (sh - 400) // 2
        self.root.geometry(f"500x400+{x}+{y}")

    def _build_ui(self):
        root = self.root

        # Drag support
        root.bind("<ButtonPress-1>",   self._start_drag)
        root.bind("<B1-Motion>",       self._do_drag)

        # Border frame
        border = tk.Frame(root, bg=ACCENT, bd=1)
        border.place(x=0, y=0, width=500, height=400)
        inner = tk.Frame(border, bg=BG)
        inner.place(x=1, y=1, width=498, height=398)

        # Close button
        close_btn = tk.Label(inner, text="✕", bg=BG, fg=FG_DIM,
                             font=("Segoe UI", 12), cursor="hand2")
        close_btn.place(x=468, y=10)
        close_btn.bind("<Button-1>", lambda _: root.destroy())
        close_btn.bind("<Enter>",    lambda _: close_btn.config(fg="#e74c3c"))
        close_btn.bind("<Leave>",    lambda _: close_btn.config(fg=FG_DIM))

        # Logo + Title
        tk.Label(inner, text="🥭", bg=BG, font=("Segoe UI", 32)).place(x=30, y=28)
        tk.Label(inner, text="MangoDefend", bg=BG, fg=FG,
                 font=("Segoe UI", 20, "bold")).place(x=90, y=32)
        tk.Label(inner, text="AI Malware Protection — Setup", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 9)).place(x=92, y=65)

        # Divider
        tk.Frame(inner, bg="#2a2a3a", height=1).place(x=20, y=96, width=460)

        # Install path
        tk.Label(inner, text="📁  Lokasi Instalasi:", bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 9)).place(x=24, y=112)
        tk.Label(inner, text="C:\\Program Files\\MangoDefend", bg=BG, fg=FG,
                 font=("Segoe UI", 9, "bold")).place(x=140, y=112)

        # Steps
        self._step_labels = []
        steps = [
            "Memeriksa dependensi sistem",
            "Menginstal Visual C++ Runtime",
            "Menyalin file aplikasi",
            "Membuat shortcut desktop",
            "Selesai",
        ]
        for i, step in enumerate(steps):
            y = 145 + i * 28
            icon = tk.Label(inner, text="⬜", bg=BG, fg=FG_DIM,
                            font=("Segoe UI", 11))
            icon.place(x=24, y=y)
            lbl = tk.Label(inner, text=step, bg=BG, fg=FG_DIM,
                           font=("Segoe UI", 10))
            lbl.place(x=52, y=y + 1)
            self._step_labels.append((icon, lbl))

        # Progress bar
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Orange.Horizontal.TProgressbar",
                         troughcolor="#1e1e2e",
                         background=ACCENT,
                         borderwidth=0,
                         thickness=10)
        self._pbar = ttk.Progressbar(inner, style="Orange.Horizontal.TProgressbar",
                                     orient="horizontal", length=452, mode="determinate")
        self._pbar.place(x=24, y=300)

        # Status label
        self._status_var = tk.StringVar(value="Klik tombol di bawah untuk memulai instalasi.")
        self._status_lbl = tk.Label(inner, textvariable=self._status_var,
                                    bg=BG, fg=FG_DIM, font=("Segoe UI", 9))
        self._status_lbl.place(x=24, y=320)

        # Install button
        self._btn = tk.Button(inner, text="  Instal Sekarang  ",
                              bg=ACCENT, fg="#1a1a1a",
                              font=("Segoe UI", 11, "bold"),
                              relief="flat", cursor="hand2",
                              command=self._start_install)
        self._btn.place(x=150, y=348, width=200, height=36)

    def _start_drag(self, e):
        self._drag_x = e.x
        self._drag_y = e.y

    def _do_drag(self, e):
        x = self.root.winfo_x() + e.x - self._drag_x
        y = self.root.winfo_y() + e.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def _set_step(self, index: int, done: bool):
        icon, lbl = self._step_labels[index]
        if done:
            icon.config(text="✅", fg=ACCENT)
            lbl.config(fg=ACCENT)
        else:
            icon.config(text="🔄", fg=FG)
            lbl.config(fg=FG)

    def _update(self, pct: int, msg: str, step_done: int = -1):
        self._pbar["value"] = pct
        self._status_var.set(msg)
        if step_done >= 0:
            self._set_step(step_done, True)
        self.root.update_idletasks()

    def _start_install(self):
        self._btn.config(state="disabled", text="  Menginstal...  ", bg="#555")
        thread = threading.Thread(target=self._run_install, daemon=True)
        thread.start()

    def _run_install(self):
        try:
            # Step 1: Cek VC++
            self._update(5, "Memeriksa dependensi sistem...")
            self._set_step(0, False)
            self.root.update_idletasks()

            if not vc_redist_installed():
                self._set_step(1, False)
                self._update(10, "Mengunduh Visual C++ Runtime dari Microsoft...")
                import tempfile
                tmp = Path(tempfile.gettempdir()) / "vc_redist.x64.exe"
                urllib.request.urlretrieve(VC_REDIST_URL, tmp)
                self._update(22, "Menginstal Visual C++ Runtime...")
                subprocess.run([str(tmp), "/quiet", "/norestart"], check=True)
                self._update(33, "Visual C++ Runtime berhasil diinstal ✓", step_done=1)
            else:
                self._update(33, "Visual C++ Runtime sudah ada ✓", step_done=1)

            self._update(33, "Dependensi sistem OK ✓", step_done=0)

            # Step 2: Copy files
            self._set_step(2, False)
            self._update(35, "Menyalin file MangoDefend...")
            src = Path(__file__).parent / "MangoDefend"
            if not src.exists():
                src = Path(__file__).parent.parent / "dist" / "MangoDefend"

            INSTALL_DIR.mkdir(parents=True, exist_ok=True)
            files = [f for f in src.rglob("*") if f.is_file()]
            total = len(files)
            for i, item in enumerate(files):
                rel    = item.relative_to(src)
                target = INSTALL_DIR / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
                pct = 35 + int((i + 1) / total * 45)
                self._update(pct, f"Menyalin: {rel.name}")

            self._update(82, "File aplikasi tersalin ✓", step_done=2)

            # Step 3: Shortcut
            self._set_step(3, False)
            self._update(88, "Membuat shortcut desktop...")
            create_shortcut(INSTALL_DIR / "MangoDefend.exe")
            self._update(92, "Shortcut desktop dibuat ✓", step_done=3)

            # Step 4: Register
            self._update(96, "Mendaftarkan aplikasi...")
            register_app()
            self._update(100, "✅  Instalasi selesai! MangoDefend siap digunakan.", step_done=4)

            # Update button
            self.root.after(0, self._on_success)

        except Exception as e:
            self.root.after(0, lambda: self._on_error(str(e)))

    def _on_success(self):
        self._btn.config(
            state="normal",
            text="  Buka MangoDefend  ",
            bg=FG_GREEN, fg="white",
            command=self._launch
        )

    def _on_error(self, msg: str):
        self._status_var.set(f"❌ Error: {msg}")
        self._btn.config(state="normal", text="  Coba Lagi  ",
                         bg="#e74c3c", fg="white",
                         command=self._start_install)

    def _launch(self):
        exe = INSTALL_DIR / "MangoDefend.exe"
        if exe.exists():
            subprocess.Popen([str(exe)])
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    if sys.platform == "win32" and not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable,
            f'"{os.path.abspath(__file__)}"', None, 1
        )
        sys.exit(0)

    app = InstallerApp()
    app.run()


if __name__ == "__main__":
    main()
