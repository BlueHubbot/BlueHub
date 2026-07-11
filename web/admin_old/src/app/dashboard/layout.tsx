"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { isAuthenticated, getUser } from "@/lib/auth";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [mounted, setMounted] = useState(false);
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (!isAuthenticated()) {
      window.location.href = "/login";
      return;
    }
    const currentUser = getUser();
    if (!currentUser) {
      window.location.href = "/login";
      return;
    }
    const normalizedRole = (currentUser.role || "").toUpperCase();
    if (!["ADMIN", "SUPERADMIN"].includes(normalizedRole)) {
      window.location.href = "/login";
      return;
    }
    setAuthorized(true);
  }, []);

  if (!mounted || !authorized) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-background text-foreground overflow-hidden">
      {/* سایدبار تزریق شده در جریان کامپوننت‌ها */}
      <Sidebar />
      
      {/* محتوای اصلی داشبورد با ایجاد اسکرول مستقل */}
      <main className="flex-1 p-8 overflow-y-auto min-h-screen">
        {children}
      </main>
    </div>
  );
}