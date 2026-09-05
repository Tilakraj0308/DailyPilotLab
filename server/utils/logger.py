import logging
import sys
import os
from loguru import logger

class InterceptHandler(logging.Handler):
    """
    Intercept standard logging messages and route them to loguru.
    """
    def emit(self, record):
        # Get corresponding Loguru level if it exists.
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )

def setup_logger():
    """
    Configure loguru logger for both console and file output,
    and intercept standard library logging messages.
    """
    # Remove default loguru handler
    logger.remove()

    # Add console logger with colored output
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
    )

    # Ensure logs dir exists in the server folder
    os.makedirs("logs", exist_ok=True)

    # Add file logger with rotation and retention (datewise + size limit)
    logger.add(
        "logs/server_{time:YYYY-MM-DD}.log",
        rotation="5 MB",
        retention=3,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
    )

    # Intercept standard logging messages
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Intercept common loggers (like uvicorn) to prevent double logging
    for _log in ['uvicorn', 'uvicorn.error', 'uvicorn.access', 'fastapi', 'watchfiles.main']:
        _logger = logging.getLogger(_log)
        _logger.handlers = [InterceptHandler()]
        _logger.propagate = False

    # Suppress watchfiles DEBUG logs which trigger infinite loops
    logging.getLogger("watchfiles.main").setLevel(logging.WARNING)

    return logger

# Make it easy to import
# e.g., from utils.logger import logger
