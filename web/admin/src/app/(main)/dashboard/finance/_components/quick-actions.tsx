"use client";

import { useTranslations } from "next-intl";
import {
  Banknote,
  ChevronLeft,
  Droplet,
  History,
  Lightbulb,
  MoreHorizontal,
  QrCode,
  SendHorizontal,
  Smartphone,
} from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { InputGroup, InputGroupAddon, InputGroupInput, InputGroupText } from "@/components/ui/input-group";

const contacts = [
  { id: 1, initials: "AR" },
  { id: 2, initials: "SC" },
  { id: 3, initials: "MJ" },
  { id: 4, initials: "ED" },
];

export function QuickActions() {
  const t = useTranslations("Finance.quick_actions");

  const shortcuts = [
    { id: 1, label: t("shortcuts.qr"), icon: QrCode },
    { id: 2, label: t("shortcuts.transfer"), icon: SendHorizontal },
    { id: 3, label: t("shortcuts.bill"), icon: Banknote },
    { id: 4, label: t("shortcuts.history"), icon: History },
    { id: 5, label: t("shortcuts.mobile"), icon: Smartphone },
    { id: 6, label: t("shortcuts.electricity"), icon: Lightbulb },
    { id: 7, label: t("shortcuts.water"), icon: Droplet },
    { id: 8, label: t("shortcuts.more"), icon: MoreHorizontal },
  ];

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="font-normal">{t("quick_transfer")}</CardTitle>
          <CardAction>
            <div className="flex items-center gap-1">
              <div className="flex space-x-reverse -space-x-2">
                {contacts.map((contact) => (
                  <Avatar key={contact.id} className="size-7 border-2 border-background">
                    <AvatarFallback className="text-[10px]">{contact.initials}</AvatarFallback>
                  </Avatar>
                ))}
              </div>
              <ChevronLeft className="size-4" />
            </div>
          </CardAction>
        </CardHeader>
        <CardContent>
          <Field orientation="horizontal">
            <InputGroup>
              <InputGroupAddon>
                <InputGroupText>$</InputGroupText>
              </InputGroupAddon>
              <InputGroupInput placeholder="0.00" />
              <InputGroupAddon align="inline-end">
                <InputGroupText>USD</InputGroupText>
              </InputGroupAddon>
            </InputGroup>
            <Button>{t("send")}</Button>
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="font-normal">{t("shortcuts_title")}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4">
            {shortcuts.map((shortcut) => {
              const Icon = shortcut.icon;
              return (
                <div key={shortcut.id} className="flex flex-col items-center gap-2.5">
                  <Button variant="outline" className="size-12 rounded-full">
                    <Icon className="size-5" />
                  </Button>
                  <span className="text-center text-muted-foreground text-xs">{shortcut.label}</span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}