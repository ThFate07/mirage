from flask import Flask, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
import subprocess
import cv2
import numpy as np
import logging

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

def blurrscale(idletime, idlecriteria):
    if idletime >= idlecriteria and idletime <= (2**1) * idlecriteria: return 0.8
    elif idletime >= (2**1) * idlecriteria and idletime <= (2**2) * idlecriteria: return 0.6
    elif idletime >= (2**2) * idlecriteria and idletime <= (2**3) * idlecriteria: return 0.5
    elif idletime >= (2**3) * idlecriteria and idletime <= (2**4) * idlecriteria: return 0.4
    elif idletime >= (2**4) * idlecriteria and idletime <= (2**5) * idlecriteria: return 0.2
    elif idletime >= (2**5) * idlecriteria: return 0.1

def lower_resolution(img, scale_factor):
    original_height, original_width = img.shape[:2]
    new_width = int(original_width * scale_factor)
    new_height = int(original_height * scale_factor)
    resized_img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    final_img = cv2.resize(resized_img, (original_width, original_height), interpolation=cv2.INTER_LINEAR)
    return final_img

def process_video(input_path, output_path):
    audio_file = 'audio.wav'
    command = f"ffmpeg -i {input_path} -ab 160k -ac 2 -ar 44100 -vn {audio_file}"
    subprocess.run(command, shell=True)

    cap = cv2.VideoCapture(input_path)
    original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    blurrCriteria = 5
    idleTime = 0
    isIdle = False

    # Choose a lower resolution for output
    lower_width = original_width // 2  # Reduce width by half
    lower_height = original_height // 2  # Reduce height by half
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_path, fourcc, fps, (lower_width, lower_height))

    ret, frame1 = cap.read()
    ret, frame2 = cap.read()

    while True:
        if not ret: break
        diff = cv2.absdiff(frame1, frame2)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=3)
        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        isAnyIdle = True
        for contour in contours:
            (x, y, w, h) = cv2.boundingRect(contour)

            if cv2.contourArea(contour) < 900:
                isIdle = True
                continue

            idleTime = 0
            isAnyIdle = False

        if not diff.any() or (isIdle and isAnyIdle):
            idleTime += 1

            if idleTime >= blurrCriteria:
                scale_factor = blurrscale(idleTime, blurrCriteria)
                frame1 = lower_resolution(frame1, scale_factor)
                frame1 = cv2.resize(frame1, (lower_width, lower_height))

        # Ensure the frame is resized before writing
        frame1_resized = cv2.resize(frame1, (lower_width, lower_height))
        out.write(frame1_resized)

        frame1 = frame2
        ret, frame2 = cap.read()

    cap.release()
    out.release()

    output_video = 'output_with_audio.avi'
    command = f"ffmpeg -i {output_path} -i {audio_file} -c:v libx264 -crf 23 -preset fast -c:a aac -b:a 160k {output_video}"
    subprocess.run(command, shell=True)


@app.route('/api/upload', methods=['POST'])
def upload_file():
    app.logger.info("Upload request received")

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
        processed_filename = f"processed_{filename}"
        processed_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
        process_video(file_path, processed_path)
        app.logger.info(f"Processed file saved at: {processed_path}")

        return jsonify({
            'message': 'File uploaded and processed successfully',
            'original_filename': filename,
            'processed_filename': processed_filename
        }), 200

    app.logger.error("File type not allowed")
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/api/video/<filename>')
def serve_video(filename):
    app.logger.info(f"Request to serve video: {filename}")
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if os.path.exists(file_path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, mimetype='video/mp4')
    else:
        return jsonify({'error': f"File not found: {filename}"}), 404

@app.route('/api/processed/<filename>')
def serve_processed_video(filename):
    app.logger.info(f"Request to serve processed video: {filename}")
    file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)

    if os.path.exists(file_path):
        return send_from_directory(app.config['PROCESSED_FOLDER'], filename, mimetype='video/mp4')
    else:
        return jsonify({'error': f"Processed file not found: {filename}"}), 404

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(PROCESSED_FOLDER, exist_ok=True)
    app.run(port=5328, debug=True)
