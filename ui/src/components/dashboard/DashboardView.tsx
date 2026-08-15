import { useEffect, useState } from "react";
import {
  TrendingUp, Wallet, AlertTriangle, Gauge, FolderKanban,
  FileSignature, FileText, BarChart3,
} from "lucide-react";
import { rpc } from "../../api/rpc";
import { str, num, int } from "../../api/entity";
import { KPICard } from "../shared/KPICard";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import { RevenueChart } from "./RevenueChart";
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

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    const [kpiRes, budgetRes] = await Promise.all([
      rpc("dashboard.get_kpis"),
      rpc<BudgetEntry[]>("dashboard.get_project_budgets"),
    ]);
    if (kpiRes.ok && kpiRes.data) setKpis(kpiRes.data as Entity);
    if (budgetRes.ok && Array.isArray(budgetRes.data)) setBudgets(budgetRes.data);
    setLoading(false);
  }

  if (loading) return <div className="flex items-center justify-center h-full text-secondary">Loading dashboard…</div>;
  if (!kpis) return (
    <EmptyStateIntro icon={BarChart3} description="Your key business metrics — revenue, outstanding payments, and project progress — will appear here." />
  );

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      <h1 className="text-lg font-semibold">Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPICard title="Revenue (YTD)" value={str(kpis, "total_revenue_ytd_formatted")} icon={TrendingUp}
          valueColor={num(kpis, "total_revenue_ytd") > 0 ? "var(--color-status-success)" : undefined} tooltip="Total revenue received from paid invoices during the current calendar year." />
        <KPICard title="Outstanding" value={str(kpis, "outstanding_amount_formatted")} icon={Wallet}
          valueColor={num(kpis, "outstanding_amount") > 0 ? "var(--color-status-warning)" : undefined} tooltip="Total amount from invoices that have been issued but not yet paid."/>
        <KPICard title="Overdue" value={str(kpis, "overdue_amount_formatted")} icon={AlertTriangle}
          valueColor={num(kpis, "overdue_amount") > 0 ? "var(--color-status-danger)" : undefined} tooltip="Outstanding invoices whose payment due date has already passed."/>
        <KPICard title="Eff. Hourly Rate" value={str(kpis, "effective_hourly_rate_formatted")} icon={Gauge}
          valueColor="var(--color-status-info)" tooltip="Average revenue per tracked work hour based on paid invoices."/>
        <KPICard title="Active Projects" value={String(int(kpis, "active_projects"))} icon={FolderKanban} tooltip="Number of projects that currently have at least one active contract."/>
        <KPICard title="Active Contracts" value={String(int(kpis, "active_contracts"))} icon={FileSignature} tooltip="Number of contracts that are currently active and generating work or invoices."/>
        <KPICard title="Unpaid Invoices" value={String(int(kpis, "unpaid_invoices"))} icon={FileText}
          valueColor={int(kpis, "unpaid_invoices") > 0 ? "var(--color-status-warning)" : undefined} tooltip="Number of invoices that have been issued but have not yet been paid." />
        <div className={kpis.country_supported === false ? "opacity-40" : ""}>
          <KPICard title="Spendable Income" value={kpis.country_supported === false ? "—" : str(kpis, "spendable_income_formatted")} icon={Wallet}
            valueColor={num(kpis, "spendable_income") > 0 ? "var(--color-status-success)" : "var(--color-status-danger)"} tooltip="Estimated income remaining after setting aside VAT and income tax reserves."/>
        </div>
      </div>

      <RevenueChart />

      {budgets.length > 0 && (
        <div className="rounded-lg bg-bg-card border border-border-subtle p-4 space-y-3">
          <h2 className="text-sm font-medium text-secondary">Project Time Budgets</h2>
          {budgets.map((b) => {
            const isOpen = !!b.open_ended;
            const trackedPct = isOpen ? 1 : (b.hours_budget > 0 ? Math.min(b.hours_tracked / b.hours_budget, 1) : 0);
            const plannedPct = isOpen ? 0 : (b.hours_budget > 0 ? Math.min(b.hours_planned / b.hours_budget, 1 - trackedPct) : 0);
            const totalHours = b.hours_tracked + b.hours_planned;
            const subtitle = isOpen
              ? `${totalHours.toFixed(1)}h total`
              : b.hours_planned > 0
                ? `${b.hours_tracked.toFixed(1)}h + ${b.hours_planned.toFixed(1)}h planned / ${b.hours_budget.toFixed(0)}h`
                : `${b.hours_tracked.toFixed(1)}h / ${b.hours_budget.toFixed(0)}h`;

            return (
              <div key={b.project_id} className="space-y-1">
                <div className="flex items-baseline justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-medium truncate">{b.project}</span>
                    {b.budget_exceeded && <AlertTriangle size={12} className="text-amber-400 shrink-0" />}
                  </div>
                  <span className="text-xs text-secondary tabular-nums">{subtitle}</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-bg-hover overflow-hidden flex">
                  <div className="h-full rounded-l-full bg-secondary transition-all duration-300"
                    style={{ width: `${trackedPct * 100}%` }} />
                  {plannedPct > 0 && (
                    <div className="h-full transition-all duration-300"
                      style={{
                        width: `${plannedPct * 100}%`,
                        background: "repeating-linear-gradient(45deg, #60A5FA 0, #60A5FA 2px, transparent 2px, transparent 5px)",
                        opacity: 0.5,
                      }} />
                  )}
                </div>
                {b.budget_exceeded && (
                  <div className="text-[11px] text-amber-400 font-medium">Budget exceeded</div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
