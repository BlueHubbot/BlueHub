"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/providers";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------
type VpsInstance = {
  id: string;
  service_id: string;
  proxmox_node: string;
  proxmox_vmid: number | null;
  cores: number;
  memory_mb: number;
  disk_gb: number;
  storage_pool: string;
  network_bridge: string;
  network_model: string;
  ostype: string;
  ostemplate: string | null;
  iso_image: string | null;
  ip_address: string | null;
  root_password: string | null;
  ssh_keys: string[] | null;
  boot_delay: number | null;
  extra_config: Record<string, unknown> | null;
  notes: string | null;
  power_status: "running" | "stopped" | "paused" | "suspended";
  vnc_port: number | null;
  created_at: string;
  updated_at: string;
};

type VpsSnapshot = {
  id: string;
  vps_instance_id: string;
  snapshot_name: string;
  description: string | null;
  size_bytes: number | null;
  is_ram_included: boolean;
  snapshot_taken_at: string;
  parent_snapshot_id: string | null;
  created_at: string;
};

type VncInfo = {
  vnc_port: number;
  vnc_password: string;
  vnc_url: string;
};

// ------------------------------------------------------------------
// API Helpers
// ------------------------------------------------------------------
async function apiFetch(path: string, options?: RequestInit) {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api/v1"}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: "Request failed" }));
    throw new Error(error.message || error.detail || "Request failed");
  }
  return res.json();
}

// ------------------------------------------------------------------
// Icons
// ------------------------------------------------------------------
function PowerIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5.636 5.636a9 9 0 1012.728 0M12 3v9" />
    </svg>
  );
}

function TerminalIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 9V5.25A2.25 2.25 0 0110.5 3h6a2.25 2.25 0 012.25 2.25v13.5A2.25 2.25 0 0116.5 21h-6a2.25 2.25 0 01-2.25-2.25V15m-3 0l3-3m0 0l-3-3m3 3H2.25" />
    </svg>
  );
}

function CameraIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0zM18.75 10.5h.008v.008h-.008V10.5z" />
    </svg>
  );
}

function RestartIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.992 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
    </svg>
  );
}

function StopIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 7.5A2.25 2.25 0 017.5 5.25h9a2.25 2.25 0 012.25 2.25v9a2.25 2.25 0 01-2.25 2.25h-9a2.25 2.25 0 01-2.25-2.25v-9z" />
    </svg>
  );
}

function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.992 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
    </svg>
  );
}

function ServerIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 17.25v-.228a4.5 4.5 0 00-.12-1.03l-2.268-9.64a3.375 3.375 0 00-3.285-2.602H7.923a3.375 3.375 0 00-3.285 2.602l-2.268 9.64a4.5 4.5 0 00-.12 1.03v.228m19.5 0a3 3 0 01-3 3H5.25a3 3 0 01-3-3m19.5 0a3 3 0 00-3-3H5.25a3 3 0 00-3 3m16.5 0h.008v.008h-.008v-.008zm-3 0h.008v.008h-.008v-.008z" />
    </svg>
  );
}

function GaugeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
    </svg>
  );
}

function ArrowPathIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.992 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
    </svg>
  );
}

