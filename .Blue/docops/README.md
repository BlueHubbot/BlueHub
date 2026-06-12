# 📋 BlueHub DocOps System

**Documentation & Operations Tracking System**

این سیستم برای ثبت و پیگیری جلسات کاری، تصمیمات، و پیشرفت پروژه BlueHub طراحی شده است.

---

## 📁 Directory Structure

```
.kiro/docops/
├── README.md                    # این فایل
├── STATUS.md                    # وضعیت فعلی پروژه (به‌روزرسانی خودکار)
├── auto_reporter.py             # اسکریپت گزارش‌گیری خودکار
│
├── templates/
│   └── session_report.md        # قالب گزارش جلسه
│
├── sessions/                    # گزارش‌های جلسات کاری
│   ├── 2026-06-10_session-1.md
│   ├── 2026-06-11_session-2.md
│   └── ...
│
└── snapshots/                   # Snapshot های خودکار (هر 6 ساعت)
    ├── 2026-06-10_09-00-00.md
    ├── 2026-06-10_15-00-00.md
    └── ...
```

---

## 🚀 Usage

### 1. ثبت پایان جلسه کاری (Manual)

استفاده از دستور Kiro:

```
/session-end
```

این دستور:
- چند سوال می‌پرسد (کارهای انجام شده، موانع، تصمیمات)
- یک فایل گزارش در `sessions/` ایجاد می‌کند
- فایل `STATUS.md` را به‌روزرسانی می‌کند

### 2. گزارش خودکار (Automatic)

سیستم به صورت خودکار هر 6 ساعت:
- وضعیت پروژه را تحلیل می‌کند
- یک snapshot در `snapshots/` ایجاد می‌کند
- فایل `STATUS.md` را به‌روزرسانی می‌کند

### 3. اجرای دستی اسکریپت

```bash
# اجرای یکباره
python .kiro/docops/auto_reporter.py

# یا با Python مستقیم
cd .kiro/docops
python auto_reporter.py
```

### 4. راه‌اندازی Celery Task (Automatic Scheduling)

```python
# در services/celery_app.py
from docops.auto_reporter import setup_celery_task

# Setup the task
setup_celery_task(celery_app)

# سپس Celery Beat را اجرا کنید:
# celery -A services.celery_app beat
```

---

## 📊 Features

### Auto-Reporter (`auto_reporter.py`)

**Data Sources:**
- `tasks.md` - درصد پیشرفت، تسک‌های کامل شده، موانع
- `design.md` - تصمیمات معماری
- `requirements.md` - نیازمندی‌های تکمیل شده
- Git history - تغییرات اخیر (optional)

**Outputs:**
- Snapshot در `snapshots/YYYY-MM-DD_HH-MM-SS.md`
- به‌روزرسانی `STATUS.md`

**Metrics Tracked:**
- درصد پیشرفت کلی
- تعداد تسک‌های کامل شده / در حال انجام / مسدود شده
- تعداد نیازمندی‌های تکمیل شده
- موانع فعال
- تصمیمات اخیر

### Session Report Template

**Sections:**
- 🎯 اهداف جلسه
- ✅ کارهای انجام شده
- 🚧 کارهای باقی‌مانده
- 🚫 موانع و ریسک‌ها
- 📝 تغییرات مهم (Changelog)
- 🗂️ تصمیمات گرفته شده
- 📊 وضعیت پروژه
- 🔄 جلسه بعد
- ⚠️ نکات مهم
- 🔗 لینک‌های مهم

---

## 🔧 Configuration

### Celery Beat Schedule

```python
# در config/celery_config.py یا services/celery_app.py
from celery.schedules import crontab

app.conf.beat_schedule = {
    'docops-auto-report': {
        'task': 'docops.generate_report',
        'schedule': 6 * 60 * 60,  # هر 6 ساعت (به ثانیه)
        'options': {'queue': 'background'}
    }
}
```

### Custom Schedule Options

```python
# هر 3 ساعت
'schedule': 3 * 60 * 60

# روزانه در ساعت 9 صبح
'schedule': crontab(hour=9, minute=0)

# در پایان هر روز کاری (شنبه تا چهارشنبه)
'schedule': crontab(hour=18, minute=0, day_of_week='0-3')
```

---

## 📝 Session Report Example

