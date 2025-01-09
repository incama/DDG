import os
# import random | maybe in the near future when performance isn't an issue
import subprocess
from math import ceil
import logging
from flask import Flask, render_template, url_for, send_from_directory, abort, request
from PIL import Image, ImageFile, ImageOps
from pathlib import Path
from config import (
    BASE_DIR, THUMBNAIL_DIR, THUMBNAIL_SIZE, THUMBNAIL_QUALITY,
    DEFAULT_FOLDER_THUMBNAIL, FFMPEG_FRAME_TIMESTAMP,
    APP_HOST, APP_PORT, APP_THREADS, ENABLE_DEBUG_MODE, LOGGING_LEVEL, DEFAULT_LIMIT
)
app = Flask(__name__)

ImageFile.LOAD_TRUNCATED_IMAGES = True
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)  # Ensure thumbnails dir exists
thumbnail_cache = {}

# Ensure the logging directory exists
log_dir = Path("log")
log_dir.mkdir(parents=True, exist_ok=True)  # Create 'log' directory if it doesn't exist

logging.basicConfig(
    filename="log/app.log",  # Log file
    filemode="a",  # Append mode (adds to logs instead of overwriting)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
    level=LOGGING_LEVEL
)

def recreate_folder_structure(file_path, base_dir, thumbnail_dir):
    relative_path = Path(file_path).relative_to(Path(base_dir))
    thumbnail_path = Path(thumbnail_dir) / relative_path
    Path(thumbnail_path).parent.mkdir(parents=True, exist_ok=True)
    return thumbnail_path.as_posix()

def generate_thumbnail(file_path, thumbnail_path, size=(200, 200), quality=95):
    file_path = Path(file_path)
    try:
        with Image.open(file_path) as img:
            # Correct image orientation
            img = ImageOps.exif_transpose(img)

            # Convert PNG with alpha channel (RGBA) to RGB
            if img.mode in ("RGBA", "P"):  # Handle transparency or palette mode
                # Create a white background and paste the image onto it
                background = Image.new("RGB", img.size, (255, 255, 255))  # Solid white
                background.paste(img, mask=img.getchannel("A"))  # Use alpha channel as mask
                img = background

            # Get original image size
            width, height = img.size
            target_width, target_height = size

            # Compute aspect ratios
            image_aspect = width / height
            target_aspect = target_width / target_height

            # Step 1: Crop the image to match the target aspect ratio (zoom effect)
            if image_aspect > target_aspect:
                # Wider than target: crop the width
                new_width = int(height * target_aspect)
                offset = (width - new_width) // 2
                box = (offset, 0, offset + new_width, height)
            else:
                # Taller than target: crop the height
                new_height = int(width / target_aspect)
                offset = (height - new_height) // 2
                box = (0, offset, width, offset + new_height)

            img = img.crop(box)  # Crop the image to the calculated box
            logging.info(f"Cropped image to box: {box}, final size before resizing: {img.size}")

            # Step 2: Resize the cropped image to the target size
            img = img.resize(size, Image.Resampling.LANCZOS)

            # Step 3: Save the resized (cropped and zoomed) thumbnail as a JPEG
            img.save(thumbnail_path, "JPEG", quality=quality)
            logging.info(f"Thumbnail saved at {thumbnail_path} with size {size}")

        return thumbnail_path

    except (FileNotFoundError, OSError) as e:
        logging.error(f"Error generating thumbnail for {file_path}: {e}")

