from PySide6.QtWidgets import (
    QMenuBar, QMainWindow, QMenu, QWidget, QVBoxLayout, QScrollArea,
    QSplitter, QFileDialog, QMessageBox, QStackedWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from app.views.components.test_selection_panel import TestSelectionPanel
from app.views.components.data_payload_panel import DataPayloadPanel
from app.views.components.status_panel import StatusPanel
from app.views.components.graph_panel import GraphPanel
from app.views.components.uart_monitor_panel import LiveMonitorPanel
from app.views.components.transmit_table import TransmitTable
from app.controllers.main_controller import MainController
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UART Protocol Testing Application")
        self.setGeometry(100, 100, 1200, 800)
        self.graph_window = None
        self.setStyleSheet(self.load_uart_stylesheet())

        # Central scrollable layout
        central_widget = QWidget()
        central_layout = QVBoxLayout()
        central_widget.setLayout(central_layout)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(central_widget)
        self.setCentralWidget(scroll_area)

        # Components
        self.test_selection = TestSelectionPanel(controller=None)
        self.payload_panel = DataPayloadPanel()
        self.transmit_table = TransmitTable()
        self.status_panel = StatusPanel()
        self.live_monitor = LiveMonitorPanel(self)

        # Right side layout: DataPayloadPanel over TransmitTable
        right_container = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.payload_panel)
        right_layout.addWidget(self.transmit_table)
        right_container.setLayout(right_layout)

        # Top splitter: Test Panel | Payload + Table | Status
        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.addWidget(self.test_selection)
        top_splitter.addWidget(right_container)
        top_splitter.addWidget(self.status_panel)
        top_splitter.setStretchFactor(0, 2)
        top_splitter.setStretchFactor(1, 4)
        top_splitter.setStretchFactor(2, 2)

        # Full layout: Top splitter + Live monitor
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self.live_monitor)
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 1)

        central_layout.addWidget(main_splitter)

        # Controller
        self.controller = MainController(self)
        self.test_selection.controller = self.controller

        # Menubar and toolbar
        self._setup_menubar()
        self._setup_toolbar()
        self.statusBar()

    def load_uart_stylesheet(self):
        path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'styles', 'uart_style.qss')
        try:
            with open(path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Warning: Stylesheet not found at {path}")
            return ""

    def _setup_menubar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        file_menu = QMenu("File", self)
        save_action = QAction("Save Config", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self.save_config)

        load_action = QAction("Load Config", self)
        load_action.setShortcut(QKeySequence("Ctrl+L"))
        load_action.triggered.connect(self.load_config)

        clear_action = QAction("Clear Fields", self)
        clear_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        clear_action.triggered.connect(self.clear_fields)

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)

        file_menu.addAction(save_action)
        file_menu.addAction(load_action)
        file_menu.addAction(clear_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        view_menu = QMenu("View", self)
        toolbar_action = QAction("Toggle Toolbar", self, checkable=True)
        toolbar_action.setShortcut(QKeySequence("Ctrl+T"))
        toolbar_action.setChecked(True)
        toolbar_action.triggered.connect(self.toggle_toolbar)
        view_menu.addAction(toolbar_action)

        graphs_menu = QMenu("Graphs", self)
        open_graph_action = QAction("Open Graph Window", self)
        open_graph_action.setShortcut(QKeySequence("Ctrl+G"))
        open_graph_action.triggered.connect(self.open_graph_window)
        graphs_menu.addAction(open_graph_action)

        report_menu = QMenu("Report", self)
        generate_report_action = QAction("Generate Report", self)
        generate_report_action.setShortcut(QKeySequence("Ctrl+R"))
        report_menu.addAction(generate_report_action)

        help_menu = QMenu("Help", self)
        about_action = QAction("About", self)
        about_action.setShortcut(QKeySequence("Ctrl+H"))
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        menu_bar.addMenu(file_menu)
        menu_bar.addMenu(view_menu)
        menu_bar.addMenu(graphs_menu)
        menu_bar.addMenu(report_menu)
        menu_bar.addMenu(help_menu)

    def open_graph_window(self):
        if self.graph_window is None or not self.graph_window.isVisible():
            self.graph_window = GraphPanel()
            self.graph_window.show()
        else:
            self.graph_window.raise_()
            self.graph_window.activateWindow()

    def save_config(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Configuration", "", "JSON Files (*.json)")
        if path:
            self.controller.save_config(path)

    def load_config(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Configuration", "", "JSON Files (*.json)")
        if path:
            self.controller.load_config(path)

    def clear_fields(self):
        self.controller.clear_config()
        QMessageBox.information(self, "Cleared", "All fields have been cleared.")

    def show_about(self):
        QMessageBox.information(self, "About", "UART Protocol Testing\nVersion 1.0")

    def toggle_toolbar(self, state):
        if state:
            self.toolbar.show()
        else:
            self.toolbar.hide()

    def _setup_toolbar(self):
        self.toolbar = self.addToolBar("Main Toolbar")
        self.toolbar.setMovable(True)
        self.toolbar.setFloatable(True)

        save_icon = QIcon.fromTheme("document-save")
        save_action = QAction(save_icon, "Save Config", self)
        save_action.setToolTip("Save configuration (Ctrl+S)")
        save_action.triggered.connect(self.save_config)

        load_icon = QIcon.fromTheme("document-open")
        load_action = QAction(load_icon, "Load Config", self)
        load_action.setToolTip("Load configuration (Ctrl+L)")
        load_action.triggered.connect(self.load_config)

        clear_icon = QIcon.fromTheme("edit-delete")
        clear_action = QAction(clear_icon, "Clear Fields", self)
        clear_action.setToolTip("Clear all fields (Ctrl+Shift+C)")
        clear_action.triggered.connect(self.clear_fields)

        graph_icon = QIcon.fromTheme("window-new")
        graph_action = QAction(graph_icon, "Open Graph", self)
        graph_action.setToolTip("Open Graph Window")
        graph_action.triggered.connect(self.open_graph_window)

        report_icon = QIcon.fromTheme("document-print")
        report_action = QAction(report_icon, "Generate Report", self)
        report_action.setToolTip("Generate Report")

        exit_icon = QIcon.fromTheme("application-exit")
        exit_action = QAction(exit_icon, "Exit", self)
        exit_action.setToolTip("Exit application (Ctrl+Q)")
        exit_action.triggered.connect(self.close)

        self.toolbar.addAction(save_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(load_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(clear_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(graph_action)
        self.toolbar.addAction(report_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(exit_action)