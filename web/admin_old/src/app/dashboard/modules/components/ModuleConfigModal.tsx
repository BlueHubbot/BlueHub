"use client";

import { useState } from "react";
import type { ModuleRegistryEntry, ModuleTogglePayload } from "@/lib/api";
import { X, Save } from "lucide-react";

interface ModuleConfigModalProps {
  module: ModuleRegistryEntry | null;
  onClose: () => void;
  onSave: (name: string, payload: ModuleTogglePayload) => Promise<void>;
}

export function ModuleConfigModal({
  module,
  onClose,
  onSave,
}: ModuleConfigModalProps) {
  const [enabled, setEnabled] = useState(module?.enabled ?? true);
  const [stopNewSales, setStopNewSales] = useState(
    module?.flags.stop_new_sales ?? false
  );
  const [terminateServices, setTerminateServices] = useState(
    module?.flags.terminate_services ?? false
  );
  const [maintenanceMode, setMaintenanceMode] = useState(
    module?.flags.maintenance_mode ?? false
  );
  const [saving, setSaving] = useState(false);

  if (!module) return null;

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(module.module_name, {
        enabled,
        stop_new_sales: stopNewSales,
        terminate_services: terminateServices,
        maintenance_mode: maintenanceMode,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg rounded-lg border bg-card shadow-lg">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div>
            <h3 className="text-lg font-semibold">
              Configure Module: {module.display_name}
            </h3>
            <p className="text-sm text-muted-foreground">
              {module.module_name} v{module.version}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-muted-foreground hover:bg-accent"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="space-y-6 px-6 py-4">
          {/* Enabled toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Enabled</p>
              <p className="text-sm text-muted-foreground">
                When disabled, no new services can be created under this module.
              </p>
            </div>
            <label className="relative inline-flex cursor-pointer items-center">
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
                className="peer sr-only"
              />
              <div className="h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all after:content-[''] peer-checked:bg-primary peer-checked:after:translate-x-full peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary/50 dark:bg-gray-700" />
            </label>
          </div>

          <hr className="border-t" />

          {/* Feature Flags */}
          <div>
            <h4 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              Feature Flags
            </h4>

            <div className="space-y-4">
              {/* Stop New Sales */}
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Stop New Sales</p>
                  <p className="text-sm text-muted-foreground">
                    Prevent new purchases/orders for this module. Existing
                    services remain active.
                  </p>
                </div>
                <label className="relative inline-flex cursor-pointer items-center">
                  <input
                    type="checkbox"
                    checked={stopNewSales}
                    onChange={(e) => setStopNewSales(e.target.checked)}
                    className="peer sr-only"
                  />
                  <div className="h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all after:content-[''] peer-checked:bg-yellow-500 peer-checked:after:translate-x-full peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-yellow-500/50 dark:bg-gray-700" />
                </label>
              </div>

              {/* Maintenance Mode */}
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Maintenance Mode</p>
                  <p className="text-sm text-muted-foreground">
                    Put the module into maintenance mode. Services may be
                    temporarily unavailable.
                  </p>
                </div>
                <label className="relative inline-flex cursor-pointer items-center">
                  <input
                    type="checkbox"
                    checked={maintenanceMode}
                    onChange={(e) => setMaintenanceMode(e.target.checked)}
                    className="peer sr-only"
                  />
                  <div className="h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all after:content-[''] peer-checked:bg-blue-500 peer-checked:after:translate-x-full peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500/50 dark:bg-gray-700" />
                </label>
              </div>

              {/* Terminate Services */}
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Terminate Services</p>
                  <p className="text-sm text-muted-foreground">
                    ⚠️ Immediately terminate all services under this module.
                    This is a destructive action.
                  </p>
                </div>
                <label className="relative inline-flex cursor-pointer items-center">
                  <input
                    type="checkbox"
                    checked={terminateServices}
                    onChange={(e) => setTerminateServices(e.target.checked)}
                    className="peer sr-only"
                  />
                  <div className="h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all after:content-[''] peer-checked:bg-red-500 peer-checked:after:translate-x-full peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-red-500/50 dark:bg-gray-700" />
                </label>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t px-6 py-4">
          <button
            onClick={onClose}
            disabled={saving}
            className="btn-secondary px-4 py-2 text-sm"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary inline-flex items-center gap-2 px-4 py-2 text-sm"
          >
            {saving ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {saving ? "Saving..." : "Save Configuration"}
          </button>
        </div>
      </div>
    </div>
  );
}