def generate_video_thumbnail(video_path, thumbnail_path, size=(200, 200), timestamp="00:00:00"):
    """
    Generate consistent thumbnails for videos by cropping and zooming
    into the video frame to match thumbnail dimensions.
    """
    try:
        # Check for FFmpeg availability
        ffmpeg_check = subprocess.run(
            ["where" if os.name == "nt" else "which", "ffmpeg"], capture_output=True
        )
        if ffmpeg_check.returncode != 0:
            raise EnvironmentError("FFmpeg is not available on this system.")
        print("FFmpeg is available.")

        # Save the raw frame to a temporary location
        extracted_frame_path = Path(thumbnail_path).with_suffix('.temp.jpg')  # Temporary file
        print(f"Raw frame will be saved at {extracted_frame_path}")

        # Step 1: Extract a frame using FFmpeg
        result = subprocess.run(
            [
                "ffmpeg",
                "-i", str(video_path),  # Input video file
                "-ss", timestamp,  # Timestamp for the frame
                "-frames:v", "1",  # Extract only one frame
                str(extracted_frame_path)  # Output path
            ],
            capture_output=True,
            text=True
        )

        # Log FFmpeg outputs for debugging
        print("FFmpeg command executed.")
        print("FFmpeg output:", result.stdout)
        print("FFmpeg errors:", result.stderr)

        # Step 2: Process the extracted image frame
        if extracted_frame_path.exists():
            generate_thumbnail(extracted_frame_path, thumbnail_path, size=size)  # Crop and resize for consistency

        # Step 3: Cleanup temporary raw frame
        if extracted_frame_path.exists():
            extracted_frame_path.unlink(missing_ok=True)
            print(f"Temporary raw frame removed: {extracted_frame_path}")

        return thumbnail_path

    except (FileNotFoundError, OSError, EnvironmentError) as e:
        print(f"Error generating video thumbnail for {video_path}: {e}")

# def get_random_preview(folder_path: Path, size=(200, 200), quality=95, background_color=(186, 193, 185)):
#     folder_path = Path(folder_path)
#
#     # Check if folder exists
#     if not folder_path.exists():
#         logging.warning(f"Folder {folder_path} does not exist.")
#         return url_for("static", filename="default_folder_thumb.png")
#
#     # Check if the folder has a cached thumbnail
#     if folder_path in thumbnail_cache:
#         logging.info(f"Cache hit for folder {folder_path}")
#         return thumbnail_cache[folder_path]  # Return cached URL
#
#     logging.info(f"Cache miss for folder {folder_path}. Generating thumbnail.")
#
#     # Gather all valid image files in the folder
#     files = [f for f in folder_path.glob("*") if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4"]]
#     logging.debug(f"Found files in folder {folder_path}: {files}")
#
#     # Check if there are no valid image files
#     if not files:
#         logging.info(f"No valid image files found in folder {folder_path}. Using fallback thumbnail.")
#         fallback = THUMBNAIL_DIR / "default_folder_thumb.png"
#         if not fallback.exists():
#             fallback.touch()  # Create an empty fallback file if it doesn't exist
#             logging.debug(f"Created an empty fallback file at {fallback}")
#         url = url_for("static", filename="default_folder_thumb.png")
#         thumbnail_cache[folder_path] = url  # Update cache
#         return url
#
#     # Randomly select an image for preview
#     selected_image = random.choice(files)
#     logging.info(f"Selected image for thumbnail: {selected_image}")
#
#     # Generate a thumbnail path
#     thumbnail_path = recreate_folder_structure(selected_image, BASE_DIR, THUMBNAIL_DIR)
#     thumbnail_path = os.path.splitext(thumbnail_path)[0] + ".jpg"
#
#     # Generate the thumbnail if it doesn't already exist
#     if not Path(thumbnail_path).exists():
#         logging.info(f"Thumbnail not found, generating: {thumbnail_path}")
#         generate_thumbnail(
#             selected_image,
#             thumbnail_path,
#             size=size,
#             quality=quality,
#             # background_color=background_color,
#         )
#
#     # Return the relative thumbnail path for URLs
#     relative_url = f"thumbnails/{Path(thumbnail_path).relative_to(THUMBNAIL_DIR).as_posix()}"
#     logging.debug(f"Generated relative URL for thumbnail: {relative_url}")
#     thumbnail_url = url_for("static", filename=relative_url)
#
#     # Cache the generated thumbnail URL
#     thumbnail_cache[folder_path] = thumbnail_url
#     return thumbnail_url
def get_first_preview(folder_path: Path, size=(200, 200), quality=95, background_color=(186, 193, 185)):
    """
    Generate a preview for a folder using the first valid image/video file found in the folder.
    """
    folder_path = Path(folder_path)

    # Check if folder exists
    if not folder_path.exists():
        logging.warning(f"Folder {folder_path} does not exist.")
        return url_for("static", filename="default_folder_thumb.png")

    # Gather all valid image/video files in the folder and sort them
    valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4"]
    files = sorted([f for f in folder_path.iterdir() if f.suffix.lower() in valid_extensions])
    logging.debug(f"Sorted files in folder {folder_path}: {files}")

    # Check if there are no valid files
    if not files:
        logging.info(f"No valid image/video files found in folder {folder_path}. Using fallback thumbnail.")
        fallback = THUMBNAIL_DIR / "default_folder_thumb.png"
        if not fallback.exists():
            fallback.touch()  # Create an empty fallback file if it doesn't exist
            logging.debug(f"Created an empty fallback file at {fallback}")
        return url_for("static", filename="default_folder_thumb.png")

    # Use the first file as the preview
    first_file = files[0]
    logging.info(f"Using the first file as thumbnail: {first_file}")

    # Generate a thumbnail path
    thumbnail_path = recreate_folder_structure(first_file, BASE_DIR, THUMBNAIL_DIR)
    thumbnail_path = os.path.splitext(thumbnail_path)[0] + ".jpg"

    # Generate the thumbnail if it doesn't already exist
    if not Path(thumbnail_path).exists():
        logging.info(f"Thumbnail not found, generating: {thumbnail_path}")
        generate_thumbnail(
            first_file,
            thumbnail_path,
            size=size,
            quality=quality,
            # background_color=background_color,
        )

    # Return the relative thumbnail path for URLs
    relative_url = f"thumbnails/{Path(thumbnail_path).relative_to(THUMBNAIL_DIR).as_posix()}"
    logging.debug(f"Generated relative URL for thumbnail: {relative_url}")
    return url_for("static", filename=relative_url)

