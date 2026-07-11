'use client';

import { useTranslations } from 'next-intl';
import { LoginForm } from '../../_components/login-form';

export default function LoginPage() {
  const t = useTranslations();

  // نگاشت هوشمند کلیدها بر اساس دکشنری واقعی شما برای هماهنگی ۱۰۰٪
  const pageTitle = t('login_panel') !== 'login_panel' ? t('login_panel') : (t('login') || 'ورود');
  const pageSubtitle = t('login_to_your_account') !== 'login_to_your_account' ? t('login_to_your_account') : 'BlueHub Admin Panel';

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-md space-y-6 rounded-lg border bg-card p-8 shadow-sm">
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold tracking-tight">{pageTitle}</h2>
          <p className="text-sm text-muted-foreground">{pageSubtitle}</p>
        </div>

        {/* تزریق فرم استاندارد و بومی‌سازی شده بدون هاردکد */}
        <LoginForm />
      </div>
    </div>
  );
}
