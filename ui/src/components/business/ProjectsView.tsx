import { useEffect, useState, useRef, useCallback } from "react";
import {
  FolderKanban, Building2, FileSignature, Calendar, Plus, Trash2, FileUp, Sparkles, Check, CheckCircle2, Save, AlertTriangle, Copy,
} from "lucide-react";
import { rpc } from "../../api/rpc";
import { str, int, num, bool, entity, dateRange, projectStatus } from "../../api/entity";
import { StatusBadge, TagBadge } from "../shared/StatusBadge";
import { statusColor } from "../shared/status-colors";
import { ProgressBar } from "../shared/ProgressBar";
import { ViewModeToggle } from "../shared/ViewModeToggle";
import { KanbanBoard, useStageStore, type BoardColumn } from "../shared/KanbanBoard";
import { Toolbar, ToolbarButtonPrimary, ToolbarButtonSecondary, ToolbarFilterGroup, ListDetailLayout, LIST_ROW_PADDING } from "../shared/ToolbarButtons";
import { useNavigation } from "../shared/NavigationContext";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import { DetailHeader, DetailAction, DetailDeleteAction, DetailSubmit, DETAIL_PANE } from "../shared/DetailHeader";
import { DetailFields, DetailField } from "../shared/DetailFields";
import { LoadError, LoadingState } from "../shared/LoadStates";
import { Section } from "../shared/Section";
import { DocumentImportPanel } from "../shared/DocumentImportPanel";
import { useFieldRequirements } from "../../hooks/useFieldRequirements";
import { useAutoSelect } from "../../hooks/useAutoSelect";
import type { Entity } from "../../api/types";
import { formatHours } from "../timetracking/format";

interface BudgetEntry {
  project_id: number;
  project: string;
  hours_tracked: number;
  hours_planned: number;
  hours_budget: number;
  hours_remaining: number;
  planned_revenue: number;
  currency: string;
  progress: number;
  budget_exceeded: boolean;
}

type Mode = "view" | "edit" | "create" | "import";

const PROJECT_COLUMNS: BoardColumn[] = ["Lead", "Offer", "Upcoming", "Active", "Completed"]
  .map((id) => ({ id, label: id, color: statusColor(id) }));

const STATUS_FILTERS = ["All", "Lead", "Offer", "Upcoming", "Active", "Completed"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];
const FILTER_COLORS: Record<string, string> = {
  ...Object.fromEntries(STATUS_FILTERS.map((s) => [s, statusColor(s)])),
  All: "var(--color-status-info)",
};