def cleanup_thumbnails(base_dir: str, thumbnail_dir: str):
    try:
        thumbnail_dir = Path(thumbnail_dir).resolve()
        base_dir = Path(base_dir).resolve()

        if not thumbnail_dir.exists():
            print(f"Thumbnail directory {thumbnail_dir} does not exist.")
            return

        # Traverse all items in the thumbnail directory
        for item in sorted(thumbnail_dir.rglob("*"), reverse=True):  # Reverse ensures we clean deepest items first
            if item.is_file():
                # Check if the original file still exists in the base directory
                corresponding_path = Path(base_dir) / item.relative_to(thumbnail_dir)
                if not corresponding_path.exists():
                    print(f"Removing unused thumbnail file: {item}")
                    try:
                        item.unlink()
                    except OSError as e:
                        print(f"Failed to remove file {item}: {e}")
            elif item.is_dir():
                # Check if the corresponding folder exists in the base structure
                corresponding_path = Path(base_dir) / item.relative_to(thumbnail_dir)
                if not corresponding_path.exists():
                    print(f"Removing unused thumbnail folder: {item}")
                    try:
                        item.rmdir()  # Only removes empty directories
                    except OSError as e:
                        print(f"Failed to remove folder {item}: {e}")

        # After recursive cleanup, check if the main thumbnail directory can also be cleaned
        try:
            if not any(thumbnail_dir.iterdir()):  # Check if directory is empty
                thumbnail_dir.rmdir()
                print(f"Thumbnail directory {thumbnail_dir} is removed.")
            else:
                print(f"Thumbnail directory {thumbnail_dir} is not empty after cleanup.")
        except OSError as e:
            print(f"Failed to remove the main thumbnail directory: {e}")

    except Exception as e:
        import traceback
        print(f"Error during thumbnail cleanup: {e}")
        traceback.print_exc()

def count_images_in_directory(folder_path: Path):
    folder_path = Path(folder_path).resolve()
    logging.debug(f"Resolved folder path: {folder_path}")

    if not folder_path.exists():
        logging.warning(f"Folder does not exist while counting images: {folder_path}")
        return 0

    try:
        logging.info(f"Counting images in folder: {folder_path}")
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.mp4', '.avi', '.mov']
        count = sum(1 for f in folder_path.glob("*") if f.suffix.lower() in image_extensions)
        logging.debug(f"Found {count} images in folder: {folder_path}")
        return count

    except Exception as e:
        logging.error(f"Error counting images in directory {folder_path}: {e}")
        return 0

