from pathlib import Path

# Base directories
APP_STATIC_FOLDER = "static"
BASE_DIR = Path("gallery").resolve()
THUMBNAIL_DIR = Path(APP_STATIC_FOLDER) / "thumbnails"
# Thumbnail generation options
THUMBNAIL_SIZE = (200, 200)
THUMBNAIL_QUALITY = 95
# Default placeholder values
DEFAULT_FOLDER_THUMBNAIL = "default_folder_thumb.png"
BACKGROUND_COLOR = (186, 193, 185)
# FFmpeg options for video thumbnails
FFMPEG_FRAME_TIMESTAMP = "00:00:01"
# App server configuration
APP_HOST = "0.0.0.0"
APP_PORT = 8080
APP_THREADS = 10
# Debugging
ENABLE_DEBUG_MODE = False
LOGGING_LEVEL = "ERROR"  # Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)