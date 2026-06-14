"""
RMAV Desktop - AI-Powered Malware Detection
Main entry point for the desktop application
"""
import sys
import os
import logging


# ── Require Administrator on Windows ───────────────────────────────────────
if False and sys.platform == "win32":
    import ctypes

    def _is_admin() -> bool:
        """Return True if the current process has administrator rights."""
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    if not _is_admin():
        # Re-launch the same script / frozen exe with elevated privileges.
        # ShellExecuteW with "runas" triggers the UAC prompt.
        script = sys.executable if getattr(sys, "frozen", False) else __file__
        params = " ".join(f'"{a}"' for a in sys.argv[1:]) if not getattr(sys, "frozen", False) else ""
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable,
            f'"{script}" {params}'.strip(), None, 1
        )
        sys.exit(0)
# ───────────────────────────────────────────────────────────────────────────

from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt
from ui.modern_window import ModernWindow
from core.config_manager import get_config

logger = logging.getLogger(__name__)


def _is_windows_admin() -> bool:
    """Return True when the current Windows process has administrator rights."""
    if sys.platform != "win32":
        return True

    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def ensure_windows_admin() -> bool:
    """Re-launch the process with UAC elevation if not already admin; returns False when child was launched."""
    if sys.platform != "win32" or _is_windows_admin():
        return True

    import ctypes

    script = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
    params = ""
    if not getattr(sys, "frozen", False):
        params = " ".join(f'"{arg}"' for arg in sys.argv[1:])

    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        f'"{script}" {params}'.strip(),
        os.path.dirname(script) or None,
        1,
    )

    if result <= 32:
        if result == 1223:
            raise RuntimeError(
                "Startup dibatalkan karena izin Administrator tidak diberikan."
            )
        raise RuntimeError(
            f"Gagal menjalankan MangoDefend sebagai Administrator (kode: {result})."
        )

    return False


def _on_malware_detected(file_path: str, scan_result: dict):
    """Log detected malware and show a desktop notification alert."""
    logger.warning("MALWARE DETECTED: %s — result: %s", file_path, scan_result.get('result'))
    try:
        from core.notification_manager import NotificationManager
        notif = NotificationManager()
        notif.show_malware_alert(
            file_path=file_path,
            file_name=os.path.basename(file_path),
            threat_level="High"
        )
    except Exception as e:
        logger.error("Failed to show malware notification: %s", e)


