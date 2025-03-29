import subprocess
import threading
import requests
import os
import time
import logging
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Create a separate logger for FFmpeg output
ffmpeg_logger = logging.getLogger('ffmpeg')
ffmpeg_logger.setLevel(logging.DEBUG)
# Create file handler for FFmpeg logs
ffmpeg_handler = logging.FileHandler('ffmpeg.log')
ffmpeg_handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
ffmpeg_logger.addHandler(ffmpeg_handler)

app = Flask(__name__)

# Configuration
RTMP_SERVER = "rtmp://localhost:1935/live"
OVERLAY_API_BASE = "http://3.6.126.60:8000"
OVERLAY_IMAGE_BASE = "http://3.6.126.60:3000"

# Dictionary to keep track of active streams
active_streams = {}

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

def process_ffmpeg_output(process, stream_id):
    """Process and log FFmpeg output"""
    while process.poll() is None:
        output = process.stderr.readline().decode('utf-8', errors='replace').strip()
        if output:
            ffmpeg_logger.debug(f"[Stream {stream_id}] {output}")

def stream_to_youtube(stream_id, youtube_url, stop_event):
    input_url = f"{RTMP_SERVER}/{stream_id}"
    logger.info(f"Starting stream from {input_url} to YouTube")
    
    overlay_image = f"{stream_id}.png"
    
    # Start FFmpeg process with improved overlay handling
    ffmpeg_command = [
        'ffmpeg',
        '-re', '-i', input_url,
        '-analyzeduration', '10M', '-probesize', '10M',  # Better file analysis
        '-loop', '1',                    # Loop the image
        '-i', overlay_image,             # Overlay image file
        '-filter_complex', '[0:v]transpose=2[v];[v][1:v]overlay=15:620:format=auto:eof_action=pass',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-b:v', '1000k',
        '-c:a', 'aac', '-ar', '44100',
        '-shortest', '-fflags', '+shortest',
        '-avoid_negative_ts', 'make_zero',
        '-f', 'flv',
        youtube_url
    ]

    # Create a buffer directory for the overlay image
    os.makedirs('buffer', exist_ok=True)
    
    # Start FFmpeg as subprocess
    logger.info(f"Executing FFmpeg command for stream {stream_id}")
    process_ffmpeg = subprocess.Popen(
        ffmpeg_command, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        bufsize=1, 
        universal_newlines=True
    )
    
    # Start a thread to process FFmpeg output
    output_thread = threading.Thread(
        target=process_ffmpeg_output, 
        args=(process_ffmpeg, stream_id)
    )
    output_thread.daemon = True
    output_thread.start()
    
    # Monitor the process
    while not stop_event.is_set():
        if process_ffmpeg.poll() is not None:
            logger.error(f"FFmpeg process for stream {stream_id} has ended unexpectedly with code {process_ffmpeg.returncode}")
            break
        time.sleep(1)
        
    # Clean up when the stream is stopped
    if process_ffmpeg.poll() is None:
        logger.info(f"Terminating FFmpeg process for stream {stream_id}")
        process_ffmpeg.terminate()
        try:
            process_ffmpeg.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning(f"FFmpeg process for stream {stream_id} did not terminate, forcing kill")
            process_ffmpeg.kill()

    logger.info(f"Stream {stream_id} stopped")

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
    
    # Start match monitoring (this will start generating the overlay image)
    if not start_match_monitoring(stream_id, overlay_id="0"):
        return jsonify({'error': 'Failed to start match monitoring'}), 500
    
    # Create a placeholder image until the API generates one
    try:
        logger.info(f"Preparing initial overlay image for stream {stream_id}")
        # Download initial image or create placeholder
        response = requests.get(f"{OVERLAY_IMAGE_BASE}/{stream_id}.png")
        if response.status_code == 200:
            with open(f"{stream_id}.png", 'wb') as f:
                f.write(response.content)
            logger.info(f"Downloaded initial overlay image for stream {stream_id}")
        else:
            # If image doesn't exist yet, create a blank placeholder
            from PIL import Image, ImageDraw
            img = Image.new('RGBA', (800, 100), (0, 0, 0, 0))
            img.save(f"{stream_id}.png")
            logger.info(f"Created blank placeholder image for stream {stream_id}")
    except Exception as e:
        logger.error(f"Error preparing initial overlay for {stream_id}: {e}", exc_info=True)
        # Create blank placeholder on exception
        from PIL import Image
        img = Image.new('RGBA', (800, 100), (0, 0, 0, 0))
        img.save(f"{stream_id}.png")
    
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

if __name__ == '__main__':
    logger.info("Starting streaming server on port 1233")
    app.run(host='0.0.0.0', port=1233)
