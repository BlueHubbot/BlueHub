import Link from "next/link";
import { useTranslations } from "next-intl";
import { Command } from "lucide-react";

import { RegisterForm } from "../../_components/register-form";
import { GoogleButton } from "../../_components/social-auth/google-button";

export default function RegisterV1() {
  const t = useTranslations();

  // دریافت هوشمند متون از دکشنری اختصاصی شما
  const textRegister = t("register") !== "register" ? t("register") : "ثبت نام";
  const textSubtitle = t("fill_in_your_details_below") !== "fill_in_your_details_below" ? t("fill_in_your_details_below") : "لطفاً اطلاعات خود را در زیر وارد کنید.";
  const textAlreadyHaveAccount = t("already_have_an_account") !== "already_have_an_account" ? t("already_have_an_account") : "قبلاً ثبت نام کرده‌اید؟";
  const textLogin = t("login") !== "login" ? t("login") : "ورود";
  const textWelcome = t("welcome") !== "welcome" ? t("welcome") : "خوش آمدید!";
  const textRightPlace = t("you_are_in_the_right_place") !== "you_are_in_the_right_place" ? t("you_are_in_the_right_place") : "درست آمده‌اید.";

  return (
    // استفاده از کدهای جهت‌دهی قالب برای راست‌چین کردن کل بدنه و محتوا
    <div className="flex h-dvh w-full flex-col lg:flex-row rtl:lg:flex-row-reverse text-right" dir="rtl">
      
      {/* بخش فرم ثبت نام - در حالت فارسی به صورت خودکار در موقعیت صحیح قرار می‌گیرد */}
      <div className="flex w-full items-center justify-center bg-background p-8 lg:w-2/3" dir="rtl">
        <div className="w-full max-w-md space-y-10 py-24 lg:py-32">
          <div className="space-y-4 text-center">
            <h2 className="text-2xl font-semibold tracking-tight">{textRegister}</h2>
            <div className="mx-auto max-w-xl text-muted-foreground text-sm">
              {textSubtitle}
            </div>
          </div>
          <div className="space-y-4 text-right">
            {/* فرم بومی‌سازی شده */}
            <RegisterForm />
            
            <GoogleButton className="w-full" variant="outline" />
            
            <p className="text-center text-muted-foreground text-xs pt-2">
              {textAlreadyHaveAccount}{" "}
              <Link prefetch={false} href="login" className="text-primary font-medium hover:underline">
                {textLogin}
              </Link>
            </p>
          </div>
        </div>
      </div>

      {/* بخش رنگی خوش‌آمدگویی - در حالت فارسی به سمت دیگر منتقل می‌شود */}
      <div className="hidden bg-primary lg:block lg:w-1/3">
        <div className="flex h-full flex-col items-center justify-center p-12 text-center">
          <div className="space-y-6">
            <Command className="mx-auto size-12 text-primary-foreground" />
            <div className="space-y-2">
              <h1 className="font-light text-5xl text-primary-foreground">{textWelcome}</h1>
              <p className="text-primary-foreground/80 text-xl">{textRightPlace}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
