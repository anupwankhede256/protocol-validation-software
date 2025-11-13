# app/views/components/test_selection_panel.py (original)
from PySide6.QtWidgets import (
    QGroupBox, QFormLayout, QComboBox, QLineEdit, QPushButton, QLabel, QVBoxLayout
)
from PySide6.QtCore import Qt
import logging
logger = logging.getLogger(__name__)

class TestSelectionPanel(QGroupBox):
    def __init__(self, controller=None):
        super().__init__("TEST SELECTION && CONFIGURATION")
        self.setMinimumWidth(315)
        self.setMaximumHeight(450)
        self.controller = controller
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        # self.baud_rate_label = QLabel("Baud Rate:")  # This was added later, causing error
        # self.baud_rate_layout.addWidget(self.baud_rate_label)  # Error line
        # self.baud_rate_layout.addWidget(self.baud_rate)  # Error line

        # --- Test Type Selection Group ---
        test_type_group = QGroupBox("")
        test_type_group.setMaximumHeight(80)
        test_type_layout = QVBoxLayout()
        test_type_layout.setContentsMargins(5, 5, 5, 5)
        test_type_layout.setSpacing(6)
        test_type_group.setLayout(test_type_layout)

        self.test_name = QComboBox()
        self.test_name.setObjectName("TestNameField")
        self.test_name.addItems([
            "RECEPTION TEST",
            "TRANSMISSION TEST",
            "LOOPBACK TEST",
            "BAUD RATE TESTING",
            "RTS/CTS HARDWARE FLOW TEST",
            "PARITY DETECTION",
            "OVERRUN DETECTION",
            "BREAK CHARACTER CONFIGURATION",
            "AUTO BAUD RATE DETECTION"
        ])
        test_type_label = QLabel("TEST NAME:")
        test_type_label.setStyleSheet("color: black; font-weight: bold; background-color: #00BFFF; padding: 2px; border-radius: 5px; font-size: 12px;")
        test_type_layout.addWidget(test_type_label)
        test_type_layout.addWidget(self.test_name)
        main_layout.addWidget(test_type_group)

        # --- Configuration Group ---
        config_group = QGroupBox("CONFIGURATION PARAMETERS")
        config_layout = QFormLayout()
        config_layout.setHorizontalSpacing(15)
        config_layout.setVerticalSpacing(15)
        config_layout.setContentsMargins(10, 15, 10, 15)
        config_group.setLayout(config_layout)

        self.device_id = QLineEdit()
        self.device_id.setObjectName("Device ID")
        config_layout.addRow(QLabel("DEVICE ID:"), self.device_id)

        self.baud_rate = QComboBox()
        self.baud_rate.setEditable(True)
        self.baud_rate.addItems([
            "300", "600", "1200", "2400", "4800", "9600", "14400",
            "19200", "38400", "57600", "115200"
        ])
        self.baud_rate.setCurrentText("115200")
        config_layout.addRow(QLabel("BAUD RATE:"), self.baud_rate)

        self.data_bits = QComboBox()
        self.data_bits.addItems(["7", "8", "9"])
        self.data_bits.setCurrentIndex(1)
        config_layout.addRow(QLabel("DATA BITS:"), self.data_bits)

        self.parity = QComboBox()
        self.parity.addItems(["None", "Even", "Odd"])
        config_layout.addRow(QLabel("PARITY:"), self.parity)

        self.stop_bits = QComboBox()
        self.stop_bits.addItems(["0.5", "1", "1.5", "2"])
        self.stop_bits.setCurrentIndex(1)
        config_layout.addRow(QLabel("STOP BITS:"), self.stop_bits)

        self.data_shift = QComboBox()
        self.data_shift.addItems(["MSB First", "LSB First"])
        config_layout.addRow(QLabel("DATA SHIFT:"), self.data_shift)

        self.handshake = QComboBox()
        self.handshake.addItems(["OFF", "RTS/CTS", "Xon/Xoff"])
        config_layout.addRow(QLabel("HANDSHAKE:"), self.handshake)

        self.add_config_btn = QPushButton("ADD CONFIG")
        config_layout.addRow(self.add_config_btn)

        main_layout.addWidget(config_group)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(20)

        self.__connect_signals__()

    def __connect_signals__(self):
        if self.controller:
            self.add_config_btn.clicked.connect(self.controller._on_add_config)
        self.test_name.currentTextChanged.connect(self.on_test_name_changed)

    def on_test_name_changed(self, test_name):
        """Handle test name selection changes."""
        logger.debug(f"Test name changed to: {test_name}")
        
        # Update the controller's test case change handler
        if hasattr(self, 'controller') and self.controller:
            self.controller._on_test_case_changed(test_name)