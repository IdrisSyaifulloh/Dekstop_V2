"""
RMAV Desktop - AI-Powered Malware Detection
Main entry point for the desktop application
"""
import sys
import os
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from ui.modern_window import ModernWindow
from core.sync_manager import SyncManager
from core.config_manager import get_config
from core.realtime_protection import RealtimeProtection
from core.notification_manager import NotificationManager
from core.model_updater import ModelUpdater
from core.embedded_backend import EmbeddedBackend



def on_malware_detected(file_path: str, scan_result: dict):
    """
    Callback function yang dipanggil saat malware terdeteksi oleh real-time protection.
    
    Fungsi ini akan:
    1. Print informasi malware ke console
    2. Menampilkan notifikasi Windows kepada user
    
    Args:
        file_path (str): Path lengkap ke file yang terdeteksi sebagai malware
                        Contoh: "C:\\Downloads\\virus.exe"
        scan_result (dict): Dictionary berisi hasil scan dengan keys:
                           - 'result': "Malware" atau "Benign"
                           - 'confidence': float (0.0-1.0)
                           - 'timestamp': waktu scan
    
    Example:
        >>> on_malware_detected("C:\\Downloads\\virus.exe", {
        ...     "result": "Malware",
        ...     "confidence": 0.95
        ... })
        # Output: Print info + tampilkan notifikasi Windows
    """
    print(f"\n MALWARE DETECTED!")
    print(f"File: {file_path}")
    print(f"Result: {scan_result['result']}")
    
    # Show notification
    try:
        from core.notification_manager import NotificationManager
        notif = NotificationManager()
        notif.show_malware_alert(
            file_path=file_path,
            file_name=os.path.basename(file_path),
            threat_level="High"
        )
    except Exception as e:
        print(f"Failed to show notification: {e}")


def main():
    """
    Entry point utama aplikasi MangoDefend.
    
    Fungsi ini menjalankan seluruh aplikasi dengan urutan:
    1. Inisialisasi Qt Application
    2. Load konfigurasi dari config.ini
    3. Start embedded backend server (AI engine)
    4. Start sync manager (sinkronisasi data ke server)
    5. Start real-time protection (monitoring file system)
    6. Buka main window (UI aplikasi)
    7. Run event loop (tunggu user interaksi)
    8. Cleanup saat aplikasi ditutup
    
    Semua komponen dijalankan secara independen menggunakan threading,
    sehingga aplikasi tetap responsive.
    
    Returns:
        int: Exit code aplikasi (0 = sukses, non-zero = error)
    
    Example:
        >>> if __name__ == "__main__":
        ...     main()
    """
    # ============================================================
    # 1. INISIALISASI QT APPLICATION
    # ============================================================
    # Buat aplikasi Qt - framework untuk UI desktop
    app = QApplication(sys.argv)
    app.setApplicationName("MangoDefend - RMAV Desktop")
    app.setOrganizationName("MangoDefend")
    
    # Set application icon jika ada
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "mango_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # ============================================================
    # 2. LOAD KONFIGURASI
    # ============================================================
    # Load pengaturan dari config.ini (backend URL, timeout, dll)
    config = get_config()
    
    # ============================================================
    # 3. START EMBEDDED BACKEND SERVER
    # ============================================================
    # Backend server adalah "mesin AI" yang melakukan analisis malware
    # Server jalan di localhost (127.0.0.1:8000) - tidak perlu internet
    embedded_backend = None
    if config.get_bool('Backend', 'use_embedded', True):
        try:
            embedded_backend = EmbeddedBackend(host="127.0.0.1", port=8000)
            if embedded_backend.start():
                print(" Server started at http://127.0.0.1:8000")
                # Update config untuk menggunakan embedded backend
                config.set('Backend', 'url', 'http://127.0.0.1:8000')
            else:
                print(" Failed to start embedded backend, running in offline mode")
                config.set('Sync', 'enabled', 'false')
        except Exception as e:
            print(f" Embedded backend error: {e}")
            config.set('Sync', 'enabled', 'false')
    
    # ============================================================
    # 4. START SYNC MANAGER
    # ============================================================
    # Sync manager menyinkronkan hasil scan lokal ke server
    # Seperti Google Drive yang auto-backup data
    sync_manager = None
    if config.is_sync_enabled():
        try:
            sync_manager = SyncManager(
                backend_url=config.get_backend_url(),
                sync_interval=config.get_sync_interval(),
                batch_size=config.get_sync_batch_size()
            )
            
            if config.is_auto_sync():
                sync_manager.start()
                print(f" Sync manager started (backend: {config.get_backend_url()})")
        except Exception as e:
            print(f"Failed to start sync manager: {e}")
    
    # ============================================================
    # 5. START REAL-TIME PROTECTION
    # ============================================================
    # Real-time protection = "satpam 24/7" yang monitor file baru
    # Saat ada file baru dibuat/download, langsung di-scan otomatis
    realtime_protection = None
    if config.get_bool('RealtimeProtection', 'enabled', False):
        try:
            scan_delay = config.get_int('RealtimeProtection', 'scan_delay', 5)
            max_queue = config.get_int('RealtimeProtection', 'max_queue_size', 100)
            
            realtime_protection = RealtimeProtection(
                scan_delay=scan_delay,
                max_queue_size=max_queue,
                on_malware_detected=on_malware_detected
            )
            
            # Add whitelisted extensions (file yang tidak perlu di-scan)
            whitelist_ext = config.get('RealtimeProtection', 'whitelist_extensions', '.txt,.log,.md')
            for ext in whitelist_ext.split(','):
                realtime_protection.whitelist_extensions.add(ext.strip())
            
            realtime_protection.start()
            print(" Real-time protection started")
            
        except Exception as e:
            print(f"Failed to start real-time protection: {e}")
    
    # ============================================================
    # 6. INITIALIZE MODEL UPDATER
    # ============================================================
    # Model updater untuk cek dan download model AI terbaru
    # Seperti update antivirus definition
    model_updater = None
    if config.get_bool('ModelUpdate', 'enabled', True):
        try:
            model_api_url = config.get('ModelUpdate', 'model_api_url', 'http://localhost:8000')
            model_updater = ModelUpdater(backend_url=model_api_url)
            print("Model updater initialized")
        except Exception as e:
            print(f"Failed to initialize model updater: {e}")
    
    # ============================================================
    # 7. CREATE AND SHOW MAIN WINDOW
    # ============================================================
    # Buat tampilan utama aplikasi
    window = ModernWindow()
    
    # Pass managers ke window agar bisa dikontrol dari UI
    if sync_manager:
        window.sync_manager = sync_manager
    if realtime_protection:
        window.realtime_protection = realtime_protection
    if model_updater:
        window.model_updater = model_updater
    
    # Set window icon
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    
    # Tampilkan window
    window.show()

    # ============================================================
    # 8. RUN EVENT LOOP
    # ============================================================
    # Event loop = tunggu user interaksi (klik tombol, dll)
    # Aplikasi akan jalan terus sampai user tutup window
    exit_code = app.exec()
    
    # ============================================================
    # 9. CLEANUP - MATIKAN SEMUA SERVICE
    # ============================================================
    # Saat aplikasi ditutup, matikan semua service dengan aman
    print("\nShutting down services...")
    
    if embedded_backend:
        print("Stopping embedded backend...")
        embedded_backend.stop()
    
    if sync_manager:
        print("Stopping sync manager...")
        sync_manager.stop()
    
    if realtime_protection:
        print("Stopping real-time protection...")
        realtime_protection.stop()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

