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

        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        logger.info(f"Attempting to clone URL: {url}")

        try:
            parsed_url = urllib.parse.urlparse(url)
            domain = parsed_url.netloc
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # إعداد جلسة مع إعدادات محسنة
            session = requests.Session()
            session.verify = False
            session.timeout = 30

            # إعداد headers محسنة لتقليد متصفح حديث
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'ar,en;q=0.9,en-US;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'Connection': 'keep-alive',
                'Host': domain
            }

            # محاولة الوصول للموقع
            try:
                response = session.get(url, headers=headers, allow_redirects=True)
                response.raise_for_status()
            except requests.exceptions.SSLError:
                # محاولة مع تعطيل التحقق من SSL
                session.verify = False
                response = session.get(url, headers=headers, allow_redirects=True)
                response.raise_for_status()

            # التحقق من نوع المحتوى
            content_type = response.headers.get('Content-Type', '').lower()
            if not any(t in content_type for t in ['text/html', 'application/xhtml+xml']):
                return jsonify({
                    'status': 'error',
                    'message': 'هذا الرابط لا يحتوي على صفحة HTML. الرجاء استخدام رابط لصفحة ويب'
                })

            # تحليل HTML مع الحفاظ على التعليقات والهيكل الأصلي
            soup = BeautifulSoup(response.content, 'html.parser', from_encoding=response.encoding)

            # حذف العناصر غير المرغوب فيها مع الحفاظ على بعض السكربتات المهمة
            for tag in soup.find_all(['iframe', 'frame', 'noscript']):
                tag.decompose()

            # معالجة السكربتات
            scripts_content = []
            for script in soup.find_all('script'):
                if script.get('src'):
                    try:
                        script_url = urllib.parse.urljoin(url, script['src'])
                        script_response = session.get(script_url, headers=headers)
                        if script_response.status_code == 200:
                            script_tag = soup.new_tag('script')
                            script_tag.string = script_response.text
                            scripts_content.append(script_tag)
                    except:
                        continue
                elif script.string:
                    scripts_content.append(script)

            # إزالة جميع السكربتات القديمة
            for script in soup.find_all('script'):
                script.decompose()

            # تحويل الروابط النسبية إلى مطلقة في الـ CSS
            def convert_urls_in_css(css_text, base_url):
                # تحويل الروابط في الـ url()
                css_text = re.sub(
                    r'url\(["\']?(?!data:|http|https)([^)"\']+)["\']?\)',
                    lambda m: f'url("{urllib.parse.urljoin(base_url, m.group(1))}")',
                    css_text
                )
                # تحويل الروابط في الـ @import
                css_text = re.sub(
                    r'@import\s+["\'](?!data:|http|https)([^"\']+)["\']',
                    lambda m: f'@import "{urllib.parse.urljoin(base_url, m.group(1))}"',
                    css_text
                )
                return css_text

            # معالجة CSS المضمن
            for style in soup.find_all('style'):
                if style.string:
                    style.string = convert_urls_in_css(style.string, url)

            # معالجة روابط CSS الخارجية
            css_links = soup.find_all('link', rel='stylesheet')
            processed_css = []

            for link in css_links:
                try:
                    css_url = urllib.parse.urljoin(url, link.get('href', ''))
                    css_response = session.get(css_url, headers=headers)
                    if css_response.status_code == 200:
                        css_text = convert_urls_in_css(css_response.text, css_url)
                        processed_css.append(css_text)
                except Exception as e:
                    logger.warning(f"Failed to load CSS from {css_url}: {str(e)}")
                    continue

            # إضافة CSS المعالج
            if processed_css:
                style_tag = soup.new_tag('style')
                style_tag.string = '\n'.join(processed_css)
                soup.head.append(style_tag)

            # تحويل الصور مع معالجة خاصة للصور الكبيرة
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and not src.startswith('data:'):
                    try:
                        img_url = urllib.parse.urljoin(url, src)
                        img_response = session.get(img_url, headers=headers)
                        if img_response.status_code == 200:
                            img_type = img_response.headers.get('Content-Type', 'image/jpeg')
                            img_size = len(img_response.content)
                            
                            if img_size < 1024 * 1024:  # أقل من 1 ميجابايت
                                img_data = base64.b64encode(img_response.content).decode('utf-8')
                                img['src'] = f'data:{img_type};base64,{img_data}'
                            else:
                                img['src'] = img_url
                                img['loading'] = 'lazy'
                                img['crossorigin'] = 'anonymous'
                    except Exception as e:
                        logger.warning(f"Failed to convert image: {str(e)}")
                        if not src.startswith(('http://', 'https://')):
                            img['src'] = urllib.parse.urljoin(url, src)

            # تحويل الروابط النسبية إلى مطلقة
            for tag in soup.find_all(['a', 'link', 'img', 'form']):
                for attr in ['href', 'src', 'action']:
                    if tag.get(attr):
                        if not tag[attr].startswith(('http://', 'https://', 'data:', '#', 'mailto:', 'tel:', 'javascript:')):
                            tag[attr] = urllib.parse.urljoin(url, tag[attr])

            # إضافة السكربتات المعالجة في نهاية الصفحة
            for script in scripts_content:
                soup.body.append(script)

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

            return jsonify({
                'status': 'success',
                'html': str(soup)
            })

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'فشل في الاتصال بالموقع {url}. {str(e)}'
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
