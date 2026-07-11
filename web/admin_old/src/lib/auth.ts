"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export interface AdminUser {
  id: string; // <--- تبدیل از number به string
  email: string;
  username: string;
  role: string;
  tenant_id: number | null;
}

export const TOKEN_KEY = "admin_token";
export const USER_KEY = "admin_user";

// مدیریت کوکی‌ها برای سینک نگه داشتن سمت سرور و کلاینت
function setCookie(name: string, value: string, days = 1) {
  if (typeof window === "undefined") return;
  const expires = new Date(Date.now() + days * 86400000).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Strict`;
}

function deleteCookie(name: string) {
  if (typeof window === "undefined") return;
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/;`;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  setCookie(TOKEN_KEY, token);
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  deleteCookie(TOKEN_KEY);
  deleteCookie(USER_KEY);
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
  setCookie(USER_KEY, JSON.stringify(user));
}

export function isAuthenticated(): boolean {
  return !!getToken() && !!getUser();
}

export function hasRole(...roles: string[]): boolean {
  const user = getUser();
  if (!user) return false;
  
  const normalizedUserRole = (user.role || "").toUpperCase();
  const normalizedRoles = roles.map(r => r.toUpperCase());
  
  return normalizedRoles.includes(normalizedUserRole);
}

// هوک محافظت از روت‌ها با تغییر مکانیزم ریدایرکت برای جلوگیری از لوپ
export function useAdminAuth(requiredRoles?: string[]) {
  const router = useRouter();
  const [user, setUserState] = useState<AdminUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const currentUser = getUser();
    const token = getToken();

    if (!token || !currentUser) {
      window.location.href = "/login";
      return;
    }

    if (requiredRoles) {
      const normalizedUserRole = (currentUser.role || "").toUpperCase();
      const normalizedRequiredRoles = requiredRoles.map(r => r.toUpperCase());
      
      if (!normalizedRequiredRoles.includes(normalizedUserRole)) {
        window.location.href = "/login";
        return;
      }
    }

    setUserState(currentUser);
    setLoading(false);
  }, [requiredRoles]);

  return { user, loading, isAuthenticated: !!user };
}

// هوک عملیات لاگین
export function useAdminLogin() {
  const login = async (email: string, password: string) => {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://109.199.108.30:8000"}/auth/login`,
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
    const userRole = data.user?.role ? String(data.user.role).toUpperCase() : "";

    if (userRole !== "ADMIN" && userRole !== "SUPERADMIN") {
      throw new Error("Access denied. Admin privileges required.");
    }

    // ذخیره همزمان در استوریج و کوکی
    setToken(data.access_token);
    setUser(data.user);
    
    // ریدایرکت اجباری در لایه مرورگر برای خروج کامل از لوپ و لود وضعیت جدید احراز هویت
    window.location.href = "/dashboard";
  };

  const logout = () => {
    removeToken();
    window.location.href = "/login";
  };

  return { login, logout };
}