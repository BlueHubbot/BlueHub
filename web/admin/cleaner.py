import os
import re

# مسیر اصلی پروژه
TARGET_DIR = "/BlueHub/web/admin"

# لیست پوشه‌هایی که نباید دست بخورند (پوشه‌های بیلد و پکیج‌ها)
EXCLUDE_DIRS = {'.next', 'node_modules', '.git'}

# نگاشت کلمات قدیمی به مقادیر جدید (به حروف بزرگ و کوچک حساس است)
REPLACEMENTS = {
    # نام کاربری طراح
    "arhamkhnz": "BlueHub",
    "ARHAMKHNZ": "BLUEHUB",
    
    # نام مخزن و کلمات کلیدی پنل
    "next-shadcn-admin-dashboard": "bluehub-admin",
    "next-shadcn-admin": "bluehub-admin",
    "shadcn-admin-dashboard": "bluehub-admin",
    
    # لینک‌های گیت‌هاب احتمالی
    "github.com/arhamkhnz": "github.com/SarmadAfzali",
}

def clean_file(file_path):
    try:
        # خواندن محتوای فایل
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # بررسی اینکه آیا نیازی به تغییر هست یا نه
        modified = False
        for old_word, new_word in REPLACEMENTS.items():
            if old_word in content:
                # جایگزینی دقیق کلمه
                content = re.sub(re.escape(old_word), new_word, content)
                modified = True
        
        # اگر فایلی تغییر کرد، ذخیره شود
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[✓] Cleaned: {file_path}")
            
    except Exception as e:
        print(f"[X] Error cleaning {file_path}: {e}")

def main():
    print("🚀 Starting global deep-clean for BlueHub...")
    for root, dirs, files in os.walk(TARGET_DIR):
        # فیلتر کردن پوشه‌های استثنا شده
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            # اسکریپت خودش را تغییر ندهد
            if file == "cleaner.py":
                continue
            
            file_path = os.path.join(root, file)
            clean_file(file_path)
            
    print("✨ Clean-up complete! Every single trace has been white-labeled.")

if __name__ == "__main__":
    main()