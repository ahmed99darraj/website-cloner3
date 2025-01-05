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
            logger.error("No URL provided")
            return jsonify({
                'status': 'error',
                'message': 'الرجاء إدخال رابط الموقع'
            })

        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        logger.info(f"Attempting to clone URL: {url}")

        try:
            session = requests.Session()
            response = session.get(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                },
                verify=False,
                timeout=15
            )
            
            response.raise_for_status()
            logger.info(f"Successfully fetched URL. Status code: {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch URL: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'فشل في الوصول إلى الموقع: {str(e)}'
            })

        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            logger.info("Successfully parsed HTML")
            
            # تحويل الروابط النسبية إلى مطلقة
            base_url = response.url
            for tag in soup.find_all(['a', 'link', 'script', 'img']):
                for attr in ['href', 'src']:
                    if tag.get(attr):
                        try:
                            abs_url = urllib.parse.urljoin(base_url, tag[attr])
                            tag[attr] = abs_url
                        except Exception as e:
                            logger.warning(f"Failed to convert URL {tag.get(attr)}: {str(e)}")

            # إضافة base tag
            base_tag = soup.new_tag('base')
            base_tag['href'] = base_url
            base_tag['target'] = '_blank'
            if soup.head:
                soup.head.insert(0, base_tag)

            logger.info("Successfully processed HTML")
            
            return jsonify({
                'status': 'success',
                'html': str(soup)
            })
            
        except Exception as e:
            logger.error(f"Failed to process HTML: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                'status': 'error',
                'message': 'فشل في معالجة محتوى الصفحة'
            })

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': 'حدث خطأ غير متوقع'
        })

@app.route('/save', methods=['POST'])
def save_website():
    try:
        modified_html = request.form.get('html')
        if not modified_html:
            return jsonify({
                'status': 'error',
                'message': 'لم يتم العثور على محتوى HTML'
            })

        # إنشاء ملف مؤقت في الذاكرة
        memory_file = io.BytesIO()
        
        # إنشاء الملف المضغوط في الذاكرة
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # تحليل HTML
            soup = BeautifulSoup(modified_html, 'html.parser')
            
            # معالجة الصور وتحديث المسارات
            for img in soup.find_all('img'):
                src = img.get('src', '')
                if src.startswith('data:image'):
                    # معالجة الصور base64
                    try:
                        header, data = src.split(',', 1)
                        img_format = header.split(';')[0].split('/')[1]
                        img_data = base64.b64decode(data)
                        img_filename = f"images/image_{hash(src)}.{img_format}"
                        zf.writestr(img_filename, img_data)
                        img['src'] = img_filename
                    except Exception as e:
                        logger.error(f"Failed to process base64 image: {str(e)}")
                        continue
                
                elif src.startswith(('http://', 'https://')):
                    # تحميل الصور الخارجية
                    try:
                        response = requests.get(src, verify=False, timeout=5)
                        if response.ok:
                            img_filename = f"images/image_{hash(src)}{os.path.splitext(src)[1] or '.jpg'}"
                            zf.writestr(img_filename, response.content)
                            img['src'] = img_filename
                    except Exception as e:
                        logger.error(f"Failed to download external image: {str(e)}")
                        continue
                
                elif src.startswith('/uploads/'):
                    # نسخ الصور المحلية
                    try:
                        filename = os.path.basename(src)
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        if os.path.exists(filepath):
                            img_filename = f"images/{filename}"
                            with open(filepath, 'rb') as f:
                                zf.writestr(img_filename, f.read())
                            img['src'] = img_filename
                    except Exception as e:
                        logger.error(f"Failed to copy local image: {str(e)}")
                        continue

            # حفظ HTML المحدث
            zf.writestr('index.html', str(soup))

        # تحضير الملف للتحميل
        memory_file.seek(0)
        
        response = send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='website.zip'
        )
        
        # إضافة headers لمنع التخزين المؤقت
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response

    except Exception as e:
        logger.error(f"Save error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'فشل في حفظ الموقع: {str(e)}'
        })

if __name__ == '__main__':
    # التأكد من أن المجلد templates موجود
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # طباعة رسالة بدء التشغيل
    logger.info("Starting server on http://localhost:5000")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
