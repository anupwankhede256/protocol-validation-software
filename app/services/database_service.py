import psycopg2
from psycopg2 import sql
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_config):
        self.db_config = db_config

    def connect(self):
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except psycopg2.Error as e:
            logger.error(f"Error connecting to the database: {e}")
            return None

    def create_tables(self):
        conn = self.connect()
        if conn is None:
            return

        try:
            with conn.cursor() as cur:
                # Create test_types table with UNIQUE constraint
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS test_types (
                        id VARCHAR(10) PRIMARY KEY,
                        test_category VARCHAR(50) NOT NULL UNIQUE
                    )
                """)

                # Create test_names table with composite UNIQUE constraint
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS test_names (
                        id VARCHAR(10) PRIMARY KEY,
                        test_type_id VARCHAR(10) REFERENCES test_types(id),
                        test_name VARCHAR(100) NOT NULL,
                        UNIQUE (test_type_id, test_name)
                    )
                """)

                # Create uart_configuration table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS uart_configuration (
                        id VARCHAR PRIMARY KEY,
                        test_name_id VARCHAR(10) REFERENCES test_names(id),
                        device_id VARCHAR(50),
                        baud_rate INTEGER,
                        data_bits INTEGER,
                        parity VARCHAR(10),
                        stop_bits NUMERIC(2,1),
                        data_shift VARCHAR(20),
                        handshake VARCHAR(20),
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create test_results table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS test_results (
                        id SERIAL PRIMARY KEY,
                        uart_config_id VARCHAR REFERENCES uart_configuration(id),
                        test_name VARCHAR(100),
                        tx_data TEXT,
                        tx_timestamp TIMESTAMP,
                        rx_data TEXT,
                        rx_timestamp TIMESTAMP,
                        status VARCHAR(20)
                    )
                """)

                # Commit table creation first
                conn.commit()

                # Predefine test types with custom IDs
                test_types_data = [
                    ("TT001", "UART Testing", [
                        ("UART01", "RECEPTION TEST"),
                        ("UART02", "TRANSMISSION TEST"),
                        ("UART03", "LOOPBACK TEST"),
                        ("UART04", "BAUD RATE TESTING"),
                        ("UART05", "RTS/CTS HARDWARE FLOW TEST"),        
                        ("UART06", "PARITY DETECTION"),
                        ("UART07", "OVERRUN DETECTION"),
                        ("UART08", "BREAK CHARACTER DETECTION"),

                    ]),
                    ("TT002", "CAN Testing", []),
                    ("TT003", "SPI Testing", []),
                    ("TT004", "I2C Testing", []),
                    ("TT005", "LIN Testing", []),
                    ("TT006", "USB Testing", [])
                ]

                for test_type_id, category, names in test_types_data:
                    # Insert test type with custom ID
                    cur.execute("""
                        INSERT INTO test_types (id, test_category) VALUES (%s, %s)
                        ON CONFLICT (test_category) DO NOTHING
                    """, (test_type_id, category))

                    # Insert test names in uppercase
                    for test_id, name in names:
                        cur.execute("""
                            INSERT INTO test_names (id, test_type_id, test_name)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (id) DO NOTHING
                        """, (test_id, test_type_id, name.upper()))
                conn.commit()
                logger.debug("Tables created successfully")
        except psycopg2.Error as e:
            logger.error(f"Error creating tables: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_test_type_id(self, test_category):
        conn = self.connect()
        if conn is None:
            return None

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id FROM test_types WHERE test_category = %s
                """, (test_category,))
                Status = cur.fetchone()
                return Status[0] if Status else None
        except psycopg2.Error as e:
            logger.error(f"Error getting test type ID: {e}")
            return None
        finally:
            conn.close()

    def get_test_name_id(self, test_type_id, test_name):
        conn = self.connect()
        if conn is None:
            return None

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id FROM test_names WHERE test_type_id = %s AND test_name = %s
                """, (test_type_id, test_name.upper()))  # Normalize to uppercase
                Status = cur.fetchone()
                return Status[0] if Status else None
        except psycopg2.Error as e:
            logger.error(f"Error getting test name ID: {e}")
            return None
        finally:
            conn.close()

    def _generate_config_id(self):
        conn = self.connect()
        if conn is None:
            return "CFG_UART_001"

        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM uart_configuration")
                count = cur.fetchone()[0]
                serial = count + 1
                return f"CFG_UART_{serial:03d}"
        except psycopg2.Error as e:
            logger.error(f"Error generating config ID: {e}")
            return "CFG_UART_001"
        finally:
            conn.close()

    def insert_uart_config(self, test_name_id, device_id,baud_rate, data_bits, parity, 
                          stop_bits, data_shift, handshake):
        conn = self.connect()
        if conn is None:
            return None

        try:
            with conn.cursor() as cur:
                config_id = self._generate_config_id()
                cur.execute("""
                    INSERT INTO uart_configuration 
                    (id, test_name_id, device_id,baud_rate, data_bits, parity, 
                     stop_bits, data_shift, handshake)
                    VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (config_id, test_name_id, device_id,baud_rate, data_bits, parity, 
                      stop_bits, data_shift, handshake))
                returned_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"UART configuration inserted with id: {returned_id}")
                return returned_id
        except psycopg2.Error as e:
            logger.error(f"Error inserting UART configuration: {e}")
            return None
        finally:
            conn.close()

    def insert_test_result(self, uart_config_id,test_name, tx_data, tx_timestamp, rx_data, rx_timestamp, status):
        conn = self.connect()
        if conn is None:
            return None

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO test_results 
                    (uart_config_id,test_name, tx_data, tx_timestamp, rx_data, rx_timestamp, status)
                    VALUES (%s, %s,%s, %s, %s, %s, %s)
                    RETURNING id
                """, (uart_config_id,test_name, tx_data, tx_timestamp, rx_data, rx_timestamp, status))
                result_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"Test Status inserted with id: {result_id}")
                return result_id
        except psycopg2.Error as e:
            logger.error(f"Error inserting test Status: {e}")
            return None
        finally:
            conn.close()
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
                    # Store the detailed baud rate results
                    test_result_data = f"Min: {min_baud:,} ({min_error:.2f}%), Max: {max_baud:,} ({max_error:.2f}%)"
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