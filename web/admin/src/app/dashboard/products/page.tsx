"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { getUser } from "@/lib/auth";
import { Plus, Search, CheckSquare, Square, Package, ExternalLink } from "lucide-react";
import { ProductFormModal } from "./components/ProductFormModal";
import { ProductDeleteModal } from "./components/ProductDeleteModal";

export interface ProductData {
  id: string;
  module_name: string;
  product_key: string;
  name: string;
  description_i18n: Record<string, string> | null;
  price: number;
  billing_cycle: string;
  metadata: Record<string, unknown> | null;
  sort_order: number;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ModuleOption {
  module_name: string;
  display_name: string;
}

export default function ProductsPage() {
  const router = useRouter();
  const user = getUser();
  const [products, setProducts] = useState<ProductData[]>([]);
  const [modules, setModules] = useState<ModuleOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filterModule, setFilterModule] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkAction, setBulkAction] = useState<"activate" | "deactivate" | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<ProductData | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ProductData | null>(null);

  const fetchProducts = useCallback(async () => {
    try {
      setError(null);
      const res = await api.get<ProductData[]>("/admin/products");
      setProducts(res.data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load products";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchModules = useCallback(async () => {
    try {
      const res = await api.get<ModuleOption[]>("/admin/modules");
      setModules(res.data);
    } catch {
      // Modules endpoint may not exist yet; silently fallback
    }
  }, []);

  useEffect(() => {
    if (!user || !["admin", "superadmin"].includes(user.role)) {
      router.push("/login");
      return;
    }
    fetchProducts();
    fetchModules();
  }, [user, router, fetchProducts, fetchModules]);

  const filtered = products.filter((p) => {
    if (search) {
      const q = search.toLowerCase();
      if (
        !p.name.toLowerCase().includes(q) &&
        !p.product_key.toLowerCase().includes(q) &&
        !p.module_name.toLowerCase().includes(q)
      ) {
        return false;
      }
    }
    if (filterModule && p.module_name !== filterModule) return false;
    return true;
  });

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === filtered.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(filtered.map((p) => p.id)));
    }
  };

  const executeBulkAction = async (action: "activate" | "deactivate") => {
    try {
      setBulkAction(action);
      const active = action === "activate";
      await Promise.all(
        Array.from(selected).map((id) =>
          api.patch(`/admin/products/${id}`, { is_active: active })
        )
      );
      setSelected(new Set());
      await fetchProducts();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : `Failed to ${action} products`;
      setError(msg);
    } finally {
      setBulkAction(null);
    }
  };

  const handleSaved = () => {
    setFormOpen(false);
    setEditingProduct(null);
    fetchProducts();
  };

  const sortedByOrder = [...filtered].sort((a, b) => a.sort_order - b.sort_order);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Products</h1>
          <p className="text-sm text-muted-foreground">
            Manage product catalog with pricing, i18n descriptions, and activation.
          </p>
        </div>
        <button
          onClick={() => {
            setEditingProduct(null);
            setFormOpen(true);
          }}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Product
        </button>
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
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by name, key, or module..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border bg-background py-2 pl-10 pr-4 text-sm outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <select
            value={filterModule}
            onChange={(e) => setFilterModule(e.target.value)}
            className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="">All Modules</option>
            {modules.map((m) => (
              <option key={m.module_name} value={m.module_name}>
                {m.display_name}
              </option>
            ))}
          </select>
        </div>

        {/* Summary */}
        <p className="text-sm text-muted-foreground">
          {sortedByOrder.length} product{sortedByOrder.length !== 1 && "s"}
          {selected.size > 0 && ` (${selected.size} selected)`}
        </p>
      </div>

      {/* Bulk actions */}
      {selected.size > 0 && (
        <div className="flex items-center gap-3 rounded-lg border bg-muted/50 p-3">
          <span className="text-sm font-medium">{selected.size} selected</span>
          <button
            onClick={() => executeBulkAction("activate")}
            disabled={bulkAction !== null}
            className="rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            {bulkAction === "activate" ? "Activating..." : "Activate All"}
          </button>
          <button
            onClick={() => executeBulkAction("deactivate")}
            disabled={bulkAction !== null}
            className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
          >
            {bulkAction === "deactivate" ? "Deactivating..." : "Deactivate All"}
          </button>
          <button
            onClick={() => setSelected(new Set())}
            className="ml-auto text-xs text-muted-foreground underline"
          >
            Clear selection
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      )}

      {/* Empty state */}
      {!loading && sortedByOrder.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Package className="h-12 w-12 text-muted-foreground/50" />
          <h3 className="mt-4 text-lg font-medium">No products found</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {search || filterModule
              ? "Try a different search or filter."
              : "Get started by creating your first product."}
          </p>
          {!search && !filterModule && (
            <button
              onClick={() => {
                setEditingProduct(null);
                setFormOpen(true);
              }}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Plus className="h-4 w-4" />
              New Product
            </button>
          )}
        </div>
      )}

      {/* Product table */}
      {!loading && sortedByOrder.length > 0 && (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="w-10 px-4 py-3 text-left">
                  <button onClick={toggleSelectAll} className="text-muted-foreground hover:text-foreground">
                    {selected.size === filtered.length && filtered.length > 0 ? (
                      <CheckSquare className="h-4 w-4" />
                    ) : (
                      <Square className="h-4 w-4" />
                    )}
                  </button>
                </th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Order</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Name / Key</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Module</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">Price</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Billing</th>
                <th className="px-4 py-3 text-center font-medium text-muted-foreground">Active</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {sortedByOrder.map((product) => (
                <tr
                  key={product.id}
                  className={`group hover:bg-muted/30 transition-colors ${
                    !product.is_active ? "opacity-60" : ""
                  }`}
                >
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleSelect(product.id)}
                      className="text-muted-foreground hover:text-foreground"
                    >
                      {selected.has(product.id) ? (
                        <CheckSquare className="h-4 w-4" />
                      ) : (
                        <Square className="h-4 w-4" />
                      )}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{product.sort_order}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col">
                      <span className="font-medium">{product.name}</span>
                      <span className="text-xs text-muted-foreground">{product.product_key}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-block rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                      {product.module_name}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    ${product.price.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {product.billing_cycle.charAt(0) + product.billing_cycle.slice(1).toLowerCase()}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`inline-block h-2.5 w-2.5 rounded-full ${
                        product.is_active ? "bg-green-500" : "bg-red-400"
                      }`}
                      title={product.is_active ? "Active" : "Inactive"}
                    />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => {
                          setEditingProduct(product);
                          setFormOpen(true);
                        }}
                        className="rounded-md border px-2.5 py-1 text-xs font-medium hover:bg-muted transition-colors"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => setDeleteTarget(product)}
                        className="rounded-md border border-red-200 px-2.5 py-1 text-xs font-medium text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create/Edit Modal */}
      {formOpen && (
        <ProductFormModal
          product={editingProduct}
          modules={modules}
          onSaved={handleSaved}
          onClose={() => {
            setFormOpen(false);
            setEditingProduct(null);
          }}
        />
      )}

      {/* Delete Modal */}
      {deleteTarget && (
        <ProductDeleteModal
          product={deleteTarget}
          onDeleted={() => {
            setDeleteTarget(null);
            fetchProducts();
          }}
          onClose={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}