def _init_services(window, config):
    """Start all heavy backend services in a daemon thread so the window appears instantly."""
    import threading

    def _run():
        """Inner worker: initialize each service and attach references to the window."""
        embedded_backend = None
        sync_manager = None
        realtime_protection = None
        model_updater = None

        # Embedded Backend
        try:
            from core.embedded_backend import EmbeddedBackend
            if config.get_bool('Backend', 'use_embedded', True):
                embedded_backend = EmbeddedBackend(host="127.0.0.1", port=8000)
                if embedded_backend.start():
                    logger.info("Embedded backend started")
                    config.set('Backend', 'url', 'http://127.0.0.1:8000')
                else:
                    logger.warning("Embedded backend failed — offline mode")
                    config.set('Sync', 'enabled', 'false')
        except Exception as e:
            logger.error("Embedded backend error: %s", e)
            config.set('Sync', 'enabled', 'false')

        # Sync Manager (imports requests)
        try:
            if config.is_sync_enabled():
                from core.sync_manager import SyncManager
                sync_manager = SyncManager(
                    backend_url=config.get_backend_url(),
                    sync_interval=config.get_sync_interval(),
                    batch_size=config.get_sync_batch_size()
                )
                if config.is_auto_sync():
                    sync_manager.start()
                    logger.info("Sync manager started")
        except Exception as e:
            logger.error("Sync manager error: %s", e)

        # Real-time Protection (imports onnxruntime via scanner)
        try:
            from core.realtime_protection import RealtimeProtection
            scan_delay = config.get_int('RealtimeProtection', 'scan_delay', 5)
            max_queue = config.get_int('RealtimeProtection', 'max_queue_size', 100)
            realtime_protection = RealtimeProtection(
                scan_delay=scan_delay,
                max_queue_size=max_queue,
                on_malware_detected=_on_malware_detected
            )
            whitelist_ext = config.get('RealtimeProtection', 'whitelist_extensions', '.txt,.log,.md')
            for ext in whitelist_ext.split(','):
                realtime_protection.whitelist_extensions.add(ext.strip())

            realtime_protection.malware_bridge = window.malware_bridge

            if config.get_bool('RealtimeProtection', 'enabled', False):
                realtime_protection.start()
                logger.info("Real-time protection auto-started")
            else:
                logger.info("Real-time protection ready (disabled)")
        except Exception as e:
            logger.error("Real-time protection error: %s", e)

        # Model Updater
        try:
            if config.get_bool('ModelUpdate', 'enabled', True):
                from core.model_updater import ModelUpdater
                model_api_url = config.get('ModelUpdate', 'model_api_url', 'http://localhost:8000')
                model_updater = ModelUpdater(backend_url=model_api_url)
                logger.info("Model updater initialized")
        except Exception as e:
            logger.error("Model updater error: %s", e)

        # Wire managers into window (simple attribute assignments, thread-safe)
        if sync_manager:
            window.sync_manager = sync_manager
        if realtime_protection:
            window.realtime_protection = realtime_protection
            window.initialize_protection()
        if model_updater:
            window.model_updater = model_updater

        # Keep references alive for shutdown
        window._embedded_backend = embedded_backend
        window._sync_manager_ref = sync_manager
        window._realtime_protection_ref = realtime_protection

        logger.info("All services initialized")

    t = threading.Thread(target=_run, daemon=True, name="ServiceInit")
    t.start()
    return t


def main():
    """Configure logging, build the Qt app, show splash, then run the event loop."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )

    try:
        if not ensure_windows_admin():
            return 0
    except RuntimeError as exc:
        logger.error("%s", exc)
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(None, str(exc), "MangoDefend", 0x10)
            except Exception:
                pass
        return 1

    # 1. Qt Application — fast, no heavy imports yet
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("MangoDefend - RMAV Desktop")
    app.setOrganizationName("MangoDefend")

    icon_path = os.path.join(os.path.dirname(__file__), "assets", "mango_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 2. Config — lightweight
    config = get_config()

    # 3. Splash screen — shown immediately, main window appears after
    from ui.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()

    # 4. Build main window (hidden until splash finishes)
    window = ModernWindow()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))

    # 4b. System tray icon
    app.setQuitOnLastWindowClosed(False)
    tray = QSystemTrayIcon(app)
    tray_icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
    tray.setIcon(tray_icon)
    tray.setToolTip("MangoDefend - AI Malware Protection")

    tray_menu = QMenu()
    act_show = QAction("Buka MangoDefend", tray_menu)
    act_quit = QAction("Keluar", tray_menu)
    tray_menu.addAction(act_show)
    tray_menu.addSeparator()
    tray_menu.addAction(act_quit)
    tray.setContextMenu(tray_menu)

    def _tray_activated(reason):
        """Buka kembali window utama ketika user double-click icon tray."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            window.show()
            window.raise_()
            window.activateWindow()

    act_show.triggered.connect(lambda: (window.show(), window.raise_(), window.activateWindow()))
    act_quit.triggered.connect(app.quit)
    tray.activated.connect(_tray_activated)
    tray.show()

    def _on_splash_finished():
        """Show the main window and kick off background service initialization."""
        window.show()
        _init_services(window, config)

    splash.finished.connect(_on_splash_finished)

    # 5. Event loop
    exit_code = app.exec()

    # 6. Shutdown
    logger.info("Shutting down services...")
    if getattr(window, '_embedded_backend', None):
        window._embedded_backend.stop()
    if getattr(window, '_sync_manager_ref', None):
        window._sync_manager_ref.stop()
    if getattr(window, '_realtime_protection_ref', None):
        window._realtime_protection_ref.stop()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
