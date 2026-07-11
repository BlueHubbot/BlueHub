import { getRequestConfig } from 'next-intl/server';
import { cookies } from 'next/headers';

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  // خواندن مستقیم نام کوکی که سیستم ترجیحات شما ذخیره می‌کند (به نام فیلد یا لوکال استاندارد)
  const locale = cookieStore.get('data-locale')?.value || cookieStore.get('NEXT_LOCALE')?.value || 'fa';

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});