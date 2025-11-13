from typing import Optional, List
import json
import time
from PySide6.QtCore import QTimer, QThread, Signal, QEventLoop
from PySide6.QtWidgets import QTableWidgetItem, QMessageBox
from app.models.uart_model import UARTTestBaseConfig, UARTPayloadConfig, UARTFullConfig
from app.services.uart_backend import UARTBackend
from app.services.database_service import Database
from datetime import datetime
import psycopg2
import logging
import socket
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)

class MainController:
    def __init__(self, main_window):
        self.main_window = main_window
        self.backend = UARTBackend()
       # self._cyclic_timer = QTimer()
       # self._cyclic_timer.timeout.connect(self._send_next_payload)
       # self._pending_index = 0
        self.base_config: Optional[UARTTestBaseConfig] = None
        self.payload_configs: List[UARTPayloadConfig] = []
        self.current_base_config: Optional[UARTTestBaseConfig] = None
        self.backend.labview.line_received.connect(self._on_labview_line_received)
        self.backend.labview.finished.connect(self._on_labview_full_response)
        self.backend.labview.progress.connect(self._on_progress_update)

        # Initialize Database
        self.db_config = {
            'dbname': 'uart_test',
            'user': 'postgres',
            'password': 'tejasai',
            'host': 'localhost',
            'port': '5432'
        }
        self.db = Database(self.db_config)
        self.db.create_tables()

        self._connect_signals()
        # Ensure send button label reflects the current test case at startup
        try:
            current_tc = self.main_window.test_selection.test_name.currentText()
            self._on_test_case_changed(current_tc)
        except Exception:
            logger.debug('Could not initialize test case dependent UI')

    def _on_labview_full_response(self, full_response: str):
        """Called when LabVIEW sends full response (for normal tests)"""
        if not self.current_base_config:
            return

        test_case = self.current_base_config.test_name.upper()

        # Skip if it's a streaming test
        if test_case in ["BAUD RATE TESTING", "AUTO BAUD RATE DETECTION"]:
            return  # Handled by line_received

        # Update Rx in live monitor
        if self.main_window.live_monitor.current_row >= 0:
            row = self.main_window.live_monitor.current_row
            self.main_window.live_monitor.table.setItem(row, 5, QTableWidgetItem(full_response.strip()))

            # Determine status
            tx_data = self.main_window.live_monitor.table.item(row, 1).text()
            status = "Pass"

            if test_case == "LOOPBACK TEST":
                if full_response.strip() != tx_data.strip():
                    status = "FAIL"
            elif test_case == "RECEPTION TEST":
                if "success" not in full_response.lower() and "received" not in full_response.lower():
                    status = "Data Received"

            item = QTableWidgetItem(status)
            item.setTextAlignment(Qt.AlignCenter)
            self.main_window.live_monitor.table.setItem(row, 6, item)

            # Save to DB
            cfg = UARTPayloadConfig(message_data=tx_data, data_length=len(tx_data))
            self._save_test_result_to_db(cfg, full_response, datetime.now(), status)

    def _on_progress_update(self, count: int):
        self.main_window.live_monitor.set_progress(count)

        # --------------------------------------------------------------------- #
    #  NEW: Real-time line handler
    # --------------------------------------------------------------------- #
    def _on_labview_line_received(self, line: str):
        """Called **immediately** when LabVIEW sends a new line."""
        if not self.current_base_config:
            return

        test_case = self.current_base_config.test_name.upper()

        if test_case == "BAUD RATE TESTING":
            self._process_baud_rate_line(line)
        elif test_case == "AUTO BAUD RATE DETECTION":
            self._process_auto_baud_line(line)
        # add more test-cases here if needed


    def _process_baud_rate_line(self, line: str):
        """Parse: 110924.326940,3.854586,110924.326940,-3.711522"""
        try:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                min_b = int(round(float(parts[0])))
                min_e = round(float(parts[1]), 2)
                max_b = int(round(float(parts[2])))
                max_e = round(float(parts[3]), 2)
                self.main_window.live_monitor.add_baud_rate_result(min_b, min_e, max_b, max_e)
        except Exception as e:
            self.logger.warning(f"Bad baud line '{line}': {e}")

    def _process_auto_baud_line(self, line: str):
        """Parse: 115200,115200  →  scalar, max"""
        try:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                scalar = int(round(float(parts[0])))
                maximum = int(round(float(parts[1])))
                self.main_window.live_monitor.add_auto_baud_rate_result(scalar, maximum, "Detected")
        except Exception as e:
            self.logger.warning(f"Bad auto-baud line '{line}': {e}")

    def _connect_signals(self):
        buttons = [
            (self.main_window.payload_panel.send_once_btn, self._on_send_once, "SEND"),
            #(self.main_window.payload_panel.send_cyclic_btn, self._on_send_cyclic, "Send Cyclic"),
            (self.main_window.payload_panel.add_btn, self.add_payload_to_table, "Add"),
            (self.main_window.payload_panel.del_btn, self.delete_selected_transmit_row, "Delete"),
            (self.main_window.test_selection.add_config_btn, self._on_add_config, "Add Config")
        ]
        for button, slot, name in buttons:
            # Connect signal directly without disconnecting first
            # This avoids the disconnect warning on fresh button instances
            button.clicked.connect(slot)
            logger.debug(f"Connected signal for {name} button")
        # Update send button label when test case changes
        try:
            self.main_window.test_selection.test_name.currentTextChanged.connect(self._on_test_case_changed)
        except Exception:
            logger.debug("Failed to connect test_name change handler; UI may differ")

    def log_status(self, message: str, duration: int = 4000, level: str = "info"):
        """Log a message to the StatusPanel."""
        self.main_window.status_panel.append_message(message, level)
        logger.debug(f"Status logged: {message} ({level})")

    def _on_add_config(self):
        """Handle ADD CONFIG button click - Opens LabVIEW VI only."""
        logger.debug("ADD CONFIG button clicked")
        base_config = self._gather_base_config()
        if not base_config:
            self.log_status("Failed to gather base configuration.", level="error")
            return

        self.current_base_config = base_config
        self.log_status("Configuration saved locally.")
        
        # Launch LabVIEW VI and add delay to ensure it’s ready
        try:
            self.log_status("Opening LabVIEW VI...")
            process = self.backend.labview.launch_vi()
            time.sleep(5)  # Wait 5 seconds for VI to initialize
            self.log_status("LabVIEW VI initialization complete. Ready to send data.")
            if process:
                self.log_status("LabVIEW VI opened successfully!")
                logger.debug("LabVIEW VI launched successfully")
            else:
                self.log_status("Failed to open LabVIEW VI.", level="error")
        except Exception as e:
            self.log_status(f"Error opening LabVIEW VI: {e}", level="error")
            logger.error(f"Error launching LabVIEW VI: {e}")
    def add_payload_to_table(self):
        logger.debug("add_payload_to_table called")
        payload_config = self._gather_payload_config()
        if not payload_config or not payload_config.message_data.strip():
            self.log_status("Invalid or empty payload input.", level="warning")
            return

        self.main_window.transmit_table.add_entry(
            data=payload_config.message_data,
            data_length=str(payload_config.data_length)
        )
        self.payload_configs.append(payload_config)
        self.log_status("Payload added to transmit table.")

    def _on_send_once(self):
        logger.debug("SEND button clicked")
        if not self.current_base_config:
            self.log_status("Add Config first!", level="warning")
            return

        # Get selected payload
        table = self.main_window.transmit_table.table
        sel = table.currentRow()
        if sel < 0 and table.rowCount() > 0:
            sel = 0
        if sel < 0:
            self.log_status("No payload to send!", level="warning")
            return

        def txt(c):
            item = table.item(sel, c)
            return item.text() if item else ""

        try:
            data_length = int(txt(1))
        except ValueError:
            data_length = len(txt(0))  # Use actual string length if parsing fails

        cfg = UARTPayloadConfig(
            message_data=txt(0),
            data_length=data_length
        )
            
        test_case = self.current_base_config.test_name.upper()
        # === BAUD RATE TESTS: Use line_received ===
        if test_case in ["BAUD RATE TESTING", "AUTO BAUD RATE DETECTION"]:
            if test_case == "BAUD RATE TESTING":
                self._handle_baud_rate_test(cfg)
            else:
                self._handle_auto_baud_rate_detection(cfg)
            return

        # === NORMAL TESTS: Use finished signal ===
        self.main_window.live_monitor.add_log_entry("Tx", cfg.message_data, str(cfg.data_length))
        self.send_config_to_labview(cfg)  # Async → response comes via _on_labview_full_response
        self.log_status("Data sent. Waiting for LabVIEW response...", level="info")


    def _handle_baud_rate_test(self, payload_config=None):
        if payload_config is None:
            payload_config = UARTPayloadConfig(message_data="a", data_length=1)
        self.send_config_to_labview(payload_config)
        self.log_status("Baud Rate Test started – waiting for results...", level="info")

    def _handle_auto_baud_rate_detection(self, payload_config=None):
        """Start AUTO BAUD RATE DETECTION – results come via line_received signal."""
        logger.debug("Starting Auto Baud Rate Detection")

        if payload_config is None:
            payload_config = UARTPayloadConfig(message_data="AUTO_BAUD_RATE_DETECTION", data_length=0)

        self.send_config_to_labview(payload_config)
        self.log_status("Auto Baud Rate Detection started – waiting for results...", level="info")


    def _save_baud_rate_test_result(self, min_baud, min_error, max_baud, max_error):
        """Save baud rate test results to database"""
        if self.db and self.current_base_config:
            test_name_id = self._get_or_create_test_name_id(self.current_base_config.test_name)
            if test_name_id:
                config_id = self.db.insert_uart_config(
                    test_name_id=test_name_id,
                    device_id=self.current_base_config.device_id or "Unknown",
                    baud_rate=self.current_base_config.baud_rate,
                    data_bits=self.current_base_config.data_bits,
                    parity=self.current_base_config.parity,
                    stop_bits=self.current_base_config.stop_bits,
                    data_shift=self.current_base_config.data_shift,
                    handshake=self.current_base_config.handshake
                )
                if config_id:
                    # For baud rate tests, we store the results in a special way
                    # You might want to create a separate table for baud rate results
                    test_result_data = f"Min: {min_baud} ({min_error}%), Max: {max_baud} ({max_error}%)"
                    self.db.insert_test_result(
                        uart_config_id=config_id,
                        test_name=self.current_base_config.test_name,
                        tx_data="BAUD_RATE_TEST",
                        tx_timestamp=datetime.now(),
                        rx_data=test_result_data,
                        rx_timestamp=datetime.now(),
                        status="Completed"
                    )
                    self.log_status("Baud rate test result saved to database.", level="info")


    def _save_test_result_to_db(self, payload_config, rx_data, rx_timestamp, status):
        """Helper method to save test results to database."""
        if self.db and self.current_base_config:
            test_name_id = self._get_or_create_test_name_id(self.current_base_config.test_name)
            if test_name_id:
                config_id = self.db.insert_uart_config(
                    test_name_id=test_name_id,
                    device_id=self.current_base_config.device_id or "Unknown",
                    baud_rate=self.current_base_config.baud_rate,
                    data_bits=self.current_base_config.data_bits,
                    parity=self.current_base_config.parity,
                    stop_bits=self.current_base_config.stop_bits,
                    data_shift=self.current_base_config.data_shift,
                    handshake=self.current_base_config.handshake
                )
                if config_id:
                    self.db.insert_test_result(
                        uart_config_id=config_id,
                        test_name=self.current_base_config.test_name,
                        tx_data=payload_config.message_data,
                        tx_timestamp=datetime.now(),
                        rx_data=rx_data,  # This will be None for specific tests
                        rx_timestamp=rx_timestamp,  # This will be None for specific tests
                        status=status
                    )
                    self.log_status("Test result saved to database.", level="info")

    def _save_auto_baud_rate_detection_summary(self, successful_results, total_results):
        """Save auto baud rate detection summary to database"""
        if self.db and self.current_base_config:
            test_name_id = self._get_or_create_test_name_id(self.current_base_config.test_name)
            if test_name_id:
                config_id = self.db.insert_uart_config(
                    test_name_id=test_name_id,
                    device_id=self.current_base_config.device_id or "Unknown",
                    baud_rate=self.current_base_config.baud_rate,
                    data_bits=self.current_base_config.data_bits,
                    parity=self.current_base_config.parity,
                    stop_bits=self.current_base_config.stop_bits,
                    data_shift=self.current_base_config.data_shift,
                    handshake=self.current_base_config.handshake
                )
                if config_id:
                    test_result_data = f"Processed {successful_results}/{total_results} auto baud rate detection sets"
                    self.db.insert_test_result(
                        uart_config_id=config_id,
                        test_name=self.current_base_config.test_name,
                        tx_data="AUTO_BAUD_RATE_DETECTION",
                        tx_timestamp=datetime.now(),
                        rx_data=test_result_data,
                        rx_timestamp=datetime.now(),
                        status="Completed"
                    )
                    self.log_status("Auto baud rate detection summary saved to database.", level="info")

    def _on_test_case_changed(self, text: str):
        normalized = text.strip().upper()

        # Button text change
        if normalized == 'RECEPTION TEST':
            self.main_window.payload_panel.send_once_btn.setText('READ')
        else:
            self.main_window.payload_panel.send_once_btn.setText('SEND')

        # NEW: Switch stacked pages
        if normalized == 'AUTO BAUD RATE DETECTION':
            self.main_window.stacked_panel.setCurrentIndex(1)  # Auto Baud page
            self.main_window.animate_stack_switch()  # Animate
        elif normalized == 'BAUD RATE TESTING':
            self.main_window.stacked_panel.setCurrentIndex(2)  # Baud Rate page
            self.main_window.animate_stack_switch()
        else:
            self.main_window.stacked_panel.setCurrentIndex(0)  # Full form
            self.main_window.animate_stack_switch()

        # Existing layout switch
        if normalized in ['BAUD RATE TESTING', 'AUTO BAUD RATE DETECTION']:
            self.main_window.live_monitor.update_columns_for_baud_rate_tests(normalized)
            self.main_window.payload_panel.send_once_btn.setText('START TEST')
            logger.info(f"Switched to {normalized} layout")
        else:
            self.main_window.live_monitor.restore_default_columns()
            logger.info("Switched to DEFAULT layout")


    def _send_next_payload(self):
        if hasattr(self, "_send_count") and hasattr(self, "_repeat_count"):
            if self._send_count >= self._repeat_count:
                self._cyclic_timer.stop()
                self.main_window.payload_panel.send_cyclic_btn.setText("Send Cyclic")
                self.log_status("Cyclic sending finished after repeats.", level="info")
                self._send_count = 0
                return

            cfg = self._payload_list[self._pending_index]
            self.main_window.live_monitor.add_log_entry("Tx", cfg.message_data, str(cfg.data_length))

            message = self._build_transmission_message(cfg)
            response = self.send_data_to_labview_and_receive(message)

            # ... log, update UI as before ...

            self._save_test_result_to_db(cfg, response, "Pass" if response and not response.startswith("Error") else "No Response")

            self._pending_index = (self._pending_index + 1) % len(self._payload_list)
            self._send_count += 1
        else:
            # Fallback to default (in case repeat not set up)
            # Original logic...
            pass

    def send_config_to_labview(self, payload_config):
        """Send both base config and payload to LabVIEW in one message"""
        try:
            # Build complete configuration message
            message = self._build_transmission_message(payload_config)
            
            # Log what we're sending
            logger.debug(f"Complete message to LabVIEW:\n{message}")
            self.log_status(f"Sending config to LabVIEW ({len(message)} bytes)")
            
            # Send to LabVIEW
            response = self.backend.labview._send_ini_message(message, 12345)
            
            # Process response
            if response and not response.startswith("Error") and response != "No Response":
                # self.log_status(f"LabVIEW acknowledged: {response}")
                return response
            else:
                self.log_status(f"LabVIEW communication issue: {response}", level="warning")
                return response
                
        except Exception as e:
            error_msg = f"Error sending to LabVIEW: {e}"
            self.log_status(error_msg, level="error")
            logger.error(error_msg)
            return f"Error: {e}"

    def _get_or_create_test_name_id(self, test_name):
        test_type_id = self.db.get_test_type_id("UART Testing")
        if not test_type_id:
            self.log_status("UART Testing category not found.", level="error")
            return None
        # Normalize test name to uppercase for consistency
        test_name = test_name.upper()
        test_name_id = self.db.get_test_name_id(test_type_id, test_name)
        if not test_name_id:
            # Dynamically insert missing test name
            try:
                conn = self.db.connect()
                if conn:
                    with conn.cursor() as cur:
                        # Generate a new test name ID
                        cur.execute("SELECT COUNT(*) FROM test_names WHERE test_type_id = %s", (test_type_id,))
                        count = cur.fetchone()[0]
                        new_id = f"UART{count + 1:02d}"
                        cur.execute("""
                            INSERT INTO test_names (id, test_type_id, test_name)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (id) DO NOTHING
                            RETURNING id
                        """, (new_id, test_type_id, test_name))
                        test_name_id = cur.fetchone()[0]
                        conn.commit()
                        logger.info(f"Inserted test name '{test_name}' with ID {test_name_id}")
                    conn.close()
            except psycopg2.Error as e:
                self.log_status(f"Error inserting test name '{test_name}': {e}", level="error")
                logger.error(f"Error inserting test name: {e}")
                return None
        return test_name_id

    def _gather_base_config(self, log=True) -> Optional[UARTTestBaseConfig]:
        ui = self.main_window.test_selection
        try:
            parity_map = {"None": "0", "Even": "10", "Odd": "20"}
            stop_bits_map = {"0.5": 0.5, "1": 1.0, "1.5": 1.5, "2": 2.0}

            parity_code = parity_map.get(ui.parity.currentText(), "0")
            stop_bits_code = stop_bits_map.get(ui.stop_bits.currentText(), 1.0)

            self.base_config = UARTTestBaseConfig(
                test_name=ui.test_name.currentText().upper(),  # Normalize to uppercase
                device_id=ui.device_id.text().strip(),
                baud_rate=int(ui.baud_rate.currentText()),
                data_bits=int(ui.data_bits.currentText()),
                parity=parity_code,
                stop_bits=float(stop_bits_code),
                data_shift=ui.data_shift.currentText(),
                handshake=ui.handshake.currentText()
            )
            if log:
                self.log_status("Base configuration added.")
            return self.base_config
        except Exception as e:
            self.log_status(f"Error gathering base config: {e}", level="error")
            return None

    def _gather_payload_config(self) -> Optional[UARTPayloadConfig]:
        ui = self.main_window.payload_panel
        try:
            return UARTPayloadConfig(
                message_data=ui.data.text(),
                data_length=ui.data_length.value()
            )
        except Exception as e:
            self.log_status(f"Error gathering payload config: {e}", level="error")
            return None

    def _gather_payloads(self):
        table = self.main_window.transmit_table.table
        rows = table.rowCount()
        payloads = []

        for row in range(rows):
            def txt(c):
                item = table.item(row, c)
                return item.text() if item else ""

            data = txt(0)
            try:
                data_length = int(txt(1))
            except ValueError:
                data_length = 0

            payloads.append(
                UARTPayloadConfig(
                    message_data=data,
                    data_length=data_length,
                )
            )
        return payloads

    def delete_selected_transmit_row(self):
        logger.debug("delete_selected_transmit_row called")
        table = self.main_window.transmit_table.table
        selected_row = table.currentRow()
        if selected_row >= 0:
            table.removeRow(selected_row)
            if selected_row < len(self.payload_configs):
                self.payload_configs.pop(selected_row)
            self.log_status("Selected row deleted.", level="warning")
        else:
            self.log_status("No row selected to delete.", level="warning")

    def save_config(self, file_path: str):
        try:
            self._gather_base_config()
            if not self.base_config:
                self.log_status("Base configuration is missing.", level="warning")
                return

            payload_config = self._gather_payload_config()
            if not payload_config:
                self.log_status("Payload configuration is incomplete.", level="warning")
                return

            full_config = UARTFullConfig(
                base_config=self.base_config,
                payload_config=payload_config
            )

            with open(file_path, 'w') as f:
                json.dump(full_config, f, default=lambda o: o.__dict__, indent=4)

            self.log_status("Configuration saved successfully!")
        except Exception as e:
            self.log_status(f"Save error: {e}", level="error")

    def load_config(self, file_path: str):
        try:
            with open(file_path, 'r') as f:
                config_dict = json.load(f)

            base = config_dict.get("base_config")
            payload = config_dict.get("payload_config")

            if base:
                self.base_config = UARTTestBaseConfig(**base)
                self.current_base_config = self.base_config
                self._apply_base_config(self.base_config)
            else:
                self.base_config = None
                self.current_base_config = None

            if payload:
                payload_config = UARTPayloadConfig(**payload)
                self._apply_payload_config(payload_config)

            self.log_status("Configuration loaded successfully!")
        except Exception as e:
            self.log_status(f"Load error: {e}", level="error")

    def clear_config(self):
        """Clear all configuration fields."""
        self.base_config = None
        self.current_base_config = None
        self.payload_configs.clear()
        self.main_window.test_selection.device_id.clear()
        self.main_window.test_selection.baud_rate.setCurrentText("115200")
        self.main_window.test_selection.data_bits.setCurrentIndex(1)
        self.main_window.test_selection.parity.setCurrentIndex(0)
        self.main_window.test_selection.stop_bits.setCurrentIndex(1)
        self.main_window.test_selection.data_shift.setCurrentIndex(0)
        self.main_window.test_selection.handshake.setCurrentIndex(0)
        self.main_window.payload_panel.data.clear()
        self.main_window.payload_panel.data_length.setValue(0)
        self.main_window.transmit_table.table.setRowCount(0)
        self.log_status("All fields cleared.", level="info")

    def _apply_base_config(self, config: UARTTestBaseConfig):
        ui = self.main_window.test_selection
        ui.test_name.setCurrentText(config.test_name)
        ui.device_id.setText(config.device_id)
        ui.baud_rate.setCurrentText(str(config.baud_rate))
        ui.data_bits.setCurrentText(str(config.data_bits))
        # Map parity back to UI values
        parity_map = {"0": "None", "10": "Even", "20": "Odd"}
        ui.parity.setCurrentText(parity_map.get(config.parity, "None"))
        ui.stop_bits.setCurrentText(str(config.stop_bits))
        ui.data_shift.setCurrentText(config.data_shift)
        ui.handshake.setCurrentText(config.handshake)

    def _apply_payload_config(self, config: UARTPayloadConfig):
        ui = self.main_window.payload_panel
        ui.data.setText(config.message_data or "")
        ui.data_length.setValue(config.data_length)

    def _build_transmission_message(self, payload_config):
        """Build proper INI format message for LabVIEW"""
        # Map stop bits to LabVIEW format
        stop_bits_map = {0.5: 5, 1.0: 10, 1.5: 15, 2.0: 20}
        stop_bits_lv = stop_bits_map.get(float(self.current_base_config.stop_bits), 10)
        
        message = "[SerialPort]\n"
        message += f"test_name = {self.current_base_config.test_name}\n"
        message += f"device_id = {self.current_base_config.device_id}\n"
        message += f"baud_rate = {self.current_base_config.baud_rate}\n"
        message += f"databits = {self.current_base_config.data_bits}\n"  # Note: databits not data_bits
        message += f"parity = {self.current_base_config.parity}\n"
        message += f"stop_bits = {stop_bits_lv}\n"  # Use LabVIEW format
        message += f"data_shift = {self.current_base_config.data_shift}\n"
        message += f"handshake = {self.current_base_config.handshake}\n"
        message += f"tx_data = {payload_config.message_data}\n"
        return message


    def send_data_to_labview_and_receive(self, message):
        try:
            logger.debug(f"Sending complete config to LabVIEW:\n{message}")
            
            # Use your LabVIEW service instead of direct socket
            response = self.backend.labview._send_ini_message(message, 12345)
            
            if response and not response.startswith("Error"):
                self.log_status(f"LabVIEW Response: {response}")
                logger.debug(f"LabVIEW communication Status: {response}")
                return response
            else:
                self.log_status("No response received from LabVIEW", level="warning")
                logger.debug("No response from LabVIEW")
                return "No Response"
                
        except Exception as e:
            self.log_status(f"Error communicating with LabVIEW: {e}", level="error")
            logger.debug(f"LabVIEW error: {e}")
            return f"Error: {e}"
        
    def closeEvent(self, event):
        if self.backend.labview.current_worker and self.backend.labview.current_worker.isRunning():
            self.backend.labview.current_worker.terminate()
            self.backend.labview.current_worker.wait()
        super().closeEvent(event)

