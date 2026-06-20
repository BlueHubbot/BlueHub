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
  Settings,
  LogOut,
  Shield,
  ChevronLeft,
  ChevronRight,
  Menu,
} from "lucide-react";
import { useState } from "react";

const menuItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, roles: ["admin", "superadmin"] },
  { href: "/dashboard/modules", label: "Modules", icon: Blocks, roles: ["superadmin"] },
  { href: "/dashboard/products", label: "Products", icon: Package, roles: ["admin", "superadmin"] },
  { href: "/dashboard/tenants", label: "Tenants", icon: Building2, roles: ["superadmin"] },
  { href: "/dashboard/users", label: "Users", icon: Users, roles: ["admin", "superadmin"] },
  { href: "/dashboard/abuse", label: "Abuse Reports", icon: AlertTriangle, roles: ["admin", "superadmin"] },
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
    (item) => user && item.roles.some((r) => r === user.role)
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

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex flex-col border-r bg-sidebar text-sidebar-foreground transition-all duration-300",
          collapsed ? "w-16" : "w-64",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Logo area */}
        <div className={cn("flex h-16 items-center border-b border-sidebar-border px-4", collapsed && "justify-center")}>
          {collapsed ? (
            <Shield className="h-6 w-6 shrink-0" />
          ) : (
            <div className="flex items-center gap-2">
              <Shield className="h-6 w-6 shrink-0" />
              <span className="text-lg font-semibold">BlueHub Admin</span>
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
                  "sidebar-link",
                  isActive ? "sidebar-link-active" : "sidebar-link-inactive",
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
        <div className="border-t border-sidebar-border p-3">
          {!collapsed && user && (
            <div className="mb-2 px-3 text-xs text-sidebar-foreground/60">
              <p className="truncate font-medium">{user.username}</p>
              <p className="truncate capitalize">{user.role}</p>
            </div>
          )}
          <button
            onClick={handleLogout}
            className={cn(
              "sidebar-link sidebar-link-inactive w-full",
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
          className="hidden border-t border-sidebar-border p-3 lg:flex items-center justify-center hover:bg-sidebar-accent transition-colors"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </aside>
    </>
  );
}