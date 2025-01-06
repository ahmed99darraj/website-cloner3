from flask import Flask, render_template, request, jsonify, send_file, url_for
import requests
from bs4 import BeautifulSoup
import os
import zipfile
import io
import urllib.parse
import logging
import traceback
from werkzeug.utils import secure_filename
from urllib3.exceptions import InsecureRequestWarning
import urllib3
import base64
import time
import re
import uuid

# تعطيل تحذيرات SSL
urllib3.disable_warnings(InsecureRequestWarning)

app = Flask(__name__)

# تكوين المجلدات
UPLOAD_FOLDER = '/tmp/uploads'
SAVED_SITES_FOLDER = '/tmp/saved_sites'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max-length

# التأكد من وجود المجلدات
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SAVED_SITES_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/clone', methods=['POST'])
def clone_website():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'No URL provided'}), 400

        url = data['url']
        
        # التحقق من صحة URL
        if not url.startswith(('http://', 'https://')):
            return jsonify({'error': 'Invalid URL format'}), 400

        # إضافة timeout للطلب
        response = requests.get(url, verify=False, timeout=8)
        
        # تحليل HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        return jsonify({
            'status': 'success',
            'html': str(soup)
        })

    except requests.Timeout:
        return jsonify({'error': 'Request timed out'}), 408
    except Exception as e:
        logging.error(f"Error cloning website: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/save', methods=['POST'])
def save_website():
    try:
        data = request.get_json()
        if not data or 'html' not in data:
            return jsonify({'error': 'No HTML content provided'}), 400

        if len(data['html']) > 5 * 1024 * 1024:  # 5MB limit
            return jsonify({'error': 'Content too large'}), 413

        # إنشاء اسم فريد للملف
        timestamp = str(int(time.time()))
        zip_filename = f'website_{timestamp}.zip'
        zip_path = os.path.join(SAVED_SITES_FOLDER, zip_filename)

        # إنشاء ملف ZIP
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr('index.html', data['html'])

        return jsonify({
            'status': 'success',
            'filename': zip_filename
        })

    except Exception as e:
        logging.error(f"Error saving website: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(
            os.path.join(SAVED_SITES_FOLDER, secure_filename(filename)),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logging.error(f"Error downloading file: {str(e)}")
        return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
