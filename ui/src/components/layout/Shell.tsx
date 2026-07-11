import { useState, useCallback, useMemo, useEffect } from "react";
import { Sidebar, type RegisteredUser } from "./Sidebar";
import { OnboardingWizard, type OnboardingData } from "./OnboardingWizard";
import { DashboardView } from "../dashboard/DashboardView";
import { ProjectsView } from "../business/ProjectsView";
import { ClientsView } from "../business/ClientsView";
import { ContractsView } from "../business/ContractsView";
import { InvoicingView } from "../invoicing/InvoicingView";
import { ContactsView } from "../contacts/ContactsView";
import { SettingsView } from "../settings/SettingsView";
import { TimelineView } from "../timeline/TimelineView";
import { TaxReservesView } from "../tax/TaxReservesView";
import { SalaryView } from "../salary/SalaryView";
import { ExpensesView } from "../salary/ExpensesView";
import { TimeTrackingView } from "../timetracking/TimeTrackingView";
import { DocumentImportView } from "../import/DocumentImportView";
import { PlaceholderView } from "../shared/PlaceholderView";
import { ViewErrorBoundary } from "../shared/ViewErrorBoundary";
import { UpdateBanner } from "./UpdateBanner";
import { StatusBar } from "./StatusBar";
import { StatusBarProvider } from "../shared/status-bar-context";
import { NavigationContext, type NavigationFilter } from "../shared/NavigationContext";
import { rpc } from "../../api/rpc";
import { useThemeProvider, ThemeContext } from "../../hooks/useTheme";

type BootState = "loading" | "welcome" | "ready";

type BootPhase =
  | "init"
  | "registry"
  | "users"
  | "demo"
  | "switching"
  | "creating";

const PHASE: Record<BootPhase, string> = {
  init:      "Warming up the boiler",
  registry:  "Inspecting the ductwork",
  users:     "Reading the engineer's roster",
  demo:      "Dispatching Harry Tuttle",
  switching: "Refitting to spec 27B/6",
  creating:  "Filing form 27B/6",
};

