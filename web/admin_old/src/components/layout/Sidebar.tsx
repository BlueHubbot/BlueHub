"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { getUser, removeToken } from "@/lib/auth";
import {
  LayoutDashboard,
  Blocks,
  Package,
  Building2,
  Users,
  AlertTriangle,
  LogOut,
  Shield,
  ChevronLeft,
  ChevronRight,
  Menu,
} from "lucide-react";
import { useState } from "react";

const menuItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, roles: ["admin", "superadmin", "SUPERADMIN", "ADMIN"] },
  { href: "/dashboard/modules", label: "Modules", icon: Blocks, roles: ["superadmin", "SUPERADMIN"] },
  { href: "/dashboard/products", label: "Products", icon: Package, roles: ["admin", "superadmin", "SUPERADMIN", "ADMIN"] },
  { href: "/dashboard/tenants", label: "Tenants", icon: Building2, roles: ["superadmin", "SUPERADMIN"] },
  { href: "/dashboard/users", label: "Users", icon: Users, roles: ["admin", "superadmin", "SUPERADMIN", "ADMIN"] },
  { href: "/dashboard/abuse", label: "Abuse Reports", icon: AlertTriangle, roles: ["admin", "superadmin", "SUPERADMIN", "ADMIN"] },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const user = getUser();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    removeToken();
    router.push("/login");
  };

  const filteredItems = menuItems.filter(
    (item) => user && item.roles.some((r) => r.toLowerCase() === user.role.toLowerCase())
  );
  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile toggle */}
      <button
        className="fixed left-4 top-4 z-50 rounded-md border bg-background p-2 shadow lg:hidden"
        onClick={() => setMobileOpen(!mobileOpen)}
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Sidebar - تبدیل به ساختار منعطف دسکتاپ و فیکس موبایل */}
      <aside
        className={cn(
          "bg-card border-r border-border text-foreground flex flex-col transition-all duration-300 min-h-screen flex-shrink-0 z-50",
          "fixed inset-y-0 left-0 lg:sticky lg:top-0", // پوزیشن استیکی در دسکتاپ و فیکس در موبایل
          collapsed ? "w-16" : "w-64",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Logo area */}
        <div className={cn("flex h-16 items-center border-b border-border px-4", collapsed && "justify-center")}>
          {collapsed ? (
            <Shield className="h-6 w-6 shrink-0 text-primary" />
          ) : (
            <div className="flex items-center gap-2">
              <Shield className="h-6 w-6 shrink-0 text-primary" />
              <span className="text-lg font-semibold tracking-tight">BlueHub Admin</span>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {filteredItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors dynamic-link",
                  isActive 
                    ? "bg-primary text-primary-foreground" 
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  collapsed && "justify-center px-2"
                )}
                title={collapsed ? item.label : undefined}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* User area */}
        <div className="border-t border-border p-3 bg-muted/30">
          {!collapsed && user && (
            <div className="mb-2 px-3 text-xs">
              <p className="truncate font-semibold text-foreground">{user.username}</p>
              <p className="truncate text-muted-foreground capitalize">{user.role}</p>
            </div>
          )}
          <button
            onClick={handleLogout}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-destructive hover:bg-destructive/10 transition-colors w-full",
              collapsed && "justify-center"
            )}
            title={collapsed ? "Logout" : undefined}
          >
            <LogOut className="h-5 w-5 shrink-0" />
            {!collapsed && <span>Logout</span>}
          </button>
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="hidden border-t border-border p-3 lg:flex items-center justify-center hover:bg-muted text-muted-foreground transition-colors"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </aside>
    </>
  );
}