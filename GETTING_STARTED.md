# 🚀 BlueHub - راهنمای شروع پروژه

## خوش آمدید به BlueHub!

این راهنما برای شروع سریع پروژه BlueHub طراحی شده است. مستندات کامل در پوشه `.kiro/specs/bluehub-platform/` قرار دارد.

---

## 📚 مستندات موجود

پروژه BlueHub دارای چهار سند اصلی است:

### 1. [README.md](.kiro/specs/bluehub-platform/README.md)
**خلاصه کلی پروژه و راهنمای مستندات**
- معرفی کلی پلتفرم
- ساختار پروژه کامل
- تکنولوژی‌های استفاده شده
- لینک‌های سریع به سایر اسناد

### 2. [requirements.md](.kiro/specs/bluehub-platform/requirements.md)
**نیازمندی‌های کامل با فرمت EARS**
- ✅ 77 نیازمندی عملیاتی (با فرمت WHEN/WHERE/THEN)
- ✅ 17 User Story برای مسیرهای مختلف کاربری
- ✅ نیازمندی‌های امنیتی، چندزبانه بودن، و Multi-Tenant
- ✅ معیارهای پذیرش برای هر فاز
- ✅ یکپارچگی با Paymenter

### 3. [design.md](.kiro/specs/bluehub-platform/design.md)
**طراحی سیستم با دیاگرام‌ها و جزئیات فنی**
- ✅ 7 دیاگرام Mermaid (معماری، جریان داده، ERD)
- ✅ طراحی کامل دیتابیس (15+ جدول)
- ✅ 20+ API endpoint با مثال‌های request/response
- ✅ جزئیات یکپارچگی با Paymenter
- ✅ معماری Module Registry و Feature Flags
- ✅ سیستم i18n (چندزبانه)
- ✅ معماری امنیتی (JWT, RBAC, Audit)
- ✅ معماری deployment (Docker, Kubernetes)

### 4. [tasks.md](.kiro/specs/bluehub-platform/tasks.md)
**تسک‌های عملیاتی فازبندی شده**
- ✅ 59 تسک تفکیک‌شده به 7 فاز
- ✅ وابستگی‌ها، اولویت‌ها، و زمان‌بندی هر تسک
- ✅ معیارهای پذیرش (Acceptance Criteria) برای هر تسک
- ✅ نکات فنی و کدهای نمونه
- ✅ برآورد زمانی: ~650 ساعت (16 هفته با 1 توسعه‌دهنده)
- ✅ دیاگرام وابستگی تسک‌ها

---

## 🗂️ ساختار فایل‌های Spec

```
.kiro/specs/bluehub-platform/
├── README.md          # خلاصه کلی و راهنمای ناوبری
├── requirements.md    # نیازمندی‌ها (EARS format)
├── design.md          # طراحی سیستم (Architecture + DB + API)
└── tasks.md           # تسک‌های فازبندی‌شده
```

---

## 🎯 گام‌های بعدی (پیشنهادی)

### گام 1: مطالعه مستندات (2-3 ساعت)
```bash
# خواندن به ترتیب زیر:
1. .kiro/specs/bluehub-platform/README.md        # شروع از اینجا
2. .kiro/specs/bluehub-platform/requirements.md  # درک نیازمندی‌ها
3. .kiro/specs/bluehub-platform/design.md        # فهم معماری
4. .kiro/specs/bluehub-platform/tasks.md         # برنامه‌ریزی اجرا
```

### گام 2: راه‌اندازی محیط توسعه (Phase 0 - Week 1)
```bash
# TASK-001: Initialize Git Repository
git init .
git checkout -b dev
git checkout -b main

# TASK-002: Docker Compose Setup
# ایجاد docker-compose.yml با PostgreSQL, Redis, MinIO

# TASK-003: Install Paymenter
# نصب Paymenter روی subdomain برای تست

# TASK-004: Create Directory Structure
# ایجاد ساختار پوشه‌های پروژه طبق design.md

# TASK-005: Python Project Init
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install fastapi uvicorn sqlalchemy alembic pydantic aiogram celery redis
```

### گام 3: پیاده‌سازی Core (Phase 1 - Week 2-3)
شروع از تسک‌های TASK-006 تا TASK-015 در `tasks.md`:
- Database Models (Core Schema)
- JWT Authentication
- RBAC System
- i18n Engine
- Module Registry
- Paymenter Webhooks

### گام 4: پیاده‌سازی اولین ماژول - VPN (Phase 2 - Week 3-5)
تسک‌های TASK-016 تا TASK-028:
- VPN Database Models
- WireGuard Integration
- VLESS+REALITY Integration
- API Endpoints
- Telegram Bot Handlers
- Web Client Pages

### گام 5: ادامه طبق Roadmap
ادامه پیاده‌سازی طبق tasks.md تا تکمیل همه فازها.

---

## 📊 آمار کلی

### نیازمندی‌ها (requirements.md)
- **تعداد کل نیازمندی‌ها:** 77
- **User Stories:** 17
- **Constraints:** 10
- **فازها:** 7 فاز (از Setup تا Advanced Features)

### طراحی (design.md)
- **دیاگرام‌های Mermaid:** 7 عدد
- **جداول دیتابیس:** 15+ جدول
- **API Endpoints:** 20+ endpoint
- **Integration Points:** 4 سرویس خارجی

