"""
Main application entry point
"""
import os
from flask import Flask
import logging

from logging_setup import setup_logging
from routes import register_routes

def create_app():
    """Create and configure the Flask application"""
    # Set up logging
    logger, ffmpeg_logger = setup_logging()
    logger.info("Initializing streaming application")

    # Create buffer directory if it doesn't exist
    os.makedirs('buffer', exist_ok=True)
    logger.info("Ensured buffer directory exists")

    # Initialize Flask app
    app = Flask(__name__)
    
    # Register routes
    app = register_routes(app)
    
    return app

if __name__ == '__main__':
    app = create_app()
    logger = logging.getLogger(__name__)
    logger.info("Starting streaming server on port 1233")
    app.run(host='0.0.0.0', port=1233)