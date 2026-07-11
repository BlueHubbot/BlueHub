import fs from 'fs';
import path from 'path';
import { glob } from 'glob';

interface TranslationKey {
  key: string;
  en: string;
  file: string;
  line?: number;
}

const SCAN_PATHS = [
  'src/**/*.tsx',
  'src/**/*.ts',
  'src/**/*.jsx',
  'src/**/*.js',
  '!**/node_modules/**',
  '!**/.*/**',
  '!**/*.test.ts',
  '!**/*.spec.ts',
];

// الگوهای پیشرفته
const PATTERNS = [
  // 1. متون داخل JSX با children
  { regex: /<[a-zA-Z][^>]*>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/[a-zA-Z]/g, group: 1 },
  
  // 2. متون داخل placeholder، label، title، aria-label
  { regex: /(placeholder|label|title|aria-label|description|name|id|value)\s*[=:]\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 2 },
  
  // 3. متون داخل toast/sonner
  { regex: /(toast|sonner|notify|message|error|success|warning|info)\s*[=:]\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 2 },
  
  // 4. متون داخل متادیتا
  { regex: /metadata\s*:\s*{[^}]*title\s*:\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 1 },
  { regex: /metadata\s*:\s*{[^}]*description\s*:\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 1 },
  
  // 5. متون داخل آبجکت‌ها (مثل statusLabels)
  { regex: /:\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']\s*[,}]/g, group: 1 },
  
  // 6. متون با template literals (متن ثابت)
  { regex: /`([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})`/g, group: 1 },
  
  // 7. متون با formatMessage یا t()
  { regex: /(formatMessage|t|getTranslations|useTranslations)\s*\([^)]*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 2 },
  
  // 8. متون داخل <title>...</title>
  { regex: /<title>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/title>/g, group: 1 },
  
  // 9. متون داخل کامپوننت‌های Shadcn (مثل DialogHeader, CardHeader)
  { regex: /<[A-Z][a-zA-Z]*[^>]*>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/[A-Z][a-zA-Z]*>/g, group: 1 },
  
  // 10. متون با children: "text"
  { regex: /children\s*:\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g, group: 1 },
  
  // 11. متون داخل [] (مثل text: "Hello")
  { regex: /:\s*["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']\s*[,}\]]/g, group: 1 },
  
  // 12. متون با <span>text</span>
  { regex: /<span[^>]*>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/span>/g, group: 1 },
  
  // 13. متون با <p>text</p>
  { regex: /<p[^>]*>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/p>/g, group: 1 },
  
  // 14. متون با <div>text</div>
  { regex: /<div[^>]*>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/div>/g, group: 1 },
];

// کلمات غیرضروری
const EXCLUDED_WORDS = [
  'true', 'false', 'null', 'undefined', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
  'className', 'class', 'style', 'id', 'key', 'ref', 'onClick', 'onChange', 'onSubmit',
  'href', 'src', 'alt', 'width', 'height', 'display', 'flex', 'grid', 'block', 'inline',
  'px', 'py', 'mx', 'my', 'text', 'font', 'bg', 'border', 'rounded', 'shadow', 'hover',
  'focus', 'active', 'disabled', 'selected', 'checked', 'default', 'sm', 'md', 'lg', 'xl',
  'center', 'left', 'right', 'top', 'bottom', 'middle', 'auto', 'none', 'hidden', 'visible',
];

function extractTexts(filePath: string): TranslationKey[] {
  const content = fs.readFileSync(filePath, 'utf-8');
  const keys: TranslationKey[] = [];
  const seen = new Set<string>();
  const lines = content.split('\n');

  // استخراج خط به خط برای دقت بیشتر
  lines.forEach((line, index) => {
    // رد کردن خطوط با import, export, require
    if (/^\s*(import|export|require|const|let|var|function|return|if|else|for|while|switch|case|default|break|continue)/.test(line)) {
      return;
    }

    PATTERNS.forEach(({ regex, group }) => {
      const regexCopy = new RegExp(regex.source, 'g');
      let match;
      while ((match = regexCopy.exec(line)) !== null) {
        const text = match[group]?.trim();
        if (!text || text.length < 2) continue;
        
        // رد کردن متون با کلمات غیرضروری
        if (EXCLUDED_WORDS.some(word => text.toLowerCase() === word)) continue;
        if (/^[0-9\s]+$/.test(text)) continue;
        if (/^[A-Z]$/.test(text)) continue;
        if (text.length > 100) continue; // احتمالا جمله نیست
        
        // ساخت کلید یکتا
        const key = text
          .toLowerCase()
          .replace(/[^a-z0-9_]/g, '_')
          .replace(/_+/g, '_')
          .replace(/^_|_$/g, '')
          .substring(0, 60);
        
        if (!key) continue;
        const id = `${key}::${text}`;
        if (seen.has(id)) continue;
        seen.add(id);
        
        keys.push({
          key: key || `text_${keys.length}`,
          en: text,
          file: path.relative(process.cwd(), filePath),
          line: index + 1,
        });
      }
    });
  });

  return keys;
}

async function main() {
  const allKeys: TranslationKey[] = [];
  const files = glob.sync(SCAN_PATHS, { 
    cwd: process.cwd(), 
    absolute: true,
    ignore: ['**/node_modules/**', '**/.*/**', '**/*.test.ts', '**/*.spec.ts'],
  });

  console.log(`🔍 اسکن ${files.length} فایل...`);

  let totalFound = 0;
  for (const file of files) {
    const keys = extractTexts(file);
    totalFound += keys.length;
    allKeys.push(...keys);
    if (keys.length > 0) {
      console.log(`  - ${path.basename(file)}: ${keys.length} کلید`);
    }
  }

  // حذف تکراری‌ها
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

  fs.writeFileSync(
    path.join(messagesDir, 'extracted_all.json'),
    JSON.stringify(result, null, 2)
  );
  console.log(`\n✅ ${result.length} کلید استخراج شد`);

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
    path.join(messagesDir, 'fa.empty_all.json'),
    JSON.stringify(faJson, null, 2)
  );
  console.log(`✅ fa.empty_all.json ایجاد شد`);

  // نمایش ۲۰ کلید نمونه
  console.log(`\n📋 نمونه کلیدها:`);
  result.slice(0, 20).forEach(({ key, en, file }) => {
    console.log(`  - ${key}: "${en}" (${path.basename(file)})`);
  });

  console.log(`\n📋 مراحل بعدی:`);
  console.log(`  1. فایل messages/extracted_all.json را بررسی کنید`);
  console.log(`  2. فایل messages/fa.empty_all.json را به تیم ترجمه بدهید`);
}

main().catch(console.error);