export function ProjectsView() {
  const { filter: navFilter } = useNavigation();
  const [projects, setProjects] = useState<Entity[]>([]);
  const [contractsMap, setContractsMap] = useState<Record<string, Entity>>({});
  const [budgetsMap, setBudgetsMap] = useState<Record<number, BudgetEntry>>({});
  const [selected, setSelected] = useState<Entity | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [viewMode, setViewMode] = useState<"list" | "board">("list");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("All");
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState<Mode>("view");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [parsedProjects, setParsedProjects] = useState<ParsedProject[]>([]);
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [duplicateSource, setDuplicateSource] = useState<Entity | null>(null);
  const selectedIdRef = useRef<number | null>(null);

  useEffect(() => { selectedIdRef.current = selected?.id ?? null; }, [selected]);

  const defaultColumn = useCallback(
    (e: { id: number; [k: string]: unknown }) =>
      PROJECT_COLUMNS.find((c) => c.id === projectStatus(e as Entity))?.id || "Active",
    [],
  );
  const stageStore = useStageStore("project", PROJECT_COLUMNS, defaultColumn);

  useEffect(() => { load(); }, []);

  async function load(selectId?: number) {
    setLoading(true);
    setLoadFailed(false);
    const [res, cRes, bRes] = await Promise.all([
      rpc<Entity[]>("projects.get_all"),
      rpc<Record<string, Entity>>("projects.get_all_contracts"),
      rpc<BudgetEntry[]>("dashboard.get_project_budgets"),
    ]);
    setLoadFailed(!res.ok || !cRes.ok || !bRes.ok);
    if (res.ok && res.data) {
      setProjects(res.data);
      const currentId = selectId ?? selectedIdRef.current;
      if (currentId != null) {
        const updated = res.data.find((p) => p.id === currentId);
        setSelected(updated || null);
      }
    }
    if (cRes.ok && cRes.data) setContractsMap(cRes.data);
    if (bRes.ok && Array.isArray(bRes.data)) {
      const map: Record<number, BudgetEntry> = {};
      for (const b of bRes.data) map[b.project_id] = b;
      setBudgetsMap(map);
    }
    setLoading(false);
  }

  // The create/import forms live in the list view's detail pane.
  function startCreate() { setViewMode("list"); setSelected(null); setDuplicateSource(null); setMode("create"); setDeleteError(null); }
  function startDuplicate(p: Entity) { setSelected(null); setDuplicateSource(p); setMode("create"); setDeleteError(null); setSaveError(null); }
  function startImport() { setViewMode("list"); setSelected(null); setParsedProjects([]); setParseError(null); setMode("import"); }
  function selectProject(p: Entity) { setSelected(p); setMode("view"); setDeleteError(null); }

  async function handleSave(data: ProjectFormData) {
    setSaveError(null);
    const project: Record<string, unknown> = {
      title: data.title,
      tag: data.tag,
      description: data.description,
      start_date: data.startDate,
      end_date: data.endDate || null,
      contract_id: data.contractId,
    };
    if (mode === "edit" && selected) project.id = selected.id;
    const res = await rpc<Entity>("projects.save", { project });
    if (res.ok) { setMode("view"); await load(res.data?.id); }
    else setSaveError(res.error || "Failed to save project.");
  }

  async function handleDelete(id: number) {
    setDeleteError(null);
    const res = await rpc("projects.delete", { id });
    if (res.ok) { setMode("view"); await load(); }
    else if (res.error) setDeleteError(res.error);
  }

  async function handleToggle(id: number) {
    await rpc("projects.toggle_completed", { id });
    await load();
    stageStore.removeEntity(id);
  }

  async function handleFileImport(file: File) {
    setParsing(true); setParseError(null); setParsedProjects([]);
    try {
      const buffer = await file.arrayBuffer();
      const base64 = btoa(new Uint8Array(buffer).reduce((d, b) => d + String.fromCharCode(b), ""));
      const res = await rpc<ParsedProject[]>("llm.parse_document", {
        file_base64: base64, file_name: file.name, entity_type: "project",
      });
      if (res.ok && res.data) {
        setParsedProjects(res.data);
        if (res.data.length === 0) setParseError("No projects found in the document.");
      } else setParseError(res.error || "Failed to parse document.");
    } catch (err) { setParseError(String(err)); }
    setParsing(false);
  }

  async function acceptProject(parsed: ParsedProject) {
    const project: Record<string, unknown> = {
      title: parsed.title, tag: parsed.tag, description: parsed.description,
      start_date: parsed.start_date, end_date: parsed.end_date,
    };
    if (parsed.selectedContractId) project.contract_id = parsed.selectedContractId;
    const res = await rpc("projects.save", { project });
    if (res.ok) { setParsedProjects((p) => p.filter((c) => c !== parsed)); await load(); }
  }

  async function acceptAll() {
    for (const p of parsedProjects) {
      const project: Record<string, unknown> = {
        title: p.title, tag: p.tag, description: p.description,
        start_date: p.start_date, end_date: p.end_date,
      };
      if (p.selectedContractId) project.contract_id = p.selectedContractId;
      await rpc("projects.save", { project });
    }
    setParsedProjects([]); await load(); setMode("view");
  }

  function discardProject(parsed: ParsedProject) {
    setParsedProjects((p) => p.filter((c) => c !== parsed));
  }

  function updateParsedProject(index: number, updated: ParsedProject) {
    setParsedProjects((p) => p.map((c, i) => i === index ? updated : c));
  }

  function matchesSearch(p: Entity) {
    if (!search) return true;
    const q = search.toLowerCase();
    return str(p, "title").toLowerCase().includes(q) || str(p, "tag").toLowerCase().includes(q)
      || clientName(p).toLowerCase().includes(q);
  }

  const filtered = projects.filter((p) =>
    (statusFilter === "All" || projectStatus(p) === statusFilter) && matchesSearch(p));
  const boardFiltered = projects.filter(matchesSearch);

  useAutoSelect(projects, filtered, selected, setSelected, {
    enabled: mode === "view",
    preferred: navFilter.contractId != null ? (p) => num(p, "contract_id") === navFilter.contractId : undefined,
  });

  function moveToColumn(id: number, colId: string) {
    stageStore.setColumn(id, colId);
    rpc("projects.set_stage", { id, stage: colId }).then(() => {
      load().then(() => stageStore.removeEntity(id));
    });
  }

  const selectedContract = selected ? entity(selected, "contract") : null;
  const selectedClient = selectedContract ? entity(selectedContract, "client") : null;

  return (
    <div className="flex flex-col h-full">
      <Toolbar title="Projects"
        actions={<>
          <ToolbarButtonPrimary icon={<Plus size={13} />} label="New" onClick={startCreate} />
          <ToolbarButtonSecondary icon={<FileUp size={13} />} label="Import" onClick={startImport} />
        </>}
        center={viewMode === "list"
          ? <ToolbarFilterGroup options={STATUS_FILTERS} value={statusFilter} onChange={setStatusFilter} colors={FILTER_COLORS} />
          : undefined}
        right={<ViewModeToggle mode={viewMode} onChange={setViewMode} />}
        search={{ value: search, onChange: setSearch }}
      />

      {loadFailed && mode === "view" ? (
        <LoadError what="projects" onRetry={load} />
      ) : loading && projects.length === 0 ? (
        <LoadingState />
      ) : projects.length === 0 && mode === "view" ? (
        <EmptyStateIntro icon={FolderKanban} description="A project is a unit of work you do under a contract. Track time against projects to generate invoices." />
      ) : viewMode === "list" ? (
        <ListDetailLayout
          footer={<>{filtered.length} project{filtered.length !== 1 ? "s" : ""}</>}
          list={filtered.length === 0
            ? <div className="p-4 text-sm text-center text-tertiary">No matches.</div>
            : filtered.map((p) => {
              const isSelected = selected?.id === p.id && mode === "view";
              const isHighlighted = !isSelected && navFilter.contractId != null && num(p, "contract_id") === navFilter.contractId;
              return (
                <button key={p.id} onClick={() => selectProject(p)}
                  className={`w-full text-left ${LIST_ROW_PADDING} border-b transition-colors flex items-center gap-3
                    ${isSelected ? "bg-bg-selected border-border-subtle" : isHighlighted ? "bg-accent/10 border-accent/30" : "border-border-subtle hover:bg-bg-hover"}`}>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium truncate">{str(p, "title")}</span>
                      <div className="flex items-center gap-2 shrink-0">
                        <TagBadge tag={str(p, "tag")} />
                        <StatusBadge status={projectStatus(p)} />
                      </div>
                    </div>
                    {clientName(p) && (
                      <div className="text-xs text-tertiary mt-0.5 truncate">{clientName(p)}</div>
                    )}
                  </div>
                </button>
              );
            })
          }
          detail={mode === "import" ? (
              <DocumentImportPanel title="Import Projects from Document" noun="project" count={parsedProjects.length}
                parsing={parsing} parseError={parseError}
                onFileSelected={handleFileImport} onAcceptAll={acceptAll} onClose={() => setMode("view")}
              >
                {parsedProjects.map((p, i) => (
                  <ParsedProjectCard key={i} project={p} contracts={Object.values(contractsMap)}
                    onAccept={() => acceptProject(p)}
                    onDiscard={() => discardProject(p)}
                    onUpdate={(updated) => updateParsedProject(i, updated)} />
                ))}
              </DocumentImportPanel>
            ) : mode === "create" ? (
              <ProjectForm key={duplicateSource?.id ?? "new"} project={duplicateSource ?? undefined} isDuplicate={duplicateSource != null} contracts={contractsMap} onSave={handleSave} onCancel={() => setMode("view")} error={saveError} />
            ) : mode === "edit" && selected ? (
              <ProjectForm project={selected} contracts={contractsMap} onSave={handleSave} onCancel={() => setMode("view")} error={saveError} />
            ) : selected ? (
              <div className={`${DETAIL_PANE} space-y-6`}>
                <DetailHeader title={str(selected, "title")}
                  badges={<>
                    <TagBadge tag={str(selected, "tag")} />
                    <StatusBadge status={projectStatus(selected)} />
                  </>}
                  actions={<>
                    <DetailAction icon={<CheckCircle2 size={13} />} label={bool(selected, "is_completed") ? "Reopen" : "Complete"}
                      onClick={() => handleToggle(selected.id)} />
                    <DetailAction icon={<Copy size={13} />} label="Duplicate" title="Create a new project based on this one"
                      onClick={() => startDuplicate(selected)} />
                    <DetailAction label="Edit" onClick={() => setMode("edit")} />
                    <DetailDeleteAction key={selected.id} label="Delete project" onDelete={() => handleDelete(selected.id)} />
                  </>} />

                {deleteError && (
                  <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">{deleteError}</div>
                )}

                {str(selected, "description") && <p className="text-sm text-secondary">{str(selected, "description")}</p>}
                <DetailFields>
                  <DetailField label="Dates">{dateRange(selected)}</DetailField>
                  <DetailField label="Client">{selectedClient ? str(selectedClient, "name") : "—"}</DetailField>
                  <DetailField label="Contract">{selectedContract ? str(selectedContract, "title") : "—"}</DetailField>
                  <DetailField label="Rate">{selectedContract ? `${str(selectedContract, "rate")} ${str(selectedContract, "currency")}/${str(selectedContract, "unit_abbrev") || "h"}` : "—"}</DetailField>
                </DetailFields>
                {selected.id != null && budgetsMap[selected.id as number] && (() => {
                  const b = budgetsMap[selected.id as number];
                  return (
                    <div className="space-y-2">
                      <BudgetBar budget={b} />
                    </div>
                  );
                })()}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full gap-2 text-tertiary">
                <FolderKanban size={36} strokeWidth={1.2} /><span className="text-sm">Select a project</span>
              </div>
            )
          }
        />
      ) : (
        <div className="flex-1 overflow-hidden">
          <KanbanBoard entities={boardFiltered} columns={PROJECT_COLUMNS}
            columnFor={(e) => stageStore.columnFor(e)} onMove={moveToColumn}
            renderCard={(proj, col) => <ProjectCard project={proj} color={col.color} budgetsMap={budgetsMap} />} />
        </div>
      )}
    </div>
  );
}

