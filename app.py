import os
import random
import subprocess
from flask import Flask, render_template, url_for, send_from_directory
from PIL import Image, ImageOps, ImageFile
app = Flask(__name__)
# Base gallery and thumbnail dirs
BASE_DIR = "gallery"
THUMBNAIL_DIR = "static/thumbnails"
ImageFile.LOAD_TRUNCATED_IMAGES = True
os.makedirs(THUMBNAIL_DIR, exist_ok=True)  # Ensure thumbnails dir exists

def recreate_folder_structure(file_path, base_dir, thumbnail_dir):
    """
    Recreate the folder structure of the gallery inside the thumbnail directory.

    Parameters:
    - file_path (str): The full path to the original file (image/video).
    - base_dir (str): The base directory of the gallery.
    - thumbnail_dir (str): The base directory for the thumbnails.

    Returns:
    - str: The full path to the thumbnail file.
    """
    # Get the relative path from the gallery base directory
    relative_path = os.path.relpath(file_path, base_dir)

    # Create corresponding paths in the thumbnail directory
    thumbnail_path = os.path.join(thumbnail_dir, relative_path)

    # Ensure the parent directory for the thumbnail exists
    os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)

    return thumbnail_path.replace("\\", "/")

def generate_thumbnail(file_path, thumbnail_path, size=(300, 300), quality=95, background_color=(186, 193, 185)):
    """
    Generate a uniform square thumbnail for an image without distorting the aspect ratio.

    Parameters:
    - file_path (str): The path to the original image file.
    - thumbnail_path (str): Path to save the resulting thumbnail.
    - size (tuple): Desired thumbnail size (width, height); default is (200, 200).

    Returns:
    - None
    """
    try:
        with Image.open(file_path) as img:
            # Fix orientation based on EXIF metadata
            img = ImageOps.exif_transpose(img)

            # Preserve aspect ratio and fit image within the square area
            img.thumbnail(size, Image.Resampling.LANCZOS)

            # Create a new square image with the specified background color
            square_thumbnail = Image.new("RGB", size, background_color)

            # Calculate coordinates to center the image on the canvas
            offset_x = (size[0] - img.width) // 2
            offset_y = (size[1] - img.height) // 2
            square_thumbnail.paste(img, (offset_x, offset_y))

            # Save the resulting thumbnail
            square_thumbnail.save(thumbnail_path)
            print(f"Thumbnail with padding saved at {thumbnail_path}")
    except Exception as e:
        print(f"Error generating padded thumbnail for {file_path}: {e}")

def generate_video_thumbnail(video_path, thumbnail_path, size=(300, 300), timestamp="00:00:01"):
    """
    Generate a thumbnail for a video file using FFmpeg and resize it to the given size.

    Parameters:
    - video_path (str): The path to the video file.
    - thumbnail_path (str): The path where the generated thumbnail will be saved.
    - size (tuple): The size of the thumbnail (width, height).
    - timestamp (str): The timestamp for the frame to extract (default is the 1-second mark).

    Returns:
    - str: The path to the generated thumbnail or None if an error occurred.
    """
    try:
        # Use FFmpeg to extract a frame at the specified timestamp
        extracted_frame_path = thumbnail_path.replace('.jpg', '_raw.jpg')
        subprocess.run(
            [
                "ffmpeg",
                "-i", video_path,  # Input video file
                "-ss", timestamp,  # Timestamp for the frame
                "-vframes", "1",  # Extract only one frame
                extracted_frame_path,  # Path to save the extracted frame
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL  # Suppress FFmpeg output
        )

        # Check if the frame was successfully extracted
        if not os.path.exists(extracted_frame_path):
            print(f"Error extracting frame from video {video_path}")
            return None

        # Resize the extracted frame to the desired thumbnail size
        with Image.open(extracted_frame_path) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumbnail_path)

        # Delete the raw extracted frame (cleanup)
        os.remove(extracted_frame_path)

        print(f"Thumbnail for video {video_path} saved at {thumbnail_path}")
        return thumbnail_path

    except Exception as e:
        print(f"Error generating video thumbnail for {video_path}: {e}")
        return None

def get_random_preview(folder_path, size=(300, 300), quality=95, background_color=(186, 193, 185)):
    """
    Get a random image from a folder and generate a uniform thumbnail as a preview.

    Parameters:
    - folder_path (str): Path to the folder containing images.
    - size (tuple): Thumbnail size (default: 300x300).
    - quality (int): JPEG output quality (default: 95).
    - background_color (tuple): Background color for padding (default: black).

    Returns:
    - str: The relative path to the generated thumbnail.
    """
    try:
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist.")
            return url_for("static", filename="default_folder_thumb.png")

        # Gather all valid image files in the folder
        files = [
            os.path.join(folder_path, file)
            for file in os.listdir(folder_path)
            if os.path.splitext(file)[1].lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        ]

        if not files:
            return url_for("static", filename="default_folder_thumb.png")

        # Randomly select an image for preview
        selected_image = random.choice(files)

        # Generate a thumbnail path
        thumbnail_path = recreate_folder_structure(selected_image, BASE_DIR, THUMBNAIL_DIR)
        thumbnail_path = os.path.splitext(thumbnail_path)[0] + ".jpg"

        # Generate the thumbnail if it doesn't already exist
        if not os.path.exists(thumbnail_path):
            generate_thumbnail(selected_image, thumbnail_path, size=size, quality=quality,
                               background_color=background_color)

        # Return the relative thumbnail path for URLs
        return f"/static/{os.path.relpath(thumbnail_path, 'static').replace('\\', '/')}"

    except Exception as e:
        print(f"Error generating preview for folder {folder_path}: {e}")
        return url_for("static", filename="default_folder_thumb.png")

