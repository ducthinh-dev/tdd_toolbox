import traceback
import logging
import logging.handlers
import logging.config
import os


def handle_error(e):
    tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
    return ''.join(tb_lines)


def setup_logger(name=__name__):
    os.makedirs('logs', exist_ok=True)
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'ERROR',
                'formatter': 'standard'
            },
            'size_rotating': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': f'logs/{name}.log',
                'maxBytes': 1024*1024,
                'backupCount': 5,
                'formatter': 'standard',
                'level': 'CRITICAL'
            },
        },
        'loggers': {
            '': {  # Root logger
                'handlers': ['console'],
                'level': 'CRITICAL',
                'propagate': True
            },
            'debugger': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False
            },
            'monitor': {
                'handlers': ['console', 'size_rotating'],
                'level': 'CRITICAL',
                'propagate': True
            }
        }
    }

    logging.config.dictConfig(LOGGING_CONFIG)
