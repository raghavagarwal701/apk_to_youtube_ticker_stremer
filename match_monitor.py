"""
Match monitoring functionality
"""
import requests
import logging
from config import OVERLAY_API_BASE

logger = logging.getLogger(__name__)

def start_match_monitoring(stream_id, overlay_id="0"):
    """Start the match monitoring by calling the API"""
    url = f"{OVERLAY_API_BASE}/start-match-monitoring"
    payload = {
        "match_id": stream_id,
        "overlay_id": overlay_id
    }
    
    try:
        logger.info(f"Starting match monitoring for stream ID: {stream_id}")
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logger.info(f"Successfully started monitoring for stream {stream_id}")
            return True
        else:
            logger.error(f"Failed to start monitoring: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error starting match monitoring: {e}", exc_info=True)
        return False