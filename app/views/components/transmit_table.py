# app/views/components/transmit_table.py
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QTableWidget, QTableWidgetItem, QSizePolicy, QHeaderView
from PySide6.QtCore import Qt

class TransmitTable(QGroupBox):
    def __init__(self):
        super().__init__("TRANSMIT TABLE")
        self.setLayout(QVBoxLayout())
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Data", "Data Length"])
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Set custom column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Data column stretches
        header.setSectionResizeMode(1, QHeaderView.Fixed)    # Data Length column fixed width
        header.resizeSection(1, 40)  # Set Data Length column to 100 pixels wide
        self.table.horizontalHeader().setStretchLastSection(True)
        self.layout().addWidget(self.table)

    def add_entry(self, data: str, data_length: str):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Create items with center alignment
        data_item = QTableWidgetItem(data)
        data_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 0, data_item)

        length_item = QTableWidgetItem(data_length)
        length_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 1, length_item)

        self.table.scrollToBottom()