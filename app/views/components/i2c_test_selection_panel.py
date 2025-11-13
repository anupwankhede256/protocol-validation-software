from PySide6.QtWidgets import (
    QGroupBox, QFormLayout, QComboBox, QLineEdit, QPushButton, QLabel, QVBoxLayout
)
from PySide6.QtGui import QRegularExpressionValidator, QFont
from PySide6.QtCore import Qt, QRegularExpression

class I2CTestSelectionPanel(QGroupBox):
    def __init__(self, controller=None):
        super().__init__("TEST SELECTION && CONFIGURATION")
        self.setMinimumWidth(315)
        self.setMaximumHeight(450)
        self.controller = controller

        # Highlight heading: larger font, bold, color
        # self.setStyleSheet("""
        #     QGroupBox {
        #         font-size: 18px;
        #         font-weight: bold;
        #         color: #234078;
        #         border: 2px solid #234078;
        #         margin-top: 10px;
        #     }
        #     QGroupBox::title {
        #         subcontrol-origin: margin;
        #         left: 8px;
        #         top: 2px;
        #         padding: 2px 12px 2px 12px;
        #     }
        # """)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        self.__init_ui__(main_layout)
        self.__connect_signals__()

    def __init_ui__(self, main_layout):
        form = QFormLayout()
        main_layout.addLayout(form)

        # Larger unified font for labels/inputs
        label_font = QFont()
        label_font.setPointSize(13)
        label_font.setBold(True)
        input_font = QFont()
        input_font.setPointSize(13)

        def style_label_input(label, widget):
            label.setFont(label_font)
            widget.setFont(input_font)
            widget.setStyleSheet("min-height: 32px;")

        # MODE
        self.mode = QComboBox()
        self.mode.addItems(["Master", "Slave"])
        mode_label = QLabel("MODE:")
        style_label_input(mode_label, self.mode)
        form.addRow(mode_label, self.mode)

        # SPEED MODE
        self.speed_mode_label = QLabel("SPEED MODE:")
        self.speed_mode = QComboBox()
        self.speed_mode.addItems([
            "Standard (100 kHz)", "Fast (400 kHz)", "Fast Plus (1 MHz)",
            "High-Speed (3.4 MHz)", "Ultra-Fast (5 MHz)"
        ])
        style_label_input(self.speed_mode_label, self.speed_mode)
        form.addRow(self.speed_mode_label, self.speed_mode)

        # TEST CASE
        self.test_case = QComboBox()
        self.test_case.addItems([
            "Read Test", "Write Test", "Repeated Start Test", "Addressing Test",
            "Clock Stretching Test", "ACK/NACK Detection Test", "Bus Arbitration Test",
            "General Call Test", "Device ID Test", "Timeout Detection Test", "Noise Detection Test"
        ])
        test_case_label = QLabel("TEST CASE:")
        style_label_input(test_case_label, self.test_case)
        form.addRow(test_case_label, self.test_case)

        # ADDRESS MODE
        self.address_mode = QComboBox()
        self.address_mode.addItems(["7-bit", "10-bit"])
        address_mode_label = QLabel("ADDRESS MODE:")
        style_label_input(address_mode_label, self.address_mode)
        form.addRow(address_mode_label, self.address_mode)

        # DEVICE ADDRESS
        self.device_address = QLineEdit()
        self.device_address.setPlaceholderText("Enter address (0x00 to 0xFF)")
        self.device_address.setMaxLength(4)
        device_address_label = QLabel("DEVICE ADDRESS:")
        style_label_input(device_address_label, self.device_address)
        form.addRow(device_address_label, self.device_address)

        # FRAME FORMAT
        self.frame_format = QComboBox()
        self.frame_format.addItems(["MSB First", "LSB First"])
        frame_format_label = QLabel("FRAME FORMAT:")
        style_label_input(frame_format_label, self.frame_format)
        form.addRow(frame_format_label, self.frame_format)

        # READ/WRITE ADDRESS
        self.read_address_label = QLabel("READ ADDRESS:")
        self.read_address = QLineEdit()
        self.read_address.setPlaceholderText("Read Address (0x00 to 0xFF)")
        self.write_address_label = QLabel("WRITE ADDRESS:")
        self.write_address = QLineEdit()
        self.write_address.setPlaceholderText("Write Address (0x00 to 0xFF)")
        hex_validator = QRegularExpressionValidator(QRegularExpression(r"^0x[0-9A-Fa-f]{0,2}$"))
        self.read_address.setValidator(hex_validator)
        self.write_address.setValidator(hex_validator)
        self.read_address.setMaxLength(4)
        self.write_address.setMaxLength(4)
        style_label_input(self.read_address_label, self.read_address)
        style_label_input(self.write_address_label, self.write_address)
        form.addRow(self.read_address_label, self.read_address)
        form.addRow(self.write_address_label, self.write_address)

        # CLOCK STRETCH
        self.clock_stretch_label = QLabel("CLOCK STRETCH:")
        self.clock_stretch = QComboBox()
        self.clock_stretch.addItems(["Enabled", "Disabled"])
        style_label_input(self.clock_stretch_label, self.clock_stretch)
        form.addRow(self.clock_stretch_label, self.clock_stretch)

        # ADD CONFIG Button
        self.add_config_btn = QPushButton("ADD CONFIG")
        self.add_config_btn.setFont(QFont("", 13,QFont.Bold))
        self.add_config_btn.setStyleSheet("min-height: 20px;")
        form.addRow(self.add_config_btn)

        form.setContentsMargins(10, 10, 10, 10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(20)

        self.update_for_mode(self.mode.currentText())
        self.update_address_validator()

    def __connect_signals__(self):
        if self.controller:
            self.add_config_btn.clicked.connect(self.controller._on_add_config)
            # Notify controller of test case changes
            self.test_case.currentTextChanged.connect(self.controller.on_test_case_changed)  # New connection
        self.mode.currentTextChanged.connect(self.update_for_mode)
        self.address_mode.currentTextChanged.connect(self.update_address_validator)
        self.address_mode.currentTextChanged.connect(self.validate_device_address)
        self.test_case.currentTextChanged.connect(self.validate_device_address)
        self.device_address.editingFinished.connect(self.validate_device_address)
        self.read_address.editingFinished.connect(self.update_register_address)
        self.write_address.editingFinished.connect(self.update_register_address)
        
    def update_for_mode(self, mode: str):
        is_master = (mode == "Master")
        self.speed_mode_label.setVisible(is_master)
        self.speed_mode.setVisible(is_master)
        self.speed_mode.setEnabled(is_master)
        self.read_address_label.setVisible(is_master)
        self.read_address.setVisible(is_master)
        self.read_address.setEnabled(is_master)
        self.write_address_label.setVisible(is_master)
        self.write_address.setVisible(is_master)
        self.write_address.setEnabled(is_master)
        self.clock_stretch.setVisible(not is_master)
        self.clock_stretch_label.setVisible(not is_master)
        self.clock_stretch.setEnabled(not is_master)

    def update_address_validator(self):
        addr_mode = self.address_mode.currentText()
        if addr_mode == "7-bit":
            validator = QRegularExpressionValidator(QRegularExpression(r"^0x[0-9A-Fa-f]{0,2}$"))
            self.device_address.setPlaceholderText("Enter address (0x00 to 0xFF)")
            self.device_address.setMaxLength(4)
        else:  # 10-bit
            validator = QRegularExpressionValidator(QRegularExpression(r"^0x[0-3][0-9A-Fa-f]{0,2}$"))
            self.device_address.setPlaceholderText("Enter address (0x000 to 0x3FF)")
            self.device_address.setMaxLength(5)
        self.device_address.setValidator(validator)
        self.device_address.setText("")

    def validate_device_address(self):
        addr_mode = self.address_mode.currentText()
        address_text = self.device_address.text().strip()
        try:
            if address_text:
                if not address_text.startswith("0x"):
                    raise ValueError("Missing 0x prefix")
                base_address = int(address_text[2:], 16)
            else:
                base_address = 0x50 if addr_mode == "7-bit" else 0x1A3
                self.device_address.setText(f"0x{base_address:02X}" if addr_mode == "7-bit" else f"0x{base_address:03X}")
                return
        except ValueError:
            base_address = 0x50 if addr_mode == "7-bit" else 0x1A3
            self.device_address.setText(f"0x{base_address:02X}" if addr_mode == "7-bit" else f"0x{base_address:03X}")
            self.device_address.setStyleSheet("border: 1px solid red;")
            self.device_address.setToolTip("Invalid hexadecimal input. Use 0x prefix (e.g., 0x50 or 0x1A3).")
            return
        if addr_mode == "7-bit" and (base_address < 0 or base_address > 0xFF):
            self.device_address.setText("0x50")
            self.device_address.setStyleSheet("border: 1px solid red;")
            self.device_address.setToolTip("Address must be 0x00-0xFF.")
        elif addr_mode == "10-bit" and (base_address < 0 or base_address > 0x3FF):
            self.device_address.setText("0x1A3")
            self.device_address.setStyleSheet("border: 1px solid red;")
            self.device_address.setToolTip("10-bit address must be 0x000-0x3FF.")
        else:
            self.device_address.setStyleSheet("")
            self.device_address.setToolTip("")
        try:
            if addr_mode == "7-bit":
                seven_bit = base_address & 0x7F
                shifted = (seven_bit << 1) & 0xFF
                tc = self.test_case.currentText()
                if tc == "Write Test":
                    w_addr = shifted | 0x0
                    self.write_address.setText(f"0x{w_addr:02X}")
                elif tc == "Read Test":
                    r_addr = shifted | 0x1
                    self.read_address.setText(f"0x{r_addr:02X}")
                else:
                    if not self.read_address.text().strip():
                        self.read_address.setText(f"0x{(shifted|1):02X}")
                    if not self.write_address.text().strip():
                        self.write_address.setText(f"0x{(shifted|0):02X}")
        except Exception:
            pass

    def update_register_address(self):
        for field in [self.read_address, self.write_address]:
            text = field.text().strip()
            try:
                if text:
                    if not text.startswith("0x"):
                        raise ValueError("Missing 0x prefix")
                    value = int(text[2:], 16)
                    if value < 0 or value > 0xFF:
                        raise ValueError("Out of range")
                    field.setStyleSheet("")
                    field.setToolTip("")
                    field.setText(f"0x{value:02X}")
                else:
                    field.setText("0x00")
            except ValueError:
                field.setText("0x00")
                field.setStyleSheet("border: 1px solid red;")
                field.setToolTip("Invalid 8-bit hexadecimal input. Use 0x00 to 0xFF (e.g., 0x00).")
