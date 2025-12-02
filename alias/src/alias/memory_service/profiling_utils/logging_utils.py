# -*- coding: utf-8 -*-
import logging
from logging.handlers import RotatingFileHandler
import os


def setup_logging():
    # Create logger
    logger = logging.getLogger()
    if logger.hasHandlers():
        return logger  # Return the existing logger if it already has handlers

    logger.setLevel(logging.INFO)

    # Get the directory path of the current file
    print(os.environ.get("LOGGING_DIR"))
    logging_dir = os.environ.get(
        "LOGGING_DIR",
        os.path.dirname(os.path.abspath(__file__)),
    )

    # Use descriptive log filename without timestamp
    log_filename = "memory_service.log"
    log_filepath = os.path.join(logging_dir, log_filename)
    # print(f"Logging to file: {log_filepath}")

    # Create rotating file handler with size-based rotation
    # maxBytes: 50MB per file, backupCount: keep 5 backup files
    file_handler = RotatingFileHandler(
        log_filepath,
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)

    # Create console handler to output logs to console
    # console_handler = logging.StreamHandler(sys.stdout)
    # console_handler.setLevel(logging.INFO)

    # Define log format, including filename and line number
    formatter = logging.Formatter(
        "(%(filename)s:%(lineno)d)-%(asctime)s - %(name)s - %(levelname)s - "
        "%(message)s ",
    )

    # Set format
    file_handler.setFormatter(formatter)
    # console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(file_handler)
    # logger.addHandler(console_handler)

    return logger
