"use client";

import { useTranslations } from "next-intl";
import { ArrowLeft, ArrowRight, ArrowUpRight, Star } from "lucide-react";

import { Avatar, AvatarFallback, AvatarGroup, AvatarGroupCount } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const customerInitials = ["EM", "OW", "NO", "MM"] as const;

export function CustomerReviews() {
  const t = useTranslations("Ecommerce.reviews");

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="font-normal text-muted-foreground text-sm">{t("title")}</CardTitle>
        <CardDescription className="text-foreground text-xl leading-none tracking-tight">
          {t("rating")}
        </CardDescription>
        <CardAction>
          <ArrowUpRight className="size-4" />
        </CardAction>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        <div className="rounded-lg bg-muted p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex flex-col gap-2">
              <div className="flex gap-0.5 text-foreground">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="size-3.5 fill-current" />
                ))}
              </div>
              <div>
                <div className="font-medium text-sm">{t("reviewer_name")}</div>
                <p className="mt-2 line-clamp-3 min-h-[4.5em] text-muted-foreground text-sm">
                  {t("review_text")}
                </p>
              </div>
            </div>

            <div className="flex gap-1">
              <Button aria-label={t("prev")} size="icon-xs" variant="outline">
                <ArrowLeft />
              </Button>
              <Button aria-label={t("next")} size="icon-xs" variant="outline">
                <ArrowRight />
              </Button>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between gap-4 rounded-lg border px-4 py-3">
          <div className="min-w-0">
            <div className="font-medium text-sm">{t("total_reviews")}</div>
            <div className="line-clamp-2 min-h-[3em] text-muted-foreground text-xs">{t("reviews_this_month")}</div>
          </div>

          <AvatarGroup>
            {customerInitials.map((initials) => (
              <Avatar key={initials}>
                <AvatarFallback>{initials}</AvatarFallback>
              </Avatar>
            ))}
            <AvatarGroupCount>+42</AvatarGroupCount>
          </AvatarGroup>
        </div>
      </CardContent>
    </Card>
  );
}