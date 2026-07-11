import {
  Banknote,
  Calendar,
  ChartBar,
  CheckSquare,
  Fingerprint,
  Forklift,
  Gauge,
  GraduationCap,
  Kanban,
  LayoutDashboard,
  ListTodo,
  Lock,
  type LucideIcon,
  Mail,
  MessageSquare,
  ReceiptText,
  Server,
  ShoppingBag,
  SquareArrowUpRight,
  Users,
} from "lucide-react";

export type NavBadge = "new" | "soon";

export interface NavSubItem {
  id: string;
  titleKey: string;
  url: string;
  icon?: LucideIcon;
  badge?: NavBadge;
  disabled?: boolean;
  newTab?: boolean;
}

interface NavItemBase {
  id: string;
  titleKey: string;
  icon?: LucideIcon;
  badge?: NavBadge;
  disabled?: boolean;
  newTab?: boolean;
}

export interface NavMainLinkItem extends NavItemBase {
  url: string;
  subItems?: never;
}

export interface NavMainParentItem extends NavItemBase {
  subItems: NavSubItem[];
}

export type NavMainItem = NavMainLinkItem | NavMainParentItem;

export interface NavGroup {
  id: number;
  labelKey: string;
  items: NavMainItem[];
}

export const sidebarItems: NavGroup[] = [
  {
    id: 1,
    labelKey: "dashboards",
    items: [
      {
        id: "default",
        titleKey: "overview",
        url: "/dashboard/default",
        icon: LayoutDashboard,
      },
      {
        id: "crm",
        titleKey: "crm",
        url: "/dashboard/crm",
        icon: ChartBar,
      },
      {
        id: "finance",
        titleKey: "finance",
        url: "/dashboard/finance",
        icon: Banknote,
      },
      {
        id: "analytics",
        titleKey: "analytics",
        url: "/dashboard/analytics",
        icon: Gauge,
      },
      {
        id: "productivity",
        titleKey: "productivity",
        url: "/dashboard/productivity",
        icon: ListTodo,
      },
      {
        id: "ecommerce",
        titleKey: "ecommerce",
        url: "/dashboard/ecommerce",
        icon: ShoppingBag,
      },
      {
        id: "academy",
        titleKey: "academy",
        url: "/dashboard/academy",
        icon: GraduationCap,
      },
      {
        id: "logistics",
        titleKey: "logistics",
        url: "/dashboard/logistics",
        icon: Forklift,
      },
    ],
  },
  {
    id: 2,
    labelKey: "core_services",
    items: [
      {
        id: "infrastructure",
        titleKey: "vpn",
        url: "/dashboard/infrastructure",
        icon: Server,
        badge: "new",
      },
      {
        id: "smart-dns",
        titleKey: "smart_dns",
        url: "/dashboard/smart-dns",
        icon: Server,
      },
      {
        id: "tasks",
        titleKey: "tasks",
        url: "/dashboard/tasks",
        icon: CheckSquare,
      },
    ],
  },
  {
    id: 3,
    labelKey: "pages",
    items: [
      {
        id: "email",
        titleKey: "email",
        url: "/dashboard/mail",
        icon: Mail,
      },
      {
        id: "chat",
        titleKey: "chat",
        url: "/dashboard/chat",
        icon: MessageSquare,
      },
      {
        id: "calendar",
        titleKey: "calendar",
        url: "/dashboard/calendar",
        icon: Calendar,
      },
      {
        id: "kanban",
        titleKey: "kanban",
        url: "/dashboard/kanban",
        icon: Kanban,
      },
    ],
  },
  {
    id: 4,
    labelKey: "management",
    items: [
      {
        id: "users",
        titleKey: "users",
        url: "/dashboard/users",
        icon: Users,
      },
      {
        id: "white-label",
        titleKey: "white_label",
        url: "/dashboard/white-label",
        icon: Lock,
      },
      {
        id: "invoice",
        titleKey: "invoices",
        url: "/dashboard/invoice",
        icon: ReceiptText,
      },
      {
        id: "authentication",
        titleKey: "authentication",
        icon: Fingerprint,
        subItems: [
          { id: "auth-login-v1", titleKey: "login_v1", url: "/auth/v1/login", newTab: true },
          { id: "auth-login-v2", titleKey: "login_v2", url: "/auth/v2/login", newTab: true },
          { id: "auth-register-v1", titleKey: "register_v1", url: "/auth/v1/register", newTab: true },
          { id: "auth-register-v2", titleKey: "register_v2", url: "/auth/v2/register", newTab: true },
        ],
      },
    ],
  },
  {
    id: 5,
    labelKey: "legacy",
    items: [
      {
        id: "legacy-dashboards",
        titleKey: "dashboards_v1",
        subItems: [
          { id: "legacy-default", titleKey: "default_v1", url: "/dashboard/default-v1" },
          { id: "legacy-crm", titleKey: "crm_v1", url: "/dashboard/crm-v1" },
          { id: "legacy-finance", titleKey: "finance_v1", url: "/dashboard/finance-v1" },
          { id: "legacy-analytics", titleKey: "analytics-v1", url: "/dashboard/analytics-v1" },
        ],
      },
    ],
  },
  {
    id: 6,
    labelKey: "misc",
    items: [
      {
        id: "others",
        titleKey: "others",
        url: "/dashboard/coming-soon",
        icon: SquareArrowUpRight,
        badge: "soon",
        disabled: true,
      },
    ],
  },
];