def get_folder_content(current_path, page=1, limit=DEFAULT_LIMIT):
    """
    Get folder and file content dynamically with pagination.

    Args:
        current_path (str): Path to the folder.
        page (int): Current page number (default: 1).
        limit (int): Number of files per page (default: 10).

    Returns:
        dict: Content including folders and paginated files.
    """
    logging.info(f"Scanning directory: {current_path}")
    content = {"folders": [], "files": []}

    current_path = Path(current_path)
    if current_path.exists():  # Check if the folder exists
        # Sort and process all directory entries
        entries = sorted(current_path.iterdir(), key=lambda entry: entry.name)

        # Separate folders and files
        folders = [entry for entry in entries if entry.is_dir()]
        files = [entry for entry in entries if entry.is_file()]

        # Process Folders
        for folder in folders:
            preview = get_first_preview(folder)  # Assuming this function exists
            logging.debug(f"Folder preview for {folder}: {preview}")
            content["folders"].append({
                "preview": preview,
                "name": folder.name,  # Only the folder name, without the full path
            })

        # Paginate Files
        total_files = len(files)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_files = files[start_idx:end_idx]

        for file in paginated_files:
            ext = file.suffix.lower()  # File extension

            # Process Images
            if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                # Generate or retrieve thumbnail
                thumbnail_path = recreate_folder_structure(file, BASE_DIR, THUMBNAIL_DIR)
                thumbnail_path = f"{Path(thumbnail_path).with_suffix('.jpg')}"

                # Normalize thumbnail_path with forward slashes
                thumbnail_path = str(Path(thumbnail_path).as_posix())

                if not Path(thumbnail_path).exists():
                    generate_thumbnail(file, thumbnail_path)

                # Build file and thumbnail URLs
                content["files"].append({
                    "type": "image",
                    "path": url_for("gallery_file", filepath=str(file.relative_to(BASE_DIR).as_posix())),
                    "thumbnail": url_for("static", filename=f"thumbnails/{Path(thumbnail_path).relative_to(THUMBNAIL_DIR).as_posix()}"),
                })
            elif ext in [".mp4", ".avi", ".mov"]:
                # Generate the thumbnail path and normalize it for URLs
                thumbnail_path = recreate_folder_structure(file, BASE_DIR, THUMBNAIL_DIR)
                thumbnail_path = os.path.splitext(thumbnail_path)[0] + ".jpg"

                if not os.path.exists(thumbnail_path):
                    generate_video_thumbnail(file, Path(thumbnail_path))
                    logging.info(f"Generated thumbnail for video file: {file} -> {thumbnail_path}")

                # Use the relative path for URL generation, ensuring forward slashes
                thumbnail_relative_url = f"thumbnails/{Path(thumbnail_path).relative_to(THUMBNAIL_DIR).as_posix()}"
                logging.debug(f"Thumbnail relative URL for video: {thumbnail_relative_url}")
                content["files"].append({
                    "type": "video",
                    # "name": file,
                    "path": url_for("gallery_file", filepath=str(file.relative_to(BASE_DIR).as_posix())),
                    "thumbnail": url_for("static", filename=f"thumbnails/{Path(thumbnail_path).relative_to(THUMBNAIL_DIR).as_posix()}"),
                })
                logging.debug(f"Thumbnail relative URL for video: {thumbnail_relative_url}")
    else:
        logging.warning(f"Directory does not exist: {current_path}")
    return content

@app.template_filter('truncate')
def truncate_filter(s, max_length=15):
    return s[:max_length] + "..." if len(s) > max_length else s
