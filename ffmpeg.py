"""
FFmpeg streaming functionality
"""
import os
import time
import subprocess
import threading
import logging
from config import RTMP_SERVER

logger = logging.getLogger(__name__)
ffmpeg_logger = logging.getLogger('ffmpeg')

# Maximum stream duration in seconds (5 hours)
MAX_STREAM_DURATION = 5 * 60 * 60

def process_ffmpeg_output(process, stream_id):
    """Process and log FFmpeg output"""
    while process.poll() is None:
        output = process.stderr.readline().decode('utf-8', errors='replace').strip()
        if output:
            ffmpeg_logger.debug(f"[Stream {stream_id}] {output}")

def stream_to_youtube(stream_id, youtube_url, stop_event):
    """Stream from RTMP server to YouTube using FFmpeg"""
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
    
    # Monitor the process with time limit
    start_time = time.time()
    
    while not stop_event.is_set():
        # Check if process has unexpectedly ended
        if process_ffmpeg.poll() is not None:
            logger.error(f"FFmpeg process for stream {stream_id} has ended unexpectedly with code {process_ffmpeg.returncode}")
            break
            
        # Check for timeout (5 hour limit)
        if time.time() - start_time > MAX_STREAM_DURATION:
            logger.warning(f"Stream {stream_id} reached maximum duration of {MAX_STREAM_DURATION/3600:.1f} hours. Terminating.")
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

    # Calculate actual stream duration
    duration = time.time() - start_time
    logger.info(f"Stream {stream_id} stopped after {duration/60:.1f} minutes")