from flask import Flask, render_template, request, jsonify, send_file, url_for, send_from_directory
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
import datetime
import socket

# تعطيل تحذيرات SSL
urllib3.disable_warnings(InsecureRequestWarning)

# إعداد التسجيل
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# إعداد مجلد التحميلات
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test', methods=['GET'])
def test_connection():
    return jsonify({'status': 'success', 'message': 'Server is running'})

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'لم يتم العثور على ملف'
            })
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'لم يتم اختيار ملف'
            })

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # إضافة timestamp للاسم لتجنب تكرار الأسماء
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{int(time.time())}{ext}"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # إرجاع مسار URL للملف المرفوع
            file_url = url_for('uploaded_file', filename=filename, _external=True)
            
            return jsonify({
                'status': 'success',
                'url': file_url
            })
            
        return jsonify({
            'status': 'error',
            'message': 'نوع الملف غير مسموح به'
        })
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'فشل في رفع الملف'
        })

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/clone', methods=['POST'])
def clone_website():
    try:
        url = request.form.get('url')
        if not url:
            return jsonify({
                'status': 'error',
                'message': 'الرجاء إدخال رابط الموقع'
            })

        # تنظيف وتحقق من الرابط
        url = url.strip()
        if not url:
            return jsonify({
                'status': 'error',
                'message': 'الرابط فارغ'
            })

        # إضافة البروتوكول إذا لم يكن موجوداً
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        logger.info(f"Attempting to clone URL: {url}")

        # التحقق من صحة تنسيق URL
        try:
            parsed_url = urllib.parse.urlparse(url)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                return jsonify({
                    'status': 'error',
                    'message': 'الرابط غير صالح'
                })
        except Exception as e:
            logger.error(f"URL parsing error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'خطأ في تنسيق الرابط'
            })

        # إعداد جلسة مع إعدادات محسنة
        session = requests.Session()
        session.verify = False
        session.timeout = 30
        
        # إعداد headers محسنة
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ar,en;q=0.9,en-US;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Connection': 'keep-alive',
            'DNT': '1'
        }

        try:
            # محاولة الاتصال مع التحقق من DNS
            parsed_url = urllib.parse.urlparse(url)
            try:
                socket.gethostbyname(parsed_url.netloc)
            except socket.gaierror:
                return jsonify({
                    'status': 'error',
                    'message': 'لا يمكن الوصول إلى النطاق. تأكد من صحة الرابط أو جرب لاحقاً'
                })

            response = session.get(url, headers=headers, allow_redirects=True)
            response.raise_for_status()

            # التحقق من نوع المحتوى
            content_type = response.headers.get('Content-Type', '').lower()
            if not any(t in content_type for t in ['text/html', 'application/xhtml+xml']):
                return jsonify({
                    'status': 'error',
                    'message': 'هذا الرابط لا يحتوي على صفحة HTML'
                })

            # تحليل HTML مع معالجة الترميز
            html_content = response.content
            if 'charset' in content_type:
                charset = content_type.split('charset=')[-1].strip()
                try:
                    html_content = html_content.decode(charset)
                except:
                    html_content = html_content.decode('utf-8', errors='ignore')
            else:
                html_content = html_content.decode('utf-8', errors='ignore')

            soup = BeautifulSoup(html_content, 'html.parser')

            # التأكد من وجود head و body
            if not soup.head:
                head = soup.new_tag('head')
                if soup.html:
                    soup.html.insert(0, head)
                else:
                    html = soup.new_tag('html')
                    html.append(head)
                    soup.append(html)

            if not soup.body:
                body = soup.new_tag('body')
                if soup.html:
                    soup.html.append(body)
                else:
                    html = soup.new_tag('html')
                    html.append(soup.head)
                    html.append(body)
                    soup = BeautifulSoup(str(html), 'html.parser')

            # إضافة meta tags ضرورية
            meta_tags = [
                {'charset': 'UTF-8'},
                {'name': 'viewport', 'content': 'width=device-width, initial-scale=1'},
                {'http-equiv': 'Content-Security-Policy', 'content': "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; img-src * data: blob:; font-src * data:; style-src * 'unsafe-inline';"}
            ]

            for meta_info in meta_tags:
                meta_tag = soup.new_tag('meta')
                for attr, value in meta_info.items():
                    meta_tag[attr] = value
                soup.head.insert(0, meta_tag)

            # معالجة العناصر غير المرغوب فيها
            for tag in soup.find_all(['iframe', 'frame', 'noscript']):
                tag.decompose()

            # معالجة السكربتات
            scripts_content = []
            for script in soup.find_all('script'):
                if script.get('src'):
                    try:
                        script_url = script['src']
                        if not script_url.startswith(('http://', 'https://')):
                            if script_url.startswith('//'):
                                script_url = 'https:' + script_url
                            else:
                                script_url = urllib.parse.urljoin(url, script_url)
                        
                        script_response = session.get(script_url, headers=headers, timeout=5, verify=False)
                        if script_response.status_code == 200:
                            script_tag = soup.new_tag('script')
                            script_tag.string = script_response.text
                            scripts_content.append(script_tag)
                    except Exception as e:
                        logger.error(f"Error loading script {script_url}: {str(e)}")
                        continue
                elif script.string:
                    scripts_content.append(script)

            # معالجة الصور
            for img in soup.find_all('img'):
                if img.get('src'):
                    try:
                        img_url = img['src']
                        if img_url.startswith('data:'):
                            continue
                            
                        if not img_url.startswith(('http://', 'https://')):
                            if img_url.startswith('//'):
                                img_url = 'https:' + img_url
                            else:
                                img_url = urllib.parse.urljoin(url, img_url)
                                
                        img_response = session.get(img_url, headers=headers, timeout=5, verify=False)
                        if img_response.status_code == 200:
                            img_data = base64.b64encode(img_response.content).decode('utf-8')
                            img['src'] = f"data:image/{img_response.headers.get('content-type', 'image/jpeg').split('/')[-1]};base64,{img_data}"
                    except Exception as e:
                        logger.error(f"Error loading image {img_url}: {str(e)}")
                        continue

            # إضافة CSS للتحرير
            edit_style = soup.new_tag('style')
            edit_style.string = '''
                [contenteditable="true"] {
                    outline: 2px dashed #007bff;
                    min-height: 20px;
                    padding: 5px;
                    margin: 2px;
                }
                [contenteditable="true"]:hover {
                    outline: 2px solid #0056b3;
                }
                [contenteditable="true"]:focus {
                    outline: 2px solid #004085;
                    box-shadow: 0 0 5px rgba(0,123,255,0.5);
                }
                .edit-toolbar {
                    position: sticky;
                    top: 0;
                    z-index: 1000;
                    background: rgba(255,255,255,0.95);
                    padding: 10px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
            '''
            soup.head.append(edit_style)

            # إضافة السكربتات في نهاية الصفحة
            for script in scripts_content:
                soup.body.append(script)

            return jsonify({
                'status': 'success',
                'html': str(soup)
            })

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'فشل في الاتصال بالموقع. {str(e)}'
            })

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'حدث خطأ غير متوقع: {str(e)}'
        })

