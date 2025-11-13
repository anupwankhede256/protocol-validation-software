from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QTableWidget, QTableWidgetItem, QSizePolicy,
    QHeaderView, QPushButton, QHBoxLayout, QFileDialog
)
from PySide6.QtCore import Qt
from datetime import datetime
import csv

class I2CMonitorPanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("LIVE MONITOR PANEL")
        self.parent = parent
        self.setLayout(QVBoxLayout())

        # Table setup
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "S.N.O", "Tx Timestamp", "Rx Timestamp", "Register Address",
            "R/W Bit", "Data", "Result"
        ])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setMinimumSectionSize(100)

        self.layout().addWidget(self.table, stretch=1)

        # Buttons layout
        btn_layout = QHBoxLayout()
        self.layout().addLayout(btn_layout)

        self.export_btn = QPushButton("EXPORT LOG")
        self.clear_btn = QPushButton("CLEAR LOG")

        # Style buttons for consistency
        button_style = "font-size: 14px; padding: 5px; font-weight: bold;"
        self.export_btn.setStyleSheet(button_style)
        self.clear_btn.setStyleSheet(button_style)

        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.clear_btn)

        # Connect buttons
        self.export_btn.clicked.connect(self.export_log)
        self.clear_btn.clicked.connect(self.clear_log)

        self.serial_number = 0
    # def update_columns_for_test_case(self, test_case):
    #     if test_case.upper() == "READ TEST":
    #         headers = ["S.N.O", "Rx Timestamp", "Register Address", "R/W Bit", "Data", "Result"]
    #         self.table.setColumnCount(len(headers))
    #         self.table.setHorizontalHeaderLabels(headers)
    #     elif test_case.upper() == "WRITE TEST":
    #         headers = ["S.N.O", "Tx Timestamp", "Register Address", "R/W Bit", "Data", "Result"]
    #         self.table.setColumnCount(len(headers))
    #         self.table.setHorizontalHeaderLabels(headers)
    #     else:
    #         headers = ["S.N.O", "Tx Timestamp", "Rx Timestamp", "Register Address", "R/W Bit", "Data", "Result"]
    #         self.table.setColumnCount(len(headers))
    #         self.table.setHorizontalHeaderLabels(headers)
    #     self.table.setRowCount(0)  # Reset table for new test type

    def update_columns_for_test_case(self, test_case):
        # Always use the full 7-column structure, regardless of test case
        headers = [
            "S.N.O", "Tx Timestamp", "Rx Timestamp", "Register Address",
            "R/W Bit", "Data", "Result"
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        # Removed: self.table.setRowCount(0)  # No reset to allow continuous logging

    def add_log_entry(self, test_case, register_address, rw_bit, data, tx_timestamp="", rx_timestamp="", result=""):
        self.serial_number += 1
        self.current_row = self.table.rowCount()
        self.table.insertRow(self.current_row)

        def center(text): 
            item = QTableWidgetItem(str(text))
            item.setTextAlignment(Qt.AlignCenter)
            return item
        items = [
            center(self.serial_number),  # Col 0: S.N.O
        center(tx_timestamp if tx_timestamp else "-"),  # Col 1: Tx Timestamp ( "-" for Read)
        center(rx_timestamp if rx_timestamp else "-"),  # Col 2: Rx Timestamp ( "-" for Write)
        center(register_address),   # Col 3: Register Address
        center(rw_bit),             # Col 4: R/W Bit
        center(data),               # Col 5: Data
        center(result)              # Col 6: Result
    ]

        # if test_case.upper() == "READ TEST":
        #     items = [
        #         center(str(self.serial_number)),
        #         center(rx_timestamp),
        #         center(register_address),
        #         center("1"),
        #         center(data),           # Data received
        #         center(result)          # e.g., "data received successfully"
        #     ]
        # elif test_case.upper() == "WRITE TEST":
        #     items = [
        #         center(str(self.serial_number)),
        #         center(tx_timestamp),
        #         center(register_address),
        #         center("0"),
        #         center(data),           # Data sent
        #         center(result)          # e.g., "data sent successfully"
        #     ]
        # else:
        #     # For other test types, expand accordingly.
        #     items = [
        #         center(str(self.serial_number)),
        #         center(tx_timestamp),
        #         center(rx_timestamp),
        #         center(register_address),
        #         center(rw_bit),
        #         center(data),
        #         center(result)
        #     ]
        for index, item in enumerate(items):
            self.table.setItem(self.current_row, index, item)

        self.table.scrollToBottom() 

    def export_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Log", "", "CSV Files (*.csv)")
        if not path:
            return

        try:
            with open(path, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["S.N.O", "Tx Timestamp", "Rx Timestamp", "Register Address",
                                 "R/W Bit", "Data", "Result"])
                for row in range(self.table.rowCount()):
                    row_data = []
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            print(f"Log exported to {path}")
        except Exception as e:
            print(f"Failed to export log: {e}")

    def clear_log(self):
        self.table.setRowCount(0)
        self.serial_number = 0  # Reset serial number