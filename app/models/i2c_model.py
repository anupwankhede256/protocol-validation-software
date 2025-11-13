from dataclasses import dataclass
from typing import Optional

@dataclass
class I2CTestBaseConfig:
    test_name: str
    device_address: str
    clock_speed: str
    addressing_mode: str
    register_address: str
    read_address: str  # Added for R/W test differentiation
    write_address: str  # Added for R/W test differentiation
    bus_mode: str

@dataclass
class I2CPayloadConfig:
    def __init__(self, message_data: str, data_length: int, register_size: int, register_address: Optional[str] = None):
        self.message_data = message_data
        self.data_length = data_length
        # Ensure register_size is always 8 or 16 bits
        if register_size not in [8, 16]:
            raise ValueError("register_size must be either 8 or 16 (bits)")
        self.register_size = register_size  # Store in bits
        self.register_address = register_address

@dataclass
class I2CFullConfig:
    base_config: Optional[I2CTestBaseConfig]
    payload_config: Optional[I2CPayloadConfig]