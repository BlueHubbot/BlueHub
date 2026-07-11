"use client";

import { Settings } from "lucide-react";
import { useShallow } from "zustand/react/shallow";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { type FontKey, fontOptions } from "@/lib/fonts/registry";
import type { ContentLayout, NavbarStyle, SidebarCollapsible, SidebarVariant } from "@/lib/preferences/layout";
import { THEME_PRESET_OPTIONS, type ThemeMode, type ThemePreset } from "@/lib/preferences/theme";
import { usePreferencesStore } from "@/stores/preferences/preferences-provider";

export function LayoutControls() {
  const t = useTranslations();
  
  const { values, resolvedThemeMode, setPreference, resetPreferences } = usePreferencesStore(
    useShallow((state) => ({
      values: state.values,
      resolvedThemeMode: state.resolvedThemeMode,
      setPreference: state.setPreference,
      resetPreferences: state.resetPreferences,
    })),
  );

  const {
    theme_mode: themeMode,
    theme_preset: themePreset,
    content_layout: contentLayout,
    navbar_style: navbarStyle,
    sidebar_variant: variant,
    sidebar_collapsible: collapsible,
    font,
    locale,
  } = values;

  const currentLang = typeof window !== "undefined" ? (document.documentElement.getAttribute("lang") as "en" | "fa") || locale || "fa" : locale || "fa";

  const onThemePresetChange = (preset: ThemePreset) => {
    setPreference("theme_preset", preset);
  };

  const onThemeModeChange = (mode: ThemeMode | "") => {
    if (!mode) return;
    setPreference("theme_mode", mode);
  };

  const onContentLayoutChange = (layout: ContentLayout | "") => {
    if (!layout) return;
    setPreference("content_layout", layout);
  };

  const onNavbarStyleChange = (style: NavbarStyle | "") => {
    if (!style) return;
    setPreference("navbar_style", style);
  };

  const onSidebarStyleChange = (value: SidebarVariant | "") => {
    if (!value) return;
    setPreference("sidebar_variant", value);
  };

  const onSidebarCollapseModeChange = (value: SidebarCollapsible | "") => {
    if (!value) return;
    setPreference("sidebar_collapsible", value);
  };

  const onFontChange = (value: FontKey | "") => {
    if (!value) return;
    setPreference("font", value);
  };

  const onLangChange = (lang: "en" | "fa") => {
    if (!lang) return;

    const nextDir = lang === "fa" ? "rtl" : "ltr";

    document.cookie = `NEXT_LOCALE=${lang}; path=/; max-age=31536000; SameSite=Lax`;
    document.cookie = `data-locale=${lang}; path=/; max-age=31536000; SameSite=Lax`;

    document.documentElement.setAttribute("lang", lang);
    document.documentElement.setAttribute("dir", nextDir);

    try {
      setPreference("locale", lang);
      setPreference("direction" as any, nextDir);
    } catch (e) {
      console.log(e);
    }

    window.location.reload();
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button size="icon">
          <Settings />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-64 max-h-[80vh] overflow-y-auto">
        <div className="flex flex-col gap-5">
          <div className="space-y-1.5">
            <h4 className="font-medium text-sm leading-none">
              {t("panel_settings_title")}
            </h4>
            <p className="text-muted-foreground text-xs">
              {t("panel_settings_desc")}
            </p>
          </div>
          <div className="space-y-3 **:data-[slot=toggle-group]:w-full **:data-[slot=toggle-group-item]:flex-1 **:data-[slot=toggle-group-item]:text-xs">

            {/* بخش تغییر زبان و لوکال */}
            <div className="space-y-1">
              <Label className="font-medium text-xs">{t("system_language")}</Label>
              <ToggleGroup
                size="sm"
                spacing={0}
                variant="outline"
                type="single"
                value={currentLang}
                onValueChange={(val) => val && onLangChange(val as "en" | "fa")}
              >
                <ToggleGroupItem value="en">English</ToggleGroupItem>
                <ToggleGroupItem value="fa">فارسی (RTL)</ToggleGroupItem>
              </ToggleGroup>
            </div>

            {/* بخش پوسته */}
            <div className="space-y-1">
              <Label className="font-medium text-xs">{t("theme_preset")}</Label>
              <Select value={themePreset} onValueChange={onThemePresetChange}>
                <SelectTrigger size="sm" className="w-full text-xs">
                  <SelectValue placeholder="Preset" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {THEME_PRESET_OPTIONS.map((preset) => (
                      <SelectItem key={preset.value} className="text-xs" value={preset.value}>
                        <span
                          className="size-2.5 rounded-full inline-block mr-2 rtl:ml-2 rtl:mr-0 align-middle"
                          style={{
                            backgroundColor: resolvedThemeMode === "dark" ? preset.primary.dark : preset.primary.light,
                          }}
                        />
                        {preset.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>

            {/* بخش فونت */}
            <div className="space-y-1">
              <Label className="font-medium text-xs">{t("fonts_label")}</Label>
              <Select value={font} onValueChange={onFontChange}>
                <SelectTrigger size="sm" className="w-full text-xs">
                  <SelectValue placeholder={t("select_font_placeholder")} />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {fontOptions
                      .filter((f: any) => currentLang === "fa" ? f.isPersian : !f.isPersian)
                      .map((font) => (
                        <SelectItem key={font.key} className="text-xs" value={font.key}>
                          {font.label}
                        </SelectItem>
                      ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>

            {/* حالت شب و روز */}
            <div className="space-y-1">
              <Label className="font-medium text-xs">{t("theme_mode_label")}</Label>
              <ToggleGroup
                size="sm"
                spacing={0}
                variant="outline"
                type="single"
                value={themeMode}
                onValueChange={onThemeModeChange}
              >
                <ToggleGroupItem value="light">{t("theme_mode_light")}</ToggleGroupItem>
                <ToggleGroupItem value="dark">{t("theme_mode_dark")}</ToggleGroupItem>
                <ToggleGroupItem value="system">{t("theme_mode_system")}</ToggleGroupItem>
              </ToggleGroup>
            </div>

            {/* لایوت صفحه */}
            <div className="space-y-1">
              <Label className="font-medium text-xs">{t("page_layout_label")}</Label>
              <ToggleGroup
                size="sm"
                spacing={0}
                variant="outline"
                type="single"
                value={contentLayout}
                onValueChange={onContentLayoutChange}
              >
                <ToggleGroupItem value="centered">{t("page_layout_centered")}</ToggleGroupItem>
                <ToggleGroupItem value="full-width">{t("page_layout_full_width")}</ToggleGroupItem>
              </ToggleGroup>
            </div>

            {/* رفتار ناوبار */}
            <div className="space-y-1">
              <Label className="font-medium text-xs">{t("navbar_behavior_label")}</Label>
              <ToggleGroup
                size="sm"
                spacing={0}
                variant="outline"
                type="single"
                value={navbarStyle}
                onValueChange={onNavbarStyleChange}
              >
                <ToggleGroupItem value="sticky">{t("navbar_behavior_sticky")}</ToggleGroupItem>
                <ToggleGroupItem value="scroll">{t("navbar_behavior_scroll")}</ToggleGroupItem>
              </ToggleGroup>
            </div>

            {/* استایل سایدبار */}
            <div className="space-y-1">
              <Label className="font-medium text-xs">{t("sidebar_style_label")}</Label>
              <ToggleGroup
                size="sm"
                spacing={0}
                variant="outline"
                type="single"
                value={variant}
                onValueChange={onSidebarStyleChange}
              >
                <ToggleGroupItem value="inset">{t("sidebar_style_inset")}</ToggleGroupItem>
                <ToggleGroupItem value="sidebar">{t("sidebar_style_sidebar")}</ToggleGroupItem>
                <ToggleGroupItem value="floating">{t("sidebar_style_floating")}</ToggleGroupItem>
              </ToggleGroup>
            </div>

            {/* جمع شدن سایدبار */}
            <div className="space-y-1">
              <Label className="font-medium text-xs">{t("sidebar_collapse_label")}</Label>
              <ToggleGroup
                size="sm"
                spacing={0}
                variant="outline"
                type="single"
                value={collapsible}
                onValueChange={onSidebarCollapseModeChange}
              >
                <ToggleGroupItem value="icon">{t("sidebar_collapse_icon")}</ToggleGroupItem>
                <ToggleGroupItem value="offcanvas">{t("sidebar_collapse_offcanvas")}</ToggleGroupItem>
              </ToggleGroup>
            </div>

            <Button type="button" size="sm" variant="outline" className="w-full text-xs" onClick={resetPreferences}>
              {t("restore_defaults")}
            </Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}