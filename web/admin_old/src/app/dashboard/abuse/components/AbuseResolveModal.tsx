"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { X, Loader2, AlertTriangle, CheckCircle2 } from "lucide-react";
import type { AbuseReport } from "../page";

interface AbuseResolveModalProps {
  report: AbuseReport;
  onResolved: () => void;
  onClose: () => void;
}

const resolutionActions = [
  {
    value: "action_taken",
    label: "Action Taken",
    description: "User was warned or service was suspended/restricted",
  },
  {
    value: "no_action",
    label: "No Action Needed",
    description: "Report was determined to be invalid or false positive",
  },
  {
    value: "escalated",
    label: "Escalated",
    description: "Issue was escalated to higher-level support or legal team",
  },
  {
    value: "banned",
    label: "User Banned",
    description: "User was permanently banned as a result of the report",
  },
  {
    value: "automated_resolved",
    label: "Auto-Resolution",
    description: "System automatically handled the issue",
  },
];

const actionTypeLabels: Record<string, string> = {
  suspend_service: "Suspend Service",
  warn_user: "Warn User",
  restrict_access: "Restrict Access",
  ban_user: "Ban User",
  no_action: "No Action",
};

export function AbuseResolveModal({ report, onResolved, onClose }: AbuseResolveModalProps) {
  const [resolutionAction, setResolutionAction] = useState("action_taken");
  const [actionType, setActionType] = useState<string>("");
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [notifyUser, setNotifyUser] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resolutionNotes.trim()) {
      setError("Please provide resolution notes.");
      return;
    }

    try {
      setError(null);
      setProcessing(true);
      await api.patch(`/admin/abuse-reports/${report.id}`, {
        status: "resolved",
        resolution: {
          action: resolutionAction,
          action_type: actionType || undefined,
          notes: resolutionNotes.trim(),
          notify_user: notifyUser,
        },
      });
      onResolved();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to resolve report";
      setError(msg);
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="relative w-full max-w-lg max-h-[90vh] overflow-hidden rounded-xl border bg-card shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4 shrink-0">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-green-100 p-2 text-green-600 dark:bg-green-900 dark:text-green-300">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold">Resolve Report</h2>
              <p className="text-sm text-muted-foreground">
                #{report.id.slice(0, 8)} &middot;{" "}
                {report.type} &middot;{" "}
                <span className="capitalize">{report.severity}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-muted-foreground hover:bg-muted transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5">
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                <p>{error}</p>
              </div>
            </div>
          )}

          {/* Resolution Action */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Resolution Action
            </label>
            <select
              value={resolutionAction}
              onChange={(e) => setResolutionAction(e.target.value)}
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
            >
              {resolutionActions.map((action) => (
                <option key={action.value} value={action.value}>
                  {action.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-muted-foreground">
              {resolutionActions.find((a) => a.value === resolutionAction)?.description}
            </p>
          </div>

          {/* Action Type (conditional) */}
          {resolutionAction === "action_taken" && (
            <div>
              <label className="block text-sm font-medium mb-2">
                Specific Action Taken
              </label>
              <select
                value={actionType}
                onChange={(e) => setActionType(e.target.value)}
                className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">Select action...</option>
                {Object.entries(actionTypeLabels).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
          )}

          {/* Resolution Notes */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Resolution Notes <span className="text-red-500">*</span>
            </label>
            <textarea
              value={resolutionNotes}
              onChange={(e) => setResolutionNotes(e.target.value)}
              placeholder="Describe how this report was resolved, what actions were taken, and any relevant context..."
              rows={5}
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary resize-none"
            />
          </div>

          {/* Notify User */}
          <div className="flex items-start gap-3 rounded-lg border p-4">
            <input
              type="checkbox"
              id="notifyUser"
              checked={notifyUser}
              onChange={(e) => setNotifyUser(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
            />
            <div>
              <label htmlFor="notifyUser" className="text-sm font-medium cursor-pointer">
                Notify affected user
              </label>
              <p className="text-xs text-muted-foreground">
                Send an email notification to the reported user about the resolution.
              </p>
            </div>
          </div>

          {/* Report summary */}
          <div className="rounded-lg bg-muted/20 p-4 space-y-1">
            <p className="text-xs font-medium text-muted-foreground">Report Summary</p>
            <p className="text-sm">
              <span className="font-medium">Description:</span>{" "}
              {report.description ? (
                report.description.length > 120
                  ? report.description.slice(0, 120) + "..."
                  : report.description
              ) : (
                "No description"
              )}
            </p>
            {report.evidence && (
              <p className="text-xs text-muted-foreground">
                (Evidence attached: {report.evidence.length} characters)
              </p>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={processing}
              className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-5 py-2 text-sm font-medium text-white hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              {processing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Resolving...
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  Resolve Report
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}