import os
import random
import subprocess
from unittest import result
from flask import Flask, render_template, url_for, send_from_directory, abort
from PIL import Image, ImageFile, ImageOps
from pathlib import Path
from config import (
    BASE_DIR, THUMBNAIL_DIR, THUMBNAIL_SIZE, THUMBNAIL_QUALITY,
    DEFAULT_FOLDER_THUMBNAIL, FFMPEG_FRAME_TIMESTAMP,
    APP_HOST, APP_PORT, APP_THREADS, ENABLE_DEBUG_MODE
)
app = Flask(__name__)
# Base gallery and thumbnail dirs
BASE_DIR = Path("gallery").resolve()
THUMBNAIL_DIR = Path(app.static_folder) / "thumbnails"
ImageFile.LOAD_TRUNCATED_IMAGES = True
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)  # Ensure thumbnails dir exists

def recreate_folder_structure(file_path, base_dir, thumbnail_dir):
    relative_path = Path(file_path).relative_to(Path(base_dir))
    thumbnail_path = Path(thumbnail_dir) / relative_path
    Path(thumbnail_path).parent.mkdir(parents=True, exist_ok=True)
    return thumbnail_path.as_posix()

def generate_thumbnail(file_path, thumbnail_path, size=(200, 200), quality=95):
    """
    Generate consistent thumbnails for images by cropping and zooming
    into the content to match thumbnail dimensions.
    """
    file_path = Path(file_path)
    try:
        with Image.open(file_path) as img:
            # Correct image oriantation
            img = ImageOps.exif_transpose(img)
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
            print(f"Cropped image to box: {box}, final size before resizing: {img.size}")

            # Step 2: Resize the cropped image to the target size
            img = img.resize(size, Image.Resampling.LANCZOS)

            # Step 3: Save the resized (cropped and zoomed) thumbnail
            img.save(thumbnail_path, "JPEG", quality=quality)
            print(f"Thumbnail saved at {thumbnail_path} with size {size}")

        return thumbnail_path
    except (FileNotFoundError, OSError) as e:
        print(f"Error generating thumbnail for {file_path}: {e}")

def generate_video_thumbnail(video_path, thumbnail_path, size=(200, 200), timestamp="00:00:01"):
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

