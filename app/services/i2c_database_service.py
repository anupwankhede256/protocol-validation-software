# import psycopg2
# from datetime import datetime
# import logging

# class Database:
#     def __init__(self, db_config):
#         self.db_config = db_config
#         self.logger = logging.getLogger(__name__)

#     def connect(self):
#         try:
#             conn = psycopg2.connect(**self.db_config)
#             return conn
#         except psycopg2.Error as e:
#             self.logger.error(f"Database connection error: {e}")
#             return None

#     def create_tables(self):
#         try:
#             conn = self.connect()
#             if conn:
#                 with conn.cursor() as cur:
#                     # Create test_types table
#                     cur.execute("""
#                         CREATE TABLE IF NOT EXISTS test_types (
#                             id SERIAL PRIMARY KEY,
#                             test_category VARCHAR(50) UNIQUE
#                         )
#                     """)
#                     # Create test_names table
#                     cur.execute("""
#                         CREATE TABLE IF NOT EXISTS test_names (
#                             id VARCHAR(10) PRIMARY KEY,
#                             test_type_id INTEGER REFERENCES test_types(id),
#                             test_name VARCHAR(100) UNIQUE
#                         )
#                     """)
#                     # Create i2c_configs table
#                     cur.execute("""
#                         CREATE TABLE IF NOT EXISTS i2c_configs (
#                             id SERIAL PRIMARY KEY,
#                             test_name_id VARCHAR(10) REFERENCES test_names(id),
#                             device_address VARCHAR(20),
#                             config_type VARCHAR(50),
#                             clock_speed VARCHAR(20),
#                             addressing_mode VARCHAR(20),
#                             register_address VARCHAR(50),
#                             bus_mode VARCHAR(20),
#                             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                         )
#                     """)
#                     # Create test_results table (shared with UART, extended for I2C)
#                     cur.execute("""
#                         CREATE TABLE IF NOT EXISTS test_results (
#                             id SERIAL PRIMARY KEY,
#                             i2c_config_id INTEGER REFERENCES i2c_configs(id),
#                             tx_data TEXT,
#                             tx_timestamp TIMESTAMP,
#                             rx_data TEXT,
#                             rx_timestamp TIMESTAMP,
#                             result VARCHAR(20)
#                         )
#                     """)
#                     # Insert I2C Testing type
#                     cur.execute("""
#                         INSERT INTO test_types (test_category) 
#                         VALUES ('I2C Testing') 
#                         ON CONFLICT (test_category) DO NOTHING
#                     """)
#                 conn.commit()
#                 conn.close()
#         except psycopg2.Error as e:
#             self.logger.error(f"Error creating tables: {e}")

#     def get_test_type_id(self, test_type: str):
#         try:
#             conn = self.connect()
#             if conn:
#                 with conn.cursor() as cur:
#                     cur.execute("SELECT id FROM test_types WHERE test_category = %s", (test_type,))
#                     result = cur.fetchone()
#                     conn.close()
#                     return result[0] if result else None
#         except psycopg2.Error as e:
#             self.logger.error(f"Error fetching test type ID: {e}")
#             return None

#     def get_test_name_id(self, test_type_id: int, test_name: str):
#         try:
#             conn = self.connect()
#             if conn:
#                 with conn.cursor() as cur:
#                     cur.execute(
#                         "SELECT id FROM test_names WHERE test_type_id = %s AND test_name = %s",
#                         (test_type_id, test_name)
#                     )
#                     result = cur.fetchone()
#                     conn.close()
#                     return result[0] if result else None
#         except psycopg2.Error as e:
#             self.logger.error(f"Error fetching test name ID: {e}")
#             return None

#     def insert_i2c_config(self, test_name_id: str, device_address: str, config_type: str,
#                          clock_speed: str, addressing_mode: str, register_address: str, bus_mode: str):
#         try:
#             conn = self.connect()
#             if conn:
#                 with conn.cursor() as cur:
#                     cur.execute("""
#                         INSERT INTO i2c_configs (test_name_id, device_address, config_type, clock_speed,
#                                                 addressing_mode, register_address, bus_mode)
#                         VALUES (%s, %s, %s, %s, %s, %s, %s)
#                         RETURNING id
#                     """, (test_name_id, device_address, config_type, clock_speed, addressing_mode,
#                           register_address, bus_mode))
#                     config_id = cur.fetchone()[0]
#                     conn.commit()
#                     conn.close()
#                     return config_id
#         except psycopg2.Error as e:
#             self.logger.error(f"Error inserting I2C config: {e}")
#             return None

#     def insert_test_result(self, i2c_config_id: int, tx_data: str, tx_timestamp: datetime,
#                           rx_data: str, rx_timestamp: datetime, result: str):
#         try:
#             conn = self.connect()
#             if conn:
#                 with conn.cursor() as cur:
#                     cur.execute("""
#                         INSERT INTO test_results (i2c_config_id, tx_data, tx_timestamp, rx_data, rx_timestamp, result)
#                         VALUES (%s, %s, %s, %s, %s, %s)
#                     """, (i2c_config_id, tx_data, tx_timestamp, rx_data, rx_timestamp, result))
#                     conn.commit()
#                     conn.close()
#         except psycopg2.Error as e:
#             self.logger.error(f"Error inserting test result: {e}")