def cleanup_thumbnails(base_dir, thumbnail_dir):
    """
    Remove thumbnails of folders that are no longer present in the gallery.

    Parameters:
    - base_dir (str): Path to the base gallery directory.
    - thumbnail_dir (str): Path to the directory containing thumbnails.

    Returns:
    - None
    """
    try:
        # Ensure the thumbnail directory exists
        if not os.path.exists(thumbnail_dir):
            print(f"Thumbnail directory {thumbnail_dir} does not exist.")
            return

        # Traverse the thumbnail directory
        for root, dirs, files in os.walk(thumbnail_dir, topdown=False):
            # Check for corresponding folders in the base directory
            for folder in dirs:
                original_folder_path = os.path.join(base_dir,
                                                    os.path.relpath(os.path.join(root, folder), thumbnail_dir))
                thumbnail_folder_path = os.path.join(root, folder)

                # If the original folder does not exist, remove its thumbnail folder
                if not os.path.exists(original_folder_path):
                    print(f"Removing unused thumbnail folder: {thumbnail_folder_path}")
                    os.rmdir(thumbnail_folder_path)  # Remove empty folder

            # Delete unused thumbnail files
            for file in files:
                thumbnail_file_path = os.path.join(root, file)
                original_file_path = os.path.join(base_dir, os.path.relpath(thumbnail_file_path, thumbnail_dir))

                if not os.path.exists(os.path.dirname(original_file_path)):
                    print(f"Removing unused thumbnail file: {thumbnail_file_path}")
                    os.remove(thumbnail_file_path)

    except Exception as e:
        print(f"Error during thumbnail cleanup: {e}")

def count_images_in_directory(folder_path):
    """
    Count how many photos (images) are contained within a directory.

    Parameters:
    - folder_path (str): Path to the directory to scan.

    Returns:
    - int: Number of image files in the directory.
    """
    try:
        # Ensure the folder exists
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist.")
            return 0

        # List all files in the folder
        files = os.listdir(folder_path)

        # Filter out files to count only images
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        images = [
            file for file in files
            if os.path.splitext(file)[1].lower() in image_extensions
        ]

        # Return the count of images
        return len(images)

    except Exception as e:
        print(f"Error counting images in directory {folder_path}: {e}")
        return 0

def get_folder_content(current_path):
    """Get folder and file content dynamically, verifying that all directories/files actually exist."""
    print(f"Scanning: {current_path}")
    content = {"folders": [], "files": []}

    if os.path.exists(current_path):
        for entry in sorted(os.listdir(current_path)):
            entry_path = os.path.join(current_path, entry)

            # Process folders
            if os.path.isdir(entry_path):
                preview = get_random_preview(entry_path)
                content["folders"].append({
                    "name": entry,
                    "preview": preview
                })

            # Process files
            elif os.path.isfile(entry_path):
                ext = os.path.splitext(entry)[1].lower()

                # For images
                if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                    # Generate the thumbnail path and normalize it for URLs
                    thumbnail_path = recreate_folder_structure(entry_path, BASE_DIR, THUMBNAIL_DIR)
                    thumbnail_path = os.path.splitext(thumbnail_path)[0] + ".jpg"

                    if not os.path.exists(thumbnail_path):
                        generate_thumbnail(entry_path, thumbnail_path)

                    # Use the relative path for URL generation, ensuring forward slashes
                    content["files"].append({
                        "type": "image",
                        "name": entry,
                        "path": url_for("gallery_file",
                                        filepath=os.path.relpath(entry_path, BASE_DIR).replace("\\", "/")),
                        "thumbnail": f"/static/{os.path.relpath(thumbnail_path, 'static').replace('\\', '/')}"
                    })

                # For videos
                elif ext in [".mp4", ".avi", ".mov"]:
                    # Generate the thumbnail path and normalize it for URLs
                    thumbnail_path = recreate_folder_structure(entry_path, BASE_DIR, THUMBNAIL_DIR)
                    thumbnail_path = os.path.splitext(thumbnail_path)[0] + ".jpg"

                    if not os.path.exists(thumbnail_path):
                        generate_video_thumbnail(entry_path, thumbnail_path)

                    # Use the relative path for URL generation, ensuring forward slashes
                    content["files"].append({
                        "type": "video",
                        "name": entry,
                        "path": url_for("gallery_file",
                                        filepath=os.path.relpath(entry_path, BASE_DIR).replace("\\", "/")),
                        "thumbnail": f"/static/{os.path.relpath(thumbnail_path, 'static').replace('\\', '/')}"
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


# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000, debug=False)

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)