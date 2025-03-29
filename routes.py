"""
API routes for the streaming application
"""
import time
import threading
import logging
from flask import request, jsonify

from config import active_streams, MAX_CONCURRENT_STREAMS
from match_monitor import start_match_monitoring
from overlay import update_overlay_image, create_initial_overlay
from ffmpeg import stream_to_youtube

logger = logging.getLogger(__name__)

def register_routes(app):
    """Register all routes with the Flask app"""
    
    @app.route('/start_stream', methods=['POST'])
    def start_stream():
        data = request.json
        youtube_url = data.get('youtube_url')
        stream_id = data.get('stream_name')  # Using stream_name as the identifier
        
        logger.info(f"Received request to start stream {stream_id}")
        
        if not youtube_url or not stream_id:
            logger.warning("Missing youtube_url or stream_name in request")
            return jsonify({'error': 'Missing youtube_url or stream_name'}), 400

        if stream_id in active_streams:
            logger.warning(f"Stream {stream_id} is already active")
            return jsonify({'error': 'Stream already active'}), 409
        
        # Check if maximum concurrent streams limit has been reached
        if len(active_streams) >= MAX_CONCURRENT_STREAMS:
            logger.warning(f"Maximum limit of {MAX_CONCURRENT_STREAMS} concurrent streams reached. Cannot start new stream.")
            return jsonify({'error': f'Maximum concurrent streams limit ({MAX_CONCURRENT_STREAMS}) reached'}), 429
            
        # Start match monitoring (this will start generating the overlay image)
        if not start_match_monitoring(stream_id, overlay_id="0"):
            return jsonify({'error': 'Failed to start match monitoring'}), 500
        
        # Create initial overlay image
        create_initial_overlay(stream_id)
        
        # Start image update thread
        stop_event_image = threading.Event()
        image_thread = threading.Thread(target=update_overlay_image, args=(stream_id, stop_event_image))
        image_thread.start()
        logger.info(f"Started overlay image update thread for stream {stream_id}")
        
        # Start streaming thread
        stop_event_stream = threading.Event()
        stream_thread = threading.Thread(target=stream_to_youtube, args=(
            stream_id, youtube_url, stop_event_stream))
        stream_thread.start()
        logger.info(f"Started streaming thread for stream {stream_id}")

        active_streams[stream_id] = {
            'stream_thread': stream_thread,
            'image_thread': image_thread,
            'stream_stop_event': stop_event_stream,
            'image_stop_event': stop_event_image,
            'youtube_url': youtube_url,
            'start_time': time.time()
        }

        logger.info(f"Stream {stream_id} started successfully")
        return jsonify({
            'message': f'Stream {stream_id} started successfully',
            'youtube_url': youtube_url
        }), 200

    @app.route('/stop_stream', methods=['POST'])
    def stop_stream():
        data = request.json
        stream_id = data.get('stream_name')
        
        logger.info(f"Received request to stop stream {stream_id}")
        
        if not stream_id:
            logger.warning("Missing stream_name in stop request")
            return jsonify({'error': 'Missing stream_name'}), 400

        if stream_id not in active_streams:
            logger.warning(f"Stream {stream_id} not found in active streams")
            return jsonify({'error': 'Stream not found'}), 404

        # Stop both threads
        logger.info(f"Signaling threads to stop for stream {stream_id}")
        active_streams[stream_id]['stream_stop_event'].set()
        active_streams[stream_id]['image_stop_event'].set()
        
        # Calculate stream duration
        start_time = active_streams[stream_id].get('start_time', 0)
        duration = time.time() - start_time
        
        active_streams[stream_id]['stream_thread'].join(timeout=10)
        active_streams[stream_id]['image_thread'].join(timeout=10)
        
        logger.info(f"Stream {stream_id} stopped after running for {duration:.1f} seconds")
        
        # Optional: You might want to call an API to stop match monitoring
        # requests.post(f"{OVERLAY_API_BASE}/stop-match-monitoring", json={"match_id": stream_id})
        
        del active_streams[stream_id]

        return jsonify({'message': f'Stream {stream_id} stopped successfully'}), 200

    @app.route('/list_streams', methods=['GET'])
    def list_streams():
        logger.info("Received request to list active streams")
        streams_info = {
            name: {
                'youtube_url': info['youtube_url'],
                'uptime': time.time() - info.get('start_time', time.time())
            } for name, info in active_streams.items()
        }
        return jsonify(streams_info), 200
    
    return app