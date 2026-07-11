"use client";

import { useState } from "react";
import {
  Save,
  Smartphone,
  Globe,
  Shield,
  Mail,
  Bell,
  Palette,
  Database,
  RefreshCw,
  Loader2,
  CheckCircle2,
} from "lucide-react";

interface SettingSection {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}

const SETTINGS_SECTIONS: SettingSection[] = [
  {
    id: "general",
    title: "General",
    description: "Basic platform settings and branding",
    icon: <Globe className="h-5 w-5" />,
  },
  {
    id: "security",
    title: "Security",
    description: "Authentication, password policies, and security rules",
    icon: <Shield className="h-5 w-5" />,
  },
  {
    id: "notifications",
    title: "Notifications",
    description: "Email and system notification configuration",
    icon: <Bell className="h-5 w-5" />,
  },
  {
    id: "email",
    title: "Email",
    description: "SMTP settings and email templates",
    icon: <Mail className="h-5 w-5" />,
  },
  {
    id: "appearance",
    title: "Appearance",
    description: "Brand colors, logo, and theme settings",
    icon: <Palette className="h-5 w-5" />,
  },
  {
    id: "maintenance",
    title: "Maintenance",
    description: "System maintenance, cache, and data management",
    icon: <Database className="h-5 w-5" />,
  },
];

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState("general");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [formData, setFormData] = useState({
    // General
    platform_name: "BlueHub",
    platform_url: "https://bluehub.io",
    support_email: "support@bluehub.io",
    default_language: "en",
    timezone: "UTC",
    // Security
    password_min_length: "8",
    password_require_special: true,
    password_require_numbers: true,
    max_login_attempts: "5",
    session_timeout: "3600",
    two_factor_required: false,
    // Notifications
    email_notifications: true,
    abuse_report_notifications: true,
    service_expiry_notifications: true,
    system_alert_notifications: true,
    // Email
    smtp_host: "",
    smtp_port: "587",
    smtp_user: "",
    smtp_pass: "",
    smtp_encryption: "tls",
    from_address: "noreply@bluehub.io",
    from_name: "BlueHub",
    // Appearance
    primary_color: "#1a56db",
    logo_url: "",
    favicon_url: "",
    custom_css: "",
  });

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;
    const checked = (e.target as HTMLInputElement).checked;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaved(false);

    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } finally {
      setSaving(false);
    }
  };

  const handleClearCache = async () => {
    try {
      await new Promise((resolve) => setTimeout(resolve, 500));
      toast.success("Cache cleared successfully");
    } catch {
      toast.error("Failed to clear cache");
    }
  };

  const renderSection = () => {
    switch (activeSection) {
      case "general":
        return (
          <div className="space-y-6">
            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Platform Name
                </label>
                <input
                  type="text"
                  name="platform_name"
                  value={formData.platform_name}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Platform URL
                </label>
                <input
                  type="url"
                  name="platform_url"
                  value={formData.platform_url}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Support Email
                </label>
                <input
                  type="email"
                  name="support_email"
                  value={formData.support_email}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Default Language
                </label>
                <select
                  name="default_language"
                  value={formData.default_language}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="en">English</option>
                  <option value="fa">Persian (Farsi)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Timezone
                </label>
                <select
                  name="timezone"
                  value={formData.timezone}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="UTC">UTC</option>
                  <option value="Asia/Tehran">Asia/Tehran (UTC+3:30)</option>
                  <option value="America/New_York">America/New_York</option>
                  <option value="Europe/London">Europe/London</option>
                  <option value="Asia/Dubai">Asia/Dubai</option>
                </select>
              </div>
            </div>
          </div>
        );

      case "security":
        return (
          <div className="space-y-6">
            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Minimum Password Length
                </label>
                <input
                  type="number"
                  name="password_min_length"
                  value={formData.password_min_length}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Max Login Attempts
                </label>
                <input
                  type="number"
                  name="max_login_attempts"
                  value={formData.max_login_attempts}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Session Timeout (seconds)
                </label>
                <input
                  type="number"
                  name="session_timeout"
                  value={formData.session_timeout}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
            </div>

            <div className="space-y-4">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  name="password_require_special"
                  checked={formData.password_require_special}
                  onChange={handleChange}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <span className="text-sm">Require special characters in passwords</span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  name="password_require_numbers"
                  checked={formData.password_require_numbers}
                  onChange={handleChange}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <span className="text-sm">Require numbers in passwords</span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  name="two_factor_required"
                  checked={formData.two_factor_required}
                  onChange={handleChange}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <span className="text-sm">Require two-factor authentication</span>
              </label>
            </div>
          </div>
        );

      case "notifications":
        return (
          <div className="space-y-6">
            <div className="space-y-4">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  name="email_notifications"
                  checked={formData.email_notifications}
                  onChange={handleChange}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <span className="text-sm">Enable email notifications</span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  name="abuse_report_notifications"
                  checked={formData.abuse_report_notifications}
                  onChange={handleChange}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <span className="text-sm">Abuse report notifications</span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  name="service_expiry_notifications"
                  checked={formData.service_expiry_notifications}
                  onChange={handleChange}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <span className="text-sm">Service expiry notifications</span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  name="system_alert_notifications"
                  checked={formData.system_alert_notifications}
                  onChange={handleChange}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <span className="text-sm">System alert notifications</span>
              </label>
            </div>
          </div>
        );

      case "email":
        return (
          <div className="space-y-6">
            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  SMTP Host
                </label>
                <input
                  type="text"
                  name="smtp_host"
                  value={formData.smtp_host}
                  onChange={handleChange}
                  placeholder="smtp.example.com"
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  SMTP Port
                </label>
                <input
                  type="number"
                  name="smtp_port"
                  value={formData.smtp_port}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  SMTP Username
                </label>
                <input
                  type="text"
                  name="smtp_user"
                  value={formData.smtp_user}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  SMTP Password
                </label>
                <input
                  type="password"
                  name="smtp_pass"
                  value={formData.smtp_pass}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Encryption
                </label>
                <select
                  name="smtp_encryption"
                  value={formData.smtp_encryption}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="tls">TLS</option>
                  <option value="ssl">SSL</option>
                  <option value="none">None</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  From Address
                </label>
                <input
                  type="email"
                  name="from_address"
                  value={formData.from_address}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  From Name
                </label>
                <input
                  type="text"
                  name="from_name"
                  value={formData.from_name}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
            </div>
          </div>
        );

      case "appearance":
        return (
          <div className="space-y-6">
            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Primary Color
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="color"
                    name="primary_color"
                    value={formData.primary_color}
                    onChange={handleChange}
                    className="h-10 w-10 rounded-lg border border-input cursor-pointer"
                  />
                  <input
                    type="text"
                    name="primary_color"
                    value={formData.primary_color}
                    onChange={handleChange}
                    className="flex-1 rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Logo URL
                </label>
                <input
                  type="url"
                  name="logo_url"
                  value={formData.logo_url}
                  onChange={handleChange}
                  placeholder="https://example.com/logo.png"
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Favicon URL
                </label>
                <input
                  type="url"
                  name="favicon_url"
                  value={formData.favicon_url}
                  onChange={handleChange}
                  placeholder="https://example.com/favicon.ico"
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Custom CSS
              </label>
              <textarea
                name="custom_css"
                value={formData.custom_css}
                onChange={handleChange}
                rows={6}
                className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm font-mono focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                placeholder="/* Custom styles */"
              />
            </div>
          </div>
        );

      case "maintenance":
        return (
          <div className="space-y-6">
            <div className="grid gap-6 sm:grid-cols-2">
              <button
                type="button"
                onClick={handleClearCache}
                className="flex items-center gap-3 rounded-xl border bg-card p-6 shadow-sm hover:bg-accent/50 transition-colors text-left"
              >
                <div className="rounded-lg bg-blue-100 p-3 dark:bg-blue-900/30">
                  <RefreshCw className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-medium">Clear Cache</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Clear all cached data and reload
                  </p>
                </div>
              </button>

              <button
                type="button"
                className="flex items-center gap-3 rounded-xl border bg-card p-6 shadow-sm hover:bg-accent/50 transition-colors text-left"
              >
                <div className="rounded-lg bg-purple-100 p-3 dark:bg-purple-900/30">
                  <Database className="h-6 w-6 text-purple-600" />
                </div>
                <div>
                  <h3 className="font-medium">Database Maintenance</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Optimize and vacuum database
                  </p>
                </div>
              </button>
            </div>

            <div className="rounded-xl border bg-card p-6 shadow-sm">
              <h3 className="font-medium text-red-600 dark:text-red-400">Danger Zone</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Irreversible actions that affect system data
              </p>
              <div className="mt-4 flex gap-3">
                <button
                  type="button"
                  className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-100 transition-colors dark:border-red-800 dark:bg-red-900/30 dark:text-red-400"
                  onClick={() => {
                    if (confirm("Are you sure you want to reset all settings to defaults?")) {
                      // Reset logic
                    }
                  }}
                >
                  Reset All Settings
                </button>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="mt-1 text-muted-foreground">
            Configure platform settings and preferences
          </p>
        </div>
        <button
          type="submit"
          form="settings-form"
          disabled={saving}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow transition-colors hover:bg-primary/90 disabled:opacity-50"
        >
          {saving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : saved ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          {saving ? "Saving..." : saved ? "Saved!" : "Save Settings"}
        </button>
      </div>

      <div className="flex flex-col gap-6 lg:flex-row">
        {/* Sidebar Navigation */}
        <nav className="lg:w-64 shrink-0">
          <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
            {SETTINGS_SECTIONS.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 text-sm transition-colors hover:bg-accent ${
                  activeSection === section.id
                    ? "bg-accent font-medium text-foreground border-l-2 border-primary"
                    : "text-muted-foreground border-l-2 border-transparent"
                }`}
              >
                {section.icon}
                <div className="text-left">
                  <div className="font-medium">{section.title}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    {section.description}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </nav>

        {/* Settings Content */}
        <div className="flex-1">
          <form id="settings-form" onSubmit={handleSave}>
            <div className="rounded-xl border bg-card p-6 shadow-sm">
              <h2 className="text-lg font-semibold mb-6">
                {SETTINGS_SECTIONS.find((s) => s.id === activeSection)?.title}
              </h2>
              {renderSection()}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// Simple toast for demo
const toast = {
  success: (msg: string) => console.log("SUCCESS:", msg),
  error: (msg: string) => console.log("ERROR:", msg),
};