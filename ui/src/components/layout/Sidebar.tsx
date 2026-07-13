import { useState, useRef, useEffect } from "react";
import {
  LayoutDashboard, CalendarDays, PieChart, Banknote,
  FolderKanban, FileSignature, Building2, Users, Clock, FileText,
  FileUp, Settings, ChevronUp, UserPlus, Trash2, CheckSquare, ReceiptText,
  type LucideIcon,
} from "lucide-react";

type SidebarItem = { id: string; label: string; icon: LucideIcon };

const SECTIONS: { label: string; items: SidebarItem[] }[] = [
  {
    label: "Insights",
    items: [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
      { id: "timeline", label: "Timeline", icon: CalendarDays },
      { id: "tax", label: "Tax & Reserves", icon: PieChart },
      { id: "salary", label: "Salary", icon: Banknote },
    ],
  },
  {
    label: "Workflows",
    items: [
      { id: "tasks", label: "Tasks", icon: CheckSquare },
      { id: "import", label: "Import", icon: FileUp },
      { id: "timetracking", label: "Time Tracking", icon: Clock },
      { id: "invoicing", label: "Invoicing", icon: FileText },
    ],
  },
  {
    label: "My Business",
    items: [
      { id: "contacts", label: "Contacts", icon: Users },
      { id: "clients", label: "Clients", icon: Building2 },
      { id: "contracts", label: "Contracts", icon: FileSignature },
      { id: "projects", label: "Projects", icon: FolderKanban },
      { id: "expenses", label: "Expenses", icon: ReceiptText },
    ],
  },
];

const SETTINGS_ITEM: SidebarItem = { id: "settings", label: "Settings", icon: Settings };

export type RegisteredUser = {
  id: number;
  name: string;
  subtitle: string;
  db_file: string;
  is_demo: boolean;
};

type Props = {
  selected: string;
  onSelect: (id: string) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  activeUser: RegisteredUser | null;
  allUsers: RegisteredUser[];
  onSwitchUser: (dbFile: string) => void;
  onAddUser: () => void;
  onDeleteUser: (dbFile: string) => void;
};

export function Sidebar({
  selected, onSelect, collapsed,
  activeUser, allUsers, onSwitchUser, onAddUser, onDeleteUser,
}: Props) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen]);

  const initials = activeUser
    ? activeUser.name.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2)
    : "?";

  return (
    <aside className={`flex flex-col bg-bg-sidebar border-r border-border-subtle transition-all duration-200 ${collapsed ? "w-14" : "w-52"}`}>
      <div className="drag-region h-13 shrink-0" />

      <nav className="flex-1 overflow-y-auto py-2 px-2 space-y-4">
        {SECTIONS.map((section) => (
          <div key={section.label}>
            {!collapsed && (
              <div className="px-2 pb-1 text-[13px] font-medium text-tertiary">
                {section.label}
              </div>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const active = selected === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onSelect(item.id)}
                    className={`no-drag flex items-center gap-2.5 w-full rounded-md px-2.5 py-1.5 text-sm transition-colors cursor-default
                      ${active ? "bg-bg-selected text-primary" : "text-secondary hover:bg-bg-hover hover:text-primary"}
                      ${collapsed ? "justify-center" : ""}`}
                    title={collapsed ? item.label : undefined}
                  >
                    <item.icon size={16} strokeWidth={1.8} className="shrink-0" />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Settings */}
      <div className="shrink-0 px-2 pb-2">
        <button
          onClick={() => onSelect(SETTINGS_ITEM.id)}
          className={`no-drag flex items-center gap-2.5 w-full rounded-md px-2.5 py-1.5 text-sm transition-colors cursor-default
            ${selected === SETTINGS_ITEM.id ? "bg-bg-selected text-primary" : "text-secondary hover:bg-bg-hover hover:text-primary"}
            ${collapsed ? "justify-center" : ""}`}
          title={collapsed ? SETTINGS_ITEM.label : undefined}
        >
          <SETTINGS_ITEM.icon size={16} strokeWidth={1.8} className="shrink-0" />
          {!collapsed && <span className="truncate">{SETTINGS_ITEM.label}</span>}
        </button>
      </div>

      {/* User switcher */}
      <div className="relative shrink-0 border-t border-border-subtle" ref={menuRef}>
        <button
          onClick={() => setMenuOpen((o) => !o)}
          className="no-drag flex items-center gap-2.5 w-full px-3 py-2.5 text-sm transition-colors hover:bg-bg-hover cursor-default"
          title={activeUser?.name ?? "No user"}
        >
          <span className="flex items-center justify-center w-7 h-7 rounded-full bg-bg-card text-primary text-xs font-semibold shrink-0">
            {initials}
          </span>
          {!collapsed && (
            <>
              <span className="flex-1 text-left truncate">
                <span className="block text-sm font-medium leading-tight truncate">{activeUser?.name ?? "No user"}</span>
                {activeUser?.subtitle && (
                  <span className="block text-[11px] text-muted leading-tight truncate">{activeUser.subtitle}</span>
                )}
              </span>
              <ChevronUp size={14} className={`text-muted transition-transform ${menuOpen ? "" : "rotate-180"}`} />
            </>
          )}
        </button>

        {menuOpen && (
          <div className="absolute left-2 right-2 bottom-full mb-1 bg-bg-sidebar border border-border-subtle rounded-lg shadow-lg z-50 py-1 max-h-64 overflow-y-auto">
            {allUsers.map((u) => (
              <div key={u.db_file} className="flex items-center group">
                <button
                  onClick={() => { onSwitchUser(u.db_file); setMenuOpen(false); }}
                  className={`flex-1 text-left px-3 py-1.5 text-sm truncate transition-colors
                    ${u.db_file === activeUser?.db_file ? "text-primary font-medium" : "text-secondary hover:bg-bg-hover hover:text-primary"}`}
                >
                  {u.name}
                  {u.is_demo && <span className="ml-1 text-[10px] text-muted">(demo)</span>}
                </button>
                {u.is_demo && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onDeleteUser(u.db_file); setMenuOpen(false); }}
                    className="opacity-0 group-hover:opacity-100 px-2 py-1 text-muted hover:text-red-400 transition-all"
                    title="Remove demo user"
                  >
                    <Trash2 size={13} />
                  </button>
                )}
              </div>
            ))}
            <div className="border-t border-border-subtle mt-1 pt-1">
              <button
                onClick={() => { onAddUser(); setMenuOpen(false); }}
                className="flex items-center gap-2 w-full px-3 py-1.5 text-sm text-secondary hover:bg-bg-hover hover:text-primary transition-colors"
              >
                <UserPlus size={14} />
                Add user
              </button>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