```markdown
# 📋 SESSION REPORT - BlueHub

**تاریخ:** 2026-06-10 | **شماره جلسه:** #5 | **وضعیت:** 🟢

## 🎯 اهداف جلسه

- **هدف اصلی:** کامل کردن مستندات زیرساخت (بخش‌های A-N)
- **خروجی مورد انتظار:** فایل INFRASTRUCTURE_COMPLETE_SPEC.md

## ✅ کارهای انجام شده

- [x] بخش A: Bare Metal & Hardware (فایل: `INFRASTRUCTURE_COMPLETE_SPEC.md`)
- [x] بخش B: Network & IP Management
- [x] بخش C-N: تمام بخش‌های باقی‌مانده (100%)

## 📊 وضعیت پروژه

| شاخص | مقدار |
| --- | --- |
| درصد پیشرفت | 100% (معماری) |
| باگ‌های باز | 0 |
| زمان تخمینی باقی‌مانده | 16 هفته (پیاده‌سازی) |

## 🔄 جلسه بعد

- **قدم اول:** شروع فاز 0 (راه‌اندازی محیط توسعه)
- **خروجی مورد انتظار:** Docker Compose و Paymenter راه‌اندازی شده
```

---

## 🔗 Integration with Kiro

### Custom Command: `/session-end`

این دستور در Kiro به صورت زیر کار می‌کند:

1. از شما سوالات زیر را می‌پرسد:
   - چه کارهایی انجام دادید؟
   - چه موانعی داشتید؟
   - چه تصمیماتی گرفته شد؟
   - برای جلسه بعد چه برنامه‌ای دارید؟

2. پاسخ‌ها را در قالب `session_report.md` قرار می‌دهد

3. فایل را در `sessions/YYYY-MM-DD_session-N.md` ذخیره می‌کند

4. فایل `STATUS.md` را به‌روزرسانی می‌کند

---

## 📈 Metrics & KPIs

### Tracked Automatically

- **Task Progress:** درصد تکمیل تسک‌ها
- **Velocity:** تعداد تسک‌های کامل شده در هفته
- **Blockers:** تعداد موانع فعال
- **Session Frequency:** تعداد جلسات در هفته
- **Phase Progress:** پیشرفت در هر فاز

### Manual Entry (via `/session-end`)

- تصمیمات مهم
- موانع و ریسک‌های جدید
- تغییرات معماری
- نکات فنی برای جلسه بعد

---

## 🎯 Best Practices

### برای استفاده بهتر:

1. **ثبت منظم:** حتماً در پایان هر جلسه کاری `/session-end` را اجرا کنید
2. **جزئیات دقیق:** در گزارش‌ها، لینک‌های فایل‌ها و commit های مرتبط را ذکر کنید
3. **موانع را سریع ثبت کنید:** هر مانع جدید را فوراً در گزارش بنویسید
4. **تصمیمات را مستند کنید:** همیشه دلیل تصمیمات را بنویسید
5. **مرور دوره‌ای:** هفته‌ای یکبار تمام گزارش‌ها را مرور کنید

### نکات امنیتی:

- ⚠️ اطلاعات حساس (رمز، API key) را در گزارش‌ها **ننویسید**
- ⚠️ از لینک‌های نسبی استفاده کنید (نه مسیر مطلق)
- ⚠️ قبل از commit، گزارش‌ها را مرور کنید

---

## 🐛 Troubleshooting

### مشکل: اسکریپت اجرا نمی‌شود

```bash
# بررسی Python version (باید 3.12+ باشد)
python --version

# نصب dependencies
pip install -r requirements.txt

# اجرا با verbose mode
python -v .kiro/docops/auto_reporter.py
```

### مشکل: Celery task اجرا نمی‌شود

```bash
# بررسی Celery worker
celery -A services.celery_app inspect active

# بررسی Celery Beat
celery -A services.celery_app beat --loglevel=info

# بررسی schedule
celery -A services.celery_app inspect scheduled
```

### مشکل: فایل‌های گزارش خالی هستند

- بررسی کنید `tasks.md` در مسیر صحیح باشد
- مطمئن شوید فرمت task ها درست است (`**ID:** TASK-XXX`)
- لاگ‌های اسکریپت را بررسی کنید

---

## 📚 References

- [Kiro Documentation](https://docs.kiro.ai)
- [Celery Beat Scheduling](https://docs.celeryproject.org/en/stable/userguide/periodic-tasks.html)
- [BlueHub Tasks](../specs/bluehub-platform/tasks.md)
- [BlueHub Requirements](../specs/bluehub-platform/requirements.md)

---

## 📞 Support

برای سوالات یا مشکلات:
1. گزارش issue در GitHub
2. مرور فایل `STATUS.md` برای وضعیت فعلی
3. بررسی آخرین snapshot در `snapshots/`

---

**Version:** 1.0  
**Last Updated:** 2026-06-10  
**Maintained by:** BlueHub Team
