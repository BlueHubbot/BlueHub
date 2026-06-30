"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export interface AdminUser {
  id: number;
  email: string;
  username: string;
  role: "superadmin" | "admin";
  tenant_id: number | null;
}

// Token storage
export const TOKEN_KEY = "admin_token";
export const USER_KEY = "admin_user";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getUser(): AdminUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AdminUser;
  } catch {
    return null;
  }
}

export function setUser(user: AdminUser): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function isAuthenticated(): boolean {
  return !!getToken() && !!getUser();
}

export function hasRole(...roles: string[]): boolean {
  const user = getUser();
  if (!user) return false;
  return roles.includes(user.role);
}

// Hook for route protection
export function useAdminAuth(requiredRoles?: string[]) {
  const router = useRouter();
  const [user, setUserState] = useState<AdminUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const currentUser = getUser();
    const token = getToken();

    if (!token || !currentUser) {
      router.replace("/login");
      return;
    }

    if (requiredRoles && !requiredRoles.includes(currentUser.role)) {
      router.replace("/dashboard");
      return;
    }

    setUserState(currentUser);
    setLoading(false);
  }, [router, requiredRoles]);

  return { user, loading, isAuthenticated: !!user };
}

// Hook for login
export function useAdminLogin() {
  const router = useRouter();

  const login = async (email: string, password: string) => {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/auth/login`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(error.detail || "Login failed");
    }

    const data = await response.json();

    // Verify the user has admin/superadmin role
    if (data.user?.role !== "admin" && data.user?.role !== "superadmin") {
      throw new Error("Access denied. Admin privileges required.");
    }

    setToken(data.access_token);
    setUser(data.user);
    router.push("/dashboard");
  };

  const logout = () => {
    removeToken();
    router.push("/login");
  };

  return { login, logout };
}