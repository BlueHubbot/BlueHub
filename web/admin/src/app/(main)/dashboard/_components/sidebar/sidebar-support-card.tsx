import Link from "next/link";
import { useTranslations } from "next-intl";
import { siX } from "simple-icons";

import { SimpleIcon } from "@/components/simple-icon";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function SidebarSupportCard() {
  const t = useTranslations(); // استفاده از سیستم نیتیو next-intl پروژه شما

  return (
    <Card size="sm" className="overflow-hidden shadow-none group-data-[collapsible=icon]:hidden">
      <CardHeader className="min-w-0 px-4">
        {/* ترجمه عنوان کارت */}
        <CardTitle className="truncate text-sm">
          {t("looking_for_something_more")}
        </CardTitle>
        
        {/* ترجمه توضیحات کارت */}
        <CardDescription className="line-clamp-2">
          {t("open_an_issue_or_do_reach_out_to_me_on")}&nbsp;
          <Link
            href="https://x.com/BlueHub"
            target="_blank"
            rel="noreferrer"
            aria-label="Reach out on X"
            className="inline-flex items-center text-foreground"
          >
            <SimpleIcon icon={siX} aria-hidden className="size-3 fill-current" />
          </Link>
          .
        </CardDescription>
      </CardHeader>
    </Card>
  );
}