"""
Dashboard View - System Overview
Main dashboard showing protection status, stats, and activity
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt, QTimer
from ui.widgets.glass_card import GlassCard
from ui.widgets.progress_ring import ProgressRing
from ui.styles.figma_theme import Colors, Typography
from datetime import datetime
import psutil


class DashboardView(QWidget):
    """
    Dashboard tab view with modern design.
    
    Displays:
    - Protection status with progress ring
    - Live stats (threats, scanned, last scan)
    - Resource usage (CPU, RAM)
    - Recent activity feed
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dark = True
        self.realtime_enabled = True
        self.last_scan = datetime.now()
        self.threats_detected = 0
        
        # Live resource update timer
        self._resource_timer = QTimer(self)
        self._resource_timer.timeout.connect(self._update_resources)
        self._resource_timer.setInterval(3000)
        self._resource_timer.start()
        
        self.setup_ui()
    
    def setup_ui(self):
        """Build dashboard UI"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        scroll.setWidget(content)
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 32)
        layout.setSpacing(24)
        
        # ===== GRID LAYOUT (Bento Style) =====
        grid = QGridLayout()
        grid.setSpacing(24)
        
        # Main Protection Card (Large - spans 2 rows, 2 cols)
        protection_card = self._create_protection_card()
        grid.addWidget(protection_card, 0, 0, 2, 2)
        
        # Threats Blocked Card (top right)
        threats_card = self._create_threats_card()
        grid.addWidget(threats_card, 0, 2, 1, 1)
        
        # Last Scan Card (bottom right)
        last_scan_card = self._create_last_scan_card()
        grid.addWidget(last_scan_card, 1, 2, 1, 1)
        
        layout.addLayout(grid)
        
        # ===== RESOURCE USAGE =====
        resource_row = QHBoxLayout()
        resource_row.setSpacing(12)
        
        resources = [
            ("CPU Usage", "2.3%"),
            ( "Memory", "128MB"),
            ("Database", "342MB")
        ]
        
        self._resource_labels = {}
        for label, value in resources:
            res_card = QFrame()
            res_card.setStyleSheet(f"""
                QFrame {{
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 12px;
                    padding: 12px;
                }}
            """)
            
            res_layout = QVBoxLayout(res_card)
            res_layout.setSpacing(4)
            
            name = QLabel(label)
            name.setStyleSheet(f"color: {Colors.DARK_TEXT_MUTED}; font-size: 11px; background: transparent;")
            res_layout.addWidget(name)
            
            val = QLabel(value)
            val.setStyleSheet(f"color: white; font-size: 16px; font-weight: bold; background: transparent;")
            res_layout.addWidget(val)
            
            self._resource_labels[label] = val
            resource_row.addWidget(res_card)
        
        layout.addLayout(resource_row)
        
        # ===== RECENT ACTIVITY SECTION =====
        activity_section = self._create_activity_section()
        layout.addWidget(activity_section)
        
        layout.addStretch()
        
        # Set main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
        self._update_resources()
    
    def _create_protection_card(self) -> GlassCard:
        """Create main protection status card"""
        card = GlassCard()
        card.setMinimumHeight(400)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        
        title_container = QWidget()
        title_container.setStyleSheet("background: transparent;")
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)
        
        title = QLabel("System Protection")
        title.setStyleSheet(f"color: white; font-size: 24px; font-weight: bold; background: transparent;")
        title_layout.addWidget(title)
        
        header.addWidget(title_container)
        header.addStretch()
        
        # Active badge
        badge = QLabel("ACTIVE")
        badge.setStyleSheet(f"""
            background: rgba(50, 205, 50, 0.2);
            color: {Colors.GREEN_500};
            border: none;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 11px;
            font-weight: bold;
            background: rgba(50, 205, 50, 0.1);
                border: none;
                border-radius: 8px;
        """)
        header.addWidget(badge)
        
        layout.addLayout(header)
        
        # Progress ring + status bars
        center_section = QHBoxLayout()
        center_section.setSpacing(48)
        
        # Progress ring
        self.progress_ring = ProgressRing(diameter=140, line_width=12)
        self.progress_ring.set_progress(1.0, animate=True)
        center_section.addWidget(self.progress_ring)
        
        # Status bars
        status_container = QWidget()
        status_container.setStyleSheet("background: transparent;")
        status_layout = QVBoxLayout(status_container)
        status_layout.setSpacing(16)
        
        statuses = [
            ("Real-time Scanning", "Active", 1.0),
            ("Behavioral Analysis", "Active", 0.98),
            ("Cloud Protection", "Active", 1.0)
        ]
        
        for label_text, status_text, progress in statuses:
            row = QVBoxLayout()
            row.setSpacing(8)
            
            # Label row
            label_row = QHBoxLayout()
            label = QLabel(label_text)
            label.setStyleSheet(f"color: {Colors.DARK_TEXT_SECONDARY}; font-size: 13px; background: transparent;")
            label_row.addWidget(label)
            label_row.addStretch()
            
            status = QLabel(status_text)
            status.setStyleSheet(f"color: {Colors.GREEN_500}; font-size: 12px; font-weight: bold; background: transparent;")
            label_row.addWidget(status)
            row.addLayout(label_row)
            
            # Progress bar
            bar_bg = QFrame()
            bar_bg.setFixedHeight(8)
            bar_bg.setStyleSheet("background: rgba(0, 0, 0, 0.3); border-radius: 4px;")
            
            bar = QFrame(bar_bg)
            bar.setGeometry(0, 0, int(300 * progress), 8)
            bar.setStyleSheet(f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.GREEN_500}, stop:1 {Colors.EMERALD_500});
                border-radius: 4px;
            """)
            row.addWidget(bar_bg)
            
            status_layout.addLayout(row)
        
        center_section.addWidget(status_container, 1)
        layout.addLayout(center_section)
        
        return card
    
    def _create_threats_card(self) -> GlassCard:
        """Create threats blocked statistic card"""
        card = GlassCard()
        card.setMinimumHeight(200)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        
        # Label
        label = QLabel("Threats Blocked")
        label.setStyleSheet(f"color: {Colors.DARK_TEXT_SECONDARY}; font-size: 13px; background: transparent;")
        layout.addWidget(label)
        
        # Value
        self.threats_value = QLabel("0")
        self.threats_value.setStyleSheet(f"""
            color: {Colors.ORANGE_500};
            font-size: 42px;
            font-weight: bold;
            background: transparent;
        """)
        layout.addWidget(self.threats_value)
        
        # Success rate
        rate = QLabel("100% success rate")
        rate.setStyleSheet(f"color: {Colors.GREEN_500}; font-size: 12px; background: transparent;")
        layout.addWidget(rate)
        
        layout.addStretch()
        
        return card
    
    def _create_last_scan_card(self) -> GlassCard:
        """Create last scan timestamp card"""
        card = GlassCard()
        card.setMinimumHeight(190)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        
        # Label
        label = QLabel("Last Scan")
        label.setStyleSheet(f"color: {Colors.DARK_TEXT_SECONDARY}; font-size: 13px; background: transparent;")
        layout.addWidget(label)
        
        # Time
        self.last_scan_time = QLabel(self.last_scan.strftime("%H:%M"))
        self.last_scan_time.setStyleSheet(f"color: white; font-size: 28px; font-weight: bold; background: transparent;")
        layout.addWidget(self.last_scan_time)
        
        # Status
        status_badge = QFrame()
        status_badge.setStyleSheet(f"""
            QFrame {{
                background: rgba(50, 205, 50, 0.1);
                border: none;
                border-radius: 8px;
            }}
        """)
        
        status_layout = QHBoxLayout(status_badge)
        status_layout.setContentsMargins(8, 6, 8, 6)
        status_layout.setSpacing(6)
        
        
        text = QLabel("No threats found")
        text.setStyleSheet(f"color: {Colors.GREEN_500}; font-size: 11px; font-weight: 600; background: transparent;")
        status_layout.addWidget(text)
        
        layout.addWidget(status_badge)
        layout.addStretch()
        
        return card
    
    def _create_activity_section(self) -> GlassCard:
        """Create recent activity feed"""
        card = GlassCard()
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("Recent Activity")
        title.setStyleSheet(f"color: white; font-size: 20px; font-weight: bold; background: transparent;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Live badge
        live_badge = QFrame()
        live_badge.setStyleSheet(f"""
            QFrame {{
                background: rgba(50, 205, 50, 0.1);
                border: none;
                border-radius: 12px;
            }}
        """)
        
        live_layout = QHBoxLayout(live_badge)
        live_layout.setContentsMargins(10, 4, 10, 4)
        live_layout.setSpacing(6)
        
        live_text = QLabel("Live")
        live_text.setStyleSheet(f"color: {Colors.GREEN_500}; font-size: 11px; font-weight: bold; background: transparent;")
        live_layout.addWidget(live_text)
        
        header.addWidget(live_badge)
        layout.addLayout(header)
        
        # Activity items
        activities = [
            ("2 min ago", "Real-time scan completed", Colors.GREEN_500),
            ("15 min ago", "System scan finished",  Colors.GREEN_500),
            ("1 hour ago", "Database updated", Colors.ORANGE_500),
            ("3 hours ago", "Threat quarantined", Colors.RED_500)
        ]
        
        activity_grid = QGridLayout()
        activity_grid.setSpacing(16)
        activity_grid.setColumnStretch(0, 1)
        activity_grid.setColumnStretch(1, 1)
        
        for idx, (time_text, action, color) in enumerate(activities):
            row = idx // 2
            col = idx % 2
            
            item = QFrame()
            item.setStyleSheet(f"""
                QFrame {{
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                    padding: 16px;
                }}
                QFrame:hover {{
                    border: 1px solid rgba(255, 165, 0, 0.3);
                }}
            """)
            
            item_layout = QHBoxLayout(item)
            item_layout.setSpacing(12)
            
            # Text
            text_container = QWidget()
            text_container.setStyleSheet("background: transparent;")
            text_layout = QVBoxLayout(text_container)
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(4)
            
            action_label = QLabel(action)
            action_label.setStyleSheet(f"color: white; font-size: 13px; font-weight: 600; background: transparent;")
            text_layout.addWidget(action_label)
            
            time_label = QLabel(time_text)
            time_label.setStyleSheet(f"color: {Colors.DARK_TEXT_MUTED}; font-size: 11px; background: transparent;")
            text_layout.addWidget(time_label)
            
            item_layout.addWidget(text_container, 1)
            
            activity_grid.addWidget(item, row, col)
        
        layout.addLayout(activity_grid)
        
        return card
    
    def _update_resources(self):
        """Update live resource usage."""
        try:
            cpu = psutil.cpu_percent(interval=0)
            if "CPU Usage" in self._resource_labels:
                self._resource_labels["CPU Usage"].setText(f"{cpu:.1f}%")
            
            proc = psutil.Process()
            mem_mb = proc.memory_info().rss / (1024 * 1024)
            if "Memory" in self._resource_labels:
                self._resource_labels["Memory"].setText(f"{mem_mb:.0f}MB")
        except Exception:
            pass
    
    def update_threats(self, count: int):
        """Update threats detected counter"""
        self.threats_detected = count
        if hasattr(self, 'threats_value'):
            self.threats_value.setText(str(count))
    
    def update_threats_count(self, count: int):
        """Alias for update_threats"""
        self.update_threats(count)
    
    def update_last_scan(self, scan_time: datetime):
        """Update last scan timestamp"""
        self.last_scan = scan_time
        if hasattr(self, 'last_scan_time'):
            self.last_scan_time.setText(scan_time.strftime("%H:%M"))
    
    def set_theme(self, is_dark: bool):
        """Update theme"""
        self.is_dark = is_dark
