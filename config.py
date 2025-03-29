"""
Configuration settings for the streaming application
"""

# Server configuration
RTMP_SERVER = "rtmp://localhost:1935/live"
OVERLAY_API_BASE = "http://3.6.126.60:8000"
OVERLAY_IMAGE_BASE = "http://3.6.126.60:3000"

# Stream constraints
MAX_CONCURRENT_STREAMS = 4
MAX_STREAM_DURATION = 5 * 60 * 60  # 5 hours in seconds

# Dictionary to keep track of active streams
active_streams = {}