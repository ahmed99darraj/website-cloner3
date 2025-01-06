from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import logging

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/clone', methods=['POST'])
def clone_website():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'الرجاء إدخال رابط الموقع'}), 400

        url = data['url'].strip()
        if not url.startswith(('http://', 'https://')):
            return jsonify({'error': 'الرجاء إدخال رابط يبدأ بـ http:// أو https://'}), 400

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        return jsonify({
            'status': 'success',
            'html': str(soup)
        })

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Request error: {str(e)}")
        return jsonify({'error': 'لا يمكن الوصول إلى الموقع. تأكد من صحة الرابط وأن الموقع متاح.'}), 400
    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return jsonify({'error': 'حدث خطأ غير متوقع. حاول مرة أخرى.'}), 500

if __name__ == '__main__':
    app.run(debug=True)
