# app/services/uart_backend.py
import logging
from app.services.labview_service import LabVIEWService

class UARTBackend:
    def __init__(self, host='127.0.0.1', send_port=12345, receive_port=12346):
        self.logger = logging.getLogger(__name__)
        self.labview = LabVIEWService(host, send_port, receive_port)
        
    def send_base_config(self, base_config):
        self.logger.info(f"Sending base_config: {base_config}")
        return self.labview.send_base_config(base_config)

    def send_payload(self, payload_config):
        self.logger.info(f"Sending payload: {payload_config}")
        return self.labview.send_payload(payload_config)

    def receive_response(self):
        return self.labview.receive_response()