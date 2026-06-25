"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { isAuthenticated, getUser, type AdminUser } from "@/lib/auth";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [user, setUser] = useState<AdminUser | null>(null);
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    setMounted(true);
    // Auth check: redirect to login if no valid token or user
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    const currentUser = getUser();
    if (!currentUser) {
      router.replace("/login");
      return;
    }
    // Only admin / superadmin roles allowed
    if (!["admin", "superadmin"].includes(currentUser.role)) {
      router.replace("/login");
      return;
    }
    setUser(currentUser);
    setAuthorized(true);
  }, [router]);

  // Avoid flash of unauthorized content during SSR/hydration
  if (!mounted || !authorized) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-y-auto pl-64 pt-4 px-8 pb-8 transition-all duration-300 max-lg:pl-0 max-lg:pt-16">
        {children}
      </main>
    </div>
  );
}