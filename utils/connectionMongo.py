import threading
import configparser
from pathlib import Path
from pymongo import MongoClient
from utils.logger import SingletonLogger

class MongoDBConnectionSingleton:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        try:
            if cls._instance is None:
                with cls._lock:
                    if cls._instance is None:
                        cls._instance = super(MongoDBConnectionSingleton, cls).__new__(cls)
                        cls._instance._initialize_connection()
            return cls._instance
        except Exception as e:
            logger = SingletonLogger.get_logger('dbLogger')
            logger.error(f"Error creating MongoDBConnectionSingleton: {e}")
            return None

    def _initialize_connection(self):
        self.logger = SingletonLogger.get_logger('dbLogger')
        try:
            project_root = Path(__file__).resolve().parents[1]  # Changed from parents[2] to parents[1]
            config_path = project_root / 'config' / 'core_config.ini'
            config = configparser.ConfigParser()
            config.read(str(config_path))

            try:
                env = config['environment']['current'].lower()
            except KeyError as e:
                raise KeyError("Missing [environment] section or 'current' key in core_config.ini")

            section = f'mongo_database_{env}'
            try:
                mongo_uri = config[section]['MONGO_HOST']
                mongo_dbname = config[section]['MONGO_DATABASE']
            except KeyError as e:
                raise KeyError(f"Missing section [{section}] or required keys in config file.")

            if not mongo_uri or not mongo_dbname:
                raise ValueError(f"MongoDB URI or database name missing in [{section}] configuration.")

            self.client = MongoClient(mongo_uri)
            self.database = self.client[mongo_dbname]
            self.logger.info("MongoDB connection established successfully.")

        except Exception as e:
            self.logger.error(f"Error connecting to MongoDB: {e}")
            self.client = None
            self.database = None

    def get_database(self):
        return self.database

    def close_connection(self):
        try:
            if self.client:
                self.client.close()
                self.logger.info("MongoDB connection closed.")
                self.client = None
                self.database = None
                MongoDBConnectionSingleton._instance = None
        except Exception as e:
            self.logger.error(f"Error closing MongoDB connection: {e}")

    def __enter__(self):
        return self.get_database()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()