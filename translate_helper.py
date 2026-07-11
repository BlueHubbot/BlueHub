import os
import json
import re

FA_JSON_PATH = '/BlueHub/web/admin/messages/fa.json'
EN_JSON_PATH = '/BlueHub/web/admin/messages/en.json'

with open(FA_JSON_PATH, 'r', encoding='utf-8') as f:
    fa_translations = json.load(f)

with open(EN_JSON_PATH, 'r', encoding='utf-8') as f:
    en_translations = json.load(f)

translation_map = {}
for k, v in fa_translations.items():
    if isinstance(v, str): translation_map[v.strip()] = k
for k, v in en_translations.items():
    if isinstance(v, str): translation_map[v.strip()] = k

def translate_file(file_path):
    if not os.path.exists(file_path):
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    has_updates = False

    # جایگزینی متون بین تگ‌های HTML بدون ایجاد فاصله خرابکارانه در ساختار تگ
    for text_val, key in translation_map.items():
        pattern_html = re.compile(r'>\s*' + re.escape(text_val) + r'\s*<')
        if pattern_html.search(content):
            content = pattern_html.sub(f">{{t('{key}')}}<", content)
            has_updates = True

        # جایگزینی متون داخل اتریبیوت‌ها یا به عنوان استرینگ درون کدهای JSX
        pattern_str = re.compile(r'(["\'])\s*' + re.escape(text_val) + r'\s*(["\'])')
        if pattern_str.search(content):
            # بررسی اینکه آیا درون یک ساختار آبجکت جاوااسکریپت مثل label: "text" هستیم یا نه
            if re.search(r'\b\w+\s*:\s*(["\'])\s*' + re.escape(text_val) + r'\s*(["\'])', content):
                content = re.sub(r'(\b\w+\s*:\s*)(["\'])\s*' + re.escape(text_val) + r'\s*(["\'])', f"\\1t('{key}')", content)
            else:
                content = pattern_str.sub(f"{{t('{key}')}}", content)
            has_updates = True

    if has_updates:
        if "useTranslations" not in content:
            content = "import { useTranslations } from 'next-intl';\n" + content
            content = re.sub(
                r'(export\s+default\s+function\s+\w+\s*\(.*?\)\s*\{|export\s+function\s+\w+\s*\(.*?\)\s*\{)',
                r'\1\n  const t = useTranslations();',
                content,
                count=1
            )
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed & Translated: {file_path}")

target_components = [
    '/BlueHub/web/admin/src/app/(main)/dashboard/default/_components/metric-cards.tsx',
    '/BlueHub/web/admin/src/app/(main)/dashboard/default/_components/performance-overview.tsx',
    '/BlueHub/web/admin/src/app/(main)/dashboard/default/_components/subscriber-overview.tsx'
]

for comp in target_components:
    translate_file(comp)
