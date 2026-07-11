import type { ReactNode } from 'react';
import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { fontVars } from '@/lib/fonts/registry';
import { PREFERENCE_DEFAULTS } from '@/lib/preferences/preferences-config';
import { PreferencesStoreProvider } from '@/stores/preferences/preferences-provider';
import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import { cookies } from 'next/headers';
import Script from 'next/script';

import './globals.css';

export default async function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  const cookieStore = await cookies();

  // خواندن وضعیت‌های ذخیره شده در کوکی سرور
  const locale = cookieStore.get('NEXT_LOCALE')?.value || 'fa';
  const contentLayout = cookieStore.get('data-content-layout')?.value || 'centered';
  const themeMode = cookieStore.get('data-theme-mode')?.value || 'light';
  const themePreset = cookieStore.get('data-theme-preset')?.value || 'default';
  const font = cookieStore.get('data-font')?.value || 'vazirmatn';

  const messages = await getMessages();
  const direction = locale === 'en' ? 'ltr' : 'rtl';

  // ترکیب مقادیر پیش‌فرض با مقادیر خوانده شده از کوکی
  const initialPreferences = {
    ...PREFERENCE_DEFAULTS,
    locale: locale as "en" | "fa",
    content_layout: contentLayout as any,
    theme_mode: themeMode as any,
    theme_preset: themePreset as any,
    font: font as any,
    direction: direction as any
  };

  return (
    <html
      lang={locale}
      dir={direction}
      data-theme-mode={themeMode}
      data-theme-preset={themePreset}
      data-font={font}
      data-content-layout={contentLayout}
      className={themeMode === 'dark' ? 'dark' : ''}
      suppressHydrationWarning
    >
      <head>
        {/* اسکریپت اصلاح‌شده و بهینه بدون ایجاد لوپ بی‌نهایت در ساختار مرورگر */}
        {locale === 'fa' && (
          <Script id="farsi-digits-interceptor" strategy="beforeInteractive">
            {`
              (function() {
                const p = ['۰','۱','۲','۳','۴','۵','۶','۷','۸','۹'];
                const config = { childList: true, subtree: true, characterData: true };
                
                function toFarsi(text) {
                  return text.replace(/[0-9]/g, function(w) { return p[parseInt(w)]; });
                }

                function walk(node) {
                  if (node.nodeType === 3) {
                    const replaced = toFarsi(node.nodeValue);
                    if (node.nodeValue !== replaced) {
                      node.nodeValue = replaced;
                    }
                  } else if (node.nodeType === 1 && node.nodeName !== 'SCRIPT' && node.nodeName !== 'STYLE') {
                    for (let i = 0; i < node.childNodes.length; i++) {
                      walk(node.childNodes[i]);
                    }
                  }
                }

                const observer = new MutationObserver(function(mutations) {
                  // غیرفعال کردن موقت برای جلوگیری از ایجاد لوپ در اثر تغییرات خودِ تابع
                  observer.disconnect();
                  
                  mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList') {
                      mutation.addedNodes.forEach(function(node) { walk(node); });
                    } else if (mutation.type === 'characterData') {
                      const replaced = toFarsi(mutation.target.nodeValue);
                      if (mutation.target.nodeValue !== replaced) {
                        mutation.target.nodeValue = replaced;
                      }
                    }
                  });
                  
                  // فعال‌سازی مجدد رصد تغییرات DOM
                  observer.observe(document.body, config);
                });

                document.addEventListener("DOMContentLoaded", function() {
                  walk(document.body);
                  observer.observe(document.body, config);
                });
              })();
            `}
          </Script>
        )}
      </head>
      <body className={`${fontVars} min-h-screen antialiased`} suppressHydrationWarning>
        <NextIntlClientProvider messages={messages}>
          <PreferencesStoreProvider initialValues={initialPreferences}>
            <TooltipProvider>
              {children}
              <Toaster />
            </TooltipProvider>
          </PreferencesStoreProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}