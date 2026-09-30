import os
import sys
from loguru import logger
from config.settings import get_settings

def setup_logger(level: str = None):
    settings = get_settings()
    log_level = level or settings.log_level
    log_dir = settings.log_dir
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        
    # Remove default handler
    logger.remove()
    
    # Add console handler with rich formatting (via sys.stderr)
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )
    
    # Add file handler
    log_file_path = os.path.join(log_dir, "app_{time:YYYY-MM-DD}.log")
    logger.add(
        log_file_path,
        rotation="10 MB",
        retention=5,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level
    )

def get_logger(name: str):
    """Get a bound logger for a specific module/component."""
    return logger.bind(name=name)
