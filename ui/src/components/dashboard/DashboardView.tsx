import { useEffect, useState } from "react";
import { AlertTriangle, BarChart3 } from "lucide-react";
import { rpc } from "../../api/rpc";
import { UnconvertedNote } from "../shared/UnconvertedNote";
import { ProgressBar } from "../shared/ProgressBar";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import { LoadError, LoadingState } from "../shared/LoadStates";
import { PageLayout } from "../shared/ToolbarButtons";
import { RevenueChart } from "./RevenueChart";
import { CashFlowChart } from "./CashFlowChart";
import { FinancialGoalsCard } from "./FinancialGoalsCard";
import { YearOverview } from "./YearOverview";
import { formatHours } from "../timetracking/format";
import type { Entity } from "../../api/types";

interface BudgetEntry {
  project_id: number;
  project: string;
  hours_tracked: number;
  hours_planned: number;
  hours_budget: number;
  hours_remaining: number;
  planned_revenue: number;
  progress: number;
  budget_exceeded: boolean;
  open_ended?: boolean;
}

export function DashboardView() {
  const [kpis, setKpis] = useState<Entity | null>(null);
  const [budgets, setBudgets] = useState<BudgetEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    setLoadFailed(false);
    const [kpiRes, budgetRes] = await Promise.all([
      rpc("dashboard.get_kpis"),
      rpc<BudgetEntry[]>("dashboard.get_project_budgets"),
    ]);
    setLoadFailed(!kpiRes.ok || !budgetRes.ok);
    if (kpiRes.ok && kpiRes.data) setKpis(kpiRes.data as Entity);
    if (budgetRes.ok && Array.isArray(budgetRes.data)) setBudgets(budgetRes.data);
    setLoading(false);
  }

  if (loadFailed) return <PageLayout title="Dashboard" fallback={<LoadError what="the dashboard" onRetry={load} />} />;
  if (loading) return <PageLayout title="Dashboard" fallback={<LoadingState />} />;
  if (!kpis) return (
    <PageLayout title="Dashboard" fallback={
      <EmptyStateIntro icon={BarChart3} description="Your key business metrics — revenue, outstanding payments, and project progress — will appear here." />
    } />
  );

  return (
    <PageLayout title="Dashboard" className="space-y-6">
      <div className="@container" data-tour="overview">
        <YearOverview kpis={kpis} />
        <UnconvertedNote items={kpis.unconverted as string[] | undefined} className="mt-2" />
      </div>

      <RevenueChart />

      <CashFlowChart />

      <FinancialGoalsCard />

      {budgets.length > 0 && (
        <div className="rounded-lg bg-bg-card border border-border-subtle p-4 space-y-3">
          <h2 className="text-sm font-medium text-secondary">Project Time Budgets</h2>
          {budgets.map((b) => {
            const isOpen = !!b.open_ended;
            const share = (h: number) => (b.hours_budget > 0 ? h / b.hours_budget : 0);
            const subtitle = isOpen
              ? `${formatHours(b.hours_tracked + b.hours_planned)} total`
              : b.hours_planned > 0
                ? `${formatHours(b.hours_tracked)} + ${formatHours(b.hours_planned)} planned / ${formatHours(b.hours_budget)}`
                : `${formatHours(b.hours_tracked)} / ${formatHours(b.hours_budget)}`;

            return (
              <ProgressBar key={b.project_id} label={b.project} subtitle={subtitle}
                progress={isOpen ? 1 : share(b.hours_tracked)} planned={isOpen ? 0 : share(b.hours_planned)}
                tone={b.budget_exceeded && !isOpen ? "warning" : "neutral"}
                icon={b.budget_exceeded && <AlertTriangle size={12} className="text-status-warning shrink-0" />} />
            );
          })}
        </div>
      )}
    </PageLayout>
  );
}
