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

        # التحقق من صحة URL
        try:
            parsed_url = urllib.parse.urlparse(url)
            domain = parsed_url.netloc
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # التحقق من DNS
            try:
                import socket
                socket.setdefaulttimeout(5)
                socket.gethostbyname(domain)
            except socket.gaierror:
                return jsonify({
                    'status': 'error',
                    'message': f'لا يمكن الوصول إلى الموقع {domain}. تأكد من صحة الرابط أو جرب لاحقاً'
                })
            except socket.timeout:
                return jsonify({
                    'status': 'error',
                    'message': 'انتهت مهلة الاتصال بالموقع. الرجاء المحاولة مرة أخرى'
                })

        except Exception as e:
            logger.error(f"URL parsing error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'الرابط غير صالح. الرجاء التأكد من صحة الرابط'
            })

        try:
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
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Referer': url,
                'Origin': base_url,
                'Connection': 'keep-alive'
            }

            # محاولة الوصول للموقع مع إعادة المحاولة
            max_retries = 3
            retry_delay = 1  # ثانية واحدة بين المحاولات

            for attempt in range(max_retries):
                try:
                    logger.info(f"Attempt {attempt + 1} to fetch URL: {url}")
                    response = session.get(url, headers=headers, allow_redirects=True)
                    response.raise_for_status()
                    break
                except (requests.exceptions.RequestException, requests.exceptions.ConnectionError) as e:
                    if attempt == max_retries - 1:  # آخر محاولة
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                    time.sleep(retry_delay)

            # التحقق من نوع المحتوى
            content_type = response.headers.get('Content-Type', '').lower()
            if not any(t in content_type for t in ['text/html', 'application/xhtml+xml']):
                return jsonify({
                    'status': 'error',
                    'message': 'هذا الرابط لا يحتوي على صفحة HTML. الرجاء استخدام رابط لصفحة ويب'
                })

            # تحليل HTML مع الحفاظ على التعليقات
            try:
                soup = BeautifulSoup(response.content, 'html.parser', from_encoding=response.encoding)
            except Exception as e:
                logger.error(f"HTML parsing error: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': 'فشل في تحليل محتوى الصفحة. قد يكون المحتوى غير صالح'
                })

            # حفظ وتنظيف العناصر غير المرغوب فيها
            for tag in soup.find_all(['script', 'iframe', 'frame', 'noscript']):
                tag.decompose()

            # معالجة meta tags
            for tag in soup.find_all('meta'):
                # الاحتفاظ بـ meta tags المهمة فقط
                if not any(attr in tag.attrs for attr in ['charset', 'viewport', 'description', 'keywords']):
                    tag.decompose()

            # إضافة meta tags مهمة
            meta_tags = [
                {'charset': 'UTF-8'},
                {'name': 'viewport', 'content': 'width=device-width, initial-scale=1'},
                {'http-equiv': 'Content-Security-Policy', 'content': "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; img-src * data: blob:; font-src * data:;"},
                {'http-equiv': 'Cache-Control', 'content': 'no-cache, no-store, must-revalidate'}
            ]

            for meta_info in meta_tags:
                meta_tag = soup.new_tag('meta')
                for attr, value in meta_info.items():
                    meta_tag[attr] = value
                if not soup.head:
                    soup.html.insert(0, soup.new_tag('head'))
                soup.head.insert(0, meta_tag)

            # معالجة الخطوط
            font_faces = []
            for style in soup.find_all('style'):
                if '@font-face' in style.string:
                    font_faces.append(style.string)

            # معالجة CSS
            processed_css_urls = set()
            all_css = []

            for link in soup.find_all('link', rel='stylesheet'):
                try:
                    css_url = urllib.parse.urljoin(url, link.get('href', ''))
                    if css_url not in processed_css_urls:
                        processed_css_urls.add(css_url)
                        css_response = session.get(css_url, headers=headers)
                        if css_response.status_code == 200:
                            css_text = css_response.text
                            
                            # تحويل المسارات النسبية في CSS
                            css_text = re.sub(r'url\(["\']?(?!data:)([^)"\']+)["\']?\)', 
                                            lambda m: f'url("{urllib.parse.urljoin(css_url, m.group(1))}")',
                                            css_text)
                            
                            all_css.append(css_text)
                except Exception as e:
                    logger.warning(f"Failed to load CSS from {css_url}: {str(e)}")

            # دمج جميع CSS
            if all_css or font_faces:
                combined_css = '\n'.join(font_faces + all_css)
                style_tag = soup.new_tag('style')
                style_tag.string = combined_css
                soup.head.append(style_tag)

            # إزالة روابط CSS الأصلية
            for link in soup.find_all('link', rel='stylesheet'):
                link.decompose()

            # تحويل الصور إلى Data URLs مع الحفاظ على الجودة
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and not src.startswith('data:'):
                    try:
                        img_url = urllib.parse.urljoin(url, src)
                        img_response = session.get(img_url, headers=headers)
                        if img_response.status_code == 200:
                            img_type = img_response.headers.get('Content-Type', 'image/jpeg')
                            # التحقق من حجم الصورة
                            if len(img_response.content) < 1024 * 1024:  # أقل من 1 ميجابايت
                                img_data = base64.b64encode(img_response.content).decode('utf-8')
                                img['src'] = f'data:{img_type};base64,{img_data}'
                            else:
                                # للصور الكبيرة، نحتفظ بالرابط الأصلي
                                img['src'] = img_url
                                img['crossorigin'] = 'anonymous'
                    except Exception as e:
                        logger.warning(f"Failed to convert image to data URL: {str(e)}")
                        if not img['src'].startswith(('http://', 'https://')):
                            img['src'] = urllib.parse.urljoin(url, src)

            # تحويل الروابط النسبية إلى مطلقة
            for tag in soup.find_all(['a', 'form']):
                for attr in ['href', 'action']:
                    if tag.get(attr):
                        try:
                            if not tag[attr].startswith(('http://', 'https://', 'data:', '#', 'mailto:', 'tel:')):
                                tag[attr] = urllib.parse.urljoin(url, tag[attr])
                        except Exception as e:
                            logger.warning(f"Failed to convert URL {tag.get(attr)}: {str(e)}")

            # إضافة CSS مخصص للتحرير
            edit_style = soup.new_tag('style')
            edit_style.string = '''
                [contenteditable="true"] {
                    outline: 2px dashed #007bff;
                    min-height: 20px;
                    padding: 5px;
                    margin: 2px;
                    position: relative;
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

            return jsonify({
                'status': 'success',
                'html': str(soup)
            })

        except requests.exceptions.SSLError as e:
            logger.error(f"SSL Error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'فشل في التحقق من شهادة SSL للموقع. جرب استخدام http بدلاً من https'
            })
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection Error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'فشل في الاتصال بالموقع. تأكد من اتصالك بالإنترنت وصحة الرابط'
            })
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout Error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'انتهت مهلة الاتصال بالموقع. الموقع بطيء جداً، حاول مرة أخرى'
            })
        except requests.exceptions.TooManyRedirects as e:
            logger.error(f"Too Many Redirects: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'عدد كبير جداً من إعادة التوجيهات. قد يكون هناك مشكلة في الموقع'
            })
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            logger.error(f"HTTP Error {status_code}: {str(e)}")
            
            if status_code == 404:
                message = 'الصفحة غير موجودة'
            elif status_code == 403:
                message = 'الوصول للموقع محظور'
            elif status_code == 401:
                message = 'يتطلب الموقع تسجيل الدخول'
            elif status_code == 429:
                message = 'تم تجاوز عدد الطلبات المسموح بها. حاول مرة أخرى بعد قليل'
            elif status_code >= 500:
                message = 'خطأ في خادم الموقع المطلوب'
            else:
                message = f'خطأ في الخادم: {status_code}'
            
            return jsonify({
                'status': 'error',
                'message': message
            })
        except Exception as e:
            logger.error(f"Unexpected error while cloning website: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                'status': 'error',
                'message': 'حدث خطأ غير متوقع أثناء محاولة استنساخ الموقع. حاول مرة أخرى أو جرب موقعاً آخر'
            })

    except Exception as e:
        logger.error(f"System error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': 'حدث خطأ في النظام'
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
