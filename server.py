import subprocess
import threading
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from score_fetch import fetch_match_data
from websocket_fech import get_score_websocket_and_get_image
from PIL import Image, ImageDraw, ImageFont
import time
import asyncio

app = Flask(__name__)

# Configuration
RTMP_SERVER = "rtmp://localhost:1935/live"

# Dictionary to keep track of active streams
active_streams = {}

async def stream_to_youtube(stream_name, youtube_url, stop_event):
    input_url = f"{RTMP_SERVER}/{stream_name}"
    print(f"Input URL: {input_url}")

    while not stop_event.is_set():
        # Start FFmpeg stream to YouTube
        overlay_image = f"{stream_name}.png"
        ffmpeg_command = [
            'ffmpeg',
            '-i', input_url,
            '-i', overlay_image,
            '-filter_complex', '[0:v]transpose=2[v];[v][1:v]overlay=335:990',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-strict', 'experimental',
            '-f', 'flv',
            youtube_url
        ]

        process = subprocess.Popen(ffmpeg_command)
        print(f"Started FFmpeg process for stream: {stream_name}")

        # Start WebSocket function in background (async)
        task = asyncio.create_task(main(stream_name))

        while not stop_event.is_set():
            if process.poll() is not None:
                print(f"FFmpeg process for stream {stream_name} has ended unexpectedly.")
                break
            
            time.sleep(1)  # Sleep to simulate image refresh or control the loop

        # Ensure process is terminated properly
        if process.poll() is None:
            process.terminate()
            process.wait()

        # Wait for the background WebSocket task to finish (if needed)
        await task

    print(f"Stream {stream_name} stopped")


async def main(stream_name):
    match_id = stream_name
    await get_score_websocket_and_get_image(match_id)



@app.route('/start_stream', methods=['POST'])
def start_stream():
    data = request.json
    youtube_url = data.get('youtube_url')
    stream_name = data.get('stream_name')
    print(youtube_url, stream_name)
    if not youtube_url or not stream_name:
        return jsonify({'error': 'Missing youtube_url or stream_name'}), 400

    if stream_name in active_streams:
        return jsonify({'error': 'Stream already active'}), 409

    stop_event = threading.Event()
    thread = threading.Thread(target=stream_to_youtube, args=(
        stream_name, youtube_url, stop_event))
    thread.start()

    active_streams[stream_name] = {
        'thread': thread,
        'stop_event': stop_event,
        'youtube_url': youtube_url
    }

    return jsonify({'message': f'Stream {stream_name} started successfully'}), 200


@app.route('/stop_stream', methods=['POST'])
def stop_stream():
    data = request.json
    stream_name = data.get('stream_name')
    if not stream_name:
        return jsonify({'error': 'Missing stream_name'}), 400

    if stream_name not in active_streams:
        return jsonify({'error': 'Stream not found'}), 404

    active_streams[stream_name]['stop_event'].set()
    active_streams[stream_name]['thread'].join()
    del active_streams[stream_name]

    return jsonify({'message': f'Stream {stream_name} stopped successfully'}), 200


@app.route('/list_streams', methods=['GET'])
def list_streams():
    return jsonify({name: {'youtube_url': info['youtube_url']} for name, info in active_streams.items()}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1233)
