"""
Simple Navbar Component
Navbar dengan logo, menu button, dan dark mode toggle
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap


class SimpleNavbar(QWidget):
    """Navbar simple dengan logo"""
    
    # Signals
    menu_clicked = Signal()
    dark_mode_toggled = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(70)
        self.is_dark_mode = False
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(20)
        
        # Menu button (hamburger icon)
        self.menu_btn = QPushButton("☰")
        self.menu_btn.setObjectName("navMenuButton")
        self.menu_btn.setFixedSize(50, 50)
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.clicked.connect(lambda: self.menu_clicked.emit())
        layout.addWidget(self.menu_btn)
        
        # Logo di tengah
        layout.addStretch()
        
        self.logo_label = QLabel()
        self.logo_label.setObjectName("navLogo")
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Load gambar dengan aspect ratio yang benar
        pixmap = QPixmap("assets/mango_icon.png")
        
        # Pakai scaled() dengan KeepAspectRatio supaya gak kepotong
        scaled_pixmap = pixmap.scaled(
            230, 60,  # width, height maksimal
            Qt.AspectRatioMode.KeepAspectRatio,  # jaga proporsi
            Qt.TransformationMode.SmoothTransformation  # smooth scaling
        )
        self.logo_label.setPixmap(scaled_pixmap)
        
        layout.addWidget(self.logo_label)
        layout.addStretch()
        
        # Dark mode toggle button (kanan)
        self.dark_mode_btn = QPushButton("🌙")
        self.dark_mode_btn.setObjectName("navDarkButton")
        self.dark_mode_btn.setFixedSize(50, 50)
        self.dark_mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dark_mode_btn.clicked.connect(self.toggle_dark_mode)
        layout.addWidget(self.dark_mode_btn)
        
        self.apply_style()
    
    def toggle_dark_mode(self):
        """Toggle dark mode dan emit signal"""
        self.is_dark_mode = not self.is_dark_mode
        
        if self.is_dark_mode:
            self.dark_mode_btn.setText("☀️")
        else:
            self.dark_mode_btn.setText("🌙")
        
        self.apply_style(self.is_dark_mode)
        self.dark_mode_toggled.emit(self.is_dark_mode)
    
    def apply_style(self, is_dark=False):
        """Apply navbar style"""
        self.is_dark_mode = is_dark
        
        if is_dark:
            self.setStyleSheet("""
                QWidget {
                    background: rgba(30, 30, 30, 0.95);
                }
                QLabel#navLogo {
                    background: transparent;
                    border: none;
                }
                QPushButton#navMenuButton, QPushButton#navDarkButton {
                    background: rgba(50, 50, 50, 0.8);
                    border: 2px solid #FFA500;
                    border-radius: 25px;
                    color: #FFA500;
                    font-size: 22px;
                    font-weight: bold;
                }
                QPushButton#navMenuButton:hover, QPushButton#navDarkButton:hover {
                    background: rgba(255, 165, 0, 0.3);
                    border: 2px solid #FFB732;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background: rgba(255, 255, 255, 0.95);
                }
                QLabel#navLogo {
                    background: transparent;
                    border: none;
                }
                QPushButton#navMenuButton, QPushButton#navDarkButton {
                    background: rgba(255, 250, 240, 0.8);
                    border: 2px solid #FF8C00;
                    border-radius: 25px;
                    color: #FF8C00;
                    font-size: 22px;
                    font-weight: bold;
                }
                QPushButton#navMenuButton:hover, QPushButton#navDarkButton:hover {
                    background: rgba(255, 140, 0, 0.2);
                    border: 2px solid #FFA500;
                }
            """)
