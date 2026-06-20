import type { Metadata } from "next";
import { Providers } from "@/lib/providers";
import { TenantThemeProvider } from "@/components/theme/TenantThemeProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    template: "%s | BlueHub",
    default: "BlueHub - VPN & Service Management",
  },
  description: "Professional VPN and service management panel",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fa" dir="rtl" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <Providers>
          <TenantThemeProvider>{children}</TenantThemeProvider>
        </Providers>
      </body>
    </html>
  );
}
