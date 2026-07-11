import fs from 'fs';
import path from 'path';
import { glob } from 'glob';

// فایل‌هایی که باید بررسی شوند (همه صفحات و کامپوننت‌ها)
const SCAN_PATHS = [
  'src/app/**/*.tsx',
  'src/app/**/*.ts',
  'src/components/**/*.tsx',
  'src/components/**/*.ts',
  'src/navigation/**/*.ts',
  'src/lib/**/*.ts',
  'src/hooks/**/*.ts',
  'src/stores/**/*.ts',
  '!src/**/*.test.ts',
  '!src/**/*.spec.ts',
  '!src/**/layout.tsx', // layout را جدا حساب می‌کنیم
  '!src/**/loading.tsx',
  '!src/**/not-found.tsx',
];

interface FileStats {
  file: string;
  hardcodedTexts: number;
  needsTranslation: boolean;
  type: 'page' | 'component' | 'navigation' | 'lib' | 'other';
}

function countHardcodedTexts(content: string): number {
  // الگوهای متون hardcoded
  const patterns = [
    />([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})</g, // JSX text
    /placeholder=["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g,
    /label=["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g,
    /title=["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g,
    /aria-label=["']([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})["']/g,
    /<h[1-6][^>]*>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/h[1-6]>/g,
    /<Button[^>]*>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/Button>/g,
    /<p[^>]*>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/p>/g,
    /<span[^>]*>([A-Za-z][A-Za-z0-9\s\.,!?\-:;()"']{2,})<\/span>/g,
  ];

  let count = 0;
  const lines = content.split('\n');
  lines.forEach((line) => {
    // رد کردن خطوط با useTranslations یا t(
    if (line.includes('useTranslations') || line.includes('t(')) return;
    // رد کردن import/export
    if (/^\s*(import|export|const|let|var|function|return)/.test(line)) return;

    patterns.forEach((pattern) => {
      const matches = line.match(pattern);
      if (matches) {
        // فیلتر کردن کلمات غیرضروری
        const valid = matches.filter((m) => {
          const text = m.replace(/<[^>]*>/g, '').trim();
          return text.length > 2 && !/^[0-9\s]+$/.test(text);
        });
        count += valid.length;
      }
    });
  });

  return count;
}

async function main() {
  const files = glob.sync(SCAN_PATHS, {
    cwd: process.cwd(),
    absolute: true,
    ignore: ['**/node_modules/**', '**/.*/**'],
  });

  const stats: FileStats[] = [];
  let totalHardcoded = 0;
  let filesWithHardcoded = 0;

  console.log(`🔍 اسکن ${files.length} فایل...\n`);

  for (const file of files) {
    const content = fs.readFileSync(file, 'utf-8');
    const hardcodedTexts = countHardcodedTexts(content);
    const relativePath = path.relative(process.cwd(), file);

    // تعیین نوع فایل
    let type: FileStats['type'] = 'other';
    if (relativePath.includes('/app/')) type = 'page';
    else if (relativePath.includes('/components/')) type = 'component';
    else if (relativePath.includes('/navigation/')) type = 'navigation';
    else if (relativePath.includes('/lib/')) type = 'lib';

    const needsTranslation = hardcodedTexts > 0;

    if (needsTranslation) {
      filesWithHardcoded++;
      totalHardcoded += hardcodedTexts;
    }

    stats.push({
      file: relativePath,
      hardcodedTexts,
      needsTranslation,
      type,
    });
  }

  // مرتب‌سازی بر اساس بیشترین تعداد متون
  stats.sort((a, b) => b.hardcodedTexts - a.hardcodedTexts);

  // نمایش آمار کلی
  console.log('📊 آمار کلی:');
  console.log(`  - کل فایل‌های اسکن شده: ${files.length}`);
  console.log(`  - فایل‌های دارای متن hardcoded: ${filesWithHardcoded}`);
  console.log(`  - کل متون hardcoded: ${totalHardcoded}`);
  console.log('');

  // نمایش تفکیک بر اساس نوع
  const pageFiles = stats.filter((s) => s.type === 'page' && s.needsTranslation);
  const componentFiles = stats.filter((s) => s.type === 'component' && s.needsTranslation);
  const navigationFiles = stats.filter((s) => s.type === 'navigation' && s.needsTranslation);
  const libFiles = stats.filter((s) => s.type === 'lib' && s.needsTranslation);

  console.log('📁 تفکیک بر اساس نوع:');
  console.log(`  - صفحات (pages): ${pageFiles.length} فایل`);
  console.log(`  - کامپوننت‌ها (components): ${componentFiles.length} فایل`);
  console.log(`  - ناوبری (navigation): ${navigationFiles.length} فایل`);
  console.log(`  - کتابخانه‌ها (lib): ${libFiles.length} فایل`);
  console.log('');

  // نمایش ۲۰ فایل با بیشترین متون
  console.log('📋 ۲۰ فایل با بیشترین متون hardcoded:');
  stats
    .filter((s) => s.needsTranslation)
    .slice(0, 20)
    .forEach((s, i) => {
      console.log(`  ${i + 1}. ${path.basename(s.file)}: ${s.hardcodedTexts} متن (${s.type})`);
    });

  // پیشنهاد اولویت
  console.log('\n🎯 پیشنهاد اولویت ترجمه:');
  console.log('  1. صفحات اصلی (dashboard, users, infrastructure, invoice)');
  console.log('  2. کامپوننت‌های عمومی (sidebar, header, modals)');
  console.log('  3. صفحات فرعی (analytics, finance, crm)');
  console.log('  4. کتابخانه‌ها و ابزارها');

  // ذخیره گزارش کامل
  const reportPath = path.join(process.cwd(), 'messages/i18n-report.json');
  fs.writeFileSync(reportPath, JSON.stringify({ files: stats, summary: { totalFiles: files.length, filesWithHardcoded, totalHardcoded } }, null, 2));
  console.log(`\n✅ گزارش کامل ذخیره شد: messages/i18n-report.json`);
}

main().catch(console.error);
