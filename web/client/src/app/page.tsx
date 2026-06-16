import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between text-sm">
        <h1 className="text-4xl font-bold text-center mb-8 animate-fade-in">
          BlueHub
        </h1>
        <p className="text-xl text-muted-foreground text-center mb-12 animate-fade-in">
          Professional VPN & Service Management Panel
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="p-6 bg-card rounded-lg border shadow-sm hover:shadow-md transition-shadow">
            <h2 className="text-lg font-semibold mb-2">VPN Management</h2>
            <p className="text-muted-foreground">
              WireGuard and Xray (V2Ray) protocol support
            </p>
          </div>

          <div className="p-6 bg-card rounded-lg border shadow-sm hover:shadow-md transition-shadow">
            <h2 className="text-lg font-semibold mb-2">Multi-Tenant</h2>
            <p className="text-muted-foreground">
              RBAC with admin/reseller/user roles
            </p>
          </div>

          <div className="p-6 bg-card rounded-lg border shadow-sm hover:shadow-md transition-shadow">
            <h2 className="text-lg font-semibold mb-2">Billing System</h2>
            <p className="text-muted-foreground">
              Integrated payment gateway with Paymenter
            </p>
          </div>
        </div>

        <div className="flex gap-4 justify-center">
          <Link
            href="/login"
            className="inline-flex items-center justify-center rounded-md bg-primary px-8 py-3 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
          >
            Login
          </Link>
          <Link
            href="/register"
            className="inline-flex items-center justify-center rounded-md border border-input bg-background px-8 py-3 text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            Register
          </Link>
        </div>
      </div>
    </main>
  );
}