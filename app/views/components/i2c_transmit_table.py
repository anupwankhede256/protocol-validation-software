
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QTableWidget, QTableWidgetItem, QSizePolicy, QHeaderView
from PySide6.QtCore import Qt

class I2CTransmitTable(QGroupBox):
    def __init__(self):
        super().__init__("TRANSMIT LOG")
        self.setLayout(QVBoxLayout())
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Address", "Data", "Data Length"])
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 100)  # Address column
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Data column stretches
        header.setSectionResizeMode(2, QHeaderView.Fixed)    # Data Length column fixed
        header.resizeSection(2, 80)  # Data Length column
        self.table.horizontalHeader().setStretchLastSection(True)
        self.layout().addWidget(self.table)

    def add_entry(self, address: str, data: str, data_length: str):
        row = self.table.rowCount()
        self.table.insertRow(row)

        address_item = QTableWidgetItem(address)
        address_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 0, address_item)

        data_item = QTableWidgetItem(data)
        data_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 1, data_item)

        length_item = QTableWidgetItem(data_length)
        length_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 2, length_item)

        self.table.scrollToBottom()
        