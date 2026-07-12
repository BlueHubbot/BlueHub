"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { sidebarItems } from "@/navigation/sidebar/sidebar-items";
import { Button } from "@/components/ui/button";

export function SearchDialog() {
  const t = useTranslations();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const filteredItems = sidebarItems.flatMap((group) =>
    group.items.flatMap((item) => {
      const title = t(item.titleKey);
      const matches = title.toLowerCase().includes(query.toLowerCase());
      if (!matches) return [];
      return [
        {
          id: item.id,
          title: title,
          url: "url" in item ? item.url : undefined,
          group: t(group.labelKey),
        },
      ];
    })
  );

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="relative w-full justify-start text-muted-foreground rtl:justify-start"
        >
          <Search className="size-4 shrink-0 rtl:ml-2 ltr:mr-2" />
          <span className="hidden lg:inline-flex">{t("search")}</span>
          <kbd className="pointer-events-none absolute right-2 hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex rtl:left-2 rtl:right-auto">
            <span className="text-xs">⌘</span>K
          </kbd>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl p-0">
        <DialogHeader className="sr-only">
          <DialogTitle>{t("search")}</DialogTitle>
        </DialogHeader>
        <Command className="rounded-lg border shadow-md">
          <CommandInput
            placeholder={t("search_placeholder")}
            value={query}
            onValueChange={setQuery}
            className="rtl:text-right"
          />
          <CommandList>
            <CommandEmpty>{t("no_results")}</CommandEmpty>
            <CommandGroup heading={t("menus")}>
              {filteredItems.map((item) => (
                <CommandItem
                  key={item.id}
                  onSelect={() => {
                    if (item.url) {
                      window.location.href = item.url;
                    }
                    setOpen(false);
                  }}
                  className="rtl:flex-row-reverse rtl:justify-between"
                >
                  <span>{item.title}</span>
                  <span className="ml-auto text-xs text-muted-foreground rtl:ml-0">
                    {item.group}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  );
}