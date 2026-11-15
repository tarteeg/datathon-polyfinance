import { Gauge, House, type LucideIcon, MessageSquare, Newspaper, ShieldAlert } from "lucide-react";

export interface NavSubItem {
  id: string;
  title: string;
  url: string;
  icon?: LucideIcon;
  disabled?: boolean;
  newTab?: boolean;
}

interface NavItemBase {
  id: string;
  title: string;
  icon?: LucideIcon;
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
  label?: string;
  items: NavMainItem[];
}

export const sidebarItems: NavGroup[] = [
  {
    id: 3,
    items: [
      { id: "home", title: "Home", url: "/dashboard/home", icon: House },
      { id: "decision-lab", title: "BreakPoint AI", url: "/dashboard/decision-lab", icon: Gauge },
      { id: "chat", title: "Finance chat", url: "/dashboard/chat", icon: MessageSquare },
    ],
  },
  {
    id: 0,
    label: "Portfolio",
    items: [],
  },
  {
    id: 1,
    label: "Dashboards",
    items: [
      {
        id: "risk-ripple-news",
        title: "News & Geopolitical Intelligence",
        url: "/dashboard/risk-ripple/news",
        icon: Newspaper,
      },
      {
        id: "risk-ripple-investigations",
        title: "Portfolio Risk & Investigations",
        url: "/dashboard/risk-ripple/investigations",
        icon: ShieldAlert,
      },
    ],
  },
];