@app.route('/save', methods=['POST'])
def save_website():
    try:
        html_content = request.form.get('html')
        if not html_content:
            return jsonify({
                'status': 'error',
                'message': 'لم يتم توفير محتوى HTML'
            })

        # إنشاء مجلد للمواقع المحفوظة
        save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_sites')
        templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

        for directory in [save_dir, templates_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

        # إنشاء اسم الملف
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f'website_{timestamp}.zip'
        zip_path = os.path.join(save_dir, zip_filename)

        # إنشاء ملف ZIP مباشرة
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # حفظ ملف HTML
            zipf.writestr('index.html', html_content)

        # إرجاع مسار الملف للتحميل
        download_url = url_for('download_file', filename=zip_filename, _external=True)
        return jsonify({
            'status': 'success',
            'message': 'تم حفظ الموقع بنجاح',
            'download_url': download_url
        })

    except Exception as e:
        logger.error(f"Save error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': 'فشل في حفظ الموقع'
        })

@app.route('/download/<filename>')
def download_file(filename):
    try:
        # التحقق من صحة اسم الملف
        if '..' in filename or '/' in filename:
            return 'Invalid filename', 400

        # التأكد من أن الملف موجود
        save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_sites')
        file_path = os.path.join(save_dir, filename)
        
        if not os.path.isfile(file_path):
            return 'File not found', 404

        # إرسال الملف
        response = send_file(
            file_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
        
        # إضافة headers لمنع التخزين المؤقت
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        return response

    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return 'Error downloading file', 500

@app.route('/view/<timestamp>')
def view_site(timestamp):
    try:
        if not timestamp or '..' in timestamp:
            return jsonify({
                'status': 'error',
                'message': 'معرف الموقع غير صالح'
            })

        site_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_sites', f'site_{timestamp}')
        index_path = os.path.join(site_dir, 'index.html')
        
        if not os.path.exists(site_dir) or not os.path.exists(index_path):
            return jsonify({
                'status': 'error',
                'message': 'الموقع غير موجود'
            })
            
        try:
            return send_from_directory(site_dir, 'index.html', mimetype='text/html')
        except Exception as e:
            logger.error(f"Error sending file: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'فشل في عرض الموقع'
            })
            
    except Exception as e:
        logger.error(f"View error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'حدث خطأ أثناء عرض الموقع'
        })

if __name__ == '__main__':
    # التأكد من أن المجلدات المطلوبة موجودة
    save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_sites')
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

    for directory in [save_dir, templates_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)

    # طباعة رسالة بدء التشغيل
    logger.info("Starting server on http://localhost:5000")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
