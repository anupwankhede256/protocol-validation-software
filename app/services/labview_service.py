# app/services/labview_service.py
import socket
import subprocess
import select
import logging
from PySide6.QtCore import QObject, Signal  # <-- CRITICAL IMPORT
from app.models.uart_model import UARTTestBaseConfig, UARTPayloadConfig
from app.services.labview_worker import LabVIEWWorker


class LabVIEWService(QObject):  # <-- MUST INHERIT FROM QObject
    line_received = Signal(str)  # <-- DEFINE THE SIGNAL HERE
    progress = Signal(int)
    finished = Signal(str)

    def __init__(self, host='127.0.0.1', send_port=12345, receive_port=12346):
        super().__init__()  # <-- CALL SUPER!
        self.logger = logging.getLogger(__name__)
        self.server_ip = host
        self.send_port = send_port
        self.receive_port = receive_port
        self.vi_file = r"C:\Users\sandbox\Downloads\UART ALL TEST CASES (1).vi"
        self.lv_shortcut = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\NI LabVIEW 2025 Q1 (64-bit).lnk"
        self.current_worker = None

    def launch_vi(self):
        cmd = f'"{self.lv_shortcut}" "{self.vi_file}"'
        try:
            p = subprocess.Popen(cmd, shell=True)
            self.lv_process = p
            self.logger.info("Launched LabVIEW VI")
            return p
        except Exception as e:
            self.logger.error(f"Failed to launch VI: {e}")
            return None
        
    def stop(self):
        self.logger.info("STOP requested - cleaning up LabVIEW resources")

        #worker thread
        if self.current_worker and self.current_worker.isRunning():
            self.logger.info("Terminating LabVIEWWorker thread...")
            self.current_worker.terminate()
            self.current_worker.wait(3000)
            self.current_worker(None)

        #LabVIEW VI process:-
        if self.lv_process:
            try:
                self.logger.info("Terminating LabVIEW VI process...")
                self.lv_process.terminate()
                self.lv_process.wait(5000)
            except Exception as e:
                self.logger.error(f"Failed to kill LabVIEW process: {e}")
            finally:
                self.lv_process=None

    def send_base_config(self, base_config):
        ini_message = self._build_ini_message(base_config)
        return self._send_ini_message(ini_message, self.send_port)

    def send_payload(self, payload_config):
        ini_message = self._build_ini_message(payload_config)
        return self._send_ini_message(ini_message, self.send_port)

    def _build_ini_message(self, config):
        stop_bits_map_lv = {0.5: 5, 1.0: 10, 1.5: 15, 2.0: 20}
        lines = ["[SerialPort]"]

        if isinstance(config, UARTTestBaseConfig):
            for key, value in config.__dict__.items():
                if key in ['test_name', 'device_id', 'baud_rate', 'parity', 'stop_bits', 'databits', 'data_shift', 'handshake']:
                    if key == 'stop_bits':
                        value = stop_bits_map_lv.get(value, 10)
                    lines.append(f"{key} = {value}")
            return "\n".join(lines)

        elif isinstance(config, UARTPayloadConfig):
            for key, value in config.__dict__.items():
                if key == 'message_data':
                    lines.append(f"tx_data = {value}")
            return "\n".join(lines)

        return "\n".join(lines)
    # Replace _send_ini_message with this:
    def _send_ini_message(self, message, port):
        """Start a background worker – keep it alive until done."""
        # Cancel any previous worker
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.terminate()
            self.current_worker.wait(3000)

        self.current_worker = LabVIEWWorker(message, self.server_ip, port)

        # Forward signals
        self.current_worker.line_received.connect(self.line_received)
        self.current_worker.progress.connect(self.progress)
        self.current_worker.finished.connect(self._on_worker_finished)
        self.current_worker.error.connect(self._on_worker_error)

        # Keep worker alive until finished
        self.current_worker.finished.connect(self.current_worker.deleteLater)
        self.current_worker.error.connect(self.current_worker.deleteLater)
        # ALSO: Connect to clear reference
        self.current_worker.finished.connect(lambda: setattr(self, 'current_worker', None))
        self.current_worker.error.connect(lambda: setattr(self, 'current_worker', None))

        self.current_worker.start()
        return "Sent (async)"
    
    def _on_worker_finished(self, full_response):
        self.logger.info(f"Worker finished. Full response: {len(full_response)} chars")
        self.finished.emit(full_response)
        # Optional: store response if needed

    def _on_worker_error(self, msg):
        self.logger.error(f"LabVIEW Worker error: {msg}")
        self.current_worker = None


    def receive_response(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((self.server_ip, self.receive_port))
                s.listen(1)
                s.setblocking(False)
                self.logger.info(f"Listening for LabVIEW response on {self.server_ip}:{self.receive_port}")
                ready = select.select([s], [], [], 30)  # 30 sec timeout
                if ready[0]:
                    conn, addr = s.accept()
                    with conn:
                        self.logger.info(f"Connected by {addr}")
                        data = conn.recv(1024)
                        response = data.decode('utf-8').strip()
                        self.logger.info(f"Received response data: {response}")
                        return response
                else:
                    self.logger.warning("Timeout waiting for LabVIEW response")
                    return None
        except Exception as e:
            self.logger.error(f"Error receiving LabVIEW response: {e}")
            return None