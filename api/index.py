import os
import cv2
import numpy as np
import subprocess
import json
import logging
import mimetypes
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Set up Flask application
app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests from frontend
logging.basicConfig(level=logging.DEBUG)

# Set up directories and allowed extensions
UPLOAD_FOLDER = os.path.abspath('uploads')
PROCESSED_FOLDER = os.path.abspath('processed')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# Ensure upload and processed directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

app.logger.info(f"Upload folder: {UPLOAD_FOLDER}")
app.logger.info(f"Processed folder: {PROCESSED_FOLDER}")

# Helper Functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_video_info(video_path):
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)

    video_stream = next((stream for stream in data['streams'] if stream['codec_type'] == 'video'), None)

    return {
        'codec': video_stream['codec_name'],
        'file_size': os.path.getsize(video_path),
        'resolution': f"{video_stream['width']}x{video_stream['height']}",
        'duration': float(data['format']['duration']),
        'bitrate': int(data['format']['bit_rate']),
        'framerate': eval(video_stream['r_frame_rate'])
    }

def blurrscale(idletime, idlecriteria):
    if idletime >= idlecriteria and idletime <= (2**1) * idlecriteria:
        return 0.8
    elif idletime > (2**1) * idlecriteria and idletime <= (2**2) * idlecriteria:
        return 0.6
    elif idletime > (2**2) * idlecriteria and idletime <= (2**3) * idlecriteria:
        return 0.4
    elif idletime > (2**3) * idlecriteria and idletime <= (2**4) * idlecriteria:
        return 0.2
    elif idletime > (2**4) * idlecriteria:
        return 0.1

def lower_resolution(img, scale_factor):
    original_height, original_width = img.shape[:2]
    new_width = int(original_width * scale_factor)
    new_height = int(original_height * scale_factor)
    resized_img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    final_img = cv2.resize(resized_img, (original_width, original_height), interpolation=cv2.INTER_LINEAR)
    return final_img

def convert_to_mp4(input_avi, output_mp4):
    command = f"ffmpeg -i {input_avi} -c:v libx264 -c:a aac {output_mp4} -y"
    try:
        subprocess.run(command, shell=True, check=True)
        app.logger.info(f"Converted {input_avi} to {output_mp4}")
    except subprocess.CalledProcessError as e:
        app.logger.error(f"Error converting to MP4: {e}")
        return None
    return output_mp4

def process_video(input_path, output_path):
    app.logger.info(f"Processing video: {input_path}")

    # Initialize video capture and writer
    cap = cv2.VideoCapture(input_path)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    file_ext = os.path.splitext(output_path)[1].lower()
    if file_ext == '.mp4':
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Use 'mp4v' codec for MP4
    else:
        fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Use 'XVID' for AVI by default

    out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

    # Initialize variables
    blurrCriteria = 10
    blurr = 0.5
    idleTime = 0
    frame_itr = 0
    process_percent = 0

    ret, frame1 = cap.read()
    ret, frame2 = cap.read()

    while True:
        frame_itr += 1
        if not ret:
            break

        diff = cv2.absdiff(frame1, frame2)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=3)
        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        isAnyIdle = True
        for contour in contours:
            if cv2.contourArea(contour) >= 1800:
                idleTime = 0
                isAnyIdle = False
                break

        if not diff.any() or isAnyIdle:
            idleTime += 1
            if idleTime >= blurrCriteria:
                blurr = blurrscale(idleTime, blurrCriteria)
                frame1 = lower_resolution(frame1, blurr)
                blurr = 0.5
                cv2.putText(frame1, "Status: Idle", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        out.write(frame1)
        frame1 = frame2
        ret, frame2 = cap.read()

    cap.release()
    out.release()

    # Convert the final AVI file to MP4
    mp4_output_path = output_path.replace(".avi", ".mp4")
    converted_mp4 = convert_to_mp4(output_path, mp4_output_path)
    return converted_mp4

@app.route('/api/upload', methods=['POST'])
def upload_file():
    app.logger.info("Upload request received")

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        app.logger.info(f"File saved at: {file_path}")

        processed_filename = f"processed_{filename.rsplit('.', 1)[0]}.avi"
        processed_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
        final_output = process_video(file_path, processed_path)

        if final_output is None:
            return jsonify({'error': 'Error processing video'}), 500

        original_info = get_video_info(file_path)
        processed_info = get_video_info(final_output)

        return jsonify({
            'message': 'File uploaded and processed successfully',
            'original_filename': filename,
            'processed_filename': os.path.basename(final_output),
            'original_info': original_info,
            'processed_info': processed_info
        }), 200

    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/api/processed/<filename>')
def serve_processed_video(filename):
    file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    if not os.path.isfile(file_path):
        return jsonify({'error': 'File not found'}), 404

    # Dynamically detect MIME type using mimetypes library
    mimetype = mimetypes.guess_type(file_path)[0]
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, mimetype=mimetype)

if __name__ == '__main__':
    app.run(port=5328, debug=True)
