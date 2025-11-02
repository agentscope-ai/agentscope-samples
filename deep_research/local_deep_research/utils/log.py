import logging
import os
from datetime import datetime
from typing import Optional

from agentscope import logger, setup_logger
from termcolor import colored


# Global flag to track if logger has been initialized
_logger_initialized = False


def setup_agentscope_logger(
    level: str = "INFO",
    log_dir: Optional[str] = None,
    log_filename: Optional[str] = None,
) -> None:
    """
    Setup AgentScope logger with file output (singleton pattern).

    This function ensures the logger is only initialized once during the program lifecycle.

    Args:
        level: The logging level (e.g., "DEBUG", "INFO", "WARNING", "ERROR").
        log_dir: Directory to store log files. Defaults to "./logs".
        log_filename: Log file name. If None, generates name with timestamp.

    Example:
        >>> from local_deep_research.utils.log import setup_agentscope_logger
        >>> setup_agentscope_logger(level="DEBUG", log_dir="./my_logs")
    """
    global _logger_initialized

    if _logger_initialized:
        logger.debug("AgentScope logger already initialized, skipping...")
        return

    # Set default log directory
    if log_dir is None:
        log_dir = os.path.join(os.getcwd(), "logs")

    # Create log directory
    os.makedirs(log_dir, exist_ok=True)

    # Generate log filename if not provided
    if log_filename is None:
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        log_filename = f"agentscope_{timestamp}.log"

    # Full log file path
    log_path = os.path.join(log_dir, log_filename)

    # Setup AgentScope logger
    setup_logger(level=level, filepath=log_path)

    # Mark as initialized
    _logger_initialized = True

    logger.info(f"AgentScope logger initialized: level={level}, file={log_path}")


class ColoredFormatter(logging.Formatter):
    """
    A custom formatter for logging that adds colors to log messages.

    This formatter adds colors to log messages based on their level,
    making it easier to distinguish between different types of logs.

    Attributes:
        COLORS: A dictionary mapping log levels to colors.
    """

    COLORS = {
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "magenta",
    }

    def format(self, record):
        """
        Format a log record with colors.

        Args:
            record: The log record to format.

        Returns:
            The formatted log message with colors.
        """
        # all line in log will be colored
        log_message = super().format(record)
        return colored(log_message, self.COLORS.get(record.levelname, "white"))

        # only log level will be colored
        # levelname_colored = colored(record.levelname, self.COLORS.get(record.levelname, 'white'))
        # record.levelname = levelname_colored
        # return super().format(record)

        # only keywords will be colored
        # message = record.msg
        # for word, color in self.KEYWORDS.items():
        #     if word in message:
        #         message = message.replace(word, colored(word, color))
        # record.msg = message
        # return super().format(record)


# config log
dev_logger = logging.getLogger("dev")
dev_formatter = ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s")
dev_handler = logging.StreamHandler()
dev_handler.setFormatter(dev_formatter)
dev_logger.addHandler(dev_handler)
dev_logger.setLevel(logging.INFO)

progress_logger = logging.getLogger("progress")
progress_handler = logging.StreamHandler()
progress_handler.setFormatter(ColoredFormatter("%(message)s"))
progress_logger.addHandler(progress_handler)
progress_logger.setLevel(logging.INFO)

dev_mode = False


def set_dev_mode(mode: bool):
    """
    Set the development mode.

    When in development mode, debug, info, and warning logs are displayed.
    When not in development mode, only error and critical logs are displayed.

    Args:
        mode: True to enable development mode, False to disable it.
    """
    global dev_mode
    dev_mode = mode


def set_level(level):
    """
    Set the logging level for the development logger.

    Args:
        level: The logging level to set (e.g., logging.DEBUG, logging.INFO).
    """
    dev_logger.setLevel(level)


def debug(message):
    """
    Log a debug message.

    Args:
        message: The message to log.
    """
    if dev_mode:
        dev_logger.debug(message)


def info(message):
    """
    Log an info message.

    Args:
        message: The message to log.
    """
    if dev_mode:
        dev_logger.info(message)


def warning(message):
    """
    Log a warning message.

    Args:
        message: The message to log.
    """
    if dev_mode:
        dev_logger.warning(message)


def error(message):
    """
    Log an error message.

    Args:
        message: The message to log.
    """
    if dev_mode:
        dev_logger.error(message)


def critical(message):
    """
    Log a critical message and raise a RuntimeError.

    Args:
        message: The message to log.

    Raises:
        RuntimeError: Always raised with the provided message.
    """
    dev_logger.critical(message)
    raise RuntimeError(message)


def color_print(message, **kwargs):
    """
    Print a colored message to the progress logger.

    Args:
        message: The message to print.
        **kwargs: Additional keyword arguments to pass to the logger.
    """
    progress_logger.info(message)