def get_random_preview(folder_path: Path, size=(200, 200), quality=95, background_color=(186, 193, 185)):
    folder_path = Path(folder_path)
    if not folder_path.exists():
        print(f"Folder {folder_path} does not exist.")
        return url_for("static", filename="default_folder_thumb.png")

    # Gather all valid image files in the folder
    files = [f for f in folder_path.glob("*") if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4"]]
    print(f"Found files in folder {folder_path}: {files}")

    # Check if there are no valid image files
    if not files:
        fallback = THUMBNAIL_DIR / "default_folder_thumb.png"
        if not fallback.exists():
            fallback.touch()  # Create an empty fallback file if it doesn't exist
        return url_for("static", filename="default_folder_thumb.png")

    # Randomly select an image for preview
    selected_image = random.choice(files)
    print(f"Selected image for thumbnail: {selected_image}")

    # Generate a thumbnail path
    thumbnail_path = recreate_folder_structure(selected_image, BASE_DIR, THUMBNAIL_DIR)
    thumbnail_path = os.path.splitext(thumbnail_path)[0] + ".jpg"

    # Generate the thumbnail if it doesn't already exist
    if not Path(thumbnail_path).exists():
        print(f"Thumbnail not found, generating: {thumbnail_path}")
        generate_thumbnail(
            selected_image,
            thumbnail_path,
            size=size,
            quality=quality,
            # background_color=background_color,
        )

    # Return the relative thumbnail path for URLs
    relative_url = f"thumbnails/{Path(thumbnail_path).relative_to(THUMBNAIL_DIR).as_posix()}"
    print(f"Generated relative URL for thumbnail: {relative_url}")
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
    print(f"Resolved folder path: {folder_path}")
    if not folder_path.exists():
        print(f"Folder {folder_path} does not exist.")
    print(f"Counting images in folder: {folder_path}")
    try:
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        return sum(1 for f in folder_path.glob("*") if f.suffix.lower() in image_extensions)
    except Exception as e:
        print(f"Error counting images in directory {folder_path}: {e}")
        return 0

def get_folder_content(current_path):
    """Get folder and file content dynamically, verifying that all directories/files actually exist."""
    print(f"Scanning: {current_path}")
    content = {"folders": [], "files": []}

    current_path = Path(current_path)
    if current_path.exists():
        for entry in sorted(os.listdir(current_path)):
            entry_path = os.path.join(current_path, entry)

            # Process folders
            if os.path.isdir(entry_path):
                preview = get_random_preview(entry_path)
                print(f"Folder preview for {entry_path}: {preview}")
                content["folders"].append({
                    "preview": preview,
                    "name": entry,
                })
                print(f"Adding folder to content: {entry}")


            # Process files
            elif os.path.isfile(entry_path):
                ext = os.path.splitext(entry)[1].lower()

                # For images
                if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                    # Generate the thumbnail path and normalize it for URLs
                    thumbnail_path = recreate_folder_structure(Path(entry_path), BASE_DIR, THUMBNAIL_DIR)
                    thumbnail_path = os.path.splitext(thumbnail_path)[0] + ".jpg"

                    if not os.path.exists(thumbnail_path):
                        generate_thumbnail(Path(entry_path), Path(thumbnail_path))
                        print(f"Generated thumbnail for image file: {entry_path} -> {thumbnail_path}")

                    # Use the relative path for URL generation, ensuring forward slashes
                    content["files"].append({
                        "type": "image",
                        "path": url_for("gallery_file", filepath=Path(entry_path).relative_to(BASE_DIR).as_posix()),
                        "thumbnail": url_for("static", filename=f"thumbnails/{Path(thumbnail_path).relative_to(THUMBNAIL_DIR).as_posix()}")
                    })
                    print(f"Thumbnail relative URL for image: thumbnails/{Path(thumbnail_path).relative_to(THUMBNAIL_DIR).as_posix()}")

                # For videos
                elif ext in [".mp4", ".avi", ".mov"]:
                    # Generate the thumbnail path and normalize it for URLs
                    thumbnail_path = recreate_folder_structure(Path(entry_path), BASE_DIR, THUMBNAIL_DIR)
                    thumbnail_path = os.path.splitext(thumbnail_path)[0] + ".jpg"

                    if not os.path.exists(thumbnail_path):
                        generate_video_thumbnail(Path(entry_path), Path(thumbnail_path))
                        print(f"Generated thumbnail for video file: {entry_path} -> {thumbnail_path}")

                    # Use the relative path for URL generation, ensuring forward slashes
                    thumbnail_relative_url = f"thumbnails/{Path(thumbnail_path).relative_to(THUMBNAIL_DIR).as_posix()}"
                    print(f"Thumbnail relative URL for video: {thumbnail_relative_url}")
                    content["files"].append({
                        "type": "video",
                        "name": entry,
                        "path": url_for("gallery_file",
                                        filepath=os.path.relpath(Path(entry_path), BASE_DIR).replace("\\", "/")),
                        "thumbnail": url_for("static", filename=thumbnail_relative_url)
                    })

    return content

@app.template_filter('truncate')
def truncate_filter(s, max_length=15):
    return s[:max_length] + "..." if len(s) > max_length else s
@app.route("/")
def gallery():
    """Main gallery landing page."""
    total_images = count_images_in_directory(BASE_DIR)
    content = get_folder_content(BASE_DIR)
    return render_template("index.html", folders=content["folders"], files=content["files"], breadcrumb=[], total_images=total_images, enumerate=enumerate)
@app.route("/<path:subpath>/")
def subgallery(subpath):
    """Dynamic route for gallery subfolders."""
    current_path = os.path.join(BASE_DIR, subpath)
    print(f"Accessing subgallery: {current_path}")

    if not os.path.exists(current_path):
        return "Folder not found", 404
    total_images = count_images_in_directory(current_path)
    content = get_folder_content(current_path)
    breadcrumb = subpath.split("/") if subpath else []
    parent_path = "/".join(breadcrumb[:-1]) if breadcrumb else None
    return render_template("index.html", folders=content["folders"], files=content["files"], breadcrumb=breadcrumb, parent_path=parent_path, total_images=total_images, enumerate=enumerate)
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
    print(f"Serving file: {full_path}")
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

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000, debug=False)

if __name__ == "__main__":
    from waitress import serve
    serve(app, host=APP_HOST, port=APP_PORT, threads=APP_THREADS)