"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/providers";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------
type StreamingService = {
  id: string;
  name: string;
  plan: "basic" | "premium" | "family";
  stream_type: "iptv" | "vod" | "catchup" | "hybrid";
  status: "active" | "suspended" | "expired" | "deleted";
  max_devices: number;
  active_devices: number;
  created_at: string;
  expires_at: string | null;
};

type StreamingProduct = {
  id: string;
  name: string;
  stream_type: string;
  description: string;
  price_monthly: number;
  price_yearly: number;
  is_available: boolean;
};

type StreamingConfig = {
  m3u_url: string;
  epg_url: string;
  xtream_username: string | null;
  xtream_password: string | null;
  xtream_host: string | null;
  allowed_ip_count: number;
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
// Persian Labels
// ------------------------------------------------------------------
const FA_LABELS: Record<string, string> = {
  title: "مدیریت استریم",
  subtitle: "مدیریت سرویس‌های IPTV، VOD و تماشای زنده",
  createService: "خرید سرویس جدید",
  activeServices: "سرویس‌های فعال",
  availablePlans: "پلن‌های موجود",
  streamType: "نوع استریم",
  plan: "پلن",
  devices: "دستگاه‌ها",
  status: "وضعیت",
  actions: "عملیات",
  downloadPlaylist: "دانلود M3U",
  copyCredentials: "کپی اطلاعات",
  epgGuide: "راهنمای EPG",
  deleteService: "حذف",
  confirmDelete: "حذف سرویس",
  confirmDeleteMsg: "آیا از حذف این سرویس استریم اطمینان دارید؟",
  cancel: "انصراف",
  confirm: "تأیید",
  loading: "در حال بارگذاری...",
  error: "خطا",
  retry: "تلاش مجدد",
  buyNow: "خرید",
  monthly: "ماهانه",
  yearly: "سالانه",
  from: "از",
  devicesLabel: "تعداد دستگاه",
  active: "فعال",
  suspended: "معلق",
  expired: "منقضی",
  deleted: "حذف شده",
  iptv: "IPTV",
  vod: "VOD",
  catchup: "بازپخش",
  hybrid: "ترکیبی",
  basic: "پایه",
  premium: "ویژه",
  family: "خانوادگی",
  configInfo: "اطلاعات پیکربندی",
  m3uUrl: "آدرس M3U",
  epgUrl: "آدرس EPG",
  xtreamUser: "نام کاربری Xtream",
  xtreamPass: "رمز عبور Xtream",
  xtreamHost: "هاست Xtream",
  allowedIps: "IP های مجاز",
  close: "بستن",
  copied: "کپی شد!",
  buyTitle: "خرید سرویس استریم",
  selectPlan: "انتخاب پلن",
  selectType: "نوع استریم",
  purchase: "پرداخت و خرید",
  logout: "خروج",
  dashboard: "داشبورد",
  streaming: "استریم",
  noServices: "هیچ سرویس استریمی یافت نشد",
  noProducts: "پلنی برای فروش موجود نیست",
  createFirst: "اولین سرویس استریم خود را خریداری کنید",
};

// ------------------------------------------------------------------
// Icons
// ------------------------------------------------------------------
function PlayIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 010 1.972l-11.54 6.347c-.75.412-1.667-.13-1.667-.986V5.653z" />
    </svg>
  );
}

function TvIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 20.25h12m-7.5-3v3m3-3v3m-10.125-3h17.25c.621 0 1.125-.504 1.125-1.125V4.875c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125z" />
    </svg>
  );
}

function DownloadIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
    </svg>
  );
}

function ClipboardIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
    </svg>
  );
}

function TrashIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
    </svg>
  );
}

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  );
}

function EyeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}

function DevicesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18.75h3" />
    </svg>
  );
}

function ShieldCheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
    </svg>
  );
}

// ------------------------------------------------------------------
// Status Badge Component
// ------------------------------------------------------------------
function StatusBadge({ status }: { status: StreamingService["status"] }) {
  const variants: Record<string, string> = {
    active: "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800",
    suspended: "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-800",
    expired: "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800",
    deleted: "bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-900/30 dark:text-gray-300 dark:border-gray-800",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${variants[status] || variants.active}`}>
      {FA_LABELS[status] || status}
    </span>
  );
}

function StreamTypeBadge({ streamType }: { streamType: StreamingService["stream_type"] }) {
  const typeColors: Record<string, string> = {
    iptv: "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300",
    vod: "bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/30 dark:text-purple-300",
    catchup: "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-300",
    hybrid: "bg-indigo-100 text-indigo-800 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-300",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${typeColors[streamType] || typeColors.iptv}`}>
      {FA_LABELS[streamType] || streamType}
    </span>
  );
}

