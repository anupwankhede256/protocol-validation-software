import logging
from app.services.i2c_labview_service import I2CService
from app.models.i2c_model import I2CTestBaseConfig, I2CPayloadConfig

class I2CBackend:
    def __init__(self, host='127.0.0.1', send_port=9561, receive_port=9562):
        self.logger = logging.getLogger(__name__)
        self.i2c_service = I2CService(host, send_port, receive_port)

    def send_base_config(self, base_config: I2CTestBaseConfig):
        self.logger.info(f"Sending I2C base_config: {base_config}")
        return self.i2c_service.send_base_config(base_config)

    def send_payload(self, payload_config: I2CPayloadConfig):
        self.logger.info(f"Sending I2C payload: {payload_config}")
        return self.i2c_service.send_payload(payload_config)

    def receive_response(self):
        return self.i2c_service.receive_response()