from pathlib import Path
import logging
import logging.config
import configparser

class SingletonLogger:
    _instances = {}
    _configured = False

    @classmethod
    def configure(cls):
        try:
            project_root = Path(__file__).resolve().parents[1]  # Changed from parents[2] to parents[1]
            config_dir = project_root / 'config'
            corefig_path = config_dir / 'core_config.ini'

            if not corefig_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {corefig_path}")

            config = configparser.ConfigParser()
            config.read(str(corefig_path))

            try:
                environment = config['environment']['current'].lower()
            except KeyError as e:
                raise ValueError("Missing [environment] section or 'current' key in core_config.ini")

            logger_section = f'logger_path_{environment}'
            try:
                log_dir = Path(config[logger_section]['log_dir'])
            except KeyError as e:
                raise ValueError(f"Missing 'log_dir' under section [{logger_section}]")

            log_dir.mkdir(parents=True, exist_ok=True)
            log_file_path = (log_dir / "default.log").as_posix()

            logger_ini_path = config_dir / 'logger.ini'
            if not logger_ini_path.exists():
                raise FileNotFoundError(f"Logger configuration file not found: {logger_ini_path}")

            logging.config.fileConfig(
                str(logger_ini_path),
                defaults={'logfilename': log_file_path},
                disable_existing_loggers=False
            )
            cls._configured = True
            logger = logging.getLogger('appLogger')
            logger.info(f"Logger configured with path: {log_file_path} (env: {environment})")

        except Exception as e:
            print(f"Error configuring logger: {e}")
            raise

    @classmethod
    def get_logger(cls, logger_name='appLogger'):
        try:
            if not cls._configured:
                raise ValueError("Logger not configured. Please call 'configure()' first.")
            if logger_name not in cls._instances:
                cls._instances[logger_name] = logging.getLogger(logger_name)
            return cls._instances[logger_name]
        except Exception as e:
            print(f"Error getting logger: {e}")
            raise