// ------------------------------------------------------------------
// Config Modal Component
// ------------------------------------------------------------------
function ConfigModal({
  config,
  onClose,
}: {
  config: StreamingConfig;
  onClose: () => void;
}) {
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const copyToClipboard = async (text: string, field: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-xl bg-white shadow-xl dark:bg-gray-800">
        <div className="flex items-center justify-between border-b p-4">
          <h3 className="text-lg font-semibold">{FA_LABELS.configInfo}</h3>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700"
          >
            ✕
          </button>
        </div>
        <div className="space-y-4 p-4">
          {/* M3U URL */}
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">{FA_LABELS.m3uUrl}</label>
            <div className="flex gap-2">
              <input
                type="text"
                readOnly
                value={config.m3u_url}
                className="flex-1 rounded-lg border bg-gray-50 px-3 py-2 text-sm font-mono dark:bg-gray-900 dark:border-gray-600"
              />
              <button
                onClick={() => copyToClipboard(config.m3u_url, "m3u")}
                className="rounded-lg border bg-gray-50 px-3 py-2 text-xs font-medium hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-700"
              >
                {copiedField === "m3u" ? FA_LABELS.copied : FA_LABELS.copyCredentials}
              </button>
            </div>
          </div>

          {/* EPG URL */}
          {config.epg_url && (
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">{FA_LABELS.epgUrl}</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  readOnly
                  value={config.epg_url}
                  className="flex-1 rounded-lg border bg-gray-50 px-3 py-2 text-sm font-mono dark:bg-gray-900 dark:border-gray-600"
                />
                <button
                  onClick={() => copyToClipboard(config.epg_url, "epg")}
                  className="rounded-lg border bg-gray-50 px-3 py-2 text-xs font-medium hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-700"
                >
                  {copiedField === "epg" ? FA_LABELS.copied : FA_LABELS.copyCredentials}
                </button>
              </div>
            </div>
          )}

          {/* Xtream Credentials */}
          {config.xtream_host && (
            <div className="rounded-lg border bg-gray-50 p-3 dark:bg-gray-900 dark:border-gray-600">
              <p className="mb-2 text-xs font-semibold text-gray-500">XTREAM API</p>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">{FA_LABELS.xtreamHost}:</span>
                  <span className="font-mono">{config.xtream_host}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">{FA_LABELS.xtreamUser}:</span>
                  <span className="font-mono">{config.xtream_username}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">{FA_LABELS.xtreamPass}:</span>
                  <span className="font-mono">{config.xtream_password}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">{FA_LABELS.allowedIps}:</span>
                  <span className="font-mono">{config.allowed_ip_count}</span>
                </div>
              </div>
            </div>
          )}
        </div>
        <div className="flex justify-end border-t p-4">
          <button
            onClick={onClose}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            {FA_LABELS.close}
          </button>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// Main Page Component
// ------------------------------------------------------------------
export default function StreamingDashboardPage() {
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const router = useRouter();

  // Services state
  const [services, setServices] = useState<StreamingService[]>([]);
  const [servicesLoading, setServicesLoading] = useState(true);
  const [servicesError, setServicesError] = useState<string | null>(null);

  // Products state
  const [products, setProducts] = useState<StreamingProduct[]>([]);
  const [productsLoading, setProductsLoading] = useState(true);

  // Modal state
  const [showBuyModal, setShowBuyModal] = useState(false);
  const [buyStreamType, setBuyStreamType] = useState<string>("iptv");
  const [buyPlan, setBuyPlan] = useState<string>("basic");
  const [buying, setBuying] = useState(false);
  const [buyError, setBuyError] = useState<string | null>(null);

  const [showConfigModal, setShowConfigModal] = useState(false);
  const [configData, setConfigData] = useState<StreamingConfig | null>(null);
  const [configLoading, setConfigLoading] = useState(false);

  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const [globalError, setGlobalError] = useState<string | null>(null);

  // Auth guard
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  // Fetch streaming services
  const fetchServices = useCallback(async () => {
    try {
      setServicesLoading(true);
      setServicesError(null);
      const data = await apiFetch("/streaming/services");
      setServices(data.services || []);
    } catch (err: any) {
      setServicesError(err.message || "Failed to load streaming services");
    } finally {
      setServicesLoading(false);
    }
  }, []);

  // Fetch available products
  const fetchProducts = useCallback(async () => {
    try {
      setProductsLoading(true);
      const data = await apiFetch("/streaming/products");
      setProducts(data.products || []);
    } catch {
      // silently fail; products section shows empty state
    } finally {
      setProductsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      fetchServices();
      fetchProducts();
    }
  }, [isAuthenticated, fetchServices, fetchProducts]);

  // Purchase streaming service
  const handlePurchase = async () => {
    try {
      setBuying(true);
      setBuyError(null);
      await apiFetch("/streaming/services", {
        method: "POST",
        body: JSON.stringify({
          stream_type: buyStreamType,
          plan: buyPlan,
        }),
      });
      setShowBuyModal(false);
      setBuyStreamType("iptv");
      setBuyPlan("basic");
      await fetchServices();
    } catch (err: any) {
      setBuyError(err.message || "Failed to purchase streaming service");
    } finally {
      setBuying(false);
    }
  };

  // View config
  const handleViewConfig = async (serviceId: string) => {
    try {
      setConfigLoading(true);
      const data = await apiFetch(`/streaming/services/${serviceId}/config`);
      setConfigData(data);
      setShowConfigModal(true);
    } catch (err: any) {
      setGlobalError(err.message || "Failed to load streaming config");
    } finally {
      setConfigLoading(false);
    }
  };

  // Download M3U playlist
  const handleDownloadPlaylist = async (serviceId: string) => {
    try {
      const data = await apiFetch(`/streaming/services/${serviceId}/config`);
      if (data?.m3u_url) {
        window.open(data.m3u_url, "_blank");
      } else {
        setGlobalError("M3U URL not available");
      }
    } catch (err: any) {
      setGlobalError(err.message || "Failed to get M3U URL");
    }
  };

  // Delete service
  const handleDeleteService = async (serviceId: string) => {
    try {
      setDeleting(true);
      await apiFetch(`/streaming/services/${serviceId}`, { method: "DELETE" });
      setDeleteConfirmId(null);
      setServices((prev) => prev.filter((s) => s.id !== serviceId));
    } catch (err: any) {
      setGlobalError(err.message || "Failed to delete streaming service");
    } finally {
      setDeleting(false);
    }
  };

  // Format date
  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return "--";
    return new Date(dateStr).toLocaleDateString("fa-IR", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  // Format price
  const formatPrice = (price: number): string => {
    return price.toLocaleString("fa-IR") + " تومان";
  };

  // Derive selected product for buy modal
  const selectedProduct = products.find(
    (p) => p.stream_type === buyStreamType
  );

  if (isLoading || !isAuthenticated) {
    return (
      <main className="flex min-h-screen items-center justify-center" dir="rtl">
        <div className="animate-pulse text-muted-foreground">{FA_LABELS.loading}</div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col" dir="rtl">
      {/* Header */}
      <header className="border-b">
        <div className="container flex h-16 items-center justify-between py-4">
          <div className="flex items-center gap-8">
            <Link href="/dashboard" className="text-xl font-bold">
              BlueHub
            </Link>
            <nav className="hidden md:flex items-center gap-4">
              <Link href="/dashboard" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                {FA_LABELS.dashboard}
              </Link>
              <Link href="/dashboard/vpn" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                VPN
              </Link>
              <Link href="/dashboard/vps" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                VPS
              </Link>
              <Link href="/dashboard/streaming" className="text-sm font-medium text-foreground">
                {FA_LABELS.streaming}
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">
              {user?.full_name || user?.email}
            </span>
            <button
              onClick={logout}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              {FA_LABELS.logout}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <section className="container py-8">
        {/* Page Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <PlayIcon className="h-7 w-7 text-primary" />
              {FA_LABELS.title}
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              {FA_LABELS.subtitle}
            </p>
          </div>
          <button
            onClick={() => setShowBuyModal(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <PlusIcon className="h-4 w-4" />
            {FA_LABELS.createService}
          </button>
        </div>

        {/* Global Error Banner */}
        {globalError && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800">
            {globalError}
            <button onClick={() => setGlobalError(null)} className="ml-4 font-medium hover:underline">
              {FA_LABELS.close}
            </button>
          </div>
        )}

        {/* Active Services Section */}
        <div className="mb-10">
          <h3 className="mb-4 text-lg font-semibold flex items-center gap-2">
            <TvIcon className="h-5 w-5 text-primary" />
            {FA_LABELS.activeServices}
            {services.length > 0 && (
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                {services.length}
              </span>
            )}
          </h3>

          {servicesLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-pulse text-muted-foreground">{FA_LABELS.loading}</div>
            </div>
          ) : servicesError ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:bg-red-900/30 dark:border-red-800">
              <p className="text-red-800 dark:text-red-300">{servicesError}</p>
              <button
                onClick={fetchServices}
                className="mt-2 text-sm font-medium text-primary hover:underline"
              >
                {FA_LABELS.retry}
              </button>
            </div>
          ) : services.length === 0 ? (
            <div className="rounded-xl border-2 border-dashed p-12 text-center">
              <TvIcon className="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600" />
              <p className="mt-3 text-gray-500">{FA_LABELS.noServices}</p>
              <p className="mt-1 text-sm text-gray-400">{FA_LABELS.createFirst}</p>
              <button
                onClick={() => setShowBuyModal(true)}
                className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                <PlusIcon className="h-4 w-4" />
                {FA_LABELS.createService}
              </button>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {services.map((service) => (
                <div
                  key={service.id}
                  className="rounded-xl border bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:bg-gray-800 dark:border-gray-700"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h4 className="font-semibold">{service.name}</h4>
                      <div className="flex items-center gap-2 mt-1">
                        <StreamTypeBadge streamType={service.stream_type} />
                        <StatusBadge status={service.status} />
                      </div>
                    </div>
                    <span className="rounded-lg bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                      {FA_LABELS[service.plan] || service.plan}
                    </span>
                  </div>

                  {/* Devices info */}
                  <div className="mb-3 flex items-center gap-1 text-sm text-muted-foreground">
                    <DevicesIcon className="h-4 w-4" />
                    <span>
                      {service.active_devices} / {service.max_devices} {FA_LABELS.devices}
                    </span>
                  </div>

                  {/* Dates */}
                  <div className="mb-4 space-y-1 text-xs text-muted-foreground">
                    <div className="flex justify-between">
                      <span>تاریخ ایجاد:</span>
                      <span>{formatDate(service.created_at)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>تاریخ انقضا:</span>
                      <span className={service.status === "expired" ? "text-red-500 font-medium" : ""}>
                        {formatDate(service.expires_at)}
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 border-t pt-3">
                    <button
                      onClick={() => handleViewConfig(service.id)}
                      disabled={configLoading}
                      className="flex-1 inline-flex items-center justify-center gap-1 rounded-lg border bg-gray-50 px-3 py-2 text-xs font-medium hover:bg-gray-100 disabled:opacity-50 dark:bg-gray-900 dark:hover:bg-gray-700 dark:border-gray-600"
                    >
                      <EyeIcon className="h-3.5 w-3.5" />
                      {FA_LABELS.configInfo}
                    </button>
                    <button
                      onClick={() => handleDownloadPlaylist(service.id)}
                      className="flex-1 inline-flex items-center justify-center gap-1 rounded-lg border bg-green-50 px-3 py-2 text-xs font-medium text-green-700 hover:bg-green-100 dark:bg-green-900/20 dark:text-green-400 dark:hover:bg-green-900/40"
                    >
                      <DownloadIcon className="h-3.5 w-3.5" />
                      M3U
                    </button>
                    <button
                      onClick={() => setDeleteConfirmId(service.id)}
                      className="inline-flex items-center justify-center rounded-lg border border-red-200 bg-red-50 px-2.5 py-2 text-xs font-medium text-red-600 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/40"
                    >
                      <TrashIcon className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Available Products Section */}
        <div>
          <h3 className="mb-4 text-lg font-semibold flex items-center gap-2">
            <ShieldCheckIcon className="h-5 w-5 text-primary" />
            {FA_LABELS.availablePlans}
          </h3>

          {productsLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-pulse text-muted-foreground">{FA_LABELS.loading}</div>
            </div>
          ) : products.length === 0 ? (
            <div className="rounded-xl border-2 border-dashed p-8 text-center">
              <p className="text-gray-500">{FA_LABELS.noProducts}</p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {products.map((product) => (
                <div
                  key={product.id}
                  className="rounded-xl border bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:bg-gray-800 dark:border-gray-700"
                >
                  <div className="mb-3 flex items-start justify-between">
                    <h4 className="font-semibold">{product.name}</h4>
                    <StreamTypeBadge
                      streamType={product.stream_type as StreamingService["stream_type"]}
                    />
                  </div>
                  <p className="mb-4 text-sm text-muted-foreground line-clamp-2">
                    {product.description}
                  </p>

                  {/* Price */}
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">{FA_LABELS.monthly}:</span>
                      <span className="font-medium">{formatPrice(product.price_monthly)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">{FA_LABELS.yearly}:</span>
                      <span className="font-medium">{formatPrice(product.price_yearly)}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      setBuyStreamType(product.stream_type);
                      setBuyPlan("basic");
                      setShowBuyModal(true);
                    }}
                    disabled={!product.is_available}
                    className="mt-4 w-full rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {product.is_available ? FA_LABELS.buyNow : "ناموجود"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Buy Modal */}
      {showBuyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl bg-white shadow-xl dark:bg-gray-800">
            <div className="flex items-center justify-between border-b p-4">
              <h3 className="text-lg font-semibold">{FA_LABELS.buyTitle}</h3>
              <button
                onClick={() => {
                  if (!buying) setShowBuyModal(false);
                }}
                disabled={buying}
                className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 disabled:opacity-50"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 p-4">
              {/* Stream Type Selection */}
              <div>
                <label className="mb-2 block text-sm font-medium">{FA_LABELS.selectType}</label>
                <div className="grid grid-cols-2 gap-2">
                  {["iptv", "vod", "catchup", "hybrid"].map((type) => (
                    <button
                      key={type}
                      onClick={() => setBuyStreamType(type)}
                      className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                        buyStreamType === type
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
                      }`}
                    >
                      {FA_LABELS[type] || type}
                    </button>
                  ))}
                </div>
              </div>

              {/* Plan Selection */}
              <div>
                <label className="mb-2 block text-sm font-medium">{FA_LABELS.selectPlan}</label>
                <div className="grid grid-cols-3 gap-2">
                  {["basic", "premium", "family"].map((plan) => (
                    <button
                      key={plan}
                      onClick={() => setBuyPlan(plan)}
                      className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                        buyPlan === plan
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
                      }`}
                    >
                      {FA_LABELS[plan] || plan}
                    </button>
                  ))}
                </div>
              </div>

              {/* Price Display */}
              {selectedProduct && (
                <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-900">
                  <p className="text-sm text-muted-foreground">
                    {FA_LABELS.from}
                    {" "}
                    <span className="font-semibold text-foreground">
                      {formatPrice(selectedProduct.price_monthly)}
                    </span>
                    {" "}
                    {FA_LABELS.monthly}
                  </p>
                </div>
              )}

              {/* Error */}
              {buyError && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:bg-red-900/30 dark:text-red-300">
                  {buyError}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 border-t p-4">
              <button
                onClick={() => setShowBuyModal(false)}
                disabled={buying}
                className="rounded-lg border px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                {FA_LABELS.cancel}
              </button>
              <button
                onClick={handlePurchase}
                disabled={buying || !selectedProduct?.is_available}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {buying ? FA_LABELS.loading : FA_LABELS.purchase}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Config Modal */}
      {showConfigModal && configData && (
        <ConfigModal
          config={configData}
          onClose={() => {
            setShowConfigModal(false);
            setConfigData(null);
          }}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm rounded-xl bg-white shadow-xl dark:bg-gray-800">
            <div className="border-b p-4">
              <h3 className="text-lg font-semibold text-red-600">{FA_LABELS.confirmDelete}</h3>
            </div>
            <div className="p-4">
              <p className="text-sm text-muted-foreground">{FA_LABELS.confirmDeleteMsg}</p>
            </div>
            <div className="flex justify-end gap-3 border-t p-4">
              <button
                onClick={() => setDeleteConfirmId(null)}
                disabled={deleting}
                className="rounded-lg border px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                {FA_LABELS.cancel}
              </button>
              <button
                onClick={() => handleDeleteService(deleteConfirmId)}
                disabled={deleting}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleting ? FA_LABELS.loading : FA_LABELS.confirm}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}