import sys
from loguru import logger

def setup_logging(log_level="INFO", log_format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"):
    """
    Configures a structured logger using Loguru.

    This setup removes the default handler and adds a new one with a custom format
    that is both human-readable and detailed. It logs to stderr by default.
    An additional sink can be configured for file-based logging.

    Args:
        log_level (str): The minimum log level to capture (e.g., "DEBUG", "INFO").
        log_format (str): The Loguru format string for log messages.
    """
    logger.remove()  # Remove the default handler to avoid duplicate outputs
    logger.add(
        sys.stderr,
        level=log_level.upper(),
        format=log_format,
        colorize=True,
    )
    # Example of adding a file logger (can be enabled via config)
    # logger.add(
    #     "logs/mpla_{time}.log",
    #     level="DEBUG",
    #     rotation="10 MB",  # Rotates the log file when it reaches 10 MB
    #     retention="7 days", # Keeps logs for 7 days
    #     enqueue=True,      # Makes logging non-blocking
    #     backtrace=True,
    #     diagnose=True,
    # )
    logger.info("Logger successfully configured.")

# You can import this logger instance across your application
# from mpla.utils.logging import logger 