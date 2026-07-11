import { createStore } from "zustand/vanilla";

import { applyPreference } from "@/lib/preferences/preference-runtime";
import {
  PREFERENCE_DEFAULTS,
  PREFERENCE_KEYS,
  type PreferenceKey,
  type PreferenceValueMap,
} from "@/lib/preferences/preferences-config";
import { persistPreference } from "@/lib/preferences/preferences-storage";
import type { ResolvedThemeMode } from "@/lib/preferences/theme";

export type PreferencesState = {
  values: PreferenceValueMap;
  resolvedThemeMode: ResolvedThemeMode;
  isSynced: boolean;
  setPreference: <K extends PreferenceKey>(key: K, value: PreferenceValueMap[K]) => void;
  resetPreferences: () => void;
};

export const createPreferencesStore = (initialValues: Partial<PreferenceValueMap> = {}) => {
  const values: PreferenceValueMap = {
    ...PREFERENCE_DEFAULTS,
    ...initialValues,
  };

  return createStore<PreferencesState>()((set) => ({
    values,
    resolvedThemeMode: values.theme_mode === "dark" ? "dark" : "light",
    isSynced: false,

    // تبدیل تابع به async برای مهار کامل فرآیند ذخیره‌سازی پیش از رفرش
    setPreference: async (key, value) => {
      const resolvedThemeMode = applyPreference(key, value);

      set((state) => {
        const nextValues = {
          ...state.values,
          [key]: value,
        } as PreferenceValueMap;

        // اگر لوکال تغییر کرد، جهت لایوت متناظر با آن را هم در وضعیت استور ست کن
        if (key === "locale") {
          (nextValues as any).direction = value === "fa" ? "rtl" : "ltr";
        }

        return {
          values: nextValues,
          ...(resolvedThemeMode ? { resolvedThemeMode } : {}),
        };
      });

      // منتظر بمان تا ترجیحات کاملاً در دیسک/کوکی پایدار شوند
      await persistPreference(key, value);

      if (key === "locale") {
        const nextDir = value === "fa" ? "rtl" : "ltr";
        
        // ذخیره قطعی کلید دایرکشن برای لایه سرور و لایوت اصلی
        await persistPreference("direction" as any, nextDir);

        // ست کردن کوکی استاندارد سیستم ترجمه
        document.cookie = `NEXT_LOCALE=${value}; path=/; max-age=31536000; SameSite=Lax`;

        // اعمال آنی روی تگ HTML برای جلوگیری از پرش تصویر لحظه‌ای
        document.documentElement.setAttribute("lang", value);
        document.documentElement.setAttribute("dir", nextDir);

        // اکنون با خیال راحت رفرش کن چون داده‌ها کاملاً هارد-سیو شده‌اند
        window.location.reload();
      }
    },

    resetPreferences: () => {
      let resolvedThemeMode: ResolvedThemeMode = "light";

      for (const key of PREFERENCE_KEYS) {
        const value = PREFERENCE_DEFAULTS[key];
        const resolved = applyPreference(key, value);

        if (resolved) resolvedThemeMode = resolved;
        void persistPreference(key, value);
      }

      set({
        values: { ...PREFERENCE_DEFAULTS },
        resolvedThemeMode,
      });
    },
  }));
};