/* ---------- Helpers ---------- */

function clientName(p: Entity): string {
  const c = entity(p, "contract");
  return c ? str(entity(c, "client") || ({} as Entity), "name") : "";
}

function ProjectCard({ project, budgetsMap }: { project: Entity; color: string; budgetsMap: Record<number, BudgetEntry> }) {
  const cName = clientName(project);
  const c = entity(project, "contract");
  const contractTitle = c ? str(c, "title") : "";
  const [from, to] = dateRange(project).split(" – ");
  const budget = project.id != null ? budgetsMap[project.id as number] : undefined;
  return (
    <div className="space-y-2">
      <div className="space-y-1">
        <div className="text-sm font-semibold leading-snug line-clamp-2 break-words">{str(project, "title")}</div>
        <TagBadge tag={str(project, "tag")} className="max-w-full" />
      </div>
      {cName && (
        <div className="flex items-center gap-1.5 text-secondary">
          <Building2 size={11} className="text-tertiary shrink-0" />
          <span className="text-xs truncate" title={cName}>{cName}</span>
        </div>
      )}
      {contractTitle && (
        <div className="flex items-center gap-1.5 text-secondary">
          <FileSignature size={11} className="text-tertiary shrink-0" />
          <span className="text-xs truncate" title={contractTitle}>{contractTitle}</span>
        </div>
      )}
      {from && (
        <div className="flex items-center gap-1.5 text-tertiary">
          <Calendar size={11} className="shrink-0" />
          {/* Break only between start and end date. */}
          <span className="text-xs min-w-0">
            <span className="whitespace-nowrap">{to ? `${from} –` : from}</span>
            {to && <>{" "}<span className="whitespace-nowrap">{to}</span></>}
          </span>
        </div>
      )}
      {budget && (
        <BudgetBar budget={budget} />
      )}
    </div>
  );
}