// ------------------------------------------------------------------
// Power Status Badge
// ------------------------------------------------------------------
function PowerBadge({ status }: { status: VpsInstance["power_status"] }) {
  const colors: Record<VpsInstance["power_status"], string> = {
    running: "bg-emerald-100 text-emerald-800 border-emerald-200",
    stopped: "bg-red-100 text-red-800 border-red-200",
    paused: "bg-amber-100 text-amber-800 border-amber-200",
    suspended: "bg-gray-100 text-gray-800 border-gray-200",
  };
  const labels: Record<VpsInstance["power_status"], string> = {
    running: "Running",
    stopped: "Stopped",
    paused: "Paused",
    suspended: "Suspended",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border ${colors[status]}`}>
      {labels[status]}
    </span>
  );
}

// ------------------------------------------------------------------
// UI Components
// ------------------------------------------------------------------
function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
      {children}
    </div>
  );
}

function Button({
  children,
  onClick,
  variant = "default",
  size = "md",
  disabled = false,
  loading = false,
  className = "",
}: {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: "default" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  loading?: boolean;
  className?: string;
}) {
  const baseStyles =
    "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none";
  const variantStyles = {
    default:
      "bg-blue-600 text-white hover:bg-blue-700 border border-blue-600",
    danger:
      "bg-red-600 text-white hover:bg-red-700 border border-red-600",
    ghost:
      "bg-transparent text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600",
  };
  const sizeStyles = {
    sm: "px-2.5 py-1.5 text-xs",
    md: "px-4 py-2 text-sm",
    lg: "px-6 py-3 text-base",
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {loading && (
        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {children}
    </button>
  );
}

function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

function EmptyState({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
}) {
  return (
    <div className="text-center py-16">
      <Icon className="mx-auto h-16 w-16 text-gray-300 dark:text-gray-600" />
      <h3 className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
      <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{description}</p>
    </div>
  );
}

// ------------------------------------------------------------------
// Main Page Component
// ------------------------------------------------------------------
export default function VpsDashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [instances, setInstances] = useState<VpsInstance[]>([]);
  const [selectedInstance, setSelectedInstance] = useState<VpsInstance | null>(null);
  const [snapshots, setSnapshots] = useState<VpsSnapshot[]>([]);
  const [vncInfo, setVncInfo] = useState<VncInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Modal states
  const [snapshotModalOpen, setSnapshotModalOpen] = useState(false);
  const [vncModalOpen, setVncModalOpen] = useState(false);
  const [restoreModalOpen, setRestoreModalOpen] = useState(false);
  const [restoreSnapshotId, setRestoreSnapshotId] = useState<string | null>(null);

  // Redirect if not authenticated
  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [loading, user, router]);

  // Fetch instances
  const fetchInstances = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await apiFetch("/vps/instances");
      setInstances(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load instances");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      fetchInstances();
    }
  }, [user, fetchInstances]);

  // Fetch instance details
  const fetchInstanceDetails = useCallback(async (instanceId: string) => {
    try {
      const data = await apiFetch(`/vps/instances/${instanceId}`);
      setSelectedInstance(data);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load instance details");
      return null;
    }
  }, []);

  // Fetch snapshots for an instance
  const fetchSnapshots = useCallback(async (instanceId: string) => {
    try {
      const data = await apiFetch(`/vps/instances/${instanceId}/snapshots`);
      setSnapshots(data);
    } catch (err) {
      // Snapshots might not be supported
      setSnapshots([]);
    }
  }, []);

  // Fetch VNC info for an instance
  const fetchVncInfo = useCallback(async (instanceId: string) => {
    try {
      const data = await apiFetch(`/vps/instances/${instanceId}/vnc`);
      setVncInfo(data);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get VNC info");
      return null;
    }
  }, []);

  // Power actions
  const handlePowerAction = useCallback(
    async (instanceId: string, action: "start" | "stop" | "reboot" | "shutdown" | "pause" | "resume") => {
      setActionLoading(`${action}-${instanceId}`);
      try {
        await apiFetch(`/vps/instances/${instanceId}/power`, {
          method: "POST",
          body: JSON.stringify({ action }),
        });
        await fetchInstances();
        if (selectedInstance?.id === instanceId) {
          await fetchInstanceDetails(instanceId);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : `Power action '${action}' failed`);
      } finally {
        setActionLoading(null);
      }
    },
    [fetchInstances, fetchInstanceDetails, selectedInstance]
  );

  // Snapshot actions
  const handleCreateSnapshot = useCallback(
    async (instanceId: string) => {
      setActionLoading(`snapshot-create-${instanceId}`);
      try {
        await apiFetch(`/vps/instances/${instanceId}/snapshots`, {
          method: "POST",
          body: JSON.stringify({
            snapshot_name: `snap-${Math.floor(Date.now() / 1000)}`,
            description: "Created from web panel",
          }),
        });
        await fetchSnapshots(instanceId);
        setSnapshotModalOpen(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Snapshot creation failed");
      } finally {
        setActionLoading(null);
      }
    },
    [fetchSnapshots]
  );

  const handleDeleteSnapshot = useCallback(
    async (instanceId: string, snapshotId: string) => {
      setActionLoading(`snapshot-delete-${snapshotId}`);
      try {
        await apiFetch(`/vps/instances/${instanceId}/snapshots/${snapshotId}`, {
          method: "DELETE",
        });
        await fetchSnapshots(instanceId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Snapshot deletion failed");
      } finally {
        setActionLoading(null);
      }
    },
    [fetchSnapshots]
  );

  const handleRestoreSnapshot = useCallback(
    async (instanceId: string, snapshotId: string) => {
      setActionLoading(`snapshot-restore-${snapshotId}`);
      try {
        await apiFetch(`/vps/instances/${instanceId}/snapshots/${snapshotId}/restore`, {
          method: "POST",
        });
        setRestoreModalOpen(false);
        await fetchSnapshots(instanceId);
        await fetchInstances();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Snapshot restore failed");
      } finally {
        setActionLoading(null);
      }
    },
    [fetchSnapshots, fetchInstances]
  );

  // Open snapshot management modal
  const openSnapshotModal = useCallback(
    async (instance: VpsInstance) => {
      setSelectedInstance(instance);
      await fetchSnapshots(instance.id);
      setSnapshotModalOpen(true);
    },
    [fetchSnapshots]
  );

  // Open VNC modal
  const openVncModal = useCallback(
    async (instance: VpsInstance) => {
      setSelectedInstance(instance);
      const info = await fetchVncInfo(instance.id);
      if (info) {
        setVncModalOpen(true);
      }
    },
    [fetchVncInfo]
  );

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <ServerIcon className="h-8 w-8 text-blue-600" />
            VPS Management
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage your virtual private servers, power controls, snapshots, and console access.
          </p>
        </div>
        <Button onClick={fetchInstances} variant="ghost" size="sm" loading={isLoading}>
          <RefreshIcon className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center justify-between">
          <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-red-400 hover:text-red-600 dark:hover:text-red-300"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading && instances.length === 0 && (
        <div className="flex items-center justify-center min-h-[40vh]">
          <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full" />
        </div>
      )}

      {/* Empty State */}
      {!isLoading && instances.length === 0 && (
        <Card>
          <EmptyState
            icon={ServerIcon}
            title="No VPS Instances"
            description="You don't have any VPS instances yet. Purchase a VPS plan to get started."
          />
        </Card>
      )}

      {/* Instance Grid */}
      {instances.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {instances.map((instance) => (
            <Card key={instance.id} className="overflow-hidden">
              {/* Card Header */}
              <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    VPS-{instance.proxmox_vmid || instance.id.slice(0, 8)}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Node: {instance.proxmox_node || "N/A"} · OS: {instance.ostype}
                  </p>
                </div>
                <PowerBadge status={instance.power_status} />
              </div>

              {/* Resource Specs */}
              <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">{instance.cores}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">vCPUs</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {instance.memory_mb >= 1024
                        ? `${(instance.memory_mb / 1024).toFixed(1)} GB`
                        : `${instance.memory_mb} MB`}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">RAM</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">{instance.disk_gb} GB</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Disk</p>
                  </div>
                </div>
                {instance.ip_address && (
                  <div className="mt-4 flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918" />
                    </svg>
                    {instance.ip_address}
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="p-4 bg-gray-50 dark:bg-gray-900/50">
                <div className="flex flex-wrap items-center gap-2">
                  {/* Power Controls */}
                  {instance.power_status === "running" && (
                    <>
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => handlePowerAction(instance.id, "stop")}
                        loading={actionLoading === `stop-${instance.id}`}
                      >
                        <StopIcon className="h-3.5 w-3.5" />
                        Stop
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handlePowerAction(instance.id, "reboot")}
                        loading={actionLoading === `reboot-${instance.id}`}
                      >
                        <RestartIcon className="h-3.5 w-3.5" />
                        Reboot
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handlePowerAction(instance.id, "shutdown")}
                        loading={actionLoading === `shutdown-${instance.id}`}
                      >
                        <PowerIcon className="h-3.5 w-3.5" />
                        Shutdown
                      </Button>
                    </>
                  )}

                  {(instance.power_status === "stopped" || instance.power_status === "suspended") && (
                    <Button
                      size="sm"
                      variant="default"
                      onClick={() => handlePowerAction(instance.id, "start")}
                      loading={actionLoading === `start-${instance.id}`}
                    >
                      <PowerIcon className="h-3.5 w-3.5" />
                      Start
                    </Button>
                  )}

                  {instance.power_status === "paused" && (
                    <Button
                      size="sm"
                      variant="default"
                      onClick={() => handlePowerAction(instance.id, "resume")}
                      loading={actionLoading === `resume-${instance.id}`}
                    >
                      <PowerIcon className="h-3.5 w-3.5" />
                      Resume
                    </Button>
                  )}

                  {/* Snapshot Management */}
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => openSnapshotModal(instance)}
                  >
                    <CameraIcon className="h-3.5 w-3.5" />
                    Snapshots
                  </Button>

                  {/* VNC Console */}
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => openVncModal(instance)}
                    disabled={instance.power_status !== "running"}
                  >
                    <TerminalIcon className="h-3.5 w-3.5" />
                    Console
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Resource Summary */}
      {instances.length > 0 && (
        <Card className="mt-8">
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
              <GaugeIcon className="h-5 w-5 text-blue-600" />
              Resource Summary
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-blue-700 dark:text-blue-400">
                  {instances.reduce((sum, i) => sum + i.cores, 0)}
                </p>
                <p className="text-xs text-blue-600 dark:text-blue-500">Total vCPUs</p>
              </div>
              <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-emerald-700 dark:text-emerald-400">
                  {instances.reduce((sum, i) => sum + i.memory_mb, 0) >= 1024
                    ? `${(instances.reduce((sum, i) => sum + i.memory_mb, 0) / 1024).toFixed(1)} GB`
                    : `${instances.reduce((sum, i) => sum + i.memory_mb, 0)} MB`}
                </p>
                <p className="text-xs text-emerald-600 dark:text-emerald-500">Total RAM</p>
              </div>
              <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-purple-700 dark:text-purple-400">
                  {instances.reduce((sum, i) => sum + i.disk_gb, 0)} GB
                </p>
                <p className="text-xs text-purple-600 dark:text-purple-500">Total Disk</p>
              </div>
              <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-amber-700 dark:text-amber-400">
                  {instances.filter((i) => i.power_status === "running").length}/{instances.length}
                </p>
                <p className="text-xs text-amber-600 dark:text-amber-500">Running</p>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Snapshot Management Modal */}
      <Modal
        open={snapshotModalOpen}
        onClose={() => setSnapshotModalOpen(false)}
        title={`Snapshots — VPS-${selectedInstance?.proxmox_vmid || selectedInstance?.id.slice(0, 8) || ""}`}
      >
        {selectedInstance && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {snapshots.length} snapshot{snapshots.length !== 1 ? "s" : ""}
              </p>
              <Button
                size="sm"
                onClick={() => handleCreateSnapshot(selectedInstance.id)}
                loading={actionLoading === `snapshot-create-${selectedInstance.id}`}
              >
                <CameraIcon className="h-3.5 w-3.5" />
                Create Snapshot
              </Button>
            </div>

            {snapshots.length === 0 ? (
              <p className="text-center py-8 text-sm text-gray-500 dark:text-gray-400">
                No snapshots yet. Create one to capture the current state.
              </p>
            ) : (
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {snapshots.map((snap) => (
                  <div
                    key={snap.id}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {snap.snapshot_name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {new Date(snap.snapshot_taken_at).toLocaleString()}
                        {snap.is_ram_included ? " · 💾 RAM" : ""}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setRestoreSnapshotId(snap.id);
                          setRestoreModalOpen(true);
                        }}
                        loading={actionLoading === `snapshot-restore-${snap.id}`}
                      >
                        <ArrowPathIcon className="h-3.5 w-3.5" />
                        Restore
                      </Button>
                      <button
                        onClick={() => handleDeleteSnapshot(selectedInstance.id, snap.id)}
                        disabled={actionLoading === `snapshot-delete-${snap.id}`}
                        className="text-red-400 hover:text-red-600 p-1 rounded"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* VNC Console Modal */}
      <Modal
        open={vncModalOpen}
        onClose={() => setVncModalOpen(false)}
        title={`Console — VPS-${selectedInstance?.proxmox_vmid || selectedInstance?.id.slice(0, 8) || ""}`}
      >
        {vncInfo && (
          <div className="space-y-4">
            <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Connection Details</h4>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Port</p>
                  <p className="text-sm font-mono text-gray-900 dark:text-white">{vncInfo.vnc_port}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Password</p>
                  <p className="text-sm font-mono text-gray-900 dark:text-white">{vncInfo.vnc_password || "N/A"}</p>
                </div>
              </div>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Use a VNC client such as RealVNC, TightVNC, or noVNC to connect to the console.
            </p>
          </div>
        )}
      </Modal>

      {/* Restore Confirmation Modal */}
      <Modal
        open={restoreModalOpen}
        onClose={() => setRestoreModalOpen(false)}
        title="Confirm Snapshot Restore"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Are you sure you want to restore this snapshot? The current state of the VPS will be replaced.
            Any data created after this snapshot was taken will be lost.
          </p>
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={() => setRestoreModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                if (restoreSnapshotId && selectedInstance) {
                  handleRestoreSnapshot(selectedInstance.id, restoreSnapshotId);
                }
              }}
              loading={restoreSnapshotId ? actionLoading === `snapshot-restore-${restoreSnapshotId}` : false}
            >
              Restore Snapshot
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}