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

        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        logger.info(f"Attempting to clone URL: {url}")

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
                        script_url = urllib.parse.urljoin(url, script['src'])
                        script_response = session.get(script_url, headers=headers, timeout=5)
                        if script_response.status_code == 200:
                            script_tag = soup.new_tag('script')
                            script_tag.string = script_response.text
                            scripts_content.append(script_tag)
                    except:
                        continue
                elif script.string:
                    scripts_content.append(script)

            # إزالة السكربتات القديمة
            for script in soup.find_all('script'):
                script.decompose()

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

        # إنشاء مجلد للمواقع المحفوظة إذا لم يكن موجوداً
        save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_sites')
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # إنشاء اسم مجلد فريد للموقع
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        site_dir = os.path.join(save_dir, f'site_{timestamp}')
        os.makedirs(site_dir)

        # تحليل HTML لاستخراج الموارد
        soup = BeautifulSoup(html_content, 'html.parser')

        # إنشاء مجلدات للموارد
        assets_dir = os.path.join(site_dir, 'assets')
        css_dir = os.path.join(assets_dir, 'css')
        js_dir = os.path.join(assets_dir, 'js')
        images_dir = os.path.join(assets_dir, 'images')
        fonts_dir = os.path.join(assets_dir, 'fonts')

        for directory in [assets_dir, css_dir, js_dir, images_dir, fonts_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

        # معالجة الصور
        for img in soup.find_all('img'):
            if img.get('src', '').startswith('data:'):
                try:
                    # استخراج نوع الصورة والبيانات
                    img_data = img['src'].split(';base64,')
                    if len(img_data) == 2:
                        img_type = img_data[0].split('/')[-1].split(';')[0]
                        img_content = base64.b64decode(img_data[1])
                        
                        # حفظ الصورة
                        img_filename = f'image_{uuid.uuid4().hex[:8]}.{img_type}'
                        img_path = os.path.join(images_dir, img_filename)
                        with open(img_path, 'wb') as f:
                            f.write(img_content)
                        
                        # تحديث مسار الصورة
                        img['src'] = f'assets/images/{img_filename}'
                except Exception as e:
                    logger.warning(f"Failed to save image: {str(e)}")

        # معالجة CSS
        for style in soup.find_all('style'):
            if style.string:
                try:
                    # حفظ CSS في ملف منفصل
                    css_filename = f'style_{uuid.uuid4().hex[:8]}.css'
                    css_path = os.path.join(css_dir, css_filename)
                    with open(css_path, 'w', encoding='utf-8') as f:
                        f.write(style.string)
                    
                    # إنشاء رابط للملف CSS
                    link_tag = soup.new_tag('link')
                    link_tag['rel'] = 'stylesheet'
                    link_tag['href'] = f'assets/css/{css_filename}'
                    style.replace_with(link_tag)
                except Exception as e:
                    logger.warning(f"Failed to save CSS: {str(e)}")

        # معالجة JavaScript
        for script in soup.find_all('script'):
            if script.string:
                try:
                    # حفظ JavaScript في ملف منفصل
                    js_filename = f'script_{uuid.uuid4().hex[:8]}.js'
                    js_path = os.path.join(js_dir, js_filename)
                    with open(js_path, 'w', encoding='utf-8') as f:
                        f.write(script.string)
                    
                    # تحديث مسار السكربت
                    script['src'] = f'assets/js/{js_filename}'
                    script.string = ''
                except Exception as e:
                    logger.warning(f"Failed to save JavaScript: {str(e)}")

        # حفظ ملف HTML الرئيسي
        index_path = os.path.join(site_dir, 'index.html')
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))

        # إنشاء ملف ZIP
        zip_filename = f'website_{timestamp}.zip'
        zip_path = os.path.join(save_dir, zip_filename)
        
        def zipdir(path, ziph):
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, path)
                    ziph.write(file_path, arcname)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipdir(site_dir, zipf)

        # إنشاء ملف للنشر السريع
        deploy_html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>تم النشر بنجاح</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 20px;
                    direction: rtl;
                }}
                .success-message {{
                    color: #28a745;
                    font-size: 24px;
                    margin: 20px 0;
                }}
                .link-container {{
                    margin: 20px 0;
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 5px;
                }}
                .download-link {{
                    display: inline-block;
                    padding: 10px 20px;
                    background: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 10px;
                }}
                .download-link:hover {{
                    background: #0056b3;
                }}
            </style>
        </head>
        <body>
            <div class="success-message">تم حفظ الموقع بنجاح!</div>
            <div class="link-container">
                <p>يمكنك الآن:</p>
                <a href="/download/{zip_filename}" class="download-link">تحميل الموقع كملف ZIP</a>
                <a href="/view/{timestamp}" class="download-link">عرض الموقع مباشرة</a>
            </div>
            <p>تم حفظ الموقع في: {site_dir}</p>
        </body>
        </html>
        '''

        deploy_path = os.path.join(site_dir, 'deploy.html')
        with open(deploy_path, 'w', encoding='utf-8') as f:
            f.write(deploy_html)

        return jsonify({
            'status': 'success',
            'message': 'تم حفظ الموقع بنجاح',
            'zip_file': zip_filename,
            'site_dir': site_dir,
            'timestamp': timestamp
        })

    except Exception as e:
        logger.error(f"Error saving website: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'حدث خطأ أثناء حفظ الموقع: {str(e)}'
        })

@app.route('/download/<filename>')
def download_file(filename):
    try:
        save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_sites')
        return send_from_directory(save_dir, filename, as_attachment=True)
    except Exception as e:
        return f'خطأ في تحميل الملف: {str(e)}'

@app.route('/view/<timestamp>')
def view_site(timestamp):
    try:
        site_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_sites', f'site_{timestamp}')
        return send_from_directory(site_dir, 'index.html')
    except Exception as e:
        return f'خطأ في عرض الموقع: {str(e)}'

if __name__ == '__main__':
    # التأكد من أن المجلد templates موجود
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # طباعة رسالة بدء التشغيل
    logger.info("Starting server on http://localhost:5000")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
