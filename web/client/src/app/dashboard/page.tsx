"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/providers";
import { useEffect } from "react";
import Link from "next/link";

export default function DashboardPage() {
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col">
      <header className="border-b">
        <div className="container flex h-16 items-center justify-between py-4">
          <Link href="/dashboard" className="text-xl font-bold">
            BlueHub
          </Link>
          <nav className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">
              {user?.full_name || user?.email}
            </span>
            <button
              onClick={logout}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Logout
            </button>
          </nav>
        </div>
      </header>

      <section className="container py-8">
        <h2 className="text-2xl font-bold mb-6">Dashboard</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-6 bg-card rounded-lg border shadow-sm">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">
              Active Services
            </h3>
            <p className="text-2xl font-bold">0</p>
          </div>

          <div className="p-6 bg-card rounded-lg border shadow-sm">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">
              Total Traffic
            </h3>
            <p className="text-2xl font-bold">0 GB</p>
          </div>

          <div className="p-6 bg-card rounded-lg border shadow-sm">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">
              Account Balance
            </h3>
            <p className="text-2xl font-bold">0 IRR</p>
          </div>

          <div className="p-6 bg-card rounded-lg border shadow-sm">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">
              Days Remaining
            </h3>
            <p className="text-2xl font-bold">--</p>
          </div>
        </div>

        <div className="mt-8 p-6 bg-card rounded-lg border shadow-sm">
          <h3 className="text-lg font-semibold mb-4">Your Services</h3>
          <p className="text-muted-foreground">
            No active services yet.{" "}
            <Link href="/services" className="text-primary hover:underline">
              Browse available plans
            </Link>
          </p>
        </div>
      </section>
    </main>
  );
}