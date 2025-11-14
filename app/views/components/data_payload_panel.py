from PySide6.QtWidgets import (
    QGroupBox, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QSpinBox, QPushButton, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, Slot, Signal

class DataPayloadPanel(QGroupBox):
    stop_clicked = Signal()

    def __init__(self):
        super().__init__("DATA PANEL")
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(10, 15, 10, 10)
        self.layout().setSpacing(10)

        self.__init_ui__()
        self.__connect_signals()

    def __init_ui__(self):
        # Create two separate columns with individual layouts
        columns_layout = QHBoxLayout()
        
        # DATA column
        data_column = QVBoxLayout()
        data_label = QLabel("DATA")
        data_label.setAlignment(Qt.AlignCenter)
        data_label.setStyleSheet("font-weight: bold;")
        
        self.data = QLineEdit()
        self.data.setPlaceholderText("Enter data")
        
        data_column.addWidget(data_label)
        data_column.addWidget(self.data)
        
        # DATA LENGTH column
        length_column = QVBoxLayout()
        length_label = QLabel("DATA LENGTH")
        length_label.setAlignment(Qt.AlignCenter)
        length_label.setStyleSheet("font-weight: bold;")
        
        self.data_length = QSpinBox()
        self.data_length.setRange(0, 150)
        self.data_length.setValue(0)
        
        length_column.addWidget(length_label)
        length_column.addWidget(self.data_length)
        
        # Add columns to main layout
        columns_layout.addLayout(data_column)
        columns_layout.addLayout(length_column)
        
        self.layout().addLayout(columns_layout)

        # Action row
        action_row = QHBoxLayout()
        
        # Send buttons
        self.send_once_btn = QPushButton("SEND")
        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setStyleSheet("color:black;")
        action_row.addWidget(self.send_once_btn)
        action_row.addWidget(self.stop_btn)
        # self.send_cyclic_btn = QPushButton("Send Cyclic")
        # action_row.addWidget(self.send_cyclic_btn)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        action_row.addWidget(spacer)

        # Add and Remove buttons
        self.add_btn = QPushButton("ADD")
        action_row.addWidget(self.add_btn)
        self.del_btn = QPushButton("REMOVE")
        action_row.addWidget(self.del_btn)
        
        self.layout().addLayout(action_row)
        # In DataPayloadPanel.__init_ui__()
        # self.repeat_count = QSpinBox()
        # self.repeat_count.setRange(1, 1000)          # Reasonable limits
        # self.repeat_count.setValue(1)                # Default to 1

        # repeat_label = QLabel("REPEAT TIMES")
        # repeat_label.setAlignment(Qt.AlignCenter)
        # repeat_label.setStyleSheet("font-weight: bold;")
        # repeat_layout = QVBoxLayout()
        # repeat_layout.addWidget(repeat_label)
        # repeat_layout.addWidget(self.repeat_count)

        # columns_layout.addLayout(repeat_layout)


    def __connect_signals(self):
        self.data_length.valueChanged.connect(self._on_length_changed)
        self.data.textChanged.connect(self._on_data_changed)
        self.stop_btn.clicked.connect(self.stop_clicked)

    @Slot()
    def _on_length_changed(self):
        max_length = self.data_length.value()
        self.data.setMaxLength(max_length)
        current_text = self.data.text()
        if len(current_text) > max_length:
            self.data.blockSignals(True)
            self.data.setText(current_text[:max_length])
            self.data.blockSignals(False)
            self._on_data_changed()

    @Slot()
    def _on_data_changed(self):
        current_length = len(self.data.text())
        self.data_length.blockSignals(True)
        self.data_length.setValue(current_length)
        self.data_length.blockSignals(False)