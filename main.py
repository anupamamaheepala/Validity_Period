from utils.logger import SingletonLogger
from utils.connectionMongo import MongoDBConnectionSingleton
from function.validity_period import ValidityPeriodMonitor

def main():
    try:
        # Configure logger
        SingletonLogger.configure()
        logger = SingletonLogger.get_logger('appLogger')
        db_logger = SingletonLogger.get_logger('dbLogger')

        logger.info("Starting Validity Period Monitor application")

        # Test MongoDB connection
        with MongoDBConnectionSingleton() as mongo_db:
            if mongo_db is None:
                raise ValueError("Failed to connect to MongoDB")
            db_logger.info(f"Connected to MongoDB database: {mongo_db.name}")

        # Run validity period check
        monitor = ValidityPeriodMonitor()
        monitor.check_validity_and_alert()

        logger.info("Validity period check completed successfully")

    except Exception as e:
        logger = SingletonLogger.get_logger('appLogger')
        logger.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    main()