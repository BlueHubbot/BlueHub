import fs from 'fs';
import path from 'path';
import { glob } from 'glob';

interface TranslationKey {
  key: string;
  en: string;
  file: string;
  line: number;
  context: string;
}

const SCAN_PATHS = [
  'src/**/*.{ts,tsx,js,jsx}',
  '!src/**/*.test.{ts,tsx}',
  '!src/**/*.spec.{ts,tsx}',
  '!**/node_modules/**',
  '!**/.next/**',
  '!**/.*/**',
];

// کلمات غیرضروری (برای فیلتر)
const EXCLUDED = new Set([
  'true', 'false', 'null', 'undefined', 'NaN', 'Infinity',
  'className', 'class', 'style', 'id', 'key', 'ref', 'type',
  'onClick', 'onChange', 'onSubmit', 'onFocus', 'onBlur',
  'href', 'src', 'alt', 'width', 'height', 'display',
  'flex', 'grid', 'block', 'inline', 'hidden', 'visible',
  'px', 'py', 'mx', 'my', 'mt', 'mb', 'ml', 'mr', 'ms', 'me',
  'text', 'font', 'bg', 'border', 'rounded', 'shadow',
  'hover', 'focus', 'active', 'disabled', 'selected',
  'sm', 'md', 'lg', 'xl', '2xl', 'center', 'left', 'right',
  'top', 'bottom', 'middle', 'auto', 'none', '0', '1', '2',
  '3', '4', '5', '6', '7', '8', '9', '10', 'undefined',
  'any', 'string', 'number', 'boolean', 'object', 'array',
]);

