from typing import Optional, List
import json
import time
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QTableWidgetItem
from app.models.i2c_model import I2CTestBaseConfig, I2CPayloadConfig, I2CFullConfig
from app.services.i2c_backend import I2CBackend
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class I2CController:
    def __init__(self, main_window):
        self.main_window = main_window
        self.backend = I2CBackend()
        self._cyclic_timer = QTimer()
        self.payload_configs: List[I2CPayloadConfig] = []
        self.current_base_config: Optional[I2CTestBaseConfig] = None
        self.base_config: Optional[I2CTestBaseConfig] = None  # Keep for legacy, but prefer current_base_config
        self._connect_signals()

    def _connect_signals(self):
        buttons = [
            (self.main_window.payload_panel.add_btn, self.add_payload_to_table, "Add"),
            (self.main_window.payload_panel.del_btn, self.delete_selected_transmit_row, "Delete"),
            (self.main_window.test_selection.add_config_btn, self._on_add_config, "Add Config"),
            (self.main_window.payload_panel.send_btn, self._on_send, "SEND")
        ]
        for button, slot, name in buttons:
            button.clicked.connect(slot)
            logger.debug(f"Connected signal for {name} button")
        # Connect test case changes to update payload panel UI
        self.main_window.test_selection.test_case.currentTextChanged.connect(self.on_test_case_changed)

    def log_status(self, message: str, duration: int = 4000, level: str = "info"):
        self.main_window.status_panel.append_message(message, level)
        logger.debug(f"Status logged: {message} ({level})")

    def on_test_case_changed(self, test_case: str):
        logger.debug(f"Test case changed to: {test_case}")
        self.main_window.payload_panel.update_for_test_case(test_case)
        self.main_window.live_monitor.update_columns_for_test_case(test_case)

    def add_payload_to_table(self):
        logger.debug("add_payload_to_table called")
        if not self.current_base_config:
            self.log_status("Please add I2C configuration first!", level="warning")
            return

        payload_config = self._gather_payload_config()
        if not payload_config:
            self.log_status("Failed to gather payload config.", level="warning")
            return

        test_case = self.main_window.test_selection.test_case.currentText()
        is_read_test = test_case == "Read Test"

        if is_read_test:
            if not payload_config.register_address.strip():
                self.log_status("Register address is required for Read Test.", level="warning")
                return
            write_data = "Read Request"  # Placeholder for read test
            data_length = self.main_window.payload_panel.read_length.value()
        else:
            raw_write_data = payload_config.message_data.strip()
            if not raw_write_data:
                self.log_status("Invalid or empty payload input.", level="warning")
                return

            # CHANGED: Always 0xXX (2 hex digits) for write data, regardless of register size
            expected_len = 4  # Always 0xXX
            zfill_width = 2  # Always pad to 2 hex digits

            values = []
            for v in raw_write_data.split():
                v = v.strip().lower()
                if v and not v.startswith('0x'):
                    v = '0x' + v.zfill(zfill_width)
                values.append(v)

            num_values = len(values)
            if num_values == 0:
                self.log_status("No valid data values provided.", level="warning")
                return

            # Validation: Always expect 0xXX
            for v in values:
                if not (v.startswith('0x') and len(v) == expected_len):
                    self.log_status(f"Invalid value: {v} (expected 0xXX for 8-bit or 0xXX for 16-bit)", level="warning")
                    return

            write_data = ' '.join(values)
            data_length = num_values  # Each value is 1 byte

        self.main_window.transmit_table.add_entry(
            address=self.current_base_config.device_address,
            data=write_data,
            data_length=str(data_length)
        )
        if is_read_test:
            payload_config.message_data = ""
            payload_config.data_length = data_length
        self.payload_configs.append(payload_config)
        self.log_status("Payload added to I2C transmit table.")

    def _on_send(self):
        logger.debug("SEND button clicked")
        if not self.current_base_config:
            self.log_status("Add Config first!", level="warning")
            return

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

        test_case = self.main_window.test_selection.test_case.currentText()
        is_read_test = test_case == "Read Test"

        register_size = int(self.main_window.payload_panel.register_size.currentText())
        register_address = self.main_window.payload_panel.register_address.text().strip()

        tx_timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        try:
            if is_read_test:
                data_length = self.main_window.payload_panel.read_length.value()
                message_data = ""
            else:
                # CHANGED: Always 0xXX (2 hex digits) for write data, regardless of register size
                raw_message_data = txt(1).strip()
                if not raw_message_data:
                    raise ValueError("Empty message data")

                expected_len = 4  # Always 0xXX
                zfill_width = 2  # Always pad to 2 hex digits

                values = []
                for v in raw_message_data.split():
                    v = v.strip().lower()
                    if v and not v.startswith('0x'):
                        v = '0x' + v.zfill(zfill_width)
                    values.append(v)

                num_values = len(values)
                if num_values == 0:
                    raise ValueError("No valid values")

                # Validation: Always expect 0xXX
                for v in values:
                    if not (v.startswith('0x') and len(v) == expected_len):
                        self.log_status(f"Invalid value in table: {v} (expected 0xXX for 8-bit or 0xXX for 16-bit)", level="warning")
                        return

                message_data = ' '.join(values)
                data_length = num_values  # Each value is 1 byte
        except ValueError:
            # CHANGED: Improved fallback
            data_length = 1 if is_read_test else 1
            message_data = ""

        cfg = I2CPayloadConfig(
            message_data=message_data,
            data_length=data_length,
            register_size=register_size,
            register_address=register_address
        )

        response = self.send_config_to_labview(cfg)
        rx_timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        if response.startswith("Error:"):
            result = "Error"
            ack_nack = "NACK"
            rx_data = ""
            self.log_status(f"Error: {response}", level="error")
        elif response == "No Response":
            result = "No Response"
            ack_nack = "NACK"
            rx_data = ""
            self.log_status("No response from LabVIEW", level="warning")
        else:
            ack_nack = "ACK" if "ACK" in response else "NACK"
            if is_read_test:
                # Process the received data from LabVIEW
                try:
                    # Log the raw response for debugging
                    self.log_status(f"Raw LabVIEW response: {response}", level="info")
                    
                    # Clean and split the response
                    clean_response = response.replace('\r', '').strip()
                    if '\n' in clean_response:
                        values = []
                        for val in clean_response.split('\n'):
                            try:
                                if val.strip():
                                    num = float(val.strip())
                                    values.append(f"{num:.3f}")
                            except ValueError:
                                continue
                        rx_data = ', '.join(values) if values else "No valid data"
                    else:
                        # Single value response
                        try:
                            num = float(clean_response)
                            rx_data = f"{num:.3f}"
                        except ValueError:
                            rx_data = clean_response
                    
                    result = "Data received successfully" if rx_data and rx_data != "No valid data" else "No valid data received"
                    self.log_status(f"Processed data: {rx_data}", level="info")
                except Exception as e:
                    rx_data = str(response)
                    result = f"Error processing data: {str(e)}"
                    self.log_status(f"Error processing response: {str(e)}", level="error")
            else:
                result = "Data sent successfully"
                rx_data = ""

        test_case = self.main_window.test_selection.test_case.currentText()
        now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        if test_case.upper() == "READ TEST":
            self.main_window.live_monitor.add_log_entry(
                test_case=test_case,
                register_address=register_address,
                rw_bit="1",          # Always "1" for read
                data=rx_data if rx_data and rx_data != "No valid data" else "No data",
                tx_timestamp="",         # Not used
                rx_timestamp=now,        # Use current time for receive
                result=result
            )
        elif test_case.upper() == "WRITE TEST":
            self.main_window.live_monitor.add_log_entry(
                test_case=test_case,
                register_address=register_address,
                rw_bit="0",          # Always "0" for write
                data=message_data,
                tx_timestamp=now,        # Use current time for transmit
                rx_timestamp="",         # Not used
                result=result,  # CHANGED: Use dynamic result instead of hardcoded
                # comment=""
            )

        # if hasattr(self.main_window.live_monitor, 'current_row') and self.main_window.live_monitor.current_row >= 0:
        #     row = self.main_window.live_monitor.current_row
        #     result_item = QTableWidgetItem(result)
        #     result_item.setTextAlignment(Qt.AlignCenter)
        #     self.main_window.live_monitor.table.setItem(row, 6, result_item)

        self.log_status(f"LabVIEW Response: {response}")

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

    def send_config_to_labview(self, payload_config: I2CPayloadConfig):
        try:
            message = self.backend.i2c_service._build_ini_message((self.current_base_config, payload_config))
            response = self.backend.i2c_service._send_ini_message(message, self.backend.i2c_service.send_port)
            if response and not response.startswith("Error") and response != "No Response":
                self.log_status("Data sent successfully to LabVIEW")
                return response
            else:
                self.log_status(f"LabVIEW communication issue: {response}", level="warning")
                return response
        except Exception as e:
            error_msg = f"Error sending to LabVIEW: {e}"
            self.log_status(error_msg, level="error")
            logger.error(error_msg)
            return f"Error: {e}"

    def _on_add_config(self):
        logger.debug("ADD CONFIG button clicked")
        base_config = self._gather_base_config()
        if not base_config:
            self.log_status("Failed to gather I2C base configuration.", level="error")
            return

        self.current_base_config = base_config
        self.base_config = base_config  # Sync for legacy
        self.log_status("I2C Configuration saved locally.")

        try:
            self.log_status("Opening LabVIEW I2C VI...")
            process = self.backend.i2c_service.launch_vi()
            time.sleep(5)
            self.log_status("LabVIEW I2C VI initialization complete. Ready to send data.")
            if process:
                self.log_status("LabVIEW I2C VI opened successfully!")
                logger.debug("LabVIEW I2C VI launched successfully")
            else:
                self.log_status("Failed to open LabVIEW I2C VI.", level="error")
        except Exception as e:
            self.log_status(f"Error opening LabVIEW I2C VI: {e}", level="error")
            logger.error(f"Error launching LabVIEW I2C VI: {e}")

    def _gather_base_config(self, log=True) -> Optional[I2CTestBaseConfig]:
        ui = self.main_window.test_selection
        try:
            device_address = getattr(ui, '_original_address', ui.device_address.text().strip())
            config = I2CTestBaseConfig(
                test_name=ui.test_case.currentText().upper(),
                device_address=device_address,
                clock_speed=ui.speed_mode.currentText(),
                addressing_mode=ui.address_mode.currentText(),
                register_address=ui.read_address.text().strip(),
                read_address=ui.read_address.text().strip(),
                write_address=ui.write_address.text().strip(),
                bus_mode=ui.frame_format.currentText()
            )
            self.base_config = config  # Sync
            if log:
                self.log_status(f"I2C Base configuration added with device address {device_address}")
            return config
        except Exception as e:
            self.log_status(f"Error gathering I2C base config: {e}", level="error")
            return None

    def _gather_payload_config(self) -> Optional[I2CPayloadConfig]:
        ui = self.main_window.payload_panel
        try:
            register_size = int(ui.register_size.currentText())
            register_address = ui.register_address.text().strip()
            if register_address:
                if not register_address.lower().startswith('0x'):
                    register_address = '0x' + register_address.zfill(2 if register_size == 8 else 4)
                else:
                    addr_value = register_address[2:].zfill(2 if register_size == 8 else 4)
                    register_address = '0x' + addr_value
                register_address = register_address.lower()

            # CHANGED: Always compute for 0xXX (2 hex digits)
            raw_message_data = ui.data.text().strip()
            message_data = raw_message_data  # Will be processed later if needed
            if raw_message_data:
                expected_len = 4  # Always 0xXX
                zfill_width = 2  # Always pad to 2 hex digits
                values = []
                for v in raw_message_data.split():
                    v = v.strip().lower()
                    if v and not v.startswith('0x'):
                        v = '0x' + v.zfill(zfill_width)
                    values.append(v)
                num_values = len([v for v in values if v.startswith('0x') and len(v) == expected_len])
                data_length = num_values  # Each is 1 byte
            else:
                data_length = 0

            return I2CPayloadConfig(
                message_data=message_data,
                data_length=data_length,
                register_address=register_address,
                register_size=register_size
            )
        except Exception as e:
            self.log_status(f"Error gathering I2C payload config: {e}", level="error")
            return None

    def _gather_payloads(self):
        table = self.main_window.transmit_table.table
        rows = table.rowCount()
        payloads = []
        for row in range(rows):
            def txt(c):
                item = table.item(row, c)
                return item.text() if item else ""
            try:
                data_length = int(txt(2))
            except ValueError:
                data_length = 0
            payloads.append(
                I2CPayloadConfig(
                    message_data=txt(1),
                    data_length=data_length
                )
            )
        return payloads

    def save_config(self, file_path: str):
        try:
            self._gather_base_config(log=False)
            if not self.current_base_config:
                self.log_status("I2C Base configuration is missing.", level="warning")
                return

            payload_config = self._gather_payload_config()
            if not payload_config:
                self.log_status("I2C Payload configuration is incomplete.", level="warning")
                return

            full_config = I2CFullConfig(
                base_config=self.current_base_config,
                payload_config=payload_config
            )

            with open(file_path, 'w') as f:
                json.dump(full_config, f, default=lambda o: o.__dict__, indent=4)
            self.log_status("I2C Configuration saved successfully!")
        except Exception as e:
            self.log_status(f"Save error: {e}", level="error")

    def load_config(self, file_path: str):
        try:
            with open(file_path, 'r') as f:
                config_dict = json.load(f)

            base = config_dict.get("base_config")
            payload = config_dict.get("payload_config")

            if base:
                self.base_config = I2CTestBaseConfig(**base)
                self.current_base_config = self.base_config
                self._apply_base_config(self.base_config)
            else:
                self.base_config = None
                self.current_base_config = None

            if payload:
                payload_config = I2CPayloadConfig(**payload)
                self._apply_payload_config(payload_config)

            self.log_status("I2C Configuration loaded successfully!")
        except Exception as e:
            self.log_status(f"Load error: {e}", level="error")

    def clear_config(self):
        self.base_config = None
        self.current_base_config = None
        self.payload_configs.clear()
        self.main_window.test_selection.test_case.setCurrentIndex(0)
        self.main_window.test_selection.device_address.clear()
        self.main_window.test_selection.speed_mode.setCurrentText("Standard (100 kHz)")
        self.main_window.test_selection.address_mode.setCurrentText("7-bit")
        self.main_window.test_selection.read_address.clear()
        self.main_window.test_selection.write_address.clear()
        # self.main_window.test_selection.bus_mode.setCurrentText("Standard") # remove or add if you need bus mode
        panel = self.main_window.payload_panel
        panel.data.clear()
        panel.write_length.setValue(1)
        panel.register_address.clear()
        panel.register_size.setCurrentIndex(0)
        self.main_window.transmit_table.table.setRowCount(0)
        self.log_status("All I2C fields cleared.", level="info")

    def _apply_base_config(self, config: I2CTestBaseConfig):
        ui = self.main_window.test_selection
        ui.test_case.setCurrentText(config.test_name)  # CHANGED: Use test_name from model
        ui.device_address.setText(config.device_address)
        ui.speed_mode.setCurrentText(config.speed_mode)
        ui.address_mode.setCurrentText(config.address_mode)
        ui.read_address.setText(config.read_address)
        ui.write_address.setText(config.write_address)
        # ui.bus_mode.setCurrentText(config.bus_mode) # remove or add if you need bus mode

    def _apply_payload_config(self, config: I2CPayloadConfig):
        ui = self.main_window.payload_panel
        ui.data.setText(config.message_data or "")
        ui.write_length.setValue(config.data_length)
        ui.register_address.setText(getattr(config, 'register_address', ''))
        # Set register size (8 or 16 bits)
        if hasattr(config, 'register_size'):
            ui.register_size.setCurrentText(str(config.register_size))

    def _build_transmission_message(self, payload_config: I2CPayloadConfig):
        """Build I2C transmission message for LabVIEW"""
        if not self.current_base_config:
            raise ValueError("No base configuration available")
            
        message = "[I2CConfig]\n"
        # Add base configuration
        message += f"test_name = {self.current_base_config.test_name}\n"
        message += f"device_address = {self.current_base_config.device_address}\n"
        message += f"clock_speed = {self.current_base_config.clock_speed}\n"
        message += f"addressing_mode = {self.current_base_config.addressing_mode}\n"
        message += f"register_address = {self.current_base_config.register_address}\n"
        message += f"bus_mode = {self.current_base_config.bus_mode}\n"
        
        # Add payload configuration
        message += f"register_size = {payload_config.register_size}\n"
        message += f"tx_data = {payload_config.message_data}\n"
        message += f"data_length = {payload_config.data_length}\n"
        
        logger.debug(f"Built I2C message:\n{message}")
        return message