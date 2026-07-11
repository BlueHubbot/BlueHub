"use client";

import { useEffect, useState } from "react";
import { adminApi, type DashboardStats } from "@/lib/api";
import { formatNumber, formatCurrency, formatRelativeTime } from "@/lib/utils";
import { useAdminAuth } from "@/lib/auth";
import {
  Users,
  Server,
  DollarSign,
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
      setStats(response);
    } catch (err) {
      setError("Failed to load dashboard stats. Using demo data.");
      setStats({
        total_users: 1250,
        active_services: 850,
        revenue_monthly: 45200,
        active_modules: 5,
        total_tenants: 8,
        pending_abuse_reports: 12,
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
      label: "Total Revenue",
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
    <div className="space-y-8 p-6 w-full max-w-full block">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b pb-5">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Welcome back, {user?.username || "Admin"}
          </p>
        </div>
        <span className="text-sm text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-3 py-1 rounded-full h-fit">
          Last updated: {formatRelativeTime(new Date().toISOString())}
        </span>
      </div>

      {error && (
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800 dark:border-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200">
          {error}
        </div>
      )}

      {/* Stats Grid - تمیز و ریسپانسیو بدون تداخل کلاس‌های سی‌اس‌اس */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6 w-full">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.label} className="bg-white dark:bg-gray-900 rounded-xl border p-6 shadow-sm flex flex-col justify-between min-w-0">
              <div className="flex items-center justify-between">
                <div className={`rounded-lg p-3 ${card.color}`}>
                  <Icon className="h-5 w-5" />
                </div>
              </div>
              <div className="mt-4">
                <p className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white">{card.value}</p>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400 truncate">{card.label}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
        {/* Pending Abuse Reports */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border p-6 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="rounded-lg bg-yellow-100 p-3 dark:bg-yellow-900/30">
              <AlertTriangle className="h-6 w-6 text-yellow-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.pending_abuse_reports}</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Pending Abuse Reports</p>
            </div>
          </div>
        </div>

        {/* System Overview */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border p-6 shadow-sm">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">System Overview</h3>
          <div className="space-y-4">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500 dark:text-gray-400">Service Utilization</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {stats.total_users > 0
                  ? ((stats.active_services / stats.total_users) * 100).toFixed(1)
                  : 0}%
              </span>
            </div>
            <div className="h-2 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
              <div
                className="h-2 rounded-full bg-blue-600 transition-all"
                style={{
                  width: `${
                    stats.total_users > 0
                      ? Math.min((stats.active_services / stats.total_users) * 100, 100)
                      : 0
                  }%`,
                }}
              />
            </div>
            <div className="flex justify-between text-sm pt-1">
              <span className="text-gray-500 dark:text-gray-400">Online Modules</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {stats.active_modules} of {stats.active_modules}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}