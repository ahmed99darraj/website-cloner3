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

app = Flask(__name__,
    template_folder='templates',  # تحديد مجلد القوالب
    static_folder='assets'        # تحديد مجلد الملفات الثابتة
)

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
            return jsonify({
                'status': 'error',
                'error': 'الرجاء إدخال رابط الموقع'
            }), 400

        url = data['url']
        if not url.startswith(('http://', 'https://')):
            return jsonify({
                'status': 'error',
                'error': 'الرجاء إدخال رابط يبدأ بـ http:// أو https://'
            }), 400

        try:
            response = requests.get(url, verify=False, timeout=10)
            response.raise_for_status()
        except requests.exceptions.SSLError:
            return jsonify({
                'status': 'error',
                'error': 'حدث خطأ في شهادة SSL للموقع'
            }), 400
        except requests.exceptions.ConnectionError:
            return jsonify({
                'status': 'error',
                'error': 'لا يمكن الاتصال بالموقع. تأكد من صحة الرابط وأن الموقع متاح.'
            }), 400
        except requests.exceptions.Timeout:
            return jsonify({
                'status': 'error',
                'error': 'انتهت مهلة الاتصال بالموقع. حاول مرة أخرى.'
            }), 400
        except requests.exceptions.RequestException as e:
            return jsonify({
                'status': 'error',
                'error': f'حدث خطأ أثناء الاتصال بالموقع: {str(e)}'
            }), 400

        if 'text/html' not in response.headers.get('content-type', '').lower():
            return jsonify({
                'status': 'error',
                'error': 'عذراً، يمكن فقط استنساخ صفحات HTML'
            }), 400

        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')

        return jsonify({
            'status': 'success',
            'html': str(soup)
        })

    except Exception as e:
        app.logger.error(f'Error: {str(e)}\\n{traceback.format_exc()}')
        return jsonify({
            'status': 'error',
            'error': 'حدث خطأ غير متوقع. حاول مرة أخرى.'
        }), 500

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
