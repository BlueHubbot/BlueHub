import fs from 'fs';
import path from 'path';
import { glob } from 'glob';

interface TranslationKey {
  key: string;
  en: string;
  file: string;
}

// پوشه‌های اسکن
const SCAN_PATHS = [
  'src/app/**/*.tsx',
  'src/app/**/*.ts',
  'src/components/**/*.tsx',
  'src/components/**/*.ts',
  'src/lib/**/*.ts',
  'src/navigation/**/*.ts',
];

// الگوهای متون انگلیسی
const PATTERNS = [
  // متن داخل تگ‌ها: <div>Hello</div>
  { regex: />\s*([A-Za-z][A-Za-z0-9\s\.,!?\-:;]+)\s*</, group: 1 },
  // متن داخل دکمه: <Button>Click me</Button>
  { regex: /<Button[^>]*>([^<]+)<\/Button>/, group: 1 },
  // متن داخل heading: <h1>Title</h1>
  { regex: /<h[1-6][^>]*>([^<]+)<\/h[1-6]>/, group: 1 },
  // متن داخل placeholder
  { regex: /placeholder=["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;]+)["']/, group: 1 },
  // متن داخل label
  { regex: /<label[^>]*>([^<]+)<\/label>/, group: 1 },
  // متن داخل value
  { regex: /value=["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;]+)["']/, group: 1 },
  // متن داخل children صریح
  { regex: /children:?\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;]+)["']/, group: 1 },
];

function extractTexts(filePath: string): TranslationKey[] {
  const content = fs.readFileSync(filePath, 'utf-8');
  const keys: TranslationKey[] = [];
  const lines = content.split('\n');

  lines.forEach((line, index) => {
    PATTERNS.forEach(({ regex, group }) => {
      const match = regex.exec(line);
      if (match && match[group]) {
        const text = match[group].trim();
        // فقط متن‌های انگلیسی (حداقل ۲ حرف)
        if (/^[A-Za-z][A-Za-z0-9\s\.,!?\-:;]{1,}$/.test(text) && text.length > 2) {
          const key = text
            .toLowerCase()
            .replace(/[^a-z0-9]/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_|_$/g, '');
          
          keys.push({
            key: key || `text_${index}`,
            en: text,
            file: path.relative(process.cwd(), filePath),
          });
        }
      }
    });
  });

  return keys;
}

async function main() {
  const allKeys: TranslationKey[] = [];
  const files = glob.sync(SCAN_PATHS, { cwd: process.cwd(), absolute: true });

  console.log(`🔍 اسکن ${files.length} فایل...`);

  for (const file of files) {
    const keys = extractTexts(file);
    allKeys.push(...keys);
  }

  // حذف تکراری‌ها
  const uniqueKeys = new Map<string, TranslationKey>();
  allKeys.forEach((item) => {
    if (!uniqueKeys.has(item.key) || uniqueKeys.get(item.key)?.en.length < item.en.length) {
      uniqueKeys.set(item.key, item);
    }
  });

  const result = Array.from(uniqueKeys.values());

  // ذخیره در فایل JSON
  const outputPath = path.join(process.cwd(), 'messages/extracted.json');
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
  console.log(`✅ ${result.length} کلید استخراج شد: ${outputPath}`);

  // تولید فایل en.json
  const enJson: Record<string, string> = {};
  result.forEach(({ key, en }) => {
    enJson[key] = en;
  });
  fs.writeFileSync(
    path.join(process.cwd(), 'messages/en.json'),
    JSON.stringify(enJson, null, 2)
  );
  console.log(`✅ فایل en.json ایجاد شد`);

  // تولید فایل fa.json خالی برای پر کردن
  const faJson: Record<string, string> = {};
  result.forEach(({ key }) => {
    faJson[key] = '';
  });
  fs.writeFileSync(
    path.join(process.cwd(), 'messages/fa.empty.json'),
    JSON.stringify(faJson, null, 2)
  );
  console.log(`✅ فایل fa.empty.json ایجاد شد (برای پر کردن توسط تیم ترجمه)`);

  console.log('\n📋 مراحل بعدی:');
  console.log('1. فایل extracted.json را بررسی کنید');
  console.log('2. فایل fa.empty.json را به تیم ترجمه بدهید');
  console.log('3. بعد از ترجمه، به fa.json تغییر نام دهید');
}

main().catch(console.error);
