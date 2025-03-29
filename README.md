# Streaming Service with Overlay

A Flask-based streaming service that relays RTMP streams to YouTube while overlaying real-time match data.

## Overview

This service provides an API for managing streams from an RTMP server to YouTube. It dynamically overlays match data over the video stream using FFmpeg. The application is designed with a modular structure for better maintainability and scalability.

## Project Structure

- `app.py` - Main application entry point
- `config.py` - Configuration settings
- `logging_setup.py` - Logging configuration
- `match_monitor.py` - Match monitoring functions
- `overlay.py` - Overlay image handling
- `ffmpeg.py` - FFmpeg streaming functionality
- `routes.py` - API endpoints

## Requirements

- Python 3.x
- FFmpeg with libx264 and support for overlay filters
- RTMP server (e.g., Nginx with RTMP module)
- PIL/Pillow for image manipulation

## Installation

1. Clone the repository
2. Install required Python packages:
   ```
   pip install flask requests pillow
   ```
3. Ensure FFmpeg is installed with required codecs

## Configuration

The main configuration settings are in `config.py`:

- `RTMP_SERVER` - Your RTMP server URL (default: "rtmp://localhost:1935/live")
- `OVERLAY_API_BASE` - API for match data (default: "http://3.6.126.60:8000")
- `OVERLAY_IMAGE_BASE` - URL for overlay images (default: "http://3.6.126.60:3000")

## API Endpoints

### Start a Stream

Start streaming from the RTMP server to YouTube.

**Endpoint:** `/start_stream`  
**Method:** POST  
**Content-Type:** application/json  

**Request Body:**
```json
{
  "youtube_url": "rtmp://a.rtmp.youtube.com/live2/your-stream-key",
  "stream_name": "unique_stream_id"
}
```

**Success Response:**
```json
{
  "message": "Stream unique_stream_id started successfully",
  "youtube_url": "rtmp://a.rtmp.youtube.com/live2/your-stream-key"
}
```

**Error Responses:**
- 400 Bad Request - Missing youtube_url or stream_name
- 409 Conflict - Stream already active
- 500 Internal Server Error - Failed to start match monitoring

### Stop a Stream

Stop an active stream.

**Endpoint:** `/stop_stream`  
**Method:** POST  
**Content-Type:** application/json  

**Request Body:**
```json
{
  "stream_name": "unique_stream_id"
}
```

**Success Response:**
```json
{
  "message": "Stream unique_stream_id stopped successfully"
}
```

**Error Responses:**
- 400 Bad Request - Missing stream_name
- 404 Not Found - Stream not found

### List Active Streams

Get information about all currently active streams.

**Endpoint:** `/list_streams`  
**Method:** GET  

**Success Response:**
```json
{
  "unique_stream_id": {
    "youtube_url": "rtmp://a.rtmp.youtube.com/live2/your-stream-key",
    "uptime": 3600.5
  },
  "another_stream_id": {
    "youtube_url": "rtmp://a.rtmp.youtube.com/live2/another-key",
    "uptime": 120.25
  }
}
```

## How It Works

1. When a stream is started, the application:
   - Starts monitoring match data via an external API
   - Creates an initial overlay image (or uses a blank placeholder)
   - Starts a thread to continuously update the overlay image
   - Starts an FFmpeg process that overlays the image on the RTMP stream and forwards to YouTube

2. The overlay image is continuously updated with match data, and the FFmpeg process uses this image to create the final stream output.

3. When a stream is stopped, the application:
   - Stops the FFmpeg process
   - Stops the overlay image update thread
   - Cleans up temporary files

## Running the Application

Start the server using:

```
python app.py
```

The server will run on port 1233 by default.

## Example API Usage

### Start a Stream
```bash
curl -X POST http://your-server-ip:1233/start_stream \
-H "Content-Type: application/json; charset=UTF-8" \
-d '{
  "youtube_url": "rtmp://a.rtmp.youtube.com/live2/your-stream-key",
  "stream_name": "my_stream_key"
}'
```

### Stop a Stream
```bash
curl -X POST http://your-server-ip:1233/stop_stream \
-H "Content-Type: application/json; charset=UTF-8" \
-d '{
  "stream_name": "my_stream_key"
}'
```

### List Active Streams
```bash
curl -X GET http://your-server-ip:1233/list_streams
```

## NGINX RTMP Configuration

This application is designed to work with an NGINX RTMP server. A basic NGINX configuration would include:

```
rtmp {
    server {
        listen 1935;
        chunk_size 4096;
        
        application live {
            live on;
            record off;
        }
    }
}
```

## Troubleshooting

- Check the application logs in `logs/application.log`
- FFmpeg-specific logs are available in `logs/ffmpeg.log`
- Ensure your RTMP server is properly configured and accessible
- Verify YouTube stream keys are valid and not expired