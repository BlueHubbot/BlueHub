"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

// ============================================
// 1. Types
// ============================================
interface I18nContextType {
  lang: "fa" | "en";
  setLang: (lang: "fa" | "en") => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  dir: "rtl" | "ltr";
}

// ============================================
// 2. Context
// ============================================
const I18nContext = createContext<I18nContextType>({
  lang: "fa",
  setLang: () => {},
  t: (key: string) => key,
  dir: "rtl",
});

// ============================================
// 3. Translations (موقت - بعداً از فایل JSON میخونه)
// ============================================
const translations: Record<string, Record<string, string>> = {
  fa: {
    // General
    "app.title": "BlueHub",
    "app.dashboard": "داشبورد",
    "app.users": "کاربران",
    "app.products": "محصولات",
    "app.modules": "ماژول‌ها",
    "app.tenants": "تیننت‌ها",
    "app.abuse": "تخلفات",
    "app.logs": "لاگ‌ها",
    "app.settings": "تنظیمات",
    "app.login": "ورود",
    "app.logout": "خروج",
    "app.search": "جستجو...",
    
    // Dashboard
    "dashboard.title": "داشبورد مدیریت",
    "dashboard.totalUsers": "کل کاربران",
    "dashboard.activeServices": "سرویس‌های فعال",
    "dashboard.totalRevenue": "درآمد کل",
    "dashboard.modules": "ماژول‌ها",
    "dashboard.recentActivity": "فعالیت‌های اخیر",
    
    // Users
    "users.title": "مدیریت کاربران",
    "users.email": "ایمیل",
    "users.fullName": "نام کامل",
    "users.role": "نقش",
    "users.status": "وضعیت",
    "users.active": "فعال",
    "users.suspended": "تعلیق شده",
    "users.createdAt": "تاریخ ثبت",
    "users.actions": "عملیات",
    
    // Products
    "products.title": "مدیریت محصولات",
    "products.name": "نام محصول",
    "products.price": "قیمت",
    "products.cycle": "دوره صورتحساب",
    "products.module": "ماژول",
    
    // Modules
    "modules.title": "مدیریت ماژول‌ها",
    "modules.enabled": "فعال",
    "modules.disabled": "غیرفعال",
    "modules.version": "نسخه",
    "modules.flags": "پرچم‌ها",
    
    // Tenants
    "tenants.title": "مدیریت تیننت‌ها",
    "tenants.name": "نام تیننت",
    "tenants.domain": "دامنه",
    "tenants.branding": "برندینگ",
    
    // Abuse
    "abuse.title": "گزارش‌های تخلف",
    "abuse.type": "نوع تخلف",
    "abuse.severity": "شدت",
    "abuse.status": "وضعیت",
    
    // Logs
    "logs.title": "لاگ‌های سیستمی",
    "logs.action": "عملیات",
    "logs.user": "کاربر",
    "logs.timestamp": "زمان",
    
    // Settings
    "settings.title": "تنظیمات",
    "settings.branding": "برندینگ",
    "settings.primaryColor": "رنگ اصلی",
    "settings.secondaryColor": "رنگ ثانویه",
    "settings.brandName": "نام برند",
    "settings.logo": "لوگو",
    "settings.language": "زبان",
    "settings.theme": "تم",
    "settings.save": "ذخیره تغییرات",
    "settings.cancel": "انصراف",
  },
  en: {
    // General
    "app.title": "BlueHub",
    "app.dashboard": "Dashboard",
    "app.users": "Users",
    "app.products": "Products",
    "app.modules": "Modules",
    "app.tenants": "Tenants",
    "app.abuse": "Abuse",
    "app.logs": "Logs",
    "app.settings": "Settings",
    "app.login": "Login",
    "app.logout": "Logout",
    "app.search": "Search...",
    
    // Dashboard
    "dashboard.title": "Admin Dashboard",
    "dashboard.totalUsers": "Total Users",
    "dashboard.activeServices": "Active Services",
    "dashboard.totalRevenue": "Total Revenue",
    "dashboard.modules": "Modules",
    "dashboard.recentActivity": "Recent Activity",
    
    // Users
    "users.title": "User Management",
    "users.email": "Email",
    "users.fullName": "Full Name",
    "users.role": "Role",
    "users.status": "Status",
    "users.active": "Active",
    "users.suspended": "Suspended",
    "users.createdAt": "Created At",
    "users.actions": "Actions",
    
    // Products
    "products.title": "Product Management",
    "products.name": "Product Name",
    "products.price": "Price",
    "products.cycle": "Billing Cycle",
    "products.module": "Module",
    
    // Modules
    "modules.title": "Module Management",
    "modules.enabled": "Enabled",
    "modules.disabled": "Disabled",
    "modules.version": "Version",
    "modules.flags": "Flags",
    
    // Tenants
    "tenants.title": "Tenant Management",
    "tenants.name": "Tenant Name",
    "tenants.domain": "Domain",
    "tenants.branding": "Branding",
    
    // Abuse
    "abuse.title": "Abuse Reports",
    "abuse.type": "Type",
    "abuse.severity": "Severity",
    "abuse.status": "Status",
    
    // Logs
    "logs.title": "System Logs",
    "logs.action": "Action",
    "logs.user": "User",
    "logs.timestamp": "Timestamp",
    
    // Settings
    "settings.title": "Settings",
    "settings.branding": "Branding",
    "settings.primaryColor": "Primary Color",
    "settings.secondaryColor": "Secondary Color",
    "settings.brandName": "Brand Name",
    "settings.logo": "Logo",
    "settings.language": "Language",
    "settings.theme": "Theme",
    "settings.save": "Save Changes",
    "settings.cancel": "Cancel",
  },
};

// ============================================
// 4. Provider
// ============================================
export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<"fa" | "en">("fa");
  const [dir, setDir] = useState<"rtl" | "ltr">("rtl");

  useEffect(() => {
    // Load saved language from localStorage
    const saved = localStorage.getItem("admin_lang") as "fa" | "en" | null;
    if (saved && (saved === "fa" || saved === "en")) {
      setLangState(saved);
      setDir(saved === "fa" ? "rtl" : "ltr");
    } else {
      // Default to Persian for RTL
      setLangState("fa");
      setDir("rtl");
    }
  }, []);

  const setLang = (newLang: "fa" | "en") => {
    setLangState(newLang);
    setDir(newLang === "fa" ? "rtl" : "ltr");
    localStorage.setItem("admin_lang", newLang);
    
    // Update HTML attributes
    if (typeof document !== "undefined") {
      document.documentElement.lang = newLang;
      document.documentElement.dir = newLang === "fa" ? "rtl" : "ltr";
    }
  };

  const t = (key: string, params?: Record<string, string | number>): string => {
    let text = translations[lang]?.[key] || key;
    
    // Replace parameters like {{name}}
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        text = text.replace(`{{${k}}}`, String(v));
      }
    }
    
    return text;
  };

  return (
    <I18nContext.Provider value={{ lang, setLang, t, dir }}>
      {children}
    </I18nContext.Provider>
  );
}

// ============================================
// 5. Hook
// ============================================
export function useI18n() {
  return useContext(I18nContext);
}