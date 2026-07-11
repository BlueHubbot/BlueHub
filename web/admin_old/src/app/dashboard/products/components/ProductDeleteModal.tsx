"use client";

import { useState } from "react";
import { X, AlertTriangle } from "lucide-react";
import type { ProductData } from "../page";

interface ProductDeleteModalProps {
  product: ProductData;
  onDeleted: () => void;
  onClose: () => void;
}

export function ProductDeleteModal({ product, onDeleted, onClose }: ProductDeleteModalProps) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDelete = async () => {
    try {
      setDeleting(true);
      setError(null);

      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || ""}/admin/products/${product.id}`,
        {
          method: "DELETE",
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        }
      );

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      onDeleted();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete product";
      setError(msg);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-xl border bg-background shadow-2xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="text-lg font-semibold text-red-600 dark:text-red-400">
            Delete Product
          </h2>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
              {error}
            </div>
          )}

          <div className="flex items-start gap-4">
            <div className="rounded-full bg-red-100 p-2 dark:bg-red-900">
              <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">
                Are you sure you want to delete this product?
              </p>
              <div className="mt-2 rounded-lg border bg-muted/50 p-3 space-y-1">
                <p className="text-sm">
                  <span className="font-medium">Name:</span> {product.name}
                </p>
                <p className="text-sm">
                  <span className="font-medium">Key:</span> {product.product_key}
                </p>
                <p className="text-sm">
                  <span className="font-medium">Module:</span> {product.module_name}
                </p>
                <p className="text-sm">
                  <span className="font-medium">Price:</span> ${product.price.toFixed(2)}
                </p>
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                This action cannot be undone. Any services using this product may be affected.
                Consider deactivating the product instead of deleting it.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 border-t px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
          >
            {deleting ? "Deleting..." : "Delete Product"}
          </button>
        </div>
      </div>
    </div>
  );
}