export function Shell() {
  const theme = useThemeProvider();
  const [bootState, setBootState] = useState<BootState>("loading");
  const [bootPhase, setBootPhase] = useState<BootPhase>("init");
  const [selected, setSelected] = useState("dashboard");
  const [collapsed, setCollapsed] = useState(false);
  const [navFilter, setNavFilter] = useState<NavigationFilter>({});
  const [activeUser, setActiveUser] = useState<RegisteredUser | null>(null);
  const [allUsers, setAllUsers] = useState<RegisteredUser[]>([]);
  const [regDialogOpen, setRegDialogOpen] = useState(false);
  const [regLoading, setRegLoading] = useState(false);

  const navigate = useCallback((view: string, filter?: NavigationFilter) => {
    setNavFilter(filter || {});
    setSelected(view);
  }, []);

  const navContext = useMemo(
    () => ({ navigate, filter: navFilter }),
    [navigate, navFilter],
  );

  async function refreshUsers() {
    const res = await rpc<RegisteredUser[]>("users.list");
    if (res.ok && res.data) setAllUsers(res.data);
  }

  async function refreshActiveUser() {
    const res = await rpc<RegisteredUser | null>("users.get_active");
    if (res.ok && res.data) setActiveUser(res.data);
    else setActiveUser(null);
  }

  useEffect(() => {
    (async () => {
      setBootPhase("registry");
      await rpc("db.ensure");
      setBootPhase("users");
      const usersRes = await rpc<RegisteredUser[]>("users.list");
      const users = usersRes.ok && usersRes.data ? usersRes.data : [];
      setAllUsers(users);

      if (users.length === 0) {
        setBootState("welcome");
      } else {
        await refreshActiveUser();
        setBootState("ready");
      }
    })();
  }, []);

  async function handleWelcomeDemo() {
    setBootPhase("demo");
    setBootState("loading");
    await rpc("users.ensure_demo");
    await refreshUsers();
    setBootPhase("switching");
    const demoSwitch = await rpc("users.switch", { db_file: "harry-tuttle.db" });
    if (demoSwitch.ok) {
      await refreshActiveUser();
    }
    setBootState("ready");
  }

  async function handleSwitchUser(dbFile: string) {
    setBootPhase("switching");
    setBootState("loading");
    await rpc("users.switch", { db_file: dbFile });
    await refreshActiveUser();
    setSelected("dashboard");
    window.location.reload();
  }

  async function handleDeleteUser(dbFile: string) {
    await rpc("users.delete", { db_file: dbFile });
    await refreshUsers();
    const remaining = allUsers.filter((u) => u.db_file !== dbFile);
    if (activeUser?.db_file === dbFile && remaining.length > 0) {
      await handleSwitchUser(remaining[0].db_file);
    } else if (remaining.length === 0) {
      setActiveUser(null);
      setBootState("welcome");
    }
  }

  async function handleRegSubmit(data: OnboardingData) {
    setRegLoading(true);
    setBootPhase("creating");
    const createParams = {
      ...(data.profile as unknown as Record<string, unknown>),
      bank_account: {
        name: data.profile.bank_name,
        IBAN: data.profile.bank_IBAN,
        BIC: data.profile.bank_BIC,
      },
    };
    const res = await rpc<RegisteredUser>("users.create", createParams);
    if (res.ok && res.data) {
      await rpc("preferences.save", {
        invoice_template: data.invoicing.invoice_template,
        language: data.invoicing.language,
        invoice_number_scheme: data.invoicing.invoice_number_scheme,
      });
      if (data.llm.model) {
        await rpc("llm.save_config", { config: data.llm });
      }
      await refreshUsers();
      await refreshActiveUser();
      setRegLoading(false);
      setRegDialogOpen(false);
      setBootState("ready");
      window.location.reload();
    } else {
      setRegLoading(false);
    }
  }

  function handleSidebarSelect(id: string) {
    setNavFilter({});
    setSelected(id);
  }

  if (bootState === "loading") {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-bg-content text-secondary">
        <div className="text-center space-y-2">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm">{PHASE[bootPhase]}…</p>
        </div>
      </div>
    );
  }

  if (bootState === "welcome") {
    return (
      <OnboardingWizard
        open
        overlay={false}
        onClose={() => setBootState("welcome")}
        onSubmit={handleRegSubmit}
        onDemo={handleWelcomeDemo}
        loading={regLoading}
      />
    );
  }

  return (
    <ThemeContext.Provider value={theme}>
      <NavigationContext.Provider value={navContext}>
        <StatusBarProvider>
          <div className="flex h-screen w-screen bg-bg-content text-primary">
            <Sidebar
              selected={selected}
              onSelect={handleSidebarSelect}
              collapsed={collapsed}
              onToggleCollapse={() => setCollapsed((c) => !c)}
              activeUser={activeUser}
              allUsers={allUsers}
              onSwitchUser={handleSwitchUser}
              onAddUser={() => setRegDialogOpen(true)}
              onDeleteUser={handleDeleteUser}
            />
            <main className="flex-1 flex flex-col overflow-hidden">
              <div className="drag-region h-13 shrink-0" />
              <UpdateBanner />
              <div className="flex-1 overflow-y-auto">
                <ViewErrorBoundary key={selected} viewName={selected}>
                  <DetailView id={selected} />
                </ViewErrorBoundary>
              </div>
              <StatusBar />
            </main>
          </div>
          <OnboardingWizard
            open={regDialogOpen}
            overlay
            onClose={() => setRegDialogOpen(false)}
            onSubmit={handleRegSubmit}
            onDemo={handleWelcomeDemo}
            loading={regLoading}
          />
        </StatusBarProvider>
      </NavigationContext.Provider>
    </ThemeContext.Provider>
  );
}

function DetailView({ id }: { id: string }) {
  switch (id) {
    case "dashboard": return <DashboardView />;
    case "timeline": return <TimelineView />;
    case "tax": return <TaxReservesView />;
    case "salary": return <SalaryView />;
    case "expenses": return <ExpensesView />;
    case "clients": return <ClientsView />;
    case "contracts": return <ContractsView />;
    case "projects": return <ProjectsView />;
    case "contacts": return <ContactsView />;
    case "timetracking": return <TimeTrackingView />;
    case "invoicing": return <InvoicingView />;
    case "import": return <DocumentImportView />;
    case "settings": return <SettingsView />;
    default: return <PlaceholderView title={id.charAt(0).toUpperCase() + id.slice(1)} />;
  }
}
