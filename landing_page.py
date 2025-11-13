import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QStackedLayout, QFrame,
    QGridLayout, QStatusBar, QSizePolicy
)
from PySide6.QtGui import QFont, QAction, QIcon, QPixmap
from PySide6.QtCore import Qt, QPropertyAnimation, QTimer
from app.views.main_window import MainWindow
from app.views.i2c_main_window import I2CWindow
import os

class FirstPage(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IoT Sandbox")
        self.setFixedSize(900, 600)

        # Status bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        # Initialize state
        self.sidebar_visible = True
        self.tabs = ["  Home", "  Videos", "  Documentation", "  Contact"]
        self.protocol_buttons = []

        # Main wrapper
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setMaximumWidth(200)
        self.sidebar.setMinimumWidth(200)
        self.sidebar_min_collapsed = 0
        self.sidebar.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #F9F6EE, stop:1 #FFFFFF);
        """)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setAlignment(Qt.AlignTop)
        side_layout.setContentsMargins(10, 10, 10, 10)
        side_layout.setSpacing(15)

        # Logo
        logo = QLabel()
        pix = QPixmap(self.resource_path("assets/icons/code-sandbox-svgrepo-com.svg"))
        if not pix.isNull():
            logo.setPixmap(pix.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        side_layout.addWidget(logo, alignment=Qt.AlignCenter)

        # Toggle shortcut
        toggle = QAction("Toggle Sidebar", self)
        toggle.setShortcut("Ctrl+S")
        toggle.triggered.connect(self.toggle_sidebar)
        self.addAction(toggle)

        # Tab buttons
        icons = [
            self.resource_path("assets/icons/home.png"),
            self.resource_path("assets/icons/videos.png"),
            self.resource_path("assets/icons/document.png"),
            self.resource_path("assets/icons/contacts.png")
        ]
        for name, ico in zip(self.tabs, icons):
            btn = QPushButton(name)
            btn.setIcon(QIcon(ico))
            btn.setStyleSheet("""
                QPushButton {
                    background: #FFF;
                    color: #333;
                    font-weight: bold;
                    text-align: left;
                    padding: 8px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background: #EEE;
                }
            """)
            btn.clicked.connect(lambda _, n=name: self.switch_page(n))
            side_layout.addWidget(btn)

        # Content (QStackedLayout)
        self.content_frame = QFrame()
        self.stack = QStackedLayout(self.content_frame)

        # Create pages
        self.home_page = self.create_home_page()
        self.edit_page = self.create_placeholder("Video tutorials Coming Soon…")
        self.view_page = self.create_placeholder("Documentation Coming Soon…")
        self.help_page = self.create_placeholder("Contact Coming Soon…")

        for w in (self.home_page, self.edit_page, self.view_page, self.help_page):
            self.stack.addWidget(w)

        self.stack.setCurrentIndex(0)

        # Assemble main layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_frame, 1)

    def create_home_page(self) -> QWidget:
        page = QWidget()
        gl = QGridLayout(page)
        gl.setContentsMargins(20, 20, 20, 20)
        gl.setSpacing(20)

        lbl = QLabel("Choose Protocol")
        lbl.setFont(QFont("Arial", 18, QFont.Bold))
        gl.addWidget(lbl, 0, 0, 1, 2)

        protocols = ["UART", "CAN", "SPI", "I2C", "LIN", "USB"]
        colors = ["#ADD8E6", "#cbefff", "#cbefff", "#ADD8E6", "#ADD8E6", "#cbefff"]
        hover_colors = ["#9CC7D5", "#B8DCEB", "#B8DCEB", "#9CC7D5", "#9CC7D5", "#B8DCEB"]
        press_colors = ["#8AB6C4", "#A5C9D8", "#A5C9D8", "#8AB6C4", "#8AB6C4", "#A5C9D8"]

        for i, prot in enumerate(protocols):
            btn = QPushButton(prot)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {colors[i]};
                    font-size: 18px;
                    font-weight: bold;
                    border-radius: 30px;
                    padding: 10px;
                }}
                QPushButton:hover {{
                    background: {hover_colors[i]};
                }}
                QPushButton:pressed {{
                    background: {press_colors[i]};
                }}
            """)
            btn.clicked.connect(lambda _, p=prot: self.protocol_selected(p))
            row, col = (i // 2) + 1, i % 2
            gl.addWidget(btn, row, col)
            self.protocol_buttons.append(btn)

        self.status_label = QLabel("No Protocol Selected")
        self.status_label.setStyleSheet("color: #666; font-size: 14px;")
        gl.addWidget(self.status_label, 4, 0, 1, 2, alignment=Qt.AlignCenter)

        return page

    def create_placeholder(self, text: str) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        lbl = QLabel(text)
        lbl.setFont(QFont("Arial", 16))
        lbl.setAlignment(Qt.AlignCenter)
        v.addStretch()
        v.addWidget(lbl)
        v.addStretch()
        return page

    def switch_page(self, name: str):
        idx = {n: i for i, n in enumerate(self.tabs)}.get(name, 0)
        self.stack.setCurrentIndex(idx)
        self.status_bar.showMessage(f"{name} clicked", 2000)

    def protocol_selected(self, proto: str):
        self.status_label.setText(f"Protocol Selected: {proto}")
        self.status_bar.showMessage(f"{proto} selected", 2000)
        if proto == "UART":
            self.open_uart_window()
        elif proto == "I2C":
            self.open_i2c_window()

    def toggle_sidebar(self):
        self.sidebar_visible = not self.sidebar_visible

        if self.sidebar_visible:
            self.sidebar.setMinimumWidth(200)
            start, end = 0, 200
        else:
            self.sidebar.setMinimumWidth(0)
            start, end = 200, 0

        anim = QPropertyAnimation(self.sidebar, b"maximumWidth", self)
        anim.setDuration(200)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.start()

        QTimer.singleShot(210, self._force_resize)
        self.status_bar.showMessage("Sidebar toggled", 1500)

    def _force_resize(self):
        self.resize(self.width() + 1, self.height())
        self.resize(self.width() - 1, self.height())

    @staticmethod
    def resource_path(relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', relative_path)))

    def open_uart_window(self):
        """Open the UART Window."""
        self.main_window = MainWindow()
        self.main_window.show()

    def open_i2c_window(self):
        """Open the I2C Window."""
        self.i2c_window = I2CWindow()
        self.i2c_window.show()