# Website Cloner

أداة لاستنساخ وتعديل المواقع الإلكترونية مع واجهة مستخدم سهلة الاستخدام.

## المميزات

- استنساخ أي موقع إلكتروني عن طريق رابط URL
- تحرير النصوص والصور والروابط مباشرة
- دعم التراجع وإعادة التغييرات
- تحميل النسخة المعدلة كملف ZIP
- دعم رفع الصور المحلية
- تحويل المسارات النسبية إلى مطلقة

## المتطلبات

- Python 3.8+
- Flask
- BeautifulSoup4
- Requests

## التثبيت

```bash
# استنساخ المشروع
git clone https://github.com/[your-username]/website-cloner.git
cd website-cloner

# تثبيت المتطلبات
pip install -r requirements.txt
```

## التشغيل المحلي

```bash
python app.py
```

ثم افتح المتصفح على الرابط: `http://localhost:5000`

## النشر

المشروع جاهز للنشر على منصات مثل Render.com:

1. قم بربط مستودع GitHub مع Render.com
2. اختر "Web Service"
3. اضبط أمر البدء على: `gunicorn app:app`
4. اضبط متغيرات البيئة حسب الحاجة

## المساهمة

نرحب بمساهماتكم! يرجى إنشاء fork للمشروع وإرسال pull request.

## الترخيص

MIT License