function BudgetBar({ budget: b }: { budget: BudgetEntry }) {
  const share = (h: number) => (b.hours_budget > 0 ? h / b.hours_budget : 0);
  const subtitle = b.hours_planned > 0
    ? `${formatHours(b.hours_tracked)} tracked + ${formatHours(b.hours_planned)} planned / ${formatHours(b.hours_budget)}`
    : `${formatHours(b.hours_tracked)} / ${formatHours(b.hours_budget)}`;

  return (
    <ProgressBar label="Time Budget" subtitle={subtitle}
      progress={share(b.hours_tracked)} planned={share(b.hours_planned)}
      tone={b.budget_exceeded ? "warning" : "neutral"}
      icon={b.budget_exceeded && <AlertTriangle size={12} className="text-status-warning shrink-0" />} />
  );
}

/* ---------- Form ---------- */

interface ProjectFormData {
  title: string;
  tag: string;
  description: string;
  startDate: string;
  endDate: string;
  contractId: number | null;
}

function ProjectForm({ project, isDuplicate = false, contracts, onSave, onCancel, error }: {
  project?: Entity;
  isDuplicate?: boolean;
  contracts: Record<string, Entity>;
  onSave: (data: ProjectFormData) => void;
  onCancel: () => void;
  error?: string | null;
}) {
  const { isRequired } = useFieldRequirements("projects");
  const existingContract = project ? entity(project, "contract") : null;
  const [form, setForm] = useState<ProjectFormData>(() => {
    if (project) return {
      title: isDuplicate ? `${str(project, "title")} (Copy)` : str(project, "title"),
      tag: isDuplicate ? `${str(project, "tag")}-copy` : str(project, "tag"),
      description: str(project, "description"),
      // A copy is a new engagement and gets its own timeframe.
      startDate: isDuplicate ? "" : str(project, "start_date"),
      endDate: isDuplicate ? "" : str(project, "end_date"),
      contractId: existingContract?.id ?? null,
    };
    return { title: "", tag: "#", description: "", startDate: "", endDate: "", contractId: null };
  });
  const [saving, setSaving] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const isNew = !project || isDuplicate;
  const contractList = Object.values(contracts);

  function update<K extends keyof ProjectFormData>(field: K, value: ProjectFormData[K]) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setValidationError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim()) { setValidationError("Title is required"); return; }
    if (!form.tag.match(/^#\S+$/)) { setValidationError("Tag must start with # and contain no spaces"); return; }
    if (!form.startDate) { setValidationError("Start date is required"); return; }
    if (!form.contractId) { setValidationError("A contract is required. Create a contract first, then assign it here."); return; }
    setSaving(true);
    await onSave(form);
    setSaving(false);
  }

  return (
    <form onSubmit={handleSubmit} className={`${DETAIL_PANE} space-y-5`}>
      <DetailHeader title={isNew ? "New Project" : "Edit Project"}
        actions={<>
          <DetailAction label="Cancel" onClick={onCancel} />
          <DetailSubmit label={saving ? "Saving…" : "Save"} disabled={saving} />
        </>} />

      <p className="text-xs text-muted"><span className="text-accent">*</span> Required</p>

      {(validationError || error) && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">{validationError || error}</div>
      )}

      <Section title="Project">
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Title" value={form.title} onChange={(v) => update("title", v)} autoFocus required={isRequired("title")} />
          <FormField label="Tag" value={form.tag} onChange={(v) => update("tag", v)} required={isRequired("tag")} />
        </div>
        <div className="mt-3">
          <label className="block text-xs text-tertiary mb-1">Description{isRequired("description") && <span className="text-accent ml-0.5">*</span>}</label>
          <textarea value={form.description} onChange={(e) => update("description", e.target.value)} rows={3}
            className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors resize-none" />
        </div>
      </Section>

      <Section title="Dates">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-tertiary mb-1">Start Date{isRequired("start_date") && <span className="text-accent ml-0.5">*</span>}</label>
            <input type="date" value={form.startDate} onChange={(e) => update("startDate", e.target.value)}
              className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors" />
          </div>
          <div>
            <label className="block text-xs text-tertiary mb-1">End Date <span className="text-muted">(optional)</span></label>
            <input type="date" value={form.endDate} onChange={(e) => update("endDate", e.target.value)}
              className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors" />
          </div>
        </div>
      </Section>

      <Section title={<>Contract<span className="text-accent ml-0.5">*</span></>}>
        <select value={form.contractId ?? ""} onChange={(e) => update("contractId", e.target.value ? Number(e.target.value) : null)}
          className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors">
          <option value="">— Select a contract —</option>
          {contractList.map((c) => <option key={c.id} value={c.id}>{str(c, "title")}</option>)}
        </select>
      </Section>
    </form>
  );
}

