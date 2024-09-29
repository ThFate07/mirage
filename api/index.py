import os
import cv2
import numpy as np
import subprocess
import json
import logging
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
    """Returns the blur scale based on the idle time."""
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
    """Reduces the resolution of the image."""
    original_height, original_width = img.shape[:2]
    new_width = int(original_width * scale_factor)
    new_height = int(original_height * scale_factor)

    resized_img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    final_img = cv2.resize(resized_img, (original_width, original_height), interpolation=cv2.INTER_LINEAR)
    return final_img

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
    isIdle = False

    ret, frame1 = cap.read()
    ret, frame2 = cap.read()

    while True:
        frame_itr += 1
        if not ret:
            break

        # Calculate the difference between two frames
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

        # Write the frame to the output video
        out.write(frame1)

        # Read the next frame
        frame1 = frame2
        ret, frame2 = cap.read()

        # Update the processing percentage
        if (process_percent + 1 - 0.3) < (frame_itr / frame_count * 100) < (process_percent + 1):
            process_percent += 1
            app.logger.info(f"Processed: {process_percent:.2f}%")

    cap.release()
    out.release()
    app.logger.info(f"Video processing completed: {output_path}")
    return output_path

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
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, mimetype='video/mp4')

if __name__ == '__main__':
    app.run(port=5328, debug=True)
