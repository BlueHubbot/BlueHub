import {
  DM_Sans,
  Figtree,
  Geist,
  Geist_Mono,
  Inter,
  JetBrains_Mono,
  Lora,
  Merriweather,
  Noto_Sans,
  Noto_Serif,
  Nunito_Sans,
  Outfit,
  Playfair_Display,
  Public_Sans,
  Raleway,
  Roboto,
  Roboto_Slab,
  Vazirmatn,
} from "next/font/google";

import { GeistPixelSquare } from "geist/font/pixel";

// --- فونت‌های انگلیسی ---
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const notoSans = Noto_Sans({ subsets: ["latin"], variable: "--font-noto-sans" });
const roboto = Roboto({ subsets: ["latin"], weight: ["400", "500", "700"], variable: "--font-roboto" });
const geist = Geist({ subsets: ["latin"], variable: "--font-geist" });
const outfit = Outfit({ subsets: ["latin"], variable: "--font-outfit" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });
const dmSans = DM_Sans({ subsets: ["latin"], variable: "--font-dm-sans" });
const nunitoSans = Nunito_Sans({ subsets: ["latin"], variable: "--font-nunito-sans" });
const figtree = Figtree({ subsets: ["latin"], variable: "--font-figtree" });
const raleway = Raleway({ subsets: ["latin"], variable: "--font-raleway" });
const publicSans = Public_Sans({ subsets: ["latin"], variable: "--font-public-sans" });
const jetBrainsMono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains-mono" });
const notoSerif = Noto_Serif({ subsets: ["latin"], variable: "--font-noto-serif" });
const robotoSlab = Roboto_Slab({ subsets: ["latin"], variable: "--font-roboto-slab" });
const merriweather = Merriweather({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-merriweather" });
const lora = Lora({ subsets: ["latin"], variable: "--font-lora" });
const playfairDisplay = Playfair_Display({ subsets: ["latin"], variable: "--font-playfair-display" });

// --- فونت استاندارد گوگل برای فارسی ---
// --- فونت استاندارد گوگل برای فارسی با ساب‌ست عربی ---
const vazirmatn = Vazirmatn({ 
  subsets: ["arabic"], 
  variable: "--font-vazirmatn" 
});

// ... کدهای ایمپورت قبلی و فونت‌های انگلیسی بدون تغییر باقی بمانند ...

// تابع کمکی برای ساختار فونت‌های سیستمی یا لود شده در بدنه
const createSystemFont = (variableName: string) => ({
  variable: variableName,
  className: "",
  style: { fontFamily: "sans-serif" },
});

export const fontRegistry = {
  // --- فونت‌های انگلیسی ---
  geist: { label: "Geist", font: geist, isPersian: false },
  inter: { label: "Inter", font: inter, isPersian: false },
  notoSans: { label: "Noto Sans", font: notoSans, isPersian: false },
  nunitoSans: { label: "Nunito Sans", font: nunitoSans, isPersian: false },
  figtree: { label: "Figtree", font: figtree, isPersian: false },
  roboto: { label: "Roboto", font: roboto, isPersian: false },
  raleway: { label: "Raleway", font: raleway, isPersian: false },
  dmSans: { label: "DM Sans", font: dmSans, isPersian: false },
  publicSans: { label: "Public Sans", font: publicSans, isPersian: false },
  outfit: { label: "Outfit", font: outfit, isPersian: false },
  geistMono: { label: "Geist Mono", font: geistMono, isPersian: false },
  geistPixelSquare: { label: "Geist Pixel Square", font: GeistPixelSquare, isPersian: false },
  jetBrainsMono: { label: "JetBrains Mono", font: jetBrainsMono, isPersian: false },
  notoSerif: { label: "Noto Serif", font: notoSerif, isPersian: false },
  robotoSlab: { label: "Roboto Slab", font: robotoSlab, isPersian: false },
  merriweather: { label: "Merriweather", font: merriweather, isPersian: false },
  lora: { label: "Lora", font: lora, isPersian: false },
  playfairDisplay: { label: "Playfair Display", font: playfairDisplay, isPersian: false },

  // --- لیست کامل ۷ فونت برتر و استاندارد فارسی ---
  vazirmatn: { label: "وزیرمتن (Vazirmatn)", font: vazirmatn, isPersian: true },
  systemTahoma: { label: "تاهما (Tahoma)", font: createSystemFont("--font-tahoma"), isPersian: true },
  shabnam: { label: "شبنم (Shabnam)", font: createSystemFont("--font-shabnam"), isPersian: true },
  samim: { label: "صمیم (Samim)", font: createSystemFont("--font-samim"), isPersian: true },
  sahel: { label: "ساحل (Sahel)", font: createSystemFont("--font-sahel"), isPersian: true },
  gandom: { label: "گندم (Gandom)", font: createSystemFont("--font-gandom"), isPersian: true },
  systemSans: { label: "فونت پیش‌فرض سیستم", font: createSystemFont("--font-sans-fa"), isPersian: true },
} as const;

// ... بقیه خطوط انتخابی اتوماتیک پایین فایل دست‌نخورده بماند ...
export type FontKey = keyof typeof fontRegistry;

export const fontKeys = Object.keys(fontRegistry) as FontKey[];

export const fontVars = Object.values(fontRegistry)
  .map(({ font }) => font.variable)
  .join(" ");

export const fontOptions = fontKeys.map((key) => ({
  key,
  label: fontRegistry[key].label,
  isPersian: (fontRegistry[key] as any).isPersian,
}));