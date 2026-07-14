import fs from 'fs';
import path from 'path';
import { glob } from 'glob';

interface TranslationKey {
  key: string;
  en: string;
  file: string;
}

const SCAN_PATHS = [
  'src/**/*.tsx',
  'src/**/*.ts',
  'src/**/*.jsx',
  'src/**/*.js',
  '!src/**/*.test.ts',
  '!src/**/*.spec.ts',
];

const PATTERNS = [
  // متون داخل JSX: <div>Hello</div>
  { regex: /<[^>]*>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/[^>]*>/g, group: 1 },
  // متون داخل placeholder
  { regex: /placeholder=["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 1 },
  // متون داخل label
  { regex: /label=["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 1 },
  // متون داخل title
  { regex: /title=["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 1 },
  // متون داخل aria-label
  { regex: /aria-label=["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 1 },
  // متون داخل description
  { regex: /description=["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 1 },
  // متون داخل heading
  { regex: /<h[1-6][^>]*>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/h[1-6]>/g, group: 1 },
  // متون داخل Button: <Button>Click</Button>
  { regex: /<Button[^>]*>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/Button>/g, group: 1 },
  // متون داخل alert
  { regex: /<Alert[^>]*>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/Alert>/g, group: 1 },
  // متون داخل toast
  { regex: /toast[^;]*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 1 },
  // متون داخل sonner
  { regex: /sonner[^;]*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 1 },
  // متون داخل message
  { regex: /message["']\s*:\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 1 },
  // متون داخل content
  { regex: /content["']\s*:\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 1 },
  // متون داخل error
  { regex: /error["']\s*:\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 1 },
  // متون داخل placeholder برای input
  { regex: /placeholder\s*=\s*{?\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']\s*}?/g, group: 1 },
  // متون با formatMessage
  { regex: /formatMessage\([^)]*['"]([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})['"]/g, group: 1 },
  // متون داخل t('...')
  { regex: /t\(['"]([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})['"]\)/g, group: 1 },
  // متون داخل useTranslations
  { regex: /useTranslations\(['"]([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})['"]\)/g, group: 1 },
  // متون داخل getTranslations
  { regex: /getTranslations\(['"]([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})['"]\)/g, group: 1 },
  // متون در متادیتا
  { regex: /metadata\s*:\s*{[^}]*title:\s*['"]([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})['"]/g, group: 1 },
  // متون در متادیتا description
  { regex: /metadata\s*:\s*{[^}]*description:\s*['"]([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})['"]/g, group: 1 },
];

function extractAllTexts(filePath: string): TranslationKey[] {
  const content = fs.readFileSync(filePath, 'utf-8');
  const keys: TranslationKey[] = [];
  const seen = new Set<string>();

  PATTERNS.forEach(({ regex }) => {
    let match;
    const regexCopy = new RegExp(regex.source, regex.flags);
    while ((match = regexCopy.exec(content)) !== null) {
      const text = match[1]?.trim();
      if (!text || text.length < 3) continue;
      
      // فقط متون با حداقل ۳ حرف انگلیسی
      if (!/^[A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,}$/.test(text)) continue;
      if (/^[0-9\s]+$/.test(text)) continue;
      if (/^[A-Z]$/.test(text)) continue;
      
      // ساخت کلید یکتا
      const key = text
        .toLowerCase()
        .replace(/[^a-z0-9_]/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_|_$/g, '')
        .substring(0, 50);
      
      if (!key || seen.has(key + text)) continue;
      seen.add(key + text);
      
      keys.push({
        key: key || `text_${keys.length}`,
        en: text,
        file: path.relative(process.cwd(), filePath),
      });
    }
  });

  return keys;
}

async function main() {
  const allKeys: TranslationKey[] = [];
  
  // دریافت فایل‌ها
  const files = glob.sync(SCAN_PATHS, { 
    cwd: process.cwd(), 
    absolute: true,
    ignore: ['**/node_modules/**', '**/.*/**', '**/*.test.ts', '**/*.spec.ts'],
  });

  console.log(`🔍 اسکن ${files.length} فایل...`);

  let totalFound = 0;
  for (const file of files) {
    const keys = extractAllTexts(file);
    totalFound += keys.length;
    allKeys.push(...keys);
  }

  // حذف تکراری‌ها (همان کلید و متن)
  const uniqueMap = new Map<string, TranslationKey>();
  allKeys.forEach((item) => {
    const id = `${item.key}::${item.en}`;
    if (!uniqueMap.has(id)) {
      uniqueMap.set(id, item);
    }
  });

  const result = Array.from(uniqueMap.values());

  // ذخیره فایل‌ها
  const messagesDir = path.join(process.cwd(), 'messages');
  if (!fs.existsSync(messagesDir)) {
    fs.mkdirSync(messagesDir, { recursive: true });
  }

  // extracted.json کامل
  fs.writeFileSync(
    path.join(messagesDir, 'extracted_full.json'),
    JSON.stringify(result, null, 2)
  );
  console.log(`✅ ${result.length} کلید استخراج شد`);

  // en.json
  const enJson: Record<string, string> = {};
  result.forEach(({ key, en }) => {
    enJson[key] = en;
  });
  fs.writeFileSync(
    path.join(messagesDir, 'en.json'),
    JSON.stringify(enJson, null, 2)
  );
  console.log(`✅ en.json ایجاد شد (${Object.keys(enJson).length} کلید)`);

  // fa.json خالی
  const faJson: Record<string, string> = {};
  result.forEach(({ key }) => {
    faJson[key] = '';
  });
  fs.writeFileSync(
    path.join(messagesDir, 'fa.empty_full.json'),
    JSON.stringify(faJson, null, 2)
  );
  console.log(`✅ fa.empty_full.json ایجاد شد`);

  // آمار
  console.log(`\n📊 آمار:`);
  console.log(`  - کل فایل‌های اسکن: ${files.length}`);
  console.log(`  - کلیدهای استخراج شده: ${result.length}`);
  
  const byFile: Record<string, number> = {};
  result.forEach(({ file }) => {
    byFile[file] = (byFile[file] || 0) + 1;
  });
  const topFiles = Object.entries(byFile)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);
  console.log(`\n📁 ۱۰ فایل با بیشترین کلید:`);
  topFiles.forEach(([file, count]) => {
    console.log(`  - ${path.basename(file)}: ${count} کلید`);
  });

  console.log(`\n📋 مراحل بعدی:`);
  console.log(`  1. فایل messages/extracted_full.json را بررسی کنید`);
  console.log(`  2. فایل messages/fa.empty_full.json را به تیم ترجمه بدهید`);
  console.log(`  3. بعد از ترجمه به fa.json تغییر نام دهید`);
}

main().catch(console.error);
