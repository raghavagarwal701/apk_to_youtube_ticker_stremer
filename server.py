import subprocess
import threading
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from score_fetch import fetch_match_data
from websocket_fech import get_score_websocket_and_get_image
from PIL import Image, ImageDraw, ImageFont
import time

app = Flask(__name__)

# Configuration
RTMP_SERVER = "rtmp://localhost:1935/live"

# Dictionary to keep track of active streams
active_streams = {}


def stream_to_youtube(stream_name, youtube_url, stop_event):
    input_url = f"{RTMP_SERVER}/{stream_name}"
    print(input_url)

    while not stop_event.is_set():
        # Generate the overlay image
        img = Image.open('score_image.png')
        overlay_image = f"{stream_name}.png"
        img.save(overlay_image)

        ffmpeg_command = [
            'ffmpeg',
            '-i', input_url,
            '-i', overlay_image,
            '-filter_complex', '[0:v]transpose=2[v];[v][1:v]overlay=15:620',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-strict', 'experimental',
            '-f', 'flv',
            youtube_url
        ]

        process_ffmpeg = subprocess.Popen(ffmpeg_command)

        # Start a separate thread or process for the score fetching
        def fetch_score():
            match_id = stream_name
            while not stop_event.is_set():
                get_score_websocket_and_get_image(match_id)

        score_thread = threading.Thread(target=fetch_score)
        score_thread.start()

        while not stop_event.is_set():
            if process_ffmpeg.poll() is not None:
                print(f"FFmpeg process for stream {stream_name} has ended unexpectedly.")
                break

            # Wait and generate the next overlay image (if needed)
            overlay_image = f"{stream_name}.png"
            time.sleep(100)  # Wait for 1 second before generating the next overlay image

        # Clean up when the stream is stopped
        if process_ffmpeg.poll() is None:
            process_ffmpeg.terminate()
            process_ffmpeg.wait()

        score_thread.join()  # Ensure the score-fetching thread finishes

    print(f"Stream {stream_name} stopped")

def main(stream_name):
    match_id = stream_name
    get_score_websocket_and_get_image(match_id)
    # print(score)

    # Open the sample image
    # img = Image.open('score_image.png')
    # draw = ImageDraw.Draw(img)

    # # Load custom font (if available, otherwise default font)
    # font_path = "OpenSans-Regular.ttf"  # Change this to the path of a .ttf font file if you want to use one
    # default_font_size = 20
    # try:
    #     font = ImageFont.truetype(font_path, default_font_size)
    # except IOError:
    #     font = ImageFont.load_default()

    # # Define score details with their specific coordinates and font sizes
    # batting_team_text_width = len(score['batting_team']) * 10
    # # Define score details with their specific coordinates and font sizes
    # score_elements = [
    #     {"text": f"{score['batting_team']}", "position": (35, 3), "font_size": 25, "color": "white"},
    #     {"text": f"{score['bowling_team']}", "position": (35, 45), "font_size": 22, "color": "white"},
    #     {"text": f"{score['score']}", "position": (35 + batting_team_text_width + 30, 6), "font_size": 20, "color": '#FFCB05'},
    #     {"text": f"{score['overs_bowled']} ", "position": (150, 14), "font_size": 14, "color": "#FFCB05"},
    #     {"text": f"{score['batter_one']}:  {score['batter_one_score']['runs']}({score['batter_one_score']['balls']})", "position": (325, 10), "font_size": 20, "color": "#ACEB6D"},
    #     {"text": f"{score['batter_two']}:  {score['batter_two_score']['runs']}({score['batter_two_score']['balls']})", "position": (325, 45), "font_size": 17, "color": "white"},
    #     {"text": f"{score['bowler']}", "position": (629, 23), "font_size": 20, "color": "#ACEB6D"},
    #     {"text": f"{score['bowler_figure']['ballsDelivered']}", "position": (757, 23), "font_size": 20, "color": "white"},
    #     {"text": f"balls", "position": (750, 49), "font_size": 12, "color": "white"},
    #     {"text": f"{score['bowler_figure']['runsGiven']}", "position": (802, 23), "font_size": 20, "color": "white"},
    #     {"text": f"runs", "position": (798, 49), "font_size": 12, "color": "white"},
    #     {"text": f"{score['bowler_figure']['wickets']}", "position": (855, 23), "font_size": 20, "color": "white"},
    #     {"text": f"wickets", "position": (840, 49), "font_size": 12, "color": "white"},
    # ]
    # # Loop through score elements and add each to the image
    # for element in score_elements:
    #     # Adjust font size if specified
    #     font = ImageFont.truetype(font_path, element["font_size"]) if font_path else ImageFont.load_default()
        
    #     # Add the text to the image at the specified position
    #     draw.text(element["position"], element["text"], font=font, fill="white")

    # # Save the modified image with match_id as the filename
    # img.save(f'{match_id}.png')

    # print(f"Image saved as {match_id}.png")


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