@app.route("/")
def gallery():
    """Main gallery landing page with pagination."""
    try:
        # Get pagination parameters
        page = int(request.args.get("page", 1))  # Default to page 1
        limit = int(request.args.get("limit", DEFAULT_LIMIT))  # Default to DEFAULT_LIMIT items per page

        # Fetch folder contents and total images
        logging.debug("Fetching images count.")
        total_images = count_images_in_directory(BASE_DIR)

        if total_images == 0:
            logging.warning("No images found in the directory.")

        content = get_folder_content(BASE_DIR, page=page, limit=limit)

        # Calculate total pages
        total_pages = max(1, ceil(total_images / limit))  # Ensure at least 1 page
        logging.debug(f"Total pages calculated: {total_pages}")

        # Calculate page range for pagination
        window_size = 7  # Number of page links to show
        start_page = max(1, page - window_size // 2)
        end_page = min(total_pages, start_page + window_size - 1)
        start_page = max(1, end_page - window_size + 1)

        # Generate pagination data
        page_numbers = list(range(start_page, end_page + 1))
        logging.debug(f"Page numbers: {page_numbers}")

        prev_url = url_for("gallery", page=page - 1, limit=limit) if page > 1 else None
        next_url = url_for("gallery", page=page + 1, limit=limit) if page < total_pages else None

        # Render the template
        return render_template(
            "index.html",
            folders=content["folders"],
            files=content["files"],
            breadcrumb=[],
            total_images=total_images,
            total_pages=total_pages,
            current_page=page,
            parent_path=None,
            prev_url=prev_url,
            next_url=next_url,
            page_numbers=page_numbers,
            enumerate=enumerate,
        )
    except Exception as e:
        logging.exception("Error in gallery function")
        return "An error occurred. Please check the logs.", 500
@app.route("/<path:subpath>/")
def subgallery(subpath):
    """Dynamic subgallery with pagination."""
    try:
        # Build the current directory path
        current_path = os.path.join(BASE_DIR, subpath)
        logging.debug(f"Accessing subgallery: subpath={subpath}, current_path={current_path}")

        # Check if the path exists
        if not os.path.exists(current_path):
            logging.warning(f"Folder not found: {current_path}")
            return "Folder not found", 404

        # Get pagination parameters
        page = int(request.args.get("page", 1))  # Default to page 1
        limit = int(request.args.get("limit", DEFAULT_LIMIT))  # Default to DEFAULT_LIMIT items per page
        logging.debug(f"Pagination parameters: page={page}, limit={limit}")

        # Fetch total images and folder contents
        total_images = count_images_in_directory(current_path)
        logging.debug(f"Total images in current_path='{current_path}': {total_images}")
        content = get_folder_content(current_path, page=page, limit=limit)

        # Breadcrumb and parent path for navigation
        breadcrumb = subpath.split("/") if subpath else []
        logging.debug(f"Breadcrumb: {breadcrumb}")
        parent_path = "/".join(breadcrumb[:-1]) if breadcrumb else None

        # Calculate total pages
        total_pages = max(1, ceil(total_images / limit))  # Ensure at least 1 page
        logging.debug(f"Total pages calculated: {total_pages}")

        # Handle page range for pagination
        window_size = 7  # Adjustable number of page links to display
        start_page = max(1, page - window_size // 2)
        end_page = min(total_pages, start_page + window_size - 1)
        start_page = max(1, end_page - window_size + 1)
        page_numbers = list(range(start_page, end_page + 1))

        # Debug log for pagination
        logging.debug(f"Page numbers: {page_numbers}")

        # Handle pagination URLs
        prev_url = url_for("subgallery", subpath=subpath, page=page - 1, limit=limit) if page > 1 else None
        next_url = url_for("subgallery", subpath=subpath, page=page + 1, limit=limit) if page < total_pages else None

        # Render the template (HTML structure assumes index.html supports folders/files display)
        return render_template(
            "index.html",
            folders=content["folders"],
            files=content["files"],
            breadcrumb=breadcrumb,
            total_images=total_images,
            total_pages=total_pages,
            current_page=page,
            parent_path=parent_path,
            prev_url=prev_url,
            next_url=next_url,
            page_numbers=page_numbers,
            enumerate=enumerate,
        )
    except Exception as e:
        logging.exception(f"Error in subgallery route: {e}")
        return "An error occurred. Please check the logs.", 500
@app.route("/cleanup-thumbnails", methods=["POST"])
def cleanup_thumbnails_route():
    """Endpoint to clean up unused thumbnails."""
    cleanup_thumbnails(BASE_DIR, THUMBNAIL_DIR)
    return "Thumbnail cleanup completed!", 200
@app.route("/view/<path:filepath>")
def gallery_file(filepath):
    """Serve files (images/videos)."""
    full_path = os.path.join(BASE_DIR, filepath)
    if not os.path.exists(full_path):
        print(f"File not found: {full_path}")
        return "File not found", 404
    logging.debug(f"Serving file: {full_path}")
    return send_from_directory(BASE_DIR, filepath)
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')
@app.route('/static/<path:filename>')
def static_files(filename):
    # Serve specific files from the static folder, not directory browsing
    return send_from_directory('static', filename)
@app.route('/static/')
def block_static_folder_listing():
    # Blocks listing of the /static/ directory
    abort(403)

# Run if waitress is acting up or for development
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000, debug=False)

if __name__ == "__main__":
    from waitress import serve
    serve(app, host=APP_HOST, port=APP_PORT, threads=APP_THREADS)