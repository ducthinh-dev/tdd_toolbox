import traceback
import logging
from logging import WARNING
import logging.handlers
import os
from dotenv import load_dotenv
import logfire
from datetime import datetime


def handle_error(e: Exception, msg_type='long') -> str:
    tb_line = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
    match msg_type:
        case 'long':
            return ''.join(tb_line)
        case 'short':
            return f"{type(e).__name__}: {e}"
        case _:
            return {
                'type': type(e).__name__,
                'message': str(e),
                'traceback': tb_line
            }


def setup_logger(name: str, log_path: str, use_logfire: bool = False) -> logging.Logger:
    """
    Sets up a logger with specified configurations.

    Args:
        name (str): The name of the logger.
        log_path (str, optional): The directory path where log files will be stored. Defaults to None.

    Returns:
        logging.Logger: Configured logger instance.

    The function creates a logger that writes logs to both console and file (if log_path is provided).
    It creates a 'logs' directory inside the given log_path if it doesn't exist.

    Example:
        >>> # Create a logger for debugging
        >>> debug_logger = setup_logger('debugger', '/path/to/logs')
        >>> debug_logger.debug('This is a debug message')

        >>> # Create a logger without file logging
        >>> simple_logger = setup_logger('simple_logger')
        >>> simple_logger.info('This is an info message')
    """

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    log_path = os.path.join(log_path, 'logs')
    file_path = os.path.join(log_path, f'{name}.log')
    os.makedirs(log_path, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=file_path,
        maxBytes=1024*1024,
        backupCount=5
    )
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.propagate = False

    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    if use_logfire:
        load_dotenv()
        LOGFIRE_TOKEN = os.environ.get('LOGFIRE_TOKEN')
        logfire.configure(token=LOGFIRE_TOKEN)
        logfire.LogfireLoggingHandler()
        logger.addHandler(logfire.LogfireLoggingHandler(level=WARNING))

    return logger


def load_config(conn, code):
    qry_config = '''
        select config_value
        from ReportConfig
        where config_name = '{code}';
    '''
    _, raw_config = conn.query_data(qry_config.format(code=code))
    root_path = raw_config[0][0]
    if not root_path:
        raise Exception(f'{code} does not exist.')
    return root_path


def log_time(ms_digits=3):
    current = datetime.now()
    stamp = f"{current.strftime('%Y-%m-%d %H:%M:%S')}.{current.strftime('%f')[:ms_digits]}"
    return stamp