class LabVIEWCommunicationThread(QThread):
    response_received = Signal(str)
    no_response = Signal()
    error_occurred = Signal(str)
    
    def __init__(self, message, wait_time=20):  # Increase wait_time to 20 seconds
        super().__init__()
        self.message = message
        self.wait_time = wait_time
        self.Status = None
        self.response_type = None

    def run(self):
        client_socket = None
        try:
            logger.debug(f"LabVIEW Thread - Message to send ({len(self.message)} bytes):\n{repr(self.message)}")
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(40)  # Increase total timeout to 40 seconds
            client_socket.connect(('127.0.0.1', 12345))
            logger.debug("Connected to LabVIEW successfully")
            
            message_to_send = self.message + "\r\n"
            message_bytes = message_to_send.encode('utf-8')
            logger.debug(f"Sending {len(message_bytes)} bytes (including terminator)")
            client_socket.sendall(message_bytes)
            logger.debug("All data sent to LabVIEW")
            
            client_socket.settimeout(20)  # Increase response timeout to 20 seconds
            logger.debug("Waiting for response from LabVIEW...")
            response = client_socket.recv(4096).decode('utf-8').strip()
            if response:
                self.Status = response
                self.response_type = 'response'
                self.response_received.emit(response)
            else:
                self.Status = "No Response"
                self.response_type = 'no_response'
                self.no_response.emit()
        except socket.timeout:
            self.Status = "No Response"
            self.response_type = 'no_response'
            self.no_response.emit()
        except Exception as e:
            self.Status = f"Error: {str(e)}"
            self.response_type = 'error'
            self.error_occurred.emit(str(e))
        finally:
            if client_socket:
                client_socket.close()