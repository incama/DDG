# DDG (Directory Driven Gallery)

DDG, or Directory Driven Gallery, is a dynamic web application designed to create a visual gallery structure powered by the file system. It automatically generates image and video thumbnails, showcases folder layouts, and enables efficient navigation within a gallery-like interface by leveraging the directory structure.

![DDG](/screenshots/screenshot-01.png?raw=true "DDG")

---

## Features

- **Dynamic Gallery System**: Automatically generates galleries based on the directory structure (nested folders supported).
- **Image and Video Support**:
  - Creates thumbnails for images while maintaining aspect ratios with padding.
  - Generates thumbnails for video files using FFmpeg.
- **Folder Previews**: Displays a random image from a folder as the folder's preview thumbnail.
- **Favicon Support**: Adds a small icon for your app in browser tabs.
- **Thumbnail Management**: Cleans up unused thumbnails to save disk space.
- **Cross-Browser Compatibility**: Works across all modern web browsers.
- **Lightweight and Reliable**: Powered by Flask and served using Waitress.

---

## Requirements

- **Python**: 3.12 or above
- **Installed Python Packages**:
  - [`Flask`](https://flask.palletsprojects.com/)
  - [`Pillow`](https://python-pillow.org/)
  - [`waitress`](https://github.com/Pylons/waitress)
- **System Dependency**:
  - [FFmpeg](https://ffmpeg.org/) (for video thumbnail generation)

---

## Installation

### 1. Clone this repository
```bash
git clone https://github.com/incama/DDG.git
cd DDG
```

### 2. Install Python Dependencies
Ensure Python is installed on your system. Next, install the required Python packages using the `requirements.txt` file:
```bash
pip install -r requirements.txt
```

### 3. Install FFmpeg
If your system doesn’t already have FFmpeg:
- On **Ubuntu/Debian**:
  ```bash
  sudo apt update
  sudo apt install ffmpeg
  ```
- On **MacOS** (via Homebrew):
  ```bash
  brew install ffmpeg
  ```
- On **Windows**: [Download FFmpeg](https://ffmpeg.org/download.html) and add it to the system `PATH`.

---

## Usage

### 1. Prepare Your Gallery
- Create a folder named `gallery` in the root of the project.
- Populate the `gallery` folder with subdirectories, images (`.jpg`, `.jpeg`, `.png`, etc.), and videos (`.mp4`, `.avi`, `.mov`, etc.).
- When adding new images you don't have to restart the app, just refresh your browser, DDG will take care of everthing!

Folder structure example:
````
gallery/
├───animals
│   ├───african
│   ├───cats
│   │   └───kittens
│   │   └───lions
│   ├───dogs
│   └───horses
├───buildings
└───cars
````

### 2. Run the Application
Run the Flask application using `waitress`:
```bash
python app.py
```

The app will start on `http://0.0.0.0:8080`. Open the URL in your browser to access your gallery.

### 3. Access the Admin Functionality
You can clean up unused thumbnail files with the following POST request to:
`http://<your-server-url>:8080/cleanup-thumbnails`

---

## Configuration

### Custom Thumbnail and Gallery Settings
Update the following variables in `app.py` according to your needs:
- `BASE_DIR`: Path to the gallery directory (default is `gallery`).
- `THUMBNAIL_DIR`: Path to the generated thumbnails (default is `static/thumbnails`).
- Thumbnail size, padding, and quality settings can be adjusted in the corresponding functions.

---

## Deployment

To deploy the app on a production server:
1. Use **Waitress** as the WSGI server (already included in the app).
2. Serve behind a reverse proxy such as **Nginx** or **Apache**.
3. Ensure all static files and dependencies are configured on the server.

---

## Roadmap

Future features planned for DDG include:
- Pagination for large directories.
- Replace Lightbox2 with something futureproof.
- ~~User authentication for private galleries/sharing~~. (not any time soon!)
- Drag-and-drop file uploads via web UI.
- Custom themes for enhanced visual design.
- Face and object recognition. (In a galaxy far, far away!)

---

## License

This project is licensed under the GPLv2 License. See the `LICENSE` file for details.

---

## Acknowledgements

- [Flask](https://flask.palletsprojects.com/): Lightweight Python web framework.
- [Pillow](https://python-pillow.org/): Image processing library used for generating thumbnails.
- [Waitress](https://github.com/Pylons/waitress): Production-ready web server.
- [FFmpeg](https://ffmpeg.org/): Tool for video processing.

Enjoy using **DDG** to manage and showcase your gallery dynamically!