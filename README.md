# FL Strike Scanner — نظام كامل ببيانات حقيقية

أداة عربية لقراءة السوق الأمريكي:
- الوقت والتقويم وحالة السوق
- لوحة الانطباع الأول: نية السوق + السيولة + المحفزات + الترند + رأي السوق + Flow Proxy
- سكانر نية السوق والقطاعات
- سكانر الأسهم القيادية
- سكانر الأسهم الصغيرة
- أخبار وترند اجتماعي

## التشغيل المحلي

### 1) تشغيل الـ Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```
يفتح على:
```text
http://127.0.0.1:5000/api/dashboard
```

### 2) تشغيل الواجهة
افتح `frontend/index.html` مباشرة، أو استخدم إضافة Live Server.

## النشر الصحيح

### Backend
ارفع مجلد `backend` على Render كـ Web Service:
- Start command:
```bash
python app.py
```
- Runtime: Python

اختياري: أضف متغير بيئة:
```text
FINNHUB_API_KEY=your_key
```
لو ما أضفته، الأخبار تحاول تأتي من Yahoo Finance.

### Frontend
ارفع مجلد `frontend` على GitHub Pages.
بعد نشر Backend، عدل أول سطر في `frontend/app.js`:
```js
const API_BASE = "https://YOUR-RENDER-APP.onrender.com";
```

## ملاحظة مهمة
الأسعار من Yahoo Finance عبر yfinance، وهي مجانية لكنها ليست بديلًا احترافيًا كاملًا مثل Benzinga/Polygon المدفوع.
