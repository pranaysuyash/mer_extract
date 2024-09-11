import os
import logging
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from utils.file_processor import process_file, reprocess_with_schema, chunk_and_process
import pandas as pd

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024  # 30MB max file size

logging.basicConfig(level=logging.ERROR)

# Ensure necessary folders exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists('outputs'):
    os.makedirs('outputs')


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # Save the uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Check the file size and process accordingly
        file_size = os.path.getsize(file_path)
        if file_size > 30 * 1024 * 1024:  # 30MB limit
            raise Exception("File size exceeds 30MB limit")

        if file_size > 5 * 1024 * 1024:  # Chunk files larger than 5MB
            html_filename, extracted_text = chunk_and_process(file_path)
        else:
            html_filename, extracted_text = process_file(file_path)

        return jsonify({
            'success': True, 
            'filename': os.path.basename(html_filename),
            'extracted_text': extracted_text
        }), 200

    except Exception as e:
        logging.error(f"Error processing file: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    # Search for the file in the outputs folder
    for root, dirs, files in os.walk('outputs'):
        if filename in files:
            return send_file(os.path.join(root, filename), as_attachment=True)
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/reprocess', methods=['POST'])
def reprocess_file():
    data = request.json
    filename = data.get('filename')
    schema = data.get('schema')

    if not filename:
        return jsonify({'error': 'Missing filename'}), 400

    if data.get('use_schema') and not schema:
        return jsonify({'error': 'Schema selected but not provided'}), 400

    try:
        csv_filename = reprocess_with_schema(filename, schema)
        return jsonify({'success': True, 'filename': os.path.basename(csv_filename)}), 200

    except Exception as e:
        logging.error(f"Error reprocessing file: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5500, debug=True)