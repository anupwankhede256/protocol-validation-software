import socket
import subprocess
import select
import logging
from app.models.i2c_model import I2CTestBaseConfig, I2CPayloadConfig,I2CFullConfig

class I2CService:
    def __init__(self, host='127.0.0.1', send_port=9561, receive_port=9562):
        self.logger = logging.getLogger(__name__)
        self.server_ip = host
        self.send_port = send_port
        self.receive_port = receive_port
        self.vi_file = r"C:\Users\sandbox\Downloads\i2c all test cases.vi" # Update to your I2C VI file
        self.lv_shortcut = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\NI LabVIEW 2025 Q1 (64-bit).lnk"
    
    def launch_vi(self):
        import time
        cmd = f'"{self.lv_shortcut}" "{self.vi_file}"'
        try:
            p = subprocess.Popen(cmd, shell=True)
            self.logger.info("Launching LabVIEW I2C VI...")
            
            # Wait for LabVIEW to initialize (5 seconds)
            time.sleep(5)
            self.logger.info("LabVIEW I2C VI launched and initialized")
            return p
        except Exception as e:
            self.logger.error(f"Failed to launch I2C VI: {e}")
            return None

    def send_base_config(self, base_config: I2CTestBaseConfig):
        ini_message = self._build_ini_message(base_config)
        return self._send_ini_message(ini_message, self.send_port)

    def send_payload(self, payload_config: I2CPayloadConfig):
        ini_message = self._build_ini_message(payload_config)
        return self._send_ini_message(ini_message, self.send_port)
    def _split_register_address(self, register_address: str, register_size: int) -> str:
        """
        Convert register address(es) into LabVIEW-compatible format.
        - Single address (8-bit):  '0xAB'
        - Single address (16-bit): '0xAB', '0xCD'
        - Multiple addresses:     '0xFA', '0xFB', '0xFC'
        """
        if not register_address or not register_address.strip():
            return ""

        # Split by whitespace and clean up
        tokens = [token.strip().lower() for token in register_address.split() if token.strip()]
        result_parts = []

        for token in tokens:
            if not token.startswith('0x'):
                token = '0x' + token.lstrip('0')
            
            # Remove 0x prefix for processing
            hex_part = token[2:]
            
            if register_size == 16:
                # Pad to 4 hex digits and split into high/low
                hex_part = hex_part.zfill(4)
                high = '0x' + hex_part[:2].upper()
                low = '0x' + hex_part[2:].upper()
                result_parts.extend([f"'0xhigh'",f"'0xlow'"])
            else:
                # 8-bit: pad to 2 digits
                hex_part = hex_part.zfill(2)
                result_parts.append('0x' + hex_part.upper())

        # Join with comma and space, wrapped in quotes
        final_result = ", ".join(result_parts)
        final_result=final_result.replace("'","'")
        self.logger.info(f"register_address input: '{register_address}' → LabVIEW format: {final_result}")
        return final_result
    # def _split_register_address(self, register_address: str, register_size: int) -> str:
    #     """Split 16-bit register address into two 8-bit addresses if needed."""
    #     if not register_address:
    #         return ""
        
    #     # Remove 0x prefix and ensure lowercase
    #     addr = register_address.lower().replace('0x', '')
        
    #     if register_size == 16:
    #         # For 16-bit, ensure we have 4 digits and split into two 8-bit values
    #         addr = addr.zfill(4)  # Pad with leading zeros if needed
    #         high_byte = addr[:2]
    #         low_byte = addr[2:]
    #         self.logger.info(f"Splitting 16-bit address {register_address} into high: 0x{high_byte}, low: 0x{low_byte}")
    #         return f"'0x{high_byte}', '0x{low_byte}'"  # Return as '0xHH', '0xLL' with space for readability
        
    #     # For 8-bit, ensure we have 2 digits
    #     addr = addr.zfill(2)
    #     self.logger.info(f"Using 8-bit address: 0x{addr}")
    #     return f"'0x{addr}'"  # Return as '0xBB'

    # def _split_register_address(self, register_address: str, register_size: int) -> str:
    #     """Split 16-bit register address into two 8-bit addresses if needed."""
    #     if not register_address:
    #         return ""
        
    #     # Remove 0x prefix and ensure uppercase
    #     addr = register_address.upper().replace('0x', '')
        
    #     if register_size == 16:
    #         # For 16-bit, ensure we have 4 digits and split into two 8-bit values
    #         addr = addr.zfill(4)  # Pad with leading zeros if needed
    #         high_byte = addr[:2]
    #         low_byte = addr[2:]
    #         self.logger.info(f"Splitting 16-bit address {register_address} into high: 0x{high_byte}, low: 0x{low_byte}")
    #         return f"'0x{high_byte}', '0x{low_byte}'"  # Return as '0xHH', '0xLL' with space for readability
        
    #     # For 8-bit, ensure we have 2 digits
    #     addr = addr.zfill(2)
    #     self.logger.info(f"Using 8-bit address: 0x{addr}")
    #     return f"'0x{addr}'"  # Return as '0xBB'

    def _build_ini_message(self, config):
        lines = ["[I2CConfig]"]
        
        if isinstance(config, I2CTestBaseConfig):
            # Handle base config
            for key, value in config.__dict__.items():
                if key in ['test_name', 'clock_speed', 'addressing_mode', 'bus_mode']:
                    lines.append(f"{key} = {value}")
                elif key == 'device_address':
                    lines.append(f"device_address = '{value}'")  # Wrap in quotes for hex string
                elif key == 'register_address':
                    # For read/write tests, use the appropriate address
                    if 'test_name' in config.__dict__:
                        test_name = config.__dict__['test_name']
                        if test_name == 'READ TEST':
                            address = config.read_address
                        elif test_name == 'WRITE TEST':
                            address = config.write_address
                        else:
                            address = value  # Use default register_address for other tests
                        lines.append(f"register_address = {self._split_register_address(address, 8)}")  # Default to 8-bit for base config

                # NEW: Always include read_address and write_address if present (for LabVIEW to access from GUI)
            if config.read_address:
                lines.append(f"read_address = '{config.read_address}'")
                self.logger.info(f"Adding read_address: {config.read_address}")
            if config.write_address:
                lines.append(f"write_address = '{config.write_address}'")
                self.logger.info(f"Adding write_address: {config.write_address}")
        elif isinstance(config, I2CPayloadConfig):
            # Handle payload config
            lines.append(f"write_data = '{config.message_data}'")  # Wrap in quotes to ensure string format
            lines.append(f"write_length = {config.data_length}")
            # Ensure we're sending register size in bits (8 or 16)
            lines.append(f"register_size = {config.register_size}")  # This should be 8 or 16
            if config.register_address:
                # Split register address based on register size
                formatted_address = self._format_register_address(config.register_address)
                split_addr = self._split_register_address(formatted_address, config.register_size)
                lines.append(f"register_address = {split_addr}")
                
                self.logger.info(f"Register address for LabVIEW: {split_addr}")
        elif isinstance(config, tuple) and len(config) == 2:
            # Handle combined base config and payload
            base_config, payload_config = config
            test_name = base_config.test_name
            
            # Add base config with original device address and read/write addresses
            lines.extend([
                f"test_name = {base_config.test_name}",
                f"device_address = '{base_config.device_address}'",  # Original 7-bit address
                f"clock_speed = {base_config.clock_speed}",
                f"addressing_mode = {base_config.addressing_mode}",
                f"bus_mode = {base_config.bus_mode}"
            ])

            # Add read/write addresses based on test type
            if base_config.read_address:
                lines.append(f"read_address = '{base_config.read_address}'")
                self.logger.info(f"Adding read_address: {base_config.read_address}")
            if base_config.write_address:
                lines.append(f"write_address = '{base_config.write_address}'")
                self.logger.info(f"Adding write_address: {base_config.write_address}")

            # Add payload config
            lines.extend([
                f"write_data = '{payload_config.message_data}'",  # Wrap in quotes to ensure string format
                f"write_length = {payload_config.data_length}",
                f"register_size = {payload_config.register_size}"  # This should be 8 or 16
            ])
            
            # Add register address from payload config
            if payload_config.register_address:
                split_addr = self._split_register_address(payload_config.register_address, payload_config.register_size)
                self.logger.info(f"Sending register address as {split_addr} with size {payload_config.register_size}")
                lines.append(f"register_address = {split_addr}")
            # Also include the base register address if different
            elif base_config.register_address:
                split_addr = self._split_register_address(base_config.register_address, 8)  # Default to 8-bit for base config
                self.logger.info(f"Using base config register address: {split_addr}")
                lines.append(f"register_address = {split_addr}")

        return "\n".join(lines)
    
    # def _format_register_address(self, address_str: str) -> str:
    #     # Split by spaces
    #     tokens = address_str.strip().split()
    #     formatted_tokens = []
    #     for t in tokens:
    #         t = t.upper()
    #         if not t.startswith('0x'):
    #             t = '0x' + t
    #         formatted_tokens.append(t)
    #     return','.join(formatted_tokens)


    def _send_ini_message(self, message, port):
        try:
            import time
            # Add initial delay to ensure LabVIEW is ready
            time.sleep(2)  # Wait 2 seconds before attempting connection
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # Set a longer initial timeout for connection
                sock.settimeout(30)  # 30 seconds timeout for initial connection
                self.logger.info(f"Connecting to LabVIEW at {self.server_ip}:{port}")
                
                # Try to connect with retry
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        sock.connect((self.server_ip, port))
                        break
                    except socket.error as e:
                        if attempt < max_retries - 1:
                            self.logger.warning(f"Connection attempt {attempt + 1} failed, retrying in 2 seconds...")
                            time.sleep(2)
                        else:
                            raise e
                
                if not message.endswith('\n'):
                    message += '\n'
                
                self.logger.info(f"Sending INI message ({len(message)} bytes):\n{message}")
                sock.sendall(message.encode('utf-8'))
                
                # Wait a moment after sending before trying to receive
                time.sleep(1)
                
                sock.settimeout(50)  # 20 second timeout for receiving response
                response = sock.recv(4096).decode('utf-8', errors='ignore').strip()
                print("response received:", response)
                cleaned_response = ''.join(char for char in response if char.isprintable() or char.isspace())
                if cleaned_response.startswith('\ufeff'):
                    cleaned_response = cleaned_response[1:]
                
                self.logger.info(f"Raw response bytes: {response.encode('utf-8')}")
                self.logger.info(f"Cleaned response: {cleaned_response}")
                
                return cleaned_response
                
        except socket.timeout:
            self.logger.warning("Timeout waiting for LabVIEW response")
            return "No Response"
        except Exception as e:
            self.logger.error(f"Error sending INI message: {e}")
            return f"Error: {e}"

    def receive_response(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((self.server_ip, self.receive_port))
                s.listen(1)
                s.setblocking(False)
                self.logger.info(f"Listening for LabVIEW response on {self.server_ip}:{self.receive_port}")
                ready = select.select([s], [], [], 30)
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