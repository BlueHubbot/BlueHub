"use client";

import type { ModuleRegistryEntry } from "@/lib/api";
import { AlertTriangle, X } from "lucide-react";

interface DisableConfirmModalProps {
  module: ModuleRegistryEntry | null;
  onConfirm: () => void;
  onCancel: () => void;
  loading: boolean;
}

export function DisableConfirmModal({
  module,
  onConfirm,
  onCancel,
  loading,
}: DisableConfirmModalProps) {
  if (!module) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md rounded-lg border bg-card p-6 shadow-lg">
        <div className="flex items-start gap-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
            <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
          </div>
          <div className="flex-1">
            <div className="flex items-start justify-between">
              <h3 className="text-lg font-semibold">Disable Module</h3>
              <button
                onClick={onCancel}
                className="rounded-md p-1 text-muted-foreground hover:bg-accent"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Are you sure you want to disable <strong>{module.display_name}</strong>?
              This will prevent new services from being created under this module.
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              Existing services will continue to run normally. You can re-enable
              the module at any time.
            </p>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="btn-secondary px-4 py-2 text-sm"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
          >
            {loading && (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            )}
            {loading ? "Disabling..." : "Yes, Disable Module"}
          </button>
        </div>
      </div>
    </div>
  );
}