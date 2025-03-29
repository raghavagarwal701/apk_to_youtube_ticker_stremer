import subprocess
import threading
import requests
import os
import time
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

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
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"Successfully started monitoring for stream {stream_id}")
            return True
        else:
            print(f"Failed to start monitoring: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error starting match monitoring: {e}")
        return False

def update_overlay_image(stream_id, stop_event, update_interval=1):
    """Download the overlay image periodically using a double-buffer approach"""
    main_path = f"{stream_id}.png"
    buffer_path = f"buffer/{stream_id}_temp.png"
    image_url = f"{OVERLAY_IMAGE_BASE}/{stream_id}.png"
    
    # Ensure buffer directory exists
    os.makedirs('buffer', exist_ok=True)
    
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
                
            else:
                print(f"Failed to get overlay image: {response.status_code}")
                
        except Exception as e:
            print(f"Error updating overlay image: {e}")
            
        # Wait for the specified interval before updating again
        time.sleep(update_interval)
    
    # Clean up the image files when stopped
    for path in [main_path, buffer_path]:
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"Removed overlay image file: {path}")
            except:
                pass

def stream_to_youtube(stream_id, youtube_url, stop_event):
    input_url = f"{RTMP_SERVER}/{stream_id}"
    print(f"Streaming from {input_url} to {youtube_url}")
    
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
    process_ffmpeg = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Monitor the process
    while not stop_event.is_set():
        if process_ffmpeg.poll() is not None:
            print(f"FFmpeg process for stream {stream_id} has ended unexpectedly.")
            break
        time.sleep(1)
        
    # Clean up when the stream is stopped
    if process_ffmpeg.poll() is None:
        process_ffmpeg.terminate()
        process_ffmpeg.wait()

    print(f"Stream {stream_id} stopped")

@app.route('/start_stream', methods=['POST'])
def start_stream():
    data = request.json
    youtube_url = data.get('youtube_url')
    stream_id = data.get('stream_name')  # Using stream_name as the identifier
    
    if not youtube_url or not stream_id:
        return jsonify({'error': 'Missing youtube_url or stream_name'}), 400

    if stream_id in active_streams:
        return jsonify({'error': 'Stream already active'}), 409
    
    # Start match monitoring (this will start generating the overlay image)
    if not start_match_monitoring(stream_id, overlay_id="0"):
        return jsonify({'error': 'Failed to start match monitoring'}), 500
    
    # Create a placeholder image until the API generates one
    try:
        # Download initial image or create placeholder
        response = requests.get(f"{OVERLAY_IMAGE_BASE}/{stream_id}.png")
        if response.status_code == 200:
            with open(f"{stream_id}.png", 'wb') as f:
                f.write(response.content)
        else:
            # If image doesn't exist yet, create a blank placeholder
            from PIL import Image, ImageDraw
            img = Image.new('RGBA', (800, 100), (0, 0, 0, 0))
            img.save(f"{stream_id}.png")
    except Exception as e:
        print(f"Error preparing initial overlay: {e}")
        # Create blank placeholder on exception
        from PIL import Image
        img = Image.new('RGBA', (800, 100), (0, 0, 0, 0))
        img.save(f"{stream_id}.png")
    
    # Start image update thread
    stop_event_image = threading.Event()
    image_thread = threading.Thread(target=update_overlay_image, args=(stream_id, stop_event_image))
    image_thread.start()
    
    # Start streaming thread
    stop_event_stream = threading.Event()
    stream_thread = threading.Thread(target=stream_to_youtube, args=(
        stream_id, youtube_url, stop_event_stream))
    stream_thread.start()

    active_streams[stream_id] = {
        'stream_thread': stream_thread,
        'image_thread': image_thread,
        'stream_stop_event': stop_event_stream,
        'image_stop_event': stop_event_image,
        'youtube_url': youtube_url
    }

    return jsonify({
        'message': f'Stream {stream_id} started successfully',
        'youtube_url': youtube_url
    }), 200

@app.route('/stop_stream', methods=['POST'])
def stop_stream():
    data = request.json
    stream_id = data.get('stream_name')
    if not stream_id:
        return jsonify({'error': 'Missing stream_name'}), 400

    if stream_id not in active_streams:
        return jsonify({'error': 'Stream not found'}), 404

    # Stop both threads
    active_streams[stream_id]['stream_stop_event'].set()
    active_streams[stream_id]['image_stop_event'].set()
    
    active_streams[stream_id]['stream_thread'].join()
    active_streams[stream_id]['image_thread'].join()
    
    # Optional: You might want to call an API to stop match monitoring
    # requests.post(f"{OVERLAY_API_BASE}/stop-match-monitoring", json={"match_id": stream_id})
    
    del active_streams[stream_id]

    return jsonify({'message': f'Stream {stream_id} stopped successfully'}), 200

@app.route('/list_streams', methods=['GET'])
def list_streams():
    return jsonify({
        name: {
            'youtube_url': info['youtube_url']
        } for name, info in active_streams.items()
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1233)
