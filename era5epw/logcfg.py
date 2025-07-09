import logging.config


def init_logging() -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": True,
            "formatters": {
                "standard": {
                    "format": (
                        "%(asctime)s "
                        + "[%(levelname)s]"
                        + "[%(filename)s:%(lineno)s - %(funcName)s()]: %(message)s"
                    )
                },
            },
            "handlers": {
                "default": {
                    "level": "INFO",
                    "formatter": "standard",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",  # Default is stderr
                },
            },
            "loggers": {"": {"handlers": ["default"], "level": "INFO"}},  # root logger
        }
    )
