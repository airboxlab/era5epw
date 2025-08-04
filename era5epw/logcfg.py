import logging.config


def init_logging(verbose: bool = False) -> None:
    # Set CDS client logger levels based on verbosity
    cds_log_level = "INFO" if verbose else "ERROR"
    app_log_level = "INFO" if verbose else "WARNING"

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
            "loggers": {
                "": {"handlers": ["default"], "level": app_log_level},  # root logger
                "cdsapi": {"handlers": ["default"], "level": cds_log_level, "propagate": False},
                "ecmwf.datastores.legacy_client": {
                    "handlers": ["default"],
                    "level": cds_log_level,
                    "propagate": False,
                },
                "multiurl": {"handlers": ["default"], "level": cds_log_level, "propagate": False},
            },
        }
    )
