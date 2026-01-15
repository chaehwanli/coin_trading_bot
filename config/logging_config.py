import logging
import logging.config
import os

def setup_logging(default_level=logging.INFO):
    """Setup logging configuration"""
    
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': default_level,
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': default_level,
                'formatter': 'standard',
                'filename': os.path.join(log_dir, 'coin_bot.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            }
        },
        'root': {
            'level': default_level,
            'handlers': ['console', 'file']
        }
    }

    logging.config.dictConfig(logging_config)
    
def get_logger(name):
    return logging.getLogger(name)