### تسک‌ها (tasks.md)
- **تعداد کل تسک‌ها:** 59
- **تسک‌های Critical:** 15
- **تسک‌های High Priority:** 24
- **زمان برآوردی:** ~650 ساعت (16 هفته)
- **تیم پیشنهادی:** 2 Backend + 1 Frontend + 1 DevOps = 8-10 هفته

---

## 🔑 ویژگی‌های کلیدی

### 1. معماری API-First
- همه منطق در FastAPI
- کلاینت‌ها (ربات، وب، موبایل) فقط لایه نمایش
- مستندات OpenAPI خودکار

### 2. طراحی Modular (Plug & Play)
- هر سرویس یک ماژول مستقل
- افزودن ماژول = ساخت پوشه + ثبت در registry
- حذف ماژول = غیرفعال از پنل ادمین

### 3. Multi-Tenant & White-Label
- یک نصب، چندین برند
- دامنه، لوگو، رنگ سفارشی
- توکن ربات تلگرام اختصاصی
- قیمت‌گذاری مجزا

### 4. Feature Flags
- فعال/غیرفعال ماژول‌ها بدون restart
- دو حالت: توقف فروش جدید یا قطع سرویس‌های فعال
- کش در Redis برای سرعت

### 5. چندزبانه (i18n)
- فارسی و انگلیسی از ابتدا
- فایل‌های JSON برای ترجمه
- قابل گسترش از پنل ادمین

### 6. امنیت
- JWT (Access + Refresh Token)
- RBAC (4 نقش: superadmin, admin, reseller, user)
- 2FA (TOTP)
- Audit Logging کامل
- ضدکرک (License + Signature)

---

## 🛠️ تکنولوژی‌ها

### Backend
- Python 3.12+, FastAPI, SQLAlchemy, Alembic
- PostgreSQL 16, Redis 7, Celery
- aiogram 3 (Telegram Bot)

### Frontend
- Next.js 15, React, TypeScript
- Shadcn UI, Tailwind CSS
- Tanstack Query

### Infrastructure
- Docker, Docker Compose, Kubernetes
- Prometheus, Grafana, ELK Stack
- GitHub Actions (CI/CD)

### Integrations
- Paymenter (Billing)
- Proxmox VE (VPS)
- WireGuard, Xray-core (VPN)
- MaxMind (Fraud Detection)

---

## 📖 منابع یادگیری

### برای Backend Developer:
1. FastAPI: https://fastapi.tiangolo.com/
2. SQLAlchemy 2.0: https://docs.sqlalchemy.org/
3. Celery: https://docs.celeryq.dev/
4. aiogram 3: https://docs.aiogram.dev/

### برای Frontend Developer:
1. Next.js 15: https://nextjs.org/docs
2. Shadcn UI: https://ui.shadcn.com/
3. Tanstack Query: https://tanstack.com/query/

### برای DevOps:
1. Docker: https://docs.docker.com/
2. Kubernetes: https://kubernetes.io/docs/
3. Prometheus: https://prometheus.io/docs/

---

## 🤔 سوالات متداول

### Q: چرا API-First؟
**A:** تا همه کلاینت‌ها (ربات، وب، موبایل، شخص ثالث) از یک منبع واحد استفاده کنند. تغییرات منطق کسب‌وکار فقط یک‌بار در API اعمال می‌شود.

### Q: چرا Modular؟
**A:** برای انعطاف‌پذیری. اگر در آینده خواستید سرویس جدیدی اضافه کنید (مثلاً Web Hosting)، فقط یک ماژول جدید می‌سازید بدون تغییر در core.

### Q: چرا Multi-Tenant؟
**A:** برای فروش white-label به نمایندگان. هر نماینده می‌تواند با برند خودش سرویس بفروشد.

### Q: Legacy bot چیست؟
**A:** ربات قدیمی تلگرام BlueHub که کاربران دارد. باید به تدریج مهاجرت دهیم (Phase 6).

### Q: زمان تحویل واقعی؟
**A:** با تیم 4 نفره (2 Backend + 1 Frontend + 1 DevOps) حدود **8-10 هفته** برای فازهای 0 تا 4 (Core + VPN + Admin + VPS).

---

## 📞 پشتیبانی

برای سوالات یا توضیحات بیشتر:
- مطالعه مستندات در `.kiro/specs/bluehub-platform/`
- بررسی task مربوطه در `tasks.md`
- مشورت با Lead Developer

---

## ✅ Checklist شروع پروژه

```markdown
- [ ] خواندن README.md
- [ ] خواندن requirements.md (حداقل بخش Functional Requirements)
- [ ] مرور design.md (دیاگرام‌ها و ERD)
- [ ] بررسی tasks.md (فاز 0 و 1)
- [ ] نصب Docker و Docker Compose
- [ ] نصب Python 3.12+
- [ ] نصب Node.js 18+ (برای Next.js)
- [ ] کلون کردن legacy bot برای مطالعه
- [ ] ساخت اکانت تست در Telegram برای ربات
- [ ] راه‌اندازی Paymenter روی سرور تست
- [ ] شروع TASK-001 (Initialize Repository)
```

---

**موفق باشید! 🚀**

*این پروژه با دقت و جزئیات کامل طراحی شده است. با پیروی از tasks.md و استفاده از مستندات، می‌توانید یک پلتفرم enterprise-grade بسازید.*

---

*آخرین به‌روزرسانی: 10 ژوئن 2026*  
*نسخه: 1.0*
