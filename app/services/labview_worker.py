# app/services/labview_worker.py
from PySide6.QtCore import QThread, Signal
import socket
import logging


class LabVIEWWorker(QThread):
    line_received = Signal(str)      # Emitted for each line
    finished = Signal(str)           # Emitted when done (full response)
    error = Signal(str)   
    progress      = Signal(int)         

    def __init__(self, message, host='127.0.0.1', port=12345):
        super().__init__()
        self.message = message
        self.host = host
        self.port = port
        self.logger = logging.getLogger(__name__)
        self._buffer = ""
        self._line_count = 0

    def run(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(120)
                self.logger.info(f"[Worker] Connecting to LabVIEW at {self.host}:{self.port}")
                sock.connect((self.host, self.port))

                if not self.message.endswith('\n'):
                    self.message += '\n'

                self.logger.info(f"[Worker] Sending message ({len(self.message)} bytes)")
                sock.sendall(self.message.encode('utf-8'))

                sock.settimeout(40)
                response_data = b""
                all_lines = []

                while True:
                    try:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break

                        response_data += chunk
                        text = chunk.decode('utf-8', errors='ignore')
                        self._buffer += text

                        lines = self._buffer.split('\n')
                        self._buffer = lines.pop() if lines else ""

                        for line in lines:
                            line = line.rstrip('\r')
                            if line.strip():
                                cleaned = ''.join(c for c in line if c.isprintable() or c in ',.-\t ')
                                all_lines.append(cleaned)
                                self._line_count += 1
                                self.logger.info(f"[Worker] Emitting line: {cleaned}")
                                self.line_received.emit(cleaned)
                                self.progress.emit(self._line_count)

                        if len(response_data) > 1024 * 1024:
                            break

                    except socket.timeout:
                        break

                # NEW: Emit full buffer as single line if no lines split
                if self._line_count == 0 and self._buffer.strip():
                    cleaned = ''.join(c for c in self._buffer if c.isprintable() or c in ',.-\t ')
                    if cleaned.strip():
                        all_lines.append(cleaned)
                        self._line_count += 1
                        self.logger.info(f"[Worker] Emitting full buffer as single line: {cleaned}")
                        self.line_received.emit(cleaned)
                        self.progress.emit(self._line_count)
                        self._buffer = ""

                # Final buffer flush
                if self._buffer.strip():
                    final = ''.join(c for c in self._buffer if c.isprintable() or c in ',.-\t ')
                    if final.strip():
                        all_lines.append(final)
                        self._line_count += 1
                        self.logger.info(f"[Worker] Emitting final line: {final}")
                        self.line_received.emit(final)
                        self.progress.emit(self._line_count)

                full = '\n'.join(all_lines)
                if full.startswith('\ufeff'):
                    full = full[1:]

                self.finished.emit(full)

        except Exception as e:
            self.error.emit(f"Error: {e}")