/* ---------- Shared UI ---------- */

function FormField({ label, value, onChange, autoFocus, required }: {
  label: string; value: string; onChange: (v: string) => void; autoFocus?: boolean; required?: boolean;
}) {
  return (
    <div>
      <label className="block text-xs text-tertiary mb-1">{label}{required && <span className="text-accent ml-0.5">*</span>}</label>
      <input type="text" value={value} onChange={(e) => onChange(e.target.value)} autoFocus={autoFocus} required={required}
        className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors" />
    </div>
  );
}

/* ---------- AI Import ---------- */

interface ParsedProject {
  title: string;
  tag: string;
  description: string;
  start_date: string;
  end_date: string;
  contract_title_hint: string;
  selectedContractId?: number;
}

function ParsedProjectCard({ project, contracts, onAccept, onDiscard, onUpdate }: {
  project: ParsedProject; contracts: Entity[];
  onAccept: () => void; onDiscard: () => void; onUpdate: (p: ParsedProject) => void;
}) {
  return (
    <div className="rounded-xl border-2 border-fuchsia-400/40 bg-fuchsia-500/5 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={14} className="text-fuchsia-400" />
          <span className="text-sm font-semibold">{project.title || "Untitled"}</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={onDiscard}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs text-secondary hover:text-red-400 hover:bg-red-500/10 transition-colors">
            <Trash2 size={12} /> Discard
          </button>
          <button onClick={onAccept}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium text-fuchsia-400 hover:bg-fuchsia-500/10 border border-fuchsia-400/30 transition-colors">
            <Check size={12} /> Accept
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <AiField label="Title" value={project.title} onChange={(v) => onUpdate({ ...project, title: v })} />
        <AiField label="Tag" value={project.tag} onChange={(v) => onUpdate({ ...project, tag: v })} />
        <AiField label="Start Date" value={project.start_date} onChange={(v) => onUpdate({ ...project, start_date: v })} />
        <AiField label="End Date" value={project.end_date} onChange={(v) => onUpdate({ ...project, end_date: v })} />
      </div>
      <div>
        <label className="block text-xs text-fuchsia-300/70 mb-0.5">Description</label>
        <textarea value={project.description} onChange={(e) => onUpdate({ ...project, description: e.target.value })} rows={2}
          className="w-full px-2.5 py-1.5 rounded-md text-sm bg-bg-card text-primary border border-fuchsia-400/30 outline-none focus:border-fuchsia-400 transition-colors resize-none" />
      </div>
      <div>
        <label className="block text-xs text-fuchsia-300/70 mb-0.5">
          Contract {project.contract_title_hint && <span className="text-fuchsia-400/60">(hint: {project.contract_title_hint})</span>}
        </label>
        <select value={project.selectedContractId ?? ""} onChange={(e) => onUpdate({ ...project, selectedContractId: e.target.value ? Number(e.target.value) : undefined })}
          className="w-full px-2.5 py-1.5 rounded-md text-sm bg-bg-card text-primary border border-fuchsia-400/30 outline-none focus:border-fuchsia-400 transition-colors">
          <option value="">— Select —</option>
          {contracts.map((c) => <option key={c.id} value={c.id}>{str(c, "title")}</option>)}
        </select>
      </div>
    </div>
  );
}

function AiField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="block text-xs text-fuchsia-300/70 mb-0.5">{label}</label>
      <input type="text" value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full px-2.5 py-1.5 rounded-md text-sm bg-bg-card text-primary border border-fuchsia-400/30 outline-none focus:border-fuchsia-400 transition-colors" />
    </div>
  );
}
