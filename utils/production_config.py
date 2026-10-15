# deployment/production_config.py
"""
Production configuration and optimization
"""

class ProductionConfig:
    # Enhanced logging
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/app.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'formatter': 'detailed',
            },
            'error_file': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/errors.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'formatter': 'detailed',
            },
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['file', 'error_file'],
                'level': 'INFO',
                'propagate': False
            }
        }
    }
    
    # Performance optimizations
    SCHEDULER_SETTINGS = {
        'max_workers': 10,
        'job_defaults': {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 300  # 5 minutes
        }
    }