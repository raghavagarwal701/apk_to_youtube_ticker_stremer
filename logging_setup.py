"""
Logging configuration for the streaming application
"""
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configure logging for the application"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure main logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Create a file handler for main logs with size limit
    main_handler = RotatingFileHandler(
        'logs/application.log',
        maxBytes=5 * 1024 * 1024,  # 5MB limit
        backupCount=3
    )
    main_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(main_handler)
    
    # Create console handler for main logs
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', 
                                                  '%Y-%m-%d %H:%M:%S'))
    logger.addHandler(console_handler)
    
    # Create a separate logger for FFmpeg output
    ffmpeg_logger = logging.getLogger('ffmpeg')
    ffmpeg_logger.setLevel(logging.DEBUG)
    
    # Create rotating file handler for FFmpeg logs
    ffmpeg_handler = RotatingFileHandler(
        'logs/ffmpeg.log',
        maxBytes=5 * 1024 * 1024,  # 5MB limit
        backupCount=3
    )
    ffmpeg_handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
    ffmpeg_logger.addHandler(ffmpeg_handler)
    
    return logger, ffmpeg_logger