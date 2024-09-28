import os
import cv2
import numpy as np
import subprocess
import json
import logging
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Use absolute paths
UPLOAD_FOLDER = os.path.abspath('uploads')
PROCESSED_FOLDER = os.path.abspath('processed')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

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
    if idletime >= idlecriteria and idletime <= (2**1) * idlecriteria:
        return 0.8
    elif idletime >= (2**1) * idlecriteria and idletime <= (2**2) * idlecriteria:
        return 0.6
    elif idletime >= (2**2) * idlecriteria and idletime <= (2**3) * idlecriteria:
        return 0.5
    elif idletime >= (2**3) * idlecriteria and idletime <= (2**4) * idlecriteria:
        return 0.4
    elif idletime >= (2**4) * idlecriteria and idletime <= (2**5) * idlecriteria:
        return 0.2
    elif idletime >= (2**5) * idlecriteria:
        return 0.1

def lower_resolution(img, scale_factor):
    original_height, original_width = img.shape[:2]
    new_width = int(original_width * scale_factor)
    new_height = int(original_height * scale_factor)
    resized_img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    final_img = cv2.resize(resized_img, (original_width, original_height), interpolation=cv2.INTER_LINEAR)
    return final_img

def extract_audio(input_video, audio_file):
    command = f"ffmpeg -i {input_video} -ab 160k -ac 2 -ar 44100 -vn {audio_file}"
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        app.logger.error(f"Error extracting audio: {e}")
        return False
    return True

def process_video(input_path, output_path):
    app.logger.info(f"Processing video: {input_path}")

    # Extract audio
    audio_file = os.path.join(app.config['PROCESSED_FOLDER'], 'temp_audio.wav')
    if not extract_audio(input_path, audio_file):
        return None

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        app.logger.error("Error opening video file")
        return None

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_path, fourcc, fps, (1280, 720))

    blurrCriteria = 10
    blurr = 0.5
    idleTime = 0

    ret, frame1 = cap.read()
    if not ret:
        app.logger.error("Error reading first frame")
        return None

    ret, frame2 = cap.read()
    if not ret:
        app.logger.error("Error reading second frame")
        return None

    try:
        while True:
            diff = cv2.absdiff(frame1, frame2)
            gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
            dilated = cv2.dilate(thresh, None, iterations=3)
            contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            isAnyIdle = True
            for contour in contours:
                if cv2.contourArea(contour) >= 900:
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

            image = cv2.resize(frame1, (1280, 720))
            out.write(image)

            frame1 = frame2
            ret, frame2 = cap.read()
            if not ret:
                break

    finally:
        cap.release()
        out.release()

    # Merge audio and video
    final_output = output_path.replace('.avi', '_with_audio.avi')
    if not add_audio_to_video(output_path, audio_file, final_output):
        return None

    # Clean up temporary files
    os.remove(output_path)
    os.remove(audio_file)

    app.logger.info(f"Video processing completed: {final_output}")
    return final_output

def add_audio_to_video(video_file, audio_file, output_file):
    command = f"ffmpeg -i {video_file} -i {audio_file} -c:v copy -c:a aac {output_file}"
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        app.logger.error(f"Error adding audio to video: {e}")
        return False
    return True

@app.route('/api/upload', methods=['POST'])
def upload_file():
    app.logger.info("Upload request received")

    # Ensure upload and processed directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

    if 'file' not in request.files:
        app.logger.error("No file part in the request")
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        app.logger.error("No selected file")
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        app.logger.info(f"File saved at: {file_path}")

        # Process the video
        processed_filename = f"processed_{filename.rsplit('.', 1)[0]}.avi"
        processed_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
        final_output = process_video(file_path, processed_path)

        if final_output is None:
            return jsonify({'error': 'Error processing video'}), 500

        # Get video info
        original_info = get_video_info(file_path)
        processed_info = get_video_info(final_output)

        return jsonify({
            'message': 'File uploaded and processed successfully',
            'original_filename': filename,
            'processed_filename': os.path.basename(final_output),
            'original_info': original_info,
            'processed_info': processed_info
        }), 200

    app.logger.error("File type not allowed")
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/api/video/<filename>')
def serve_video(filename):
    app.logger.info(f"Request to serve video: {filename}")
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, mimetype='video/mp4')

@app.route('/api/processed/<filename>')
def serve_processed_video(filename):
    app.logger.info(f"Request to serve processed video: {filename}")
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, mimetype='video/mp4')

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(PROCESSED_FOLDER, exist_ok=True)
    app.run(port=5328, debug=True)
