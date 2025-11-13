# app/views/components/uart_monitor_panel.py
from PySide6.QtWidgets import (
    QGroupBox, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QPushButton, QHBoxLayout, QFileDialog, QHeaderView, QSizePolicy
)
from PySide6.QtCore import Qt
from datetime import datetime
import csv
import logging
logger = logging.getLogger(__name__)

class LiveMonitorPanel(QGroupBox):
    def __init__(self, main_window):
        super().__init__("LOGGER PANEL")
        self.main_window = main_window  # Store reference to MainWindow

        # Main vertical layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Table setup
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["S.N.O","Test Case","Tx Timestamp", "Tx Data", "Rx Timestamp", "Rx Data", "Status"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        # Hide the vertical header (row numbers on the left side)
        self.table.verticalHeader().setVisible(False)


        # Set size policy to expanding so table fills available space
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Set stretch mode to fill the available width
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setMinimumSectionSize(120)  # Set a global minimum for all columns

        # Add table to layout with stretch to fill space
        main_layout.addWidget(self.table, stretch=1)

        # Buttons layout
        btn_layout = QHBoxLayout()
        main_layout.addLayout(btn_layout)

        self.export_btn = QPushButton("EXPORT LOG")
        self.clear_btn = QPushButton("CLEAR LOG")

        # Style buttons for consistency
        button_style = "font-size: 14px; padding: 5px;"
        self.export_btn.setStyleSheet(button_style)
        self.clear_btn.setStyleSheet(button_style)

        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.clear_btn)

        # Connect buttons
        self.export_btn.clicked.connect(self.export_log)
        self.clear_btn.clicked.connect(self.clear_log)

        self.current_row = -1  # Track the current transaction row
        self.serial_number = 0  # Track serial number

    def set_progress(self, count: int):
        if not hasattr(self, 'progress_label'):
            from PySide6.QtWidgets import QLabel
            self.progress_label = QLabel("Lines received: 0")
            self.layout().addWidget(self.progress_label)
            self.progress_label.setText(f"Lines received: {count}")
    # Or update QProgressBar if you have one

    def update_columns_for_baud_rate_tests(self, test_name):
        """Update table columns for both BAUD RATE TESTING and AUTO BAUD RATE DETECTION"""
        self.table.setColumnCount(5)
        
        if test_name == "BAUD RATE TESTING":
            self.table.setHorizontalHeaderLabels([
                "S.N.O", 
                "Min Baud Rate", 
                "Error %", 
                "Max Baud Rate", 
                "Error %"
            ])
        elif test_name == "AUTO BAUD RATE DETECTION":
            self.table.setHorizontalHeaderLabels([
                "S.N.O", 
                "Test Case", 
                "Scalar Baud Rate", 
                "Max Baud Rate", 
                "Status"
            ])
        
        # Clear existing data when switching to baud rate tests
        self.table.setRowCount(0)
        self.current_row = -1
        self.serial_number = 0

    # Remove the old individual functions and replace with the common one
    # Remove: update_columns_for_baud_rate_test()
    # Remove: update_columns_for_auto_baud_rate_detection()
    def restore_default_columns(self):
        """Restore default columns for other test cases"""
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "S.N.O", "Test Case", "Tx Timestamp", "Tx Data", "Rx Timestamp", "Rx Data", "Status"
        ])
    
    def add_baud_rate_result(self, min_baud_rate, min_error, max_baud_rate, max_error):
        """Add a baud rate test result to the table (for BAUD RATE TESTING)"""
        logger.info(f"LIVE MONITOR - Adding baud rate result: min={min_baud_rate}, min_err={min_error}, max={max_baud_rate}, max_err={max_error}")
        self.serial_number += 1
        self.current_row = self.table.rowCount()
        self.table.insertRow(self.current_row)

        # Column indices for baud rate test layout
        SNO_COL = 0
        MIN_BAUD_COL = 1
        MIN_ERROR_COL = 2
        MAX_BAUD_COL = 3
        MAX_ERROR_COL = 4

        # S.N.O
        sno_item = QTableWidgetItem(str(self.serial_number))
        sno_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(self.current_row, SNO_COL, sno_item)

        # Min Baud Rate
        min_baud_item = QTableWidgetItem(f"{min_baud_rate:,}")
        min_baud_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(self.current_row, MIN_BAUD_COL, min_baud_item)

        # Min Error %
        min_error_item = QTableWidgetItem(f"{min_error:.2f}%")
        min_error_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(self.current_row, MIN_ERROR_COL, min_error_item)

        # Max Baud Rate
        max_baud_item = QTableWidgetItem(f"{max_baud_rate:,}")
        max_baud_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(self.current_row, MAX_BAUD_COL, max_baud_item)

        # Max Error %
        max_error_item = QTableWidgetItem(f"{max_error:.2f}%")
        max_error_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(self.current_row, MAX_ERROR_COL, max_error_item)

        self.table.scrollToBottom()

    def add_auto_baud_rate_result(self, scalar_baud_rate, max_baud_rate, status="Detected"):
        """Add an auto baud rate detection result to the table (for AUTO BAUD RATE DETECTION)"""
        logger.info(f"LIVE MONITOR - Adding auto baud rate result: scalar={scalar_baud_rate}, max={max_baud_rate}, status={status}")
        
        self.serial_number += 1
        self.current_row = self.table.rowCount()
        self.table.insertRow(self.current_row)

        # Column indices for auto baud rate detection layout
        SNO_COL = 0
        TEST_CASE_COL = 1
        SCALAR_BAUD_COL = 2
        MAX_BAUD_COL = 3
        STATUS_COL = 4

        # S.N.O
        sno_item = QTableWidgetItem(str(self.serial_number))
        sno_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(self.current_row, SNO_COL, sno_item)

        # Test Case
        test_case_item = QTableWidgetItem("AUTO BAUD RATE DETECTION")
        test_case_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(self.current_row, TEST_CASE_COL, test_case_item)

        # Scalar Baud Rate
        scalar_baud_item = QTableWidgetItem(f"{scalar_baud_rate:,}")
        scalar_baud_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(self.current_row, SCALAR_BAUD_COL, scalar_baud_item)

        # Max Baud Rate
        max_baud_item = QTableWidgetItem(f"{max_baud_rate:,}")
        max_baud_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(self.current_row, MAX_BAUD_COL, max_baud_item)

        # Status
        status_item = QTableWidgetItem(status)
        status_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(self.current_row, STATUS_COL, status_item)

        self.table.scrollToBottom()

    def add_log_entry(self, direction: str, data: str, length: str):
            test_name = ""
            if self.main_window and hasattr(self.main_window, 'controller'):
                cfg = getattr(self.main_window.controller, 'current_base_config', None)
                if cfg and hasattr(cfg, 'test_name'):
                    test_name = cfg.test_name.upper()
            
            if test_name in ["BAUD RATE TESTING", "AUTO BAUD RATE DETECTION"]:
                # Baud rate tests use add_baud_rate_result instead
                return
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Get current test name
            test_name = ""
            if self.main_window and hasattr(self.main_window, 'controller'):
                cfg = getattr(self.main_window.controller, 'current_base_config', None)
                if cfg and hasattr(cfg, 'test_name'):
                    test_name = cfg.test_name.upper()

            if direction == "Tx":
                self.serial_number += 1
                self.current_row = self.table.rowCount()
                self.table.insertRow(self.current_row)

                # Column indices (fixed - 7 columns)
                SNO_COL = 0
                TEST_CASE_COL = 1
                TX_TS_COL = 2
                TX_DATA_COL = 3
                RX_TS_COL = 4
                RX_DATA_COL = 5
                STATUS_COL = 6

                # S.N.O - Always show
                sno_item = QTableWidgetItem(str(self.serial_number))
                sno_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(self.current_row, SNO_COL, sno_item)

                # Test Case - Always show
                test_case_item = QTableWidgetItem(test_name)
                test_case_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(self.current_row, TEST_CASE_COL, test_case_item)

                # Handle different test cases for Tx data
                if test_name == "RECEPTION TEST":
                    # For RECEPTION TEST: Show dashes in Tx columns
                    tx_ts_item = QTableWidgetItem("—")
                    tx_data_item = QTableWidgetItem("—")
                else:
                    # For all other tests: Show actual Tx data
                    tx_ts_item = QTableWidgetItem(timestamp)
                    tx_data_item = QTableWidgetItem(data)

                tx_ts_item.setTextAlignment(Qt.AlignCenter)
                tx_data_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(self.current_row, TX_TS_COL, tx_ts_item)
                self.table.setItem(self.current_row, TX_DATA_COL, tx_data_item)

                # Initialize Rx columns with dashes for tests that don't expect responses
                rx_ts_item = QTableWidgetItem("—")
                rx_data_item = QTableWidgetItem("—")
                rx_ts_item.setTextAlignment(Qt.AlignCenter)
                rx_data_item.setTextAlignment(Qt.AlignCenter)
                
                # Only show actual Rx data for tests that expect responses
                if test_name not in ["TRANSMISSION TEST", "RTS/CTS HARDWARE FLOW TEST", "PARITY DETECTION"]:
                    # These will be updated when Rx data comes
                    pass
                
                self.table.setItem(self.current_row, RX_TS_COL, rx_ts_item)
                self.table.setItem(self.current_row, RX_DATA_COL, rx_data_item)

                # Status - Always show, initialize as "Pending"
                status_item = QTableWidgetItem("Pending")
                status_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(self.current_row, STATUS_COL, status_item)
                
            elif direction == "Rx" and self.current_row >= 0:
                # Column indices
                RX_TS_COL = 4
                RX_DATA_COL = 5
                STATUS_COL = 6

                # Get current test name again to be sure
                current_test_name = ""
                if self.main_window and hasattr(self.main_window, 'controller'):
                    cfg = getattr(self.main_window.controller, 'current_base_config', None)
                    if cfg and hasattr(cfg, 'test_name'):
                        current_test_name = cfg.test_name.upper()

                # Handle different test cases for Rx data
                if current_test_name in ["TRANSMISSION TEST", "RTS/CTS HARDWARE FLOW TEST", "PARITY DETECTION"]:
                    # For these tests: Keep dashes in Rx columns
                    rx_ts_item = QTableWidgetItem("—")
                    rx_data_item = QTableWidgetItem("—")
                else:
                    # For all other tests: Show actual Rx data
                    rx_ts_item = QTableWidgetItem(timestamp)
                    rx_data_item = QTableWidgetItem(data)

                rx_ts_item.setTextAlignment(Qt.AlignCenter)
                rx_data_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(self.current_row, RX_TS_COL, rx_ts_item)
                self.table.setItem(self.current_row, RX_DATA_COL, rx_data_item)

            self.table.scrollToBottom()
    def export_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Log", "", "CSV Files (*.csv)")
        if not path:
            return

        try:
            with open(path, mode='w', newline='') as file:
                writer = csv.writer(file)
                
                # Check current test mode
                current_test = ""
                if self.main_window and hasattr(self.main_window, 'controller'):
                    cfg = getattr(self.main_window.controller, 'current_base_config', None)
                    if cfg and hasattr(cfg, 'test_name'):
                        current_test = cfg.test_name.upper()
                
                # Set headers based on test type
                if current_test == "BAUD RATE TESTING":
                    writer.writerow(["S.N.O", "Min Baud Rate", "Error %", "Max Baud Rate", "Error %"])
                elif current_test == "AUTO BAUD RATE DETECTION":
                    writer.writerow(["S.N.O", "Test Case", "Scalar Baud Rate", "Max Baud Rate", "Status"])
                else:
                    writer.writerow(["S.N.O", "Test Case", "Tx Timestamp", "Tx Data", "Rx Timestamp", "Rx Data", "Status"])
                        
                for row in range(self.table.rowCount()):
                    row_data = []
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        text = item.text() if item else ""
                        if text == "—":
                            text = ""
                        row_data.append(text)
                    writer.writerow(row_data)
                        
                # Add summary for baud rate tests
                if current_test in ["BAUD RATE TESTING", "AUTO BAUD RATE DETECTION"]:
                    writer.writerow([])  # Empty line
                    writer.writerow(["Summary", f"Total results: {self.table.rowCount()}"])
                        
            print(f"Log exported to {path} with {self.table.rowCount()} rows")
        except Exception as e:
            print(f"Failed to export log: {e}")

    def clear_log(self):
        self.table.setRowCount(0)
        self.current_row = -1  # Reset current row
        self.serial_number = 0  # Reset serial number
    # def update_columns_for_test(self, test_name):
    #     """Dynamically set columns based on test type."""
    #     t = test_name.strip().upper()
    #     if t == "TRANSMISSION TEST" or t == "RTS/CTS HARDWARE FLOW TEST" or t == "PARITY DETECTION":
    #         headers = ["S.N.O", "Tx Timestamp", "Tx Data", "Status"]
    #         self.table.setColumnCount(len(headers))
    #         self.table.setHorizontalHeaderLabels(headers)
    #     elif test_name.upper() == "RECEPTION TEST":
    #         headers = ["S.N.O", "Rx Timestamp", "Rx Data", "Status"]
    #         self.table.setColumnCount(len(headers))
    #         self.table.setHorizontalHeaderLabels(headers)
    #     else:
    #         # Show all for other/complex tests
    #         headers = ["S.N.O", "Tx Timestamp", "Tx Data", "Rx Timestamp", "Rx Data", "Status"]
    #         self.table.setColumnCount(len(headers))
    #         self.table.setHorizontalHeaderLabels(headers)
    #     # Optionally reset table contents to avoid mismatches
    #     self.table.setRowCount(0)

