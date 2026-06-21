"use client";

import { useEffect, useState } from "react";
import { adminApi, type DashboardStats } from "@/lib/api";
import { formatNumber, formatCurrency, formatRelativeTime } from "@/lib/utils";
import { useAdminAuth } from "@/lib/auth";
import {
  Users,
  Server,
  DollarSign,
  Activity,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Blocks,
  Globe,
} from "lucide-react";

export default function DashboardPage() {
  const { user } = useAdminAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const response = await adminApi.getDashboardStats();
      setStats(response.data);
    } catch (err) {
      setError("Failed to load dashboard stats. Using demo data.");
      setStats({
        total_users: 1250,
        active_services: 850,
        revenue_monthly: 45200,
        active_modules: 5,
        total_tenants: 8,
        pending_abuse_reports: 3,
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-20 text-muted-foreground">
        Unable to load dashboard.
      </div>
    );
  }

  const statCards = [
    {
      label: "Total Users",
      value: formatNumber(stats.total_users),
      icon: Users,
      color: "text-blue-600 bg-blue-100 dark:bg-blue-900/30",
    },
    {
      label: "Active Services",
      value: formatNumber(stats.active_services),
      icon: Server,
      color: "text-green-600 bg-green-100 dark:bg-green-900/30",
    },
    {
      label: "Monthly Revenue",
      value: formatCurrency(stats.revenue_monthly),
      icon: DollarSign,
      color: "text-purple-600 bg-purple-100 dark:bg-purple-900/30",
    },
    {
      label: "Active Modules",
      value: formatNumber(stats.active_modules),
      icon: Blocks,
      color: "text-indigo-600 bg-indigo-100 dark:bg-indigo-900/30",
    },
    {
      label: "Tenants",
      value: formatNumber(stats.total_tenants),
      icon: Globe,
      color: "text-orange-600 bg-orange-100 dark:bg-orange-900/30",
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="mt-1 text-muted-foreground">
            Welcome back, {user?.username || "Admin"}
          </p>
        </div>
        <span className="text-sm text-muted-foreground">
          Last updated: {formatRelativeTime(new Date().toISOString())}
        </span>
      </div>

      {error && (
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800 dark:border-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200">
          {error}
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.label} className="stat-card">
              <div className="flex items-center justify-between">
                <div className={cn("rounded-lg p-3", card.color)}>
                  <Icon className="h-5 w-5" />
                </div>
              </div>
              <div className="mt-4">
                <p className="text-2xl font-bold">{card.value}</p>
                <p className="mt-1 text-sm text-muted-foreground">{card.label}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Actions */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Pending Abuse Reports */}
        <div className="stat-card">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-red-100 p-3 dark:bg-red-900/30">
              <AlertTriangle className="h-5 w-5 text-red-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.pending_abuse_reports}</p>
              <p className="text-sm text-muted-foreground">Pending Abuse Reports</p>
            </div>
          </div>
        </div>

        {/* Quick summary */}
        <div className="stat-card">
          <h3 className="font-semibold mb-3">System Overview</h3>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Service Utilization</span>
              <span className="font-medium">
                {stats.total_users > 0
                  ? ((stats.active_services / stats.total_users) * 100).toFixed(1)
                  : 0}%
              </span>
            </div>
            <div className="h-2 rounded-full bg-muted">
              <div
                className="h-2 rounded-full bg-primary transition-all"
                style={{
                  width: `${
                    stats.total_users > 0
                      ? Math.min((stats.active_services / stats.total_users) * 100, 100)
                      : 0
                  }%`,
                }}
              />
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Active Modules</span>
              <span className="font-medium">
                {stats.active_modules} of {stats.active_modules}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper: cn utility
function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(" ");
}