// الگوهای استخراج (به‌ترتیب اولویت)
const PATTERNS = [
  // 1. متون داخل JSX: <Tag>text</Tag>
  { regex: /<[a-zA-Z][a-zA-Z0-9]*[^>]*>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/[a-zA-Z][a-zA-Z0-9]*>/g, group: 1 },
  
  // 2. متون داخل attributes: placeholder="text", label="text"
  { regex: /\b(placeholder|label|title|aria-label|description|name|value|defaultValue|help|error|success|warning|info|message|content|text|heading|subheading)\s*[=:]\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 2 },
  
  // 3. متون داخل آبجکت‌ها: { key: "value" }
  { regex: /["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']\s*[,}\]]/g, group: 1 },
  
  // 4. متون داخل آرایه‌ها: ["text"]
  { regex: /\[\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']\s*[,?\]]/g, group: 1 },
  
  // 5. متون با template literals: `text ${var}`
  { regex: /`([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})`/g, group: 1 },
  
  // 6. متون با t() یا formatMessage
  { regex: /\b(t|formatMessage|getTranslations|useTranslations)\s*\(\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 2 },
  
  // 7. متون داخل metadata
  { regex: /metadata\s*:\s*\{[^}]*\b(title|description|keywords)\s*:\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 2 },
  
  // 8. متون با children: "text"
  { regex: /children\s*:\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 1 },
  
  // 9. متون با toast/sonner/notify
  { regex: /\b(toast|sonner|notify|message|error|success|warning|info)\s*[({:]\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 2 },
  
  // 10. متون داخل <title> و <meta>
  { regex: /<title>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/title>/g, group: 1 },
  { regex: /<meta[^>]*content=["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["'][^>]*>/g, group: 1 },
  
  // 11. متون داخل کامپوننت‌های Shadcn
  { regex: /<([A-Z][a-zA-Z]+)[^>]*>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/\1>/g, group: 2 },
  
  // 12. متون داخل توابع (return)
  { regex: /return\s*\(?\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 1 },
  
  // 13. متون با console.log
  { regex: /console\.(log|warn|error|info)\s*\(\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 2 },
  
  // 14. متون داخل switch/case
  { regex: /case\s+["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 1 },
];

function extractAll(filePath: string): TranslationKey[] {
  const content = fs.readFileSync(filePath, 'utf-8');
  const keys: TranslationKey[] = [];
  const seen = new Set<string>();
  const lines = content.split('\n');

  lines.forEach((line, index) => {
    // رد کردن خطوط غیرضروری
    if (/^\s*(import|export|require|const|let|var|function|class|interface|type|enum|declare|module|namespace)/.test(line)) {
      return;
    }
    if (/\/\//.test(line)) return; // رد کردن کامنت‌ها

    PATTERNS.forEach(({ regex, group }) => {
      const regexCopy = new RegExp(regex.source, 'g');
      let match;
      while ((match = regexCopy.exec(line)) !== null) {
        const text = match[group]?.trim();
        if (!text || text.length < 2) continue;
        if (text.length > 150) continue; // احتمالاً جمله نیست
        if (EXCLUDED.has(text.toLowerCase())) continue;
        if (/^[0-9\s,]+$/.test(text)) continue;
        if (/^[A-Z]$/.test(text)) continue;
        if (/^[a-z]+_[a-z]+$/.test(text)) continue; // متغیرهای underscore

        // ساخت کلید یکتا
        const key = text
          .toLowerCase()
          .replace(/[^a-z0-9_]/g, '_')
          .replace(/_+/g, '_')
          .replace(/^_|_$/g, '')
          .substring(0, 60);

        if (!key) continue;
        const id = `${key}::${text}`;
        if (seen.has(id)) return;
        seen.add(id);

        // گرفتن context (چند کلمه قبل و بعد)
        const lineContext = line.trim();
        const context = lineContext.length > 100 ? lineContext.substring(0, 100) + '...' : lineContext;

        keys.push({
          key,
          en: text,
          file: path.relative(process.cwd(), filePath),
          line: index + 1,
          context,
        });
      }
    });
  });

  return keys;
}

async function main() {
  console.log('🔍 اسکن دقیق تمام فایل‌ها...\n');

  const allKeys: TranslationKey[] = [];
  const files = glob.sync(SCAN_PATHS, { 
    cwd: process.cwd(), 
    absolute: true,
  });

  console.log(`📁 ${files.length} فایل یافت شد\n`);

  let fileCount = 0;
  for (const file of files) {
    const keys = extractAll(file);
    if (keys.length > 0) {
      fileCount++;
      allKeys.push(...keys);
      console.log(`  ✅ ${path.basename(file)}: ${keys.length} کلید`);
    }
  }

  // حذف تکراری‌های نهایی
  const uniqueMap = new Map<string, TranslationKey>();
  allKeys.forEach((item) => {
    const id = `${item.key}::${item.en}`;
    if (!uniqueMap.has(id) || uniqueMap.get(id)!.file !== item.file) {
      uniqueMap.set(id, item);
    }
  });

  const result = Array.from(uniqueMap.values());

  // مرتب‌سازی بر اساس کلید
  result.sort((a, b) => a.key.localeCompare(b.key));

  const messagesDir = path.join(process.cwd(), 'messages');
  if (!fs.existsSync(messagesDir)) {
    fs.mkdirSync(messagesDir, { recursive: true });
  }

  // ذخیره کامل
  fs.writeFileSync(
    path.join(messagesDir, 'extracted_ultimate.json'),
    JSON.stringify(result, null, 2)
  );

  // en.json یکتا
  const enJson: Record<string, string> = {};
  result.forEach(({ key, en }) => {
    if (!enJson[key]) {
      enJson[key] = en;
    }
  });
  fs.writeFileSync(
    path.join(messagesDir, 'en.json'),
    JSON.stringify(enJson, null, 2)
  );

  // fa.json خالی
  const faJson: Record<string, string> = {};
  Object.keys(enJson).forEach((key) => {
    faJson[key] = '';
  });
  fs.writeFileSync(
    path.join(messagesDir, 'fa.empty_ultimate.json'),
    JSON.stringify(faJson, null, 2)
  );

  // آمار نهایی
  console.log(`\n${'='.repeat(60)}`);
  console.log(`📊 آمار نهایی:`);
  console.log(`  - فایل‌های اسکن شده: ${files.length}`);
  console.log(`  - فایل‌های دارای متن: ${fileCount}`);
  console.log(`  - کل کلیدهای استخراج شده: ${allKeys.length}`);
  console.log(`  - کلیدهای یکتا: ${result.length}`);
  console.log(`  - کلیدهای en.json: ${Object.keys(enJson).length}`);
  console.log(`${'='.repeat(60)}`);

  // ۲۰ کلید نمونه
  console.log(`\n📋 ۲۰ کلید نمونه:`);
  result.slice(0, 20).forEach(({ key, en, file, line }) => {
    console.log(`  ${key}: "${en}" (${path.basename(file)}:${line})`);
  });

  console.log(`\n✅ فایل‌های تولید شده:`);
  console.log(`  - messages/extracted_ultimate.json (${result.length} کلید با اطلاعات کامل)`);
  console.log(`  - messages/en.json (${Object.keys(enJson).length} کلید)`);
  console.log(`  - messages/fa.empty_ultimate.json (${Object.keys(faJson).length} کلید خالی برای ترجمه)`);
}

main().catch(console.error);
