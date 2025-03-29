"""
Overlay image handling functionality
"""
import os
import time
import requests
import logging
from PIL import Image
from config import OVERLAY_IMAGE_BASE

logger = logging.getLogger(__name__)

def update_overlay_image(stream_id, stop_event, update_interval=1):
    """Download the overlay image periodically using a double-buffer approach"""
    main_path = f"{stream_id}.png"
    buffer_path = f"buffer/{stream_id}_temp.png"
    image_url = f"{OVERLAY_IMAGE_BASE}/{stream_id}.png"
    
    # Ensure buffer directory exists
    os.makedirs('buffer', exist_ok=True)
    
    logger.info(f"Starting overlay image updates for stream {stream_id}")
    while not stop_event.is_set():
        try:
            # Download to temp location first
            response = requests.get(image_url)
            if response.status_code == 200:
                # Save to buffer first
                with open(buffer_path, 'wb') as f:
                    f.write(response.content)
                
                # Then safely move to the main location
                # This is an atomic operation on most filesystems
                os.replace(buffer_path, main_path)
                logger.debug(f"Updated overlay image for stream {stream_id}")
                
            else:
                logger.warning(f"Failed to get overlay image for {stream_id}: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error updating overlay image for {stream_id}: {e}", exc_info=True)
            
        # Wait for the specified interval before updating again
        time.sleep(update_interval)
    
    # Clean up the image files when stopped
    logger.info(f"Stopping overlay image updates for stream {stream_id}")
    for path in [main_path, buffer_path]:
        if os.path.exists(path):
            try:
                os.remove(path)
                logger.info(f"Removed overlay image file: {path}")
            except Exception as e:
                logger.error(f"Failed to remove {path}: {e}")

def create_initial_overlay(stream_id):
    """Create or download the initial overlay image"""
    try:
        logger.info(f"Preparing initial overlay image for stream {stream_id}")
        # Download initial image or create placeholder
        response = requests.get(f"{OVERLAY_IMAGE_BASE}/{stream_id}.png")
        if response.status_code == 200:
            with open(f"{stream_id}.png", 'wb') as f:
                f.write(response.content)
            logger.info(f"Downloaded initial overlay image for stream {stream_id}")
            return True
        else:
            # If image doesn't exist yet, create a blank placeholder
            img = Image.new('RGBA', (800, 100), (0, 0, 0, 0))
            img.save(f"{stream_id}.png")
            logger.info(f"Created blank placeholder image for stream {stream_id}")
            return True
    except Exception as e:
        logger.error(f"Error preparing initial overlay for {stream_id}: {e}", exc_info=True)
        # Create blank placeholder on exception
        img = Image.new('RGBA', (800, 100), (0, 0, 0, 0))
        img.save(f"{stream_id}.png")
        return True