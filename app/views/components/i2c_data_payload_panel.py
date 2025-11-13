from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QPushButton, QLabel, QSpinBox, QHBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Slot, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator

class I2CPayloadConfig:
    def __init__(self, message_data: str, data_length: int, register_size: int, register_address=None):
        self.message_data = message_data
        self.data_length = data_length
        self.register_size = register_size
        self.register_address = register_address
        self.multi_data_validator_8 = QRegularExpressionValidator(QRegularExpression(r"^(0x[0-9A-Fa-f]{2}\s?)+$"))
        self.multi_data_validator_16 = QRegularExpressionValidator(QRegularExpression(r"^(0x[0-9A-Fa-f]{4}\s?)+$"))  # Changed {2} to {4}

class I2CDataPayloadPanel(QGroupBox):
    def __init__(self):
        super().__init__("DATA PANEL")
        self.transmit_log_dialog = None
        layout = QVBoxLayout()
        self.setLayout(layout)
        self._init_ui(layout)
        self._connect_signals()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _init_ui(self, layout):
        form = QFormLayout()
        form.setSpacing(15)
        form.setHorizontalSpacing(15)
        form.setContentsMargins(10, 15, 10, 15)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 15, 10, 15)
        layout.addLayout(form)

        # REGISTER SIZE
        self.register_size = QComboBox()
        self.register_size.addItems(["8", "16"])
        self.register_size_label = QLabel("REGISTER SIZE (BITS):")
        self.register_size_label.setStyleSheet("font-weight: bold;")
        self.register_size.setStyleSheet("font-weight: bold;")
        form.addRow(self.register_size_label, self.register_size)

        # READ LENGTH
        self.read_length = QSpinBox()
        self.read_length.setRange(1, 2)
        self.read_length.setEnabled(False)  # Initially disabled
        self.read_length_label = QLabel("READ LENGTH (BYTES):")
        self.read_length_label.setStyleSheet("font-weight: bold;")
        self.read_length.setStyleSheet("font-weight: bold;")
        form.addRow(self.read_length_label, self.read_length)

        # WRITE LENGTH
        self.write_length = QSpinBox()
        self.write_length.setRange(1, 2)
        self.write_length.setEnabled(False)  # Initially disabled
        self.write_length_label = QLabel("WRITE LENGTH (BYTES):")
        self.write_length_label.setStyleSheet("font-weight: bold;")
        self.write_length.setStyleSheet("font-weight: bold;")
        form.addRow(self.write_length_label, self.write_length)

        # REGISTER ADDRESS
        self.register_address = QLineEdit()
        self.register_address.setPlaceholderText("Register Address (0x00 to 0xFF)")
        # For 8-bit register addresses
        self.regaddr_validator_8 = QRegularExpressionValidator(QRegularExpression(r"^(0x[0-9A-Fa-f]{2}(\s+)?)+$"))

        # For 16-bit register addresses
        self.regaddr_validator_16 = QRegularExpressionValidator(QRegularExpression(r"^(0x[0-9A-Fa-f]{4}(\s+)?)+$"))


        self.data_validator = QRegularExpressionValidator(QRegularExpression(r"^0x[0-9A-Fa-f]{0,2}$"))
        self.data_validator_16 = QRegularExpressionValidator(QRegularExpression(r"^0x[0-9A-Fa-f]{0,4}$"))
        try:
            for v in [self.regaddr_validator_8, self.regaddr_validator_16,
                      self.data_validator, self.data_validator_16]:
                v.setValidationMode(QRegularExpressionValidator.Intermediate)
        except AttributeError:
            pass
        self.register_address.setValidator(self.regaddr_validator_8)
        self.register_address.setMaxLength(4)
        self.register_address_label = QLabel("REGISTER ADDRESS:")
        self.register_address_label.setStyleSheet("font-weight: bold;")
        self.register_address.setStyleSheet("font-weight: bold;")
        form.addRow(self.register_address_label, self.register_address)

        # WRITE DATA
        self.data = QLineEdit()
        self.data.setPlaceholderText("Write Data (0x00 to 0xFF)")
        # validators for multi-value input (8-bit and 16-bit hex values)
        self.multi_data_validator_8 = QRegularExpressionValidator(QRegularExpression(r"^(0x[0-9A-Fa-f]{2}\s?)+$"))
        self.multi_data_validator_16 = QRegularExpressionValidator(QRegularExpression(r"^(0x[0-9A-Fa-f]{2}\s?)+$"))
        # default to 8-bit multi validator
        self.data.setValidator(self.multi_data_validator_8)
        self.data.setMaxLength(500)
        self.data.setPlaceholderText("Write Data")  # Allow multiple bytes with spaces
        self.data_label = QLabel("WRITE DATA:")
        self.data_label.setStyleSheet("font-weight: bold;")
        self.data.setStyleSheet("font-weight: bold;")
        self.data_row = form.addRow(self.data_label, self.data)  # Store row index for visibility control

        # BUTTONS
        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        self.add_btn = QPushButton("ADD")
        self.del_btn = QPushButton("REMOVE")
        self.send_btn = QPushButton("SEND")
        for btn in (self.add_btn, self.del_btn, self.send_btn):
            btn.setFixedSize(130, 32)
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            btn.setStyleSheet("font-weight: bold;")
        button_row.addWidget(self.add_btn)
        button_row.addWidget(self.del_btn)
        button_row.addStretch()
        button_row.addWidget(self.send_btn)
        form.addRow(button_row)
        layout.addStretch()

        # initialize UI according to default register size
        self._apply_register_size(self.register_size.currentText())

    # NOTE: `update_for_test_case` is defined below with @Slot(str).

    def _connect_signals(self):
        self.register_size.currentTextChanged.connect(self._apply_register_size)

    @Slot(str)
    def update_for_test_case(self, test_case: str):
        """Update UI based on the selected test case."""
        self.test_case = test_case
        self._update_ui_for_test_case(test_case)

    def _update_ui_for_test_case(self, test_case: str):
        """Helper method to show/hide write data field and update button text."""
        if test_case == "Read Test":
            self.data_label.setVisible(False)
            self.data.setVisible(False)
            self.send_btn.setText("READ")
        else:  # Default behavior for "Write Test" and other test cases
            self.data_label.setVisible(True)
            self.data.setVisible(True)
            self.send_btn.setText("SEND")

    @Slot()
    def _apply_register_size(self, size_str):
        size_bits = int(size_str)
        if size_bits not in [8, 16]:
            raise ValueError("Register size must be 8 or 16 bits")

        size_bytes = size_bits // 8
        self.read_length.setValue(size_bytes)
        self.write_length.setValue(size_bytes)
        self.read_length.setEnabled(False)
        self.write_length.setEnabled(False)

        if size_bits == 8:
            self.register_address.setPlaceholderText("Register Address (space-separated 0x00 values)")
            self.register_address.setValidator(self.regaddr_validator_8)
            self.register_address.setMaxLength(500)
        else:
            self.register_address.setPlaceholderText("Register Address (space-separated 0x0000 values)")
            self.register_address.setValidator(self.regaddr_validator_16)
            self.register_address.setMaxLength(500)

        self.register_address.clear()
        self.data.clear()