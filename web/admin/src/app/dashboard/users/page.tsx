"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { getUser } from "@/lib/auth";
import {
  Search,
  Users,
  Shield,
  ShieldOff,
  RotateCcw,
  Eye,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { UserEditModal } from "./components/UserEditModal";
import { UserDetailModal } from "./components/UserDetailModal";

export interface UserData {
  id: string;
  email: string;
  username: string;
  telegram_id: string | null;
  role: string;
  language: string;
  active: boolean;
  suspended: boolean;
  tenant_id: string | null;
  tenant_name?: string;
  created_at: string;
  updated_at?: string;
}

export interface ServiceData {
  id: string;
  type: string;
  status: string;
  name?: string;
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  action: string;
  details: string;
  ip_address: string;
  created_at: string;
}

interface PaginationData {
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export default function UsersPage() {
  const router = useRouter();
  const user = getUser();
  const [users, setUsers] = useState<UserData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filterRole, setFilterRole] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterTenant, setFilterTenant] = useState("");
  const [tenantOptions, setTenantOptions] = useState<{ id: string; name: string }[]>([]);

  // Pagination
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState<PaginationData>({
    total: 0,
    page: 1,
    per_page: 100,
    pages: 1,
  });

  // Modal state
  const [editingUser, setEditingUser] = useState<UserData | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [detailUser, setDetailUser] = useState<UserData | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);

  // Action loading states
  const [suspending, setSuspending] = useState<string | null>(null);
  const [resettingPwd, setResettingPwd] = useState<string | null>(null);

  const fetchTenants = useCallback(async () => {
    try {
      const res = await api.get<{ id: string; name: string }[]>("/admin/tenants");
      setTenantOptions(res.data);
    } catch {
      // tenants endpoint may be unavailable for non-superadmin
    }
  }, []);

  const fetchUsers = useCallback(async () => {
    try {
      setError(null);
      setLoading(true);
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      if (filterRole) params.set("role", filterRole);
      if (filterStatus) params.set("status", filterStatus);
      if (filterTenant) params.set("tenant_id", filterTenant);
      params.set("page", String(page));
      params.set("per_page", "100");

      const res = await api.get<{ users: UserData[]; pagination: PaginationData }>(
        `/admin/users?${params.toString()}`
      );
      setUsers(res.data.users);
      setPagination(res.data.pagination);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load users";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [search, filterRole, filterStatus, filterTenant, page]);

  useEffect(() => {
    if (!user || !["admin", "superadmin"].includes(user.role)) {
      router.push("/login");
      return;
    }
    fetchUsers();
    if (user.role === "superadmin") {
      fetchTenants();
    }
  }, [user, router, fetchUsers, fetchTenants]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [search, filterRole, filterStatus, filterTenant]);

  const handleSuspendToggle = async (targetUser: UserData) => {
    try {
      setSuspending(targetUser.id);
      setError(null);
      await api.patch(`/admin/users/${targetUser.id}`, {
        suspended: !targetUser.suspended,
      });
      await fetchUsers();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update user";
      setError(msg);
    } finally {
      setSuspending(null);
    }
  };

  const handleResetPassword = async (targetUser: UserData) => {
    try {
      setResettingPwd(targetUser.id);
      setError(null);
      await api.post(`/admin/users/${targetUser.id}/reset-password`);
      // Show success feedback
      alert(`Password reset link sent to ${targetUser.email}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to reset password";
      setError(msg);
    } finally {
      setResettingPwd(null);
    }
  };

  const handleEditSaved = () => {
    setEditModalOpen(false);
    setEditingUser(null);
    fetchUsers();
  };

  const roleBadgeColors: Record<string, string> = {
    superadmin:
      "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
    admin: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    user: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
    reseller:
      "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  };

  const statusColors: Record<string, string> = {
    active: "bg-green-500",
    suspended: "bg-red-500",
    inactive: "bg-gray-400",
  };

  const getStatus = (u: UserData): "active" | "suspended" | "inactive" => {
    if (u.suspended) return "suspended";
    if (!u.active) return "inactive";
    return "active";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Users</h1>
          <p className="text-sm text-muted-foreground">
            Manage platform users with role assignment, suspension, and audit capabilities.
          </p>
        </div>
        <p className="text-sm text-muted-foreground">
          {pagination.total} user{pagination.total !== 1 && "s"}
        </p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
          <p>{error}</p>
          <button onClick={() => setError(null)} className="mt-1 underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 min-w-[250px] max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by email or Telegram ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border bg-background py-2 pl-10 pr-4 text-sm outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <select
          value={filterRole}
          onChange={(e) => setFilterRole(e.target.value)}
          className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="">All Roles</option>
          <option value="user">User</option>
          <option value="admin">Admin</option>
          <option value="superadmin">Superadmin</option>
          <option value="reseller">Reseller</option>
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="inactive">Inactive</option>
        </select>
        {user?.role === "superadmin" && (
          <select
            value={filterTenant}
            onChange={(e) => setFilterTenant(e.target.value)}
            className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="">All Tenants</option>
            {tenantOptions.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      )}

      {/* Empty state */}
      {!loading && users.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Users className="h-12 w-12 text-muted-foreground/50" />
          <h3 className="mt-4 text-lg font-medium">No users found</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {search || filterRole || filterStatus || filterTenant
              ? "Try different filters."
              : "No users registered yet."}
          </p>
        </div>
      )}

      {/* Users table */}
      {!loading && users.length > 0 && (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">User</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Telegram</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Role</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Language</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Tenant</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Joined</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {users.map((u) => {
                const status = getStatus(u);
                return (
                  <tr
                    key={u.id}
                    className={`group hover:bg-muted/30 transition-colors ${
                      status !== "active" ? "opacity-60" : ""
                    }`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <span className="font-medium">{u.username || u.email}</span>
                        <span className="text-xs text-muted-foreground">{u.email}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {u.telegram_id ? (
                        <code className="rounded bg-muted px-2 py-0.5 text-xs font-mono">
                          {u.telegram_id}
                        </code>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          roleBadgeColors[u.role] || "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {u.role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-block h-2.5 w-2.5 rounded-full ${
                            statusColors[status]
                          }`}
                        />
                        <span className="text-xs capitalize">{status}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {u.language || "en"}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {u.tenant_name || (
                        <span className="text-xs italic">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                      {u.created_at
                        ? new Date(u.created_at).toLocaleDateString()
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {/* View detail */}
                        <button
                          onClick={() => {
                            setDetailUser(u);
                            setDetailModalOpen(true);
                          }}
                          className="rounded-md p-1.5 text-muted-foreground hover:bg-muted transition-colors"
                          title="View details & services"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        {/* Edit */}
                        <button
                          onClick={() => {
                            setEditingUser(u);
                            setEditModalOpen(true);
                          }}
                          className="rounded-md border px-2.5 py-1 text-xs font-medium hover:bg-muted transition-colors"
                        >
                          Edit
                        </button>
                        {/* Suspend / Unsuspend */}
                        <button
                          onClick={() => handleSuspendToggle(u)}
                          disabled={suspending === u.id}
                          className={`inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
                            u.suspended
                              ? "border-green-200 text-green-600 hover:bg-green-50 dark:border-green-800 dark:text-green-400 dark:hover:bg-green-950"
                              : "border-red-200 text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950"
                          }`}
                          title={u.suspended ? "Unsuspend user" : "Suspend user"}
                        >
                          {suspending === u.id ? (
                            <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                          ) : u.suspended ? (
                            <Shield className="h-3.5 w-3.5" />
                          ) : (
                            <ShieldOff className="h-3.5 w-3.5" />
                          )}
                          {u.suspended ? "Unsuspend" : "Suspend"}
                        </button>
                        {/* Reset password */}
                        <button
                          onClick={() => handleResetPassword(u)}
                          disabled={resettingPwd === u.id}
                          className="rounded-md border px-2.5 py-1 text-xs font-medium hover:bg-muted transition-colors disabled:opacity-50"
                          title="Send password reset link"
                        >
                          {resettingPwd === u.id ? (
                            <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                          ) : (
                            <RotateCcw className="h-3.5 w-3.5 inline-block" />
                          )}
                          <span className="ml-1">Reset</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {!loading && pagination.pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {pagination.page} of {pagination.pages} ({pagination.total} users)
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="inline-flex items-center gap-1 rounded-lg border px-3 py-2 text-sm font-medium hover:bg-muted transition-colors disabled:opacity-50"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </button>
            {Array.from({ length: pagination.pages }, (_, i) => i + 1)
              .filter((p) => {
                // Show first, last, and pages around current
                return (
                  p === 1 ||
                  p === pagination.pages ||
                  Math.abs(p - page) <= 2
                );
              })
              .map((p, idx, arr) => (
                <span key={p} className="flex items-center">
                  {idx > 0 && arr[idx - 1] !== p - 1 && (
                    <span className="px-1 text-muted-foreground">...</span>
                  )}
                  <button
                    onClick={() => setPage(p)}
                    className={`min-w-[36px] rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                      p === page
                        ? "bg-primary text-primary-foreground border-primary"
                        : "hover:bg-muted"
                    }`}
                  >
                    {p}
                  </button>
                </span>
              ))}
            <button
              onClick={() => setPage((p) => Math.min(pagination.pages, p + 1))}
              disabled={page >= pagination.pages}
              className="inline-flex items-center gap-1 rounded-lg border px-3 py-2 text-sm font-medium hover:bg-muted transition-colors disabled:opacity-50"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editModalOpen && editingUser && (
        <UserEditModal
          user={editingUser}
          onSaved={handleEditSaved}
          onClose={() => {
            setEditModalOpen(false);
            setEditingUser(null);
          }}
        />
      )}

      {/* Detail Modal */}
      {detailModalOpen && detailUser && (
        <UserDetailModal
          user={detailUser}
          onClose={() => {
            setDetailModalOpen(false);
            setDetailUser(null);
          }}
        />
      )}
    </div>
  );
}