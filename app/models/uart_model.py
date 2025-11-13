# app/models/uart_model.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class UARTTestBaseConfig:
    test_name: str
    device_id: str
    baud_rate: int
    stop_bits: float
    parity: str
    data_bits: int
    data_shift: str
    handshake: str

@dataclass
class UARTPayloadConfig:
    message_data: str
    data_length: int

@dataclass
class UARTFullConfig:
    base_config: UARTTestBaseConfig
    payload_config: UARTPayloadConfig