import { useEffect, useState, useRef, useCallback } from "react";
import {
  FolderKanban, Building2, FileSignature, Calendar, Clock, FileText, Search,
  Plus, Trash2, Save, X, FileUp, Sparkles, Check, CheckCheck, Loader2, CheckCircle2,
} from "lucide-react";
import { rpc } from "../../api/rpc";
import { str, int, num, bool, entity, dateRange, projectStatus } from "../../api/entity";
import { StatusBadge } from "../shared/StatusBadge";
import { ProgressBar } from "../shared/ProgressBar";
import { ViewModeToggle } from "../shared/ViewModeToggle";
import { KanbanBoard, useStageStore, type BoardColumn } from "../shared/KanbanBoard";
import { useNavigation } from "../shared/NavigationContext";
import type { Entity } from "../../api/types";
import { projectColumnAfterCompletedToggle } from "./projectBoard";

interface BudgetEntry {
  project_id: number;
  project: string;
  hours_tracked: number;
  hours_budget: number;
  progress: number;
}

type Mode = "view" | "edit" | "create" | "import";

const PROJECT_COLUMNS: BoardColumn[] = [
  { id: "Lead", label: "Lead", color: "#a855f7" },
  { id: "Offer", label: "Offer", color: "#f97316" },
  { id: "Upcoming", label: "Upcoming", color: "#3b82f6" },
  { id: "Active", label: "Active", color: "#22c55e" },
  { id: "Completed", label: "Completed", color: "#8e8e93" },
];

const STATUS_FILTERS = ["All", "Active", "Upcoming", "Completed"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];
const FILTER_COLORS: Record<string, string> = {
  All: "#007AFF", Active: "#34d399", Upcoming: "#60a5fa", Completed: "#a0a0a0",
};

export function ProjectsView() {
  const { filter: navFilter } = useNavigation();
  const [projects, setProjects] = useState<Entity[]>([]);
  const [contractsMap, setContractsMap] = useState<Record<string, Entity>>({});
  const [budgetsMap, setBudgetsMap] = useState<Record<number, BudgetEntry>>({});
  const [selected, setSelected] = useState<Entity | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"list" | "board">("list");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("All");
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState<Mode>("view");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [parsedProjects, setParsedProjects] = useState<ParsedProject[]>([]);
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const selectedIdRef = useRef<number | null>(null);

  useEffect(() => { selectedIdRef.current = selected?.id ?? null; }, [selected]);

  const defaultColumn = useCallback(
    (e: { id: number; [k: string]: unknown }) =>
      PROJECT_COLUMNS.find((c) => c.id === projectStatus(e as Entity))?.id || "Active",
    [],
  );
  const stageStore = useStageStore("project", PROJECT_COLUMNS, defaultColumn);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    const [res, cRes, bRes] = await Promise.all([
      rpc<Entity[]>("projects.get_all"),
      rpc<Record<string, Entity>>("projects.get_all_contracts"),
      rpc<BudgetEntry[]>("dashboard.get_project_budgets"),
    ]);
    if (res.ok && res.data) {
      setProjects(res.data);
      const currentId = selectedIdRef.current;
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

  function startCreate() { setSelected(null); setMode("create"); setDeleteError(null); }
  function startImport() { setSelected(null); setParsedProjects([]); setParseError(null); setMode("import"); }
  function selectProject(p: Entity) { setSelected(p); setMode("view"); setDeleteError(null); }

  async function handleSave(data: ProjectFormData) {
    setSaveError(null);
    const project: Record<string, unknown> = {
      title: data.title,
      tag: data.tag,
      description: data.description,
      start_date: data.startDate,
      end_date: data.endDate,
      contract_id: data.contractId,
    };
    if (mode === "edit" && selected) project.id = selected.id;
    const res = await rpc("projects.save", { project });
    if (res.ok) { setMode("view"); await load(); }
    else setSaveError(res.error || "Failed to save project.");
  }

  async function handleDelete(id: number) {
    setDeleteError(null);
    const res = await rpc("projects.delete", { id });
    if (res.ok) { setSelected(null); setMode("view"); await load(); }
    else if (res.error) setDeleteError(res.error);
  }

  async function handleToggle(id: number) {
    const res = await rpc("projects.toggle_completed", { id });
    if (res.ok) {
      const proj = projects.find((p) => p.id === id);
      if (proj) stageStore.setColumn(id, projectColumnAfterCompletedToggle(projectStatus(proj)));
    }
    await load();
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

  function moveToColumn(id: number, colId: string) {
    stageStore.setColumn(id, colId);
    if (colId === "Completed") rpc("projects.toggle_completed", { id }).then(load);
    else {
      const proj = projects.find((p) => p.id === id);
      if (proj && projectStatus(proj) === "Completed") rpc("projects.toggle_completed", { id }).then(load);
    }
  }

  const selectedContract = selected ? entity(selected, "contract") : null;
  const selectedClient = selectedContract ? entity(selectedContract, "client") : null;

  if (loading && projects.length === 0)
    return <div className="flex items-center justify-center h-full text-secondary">Loading projects…</div>;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 py-2 shrink-0 border-b border-border-subtle">
        <h2 className="text-sm font-semibold">Projects</h2>
        <ToolbarButton icon={<Plus size={15} />} onClick={startCreate} />
        <ToolbarButton icon={<FileUp size={15} />} label="Import" onClick={startImport} />
        <div className="flex-1" />
        {viewMode === "list" && (
          <div className="flex items-center gap-1">
            {STATUS_FILTERS.map((s) => {
              const c = FILTER_COLORS[s];
              return (
                <button key={s} onClick={() => setStatusFilter(s)}
                  className="px-2 py-1 rounded-md text-xs font-medium transition-colors"
                  style={{
                    background: statusFilter === s ? `${c}22` : "transparent",
                    color: statusFilter === s ? c : "var(--color-tertiary)",
                    border: statusFilter === s ? `1px solid ${c}44` : "1px solid transparent",
                  }}>{s}</button>
              );
            })}
          </div>
        )}
        <ViewModeToggle mode={viewMode} onChange={setViewMode} />
        <div className="flex-1" />
        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
          <input type="text" placeholder="Search…" value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 pr-3 py-1.5 rounded-md text-sm outline-none w-44 bg-bg-card text-primary border border-border-subtle placeholder:text-muted" />
        </div>
      </div>

      {viewMode === "list" ? (
        <div className="flex flex-1 overflow-hidden">
          <div className="w-72 shrink-0 flex flex-col border-r border-border-subtle">
            <div className="flex-1 overflow-y-auto">
              {filtered.length === 0
                ? <div className="p-4 text-sm text-center text-tertiary">No projects.</div>
                : filtered.map((p) => {
                  const isSelected = selected?.id === p.id && mode === "view";
                  const isHighlighted = !isSelected && navFilter.contractId != null && num(p, "contract_id") === navFilter.contractId;
                  return (
                    <button key={p.id} onClick={() => selectProject(p)}
                      className={`w-full text-left px-4 py-2.5 border-b transition-colors
                        ${isSelected ? "bg-bg-selected border-border-subtle" : isHighlighted ? "bg-accent/10 border-accent/30" : "border-border-subtle hover:bg-bg-hover"}`}>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium truncate">{str(p, "title")}</span>
                        <StatusBadge status={projectStatus(p)} />
                      </div>
                      <div className="text-xs text-secondary mt-0.5 truncate">{str(p, "tag")}</div>
                    </button>
                  );
                })}
            </div>
            <div className="px-4 py-2 text-xs text-tertiary border-t border-border-subtle">
              {filtered.length} project{filtered.length !== 1 ? "s" : ""}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {mode === "import" ? (
              <ProjectImportPanel
                parsing={parsing} parseError={parseError} parsedProjects={parsedProjects}
                contracts={contractsMap}
                onFileSelected={handleFileImport} onAccept={acceptProject} onAcceptAll={acceptAll}
                onDiscard={discardProject} onUpdate={updateParsedProject} onClose={() => setMode("view")}
              />
            ) : mode === "create" ? (
              <ProjectForm contracts={contractsMap} onSave={handleSave} onCancel={() => setMode("view")} error={saveError} />
            ) : mode === "edit" && selected ? (
              <ProjectForm project={selected} contracts={contractsMap} onSave={handleSave} onCancel={() => setMode("view")} error={saveError} />
            ) : selected ? (
              <div className="p-6 max-w-2xl space-y-5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-bg-card flex items-center justify-center">
                    <FolderKanban size={18} className="text-secondary" />
                  </div>
                  <div>
                    <h1 className="text-lg font-semibold">{str(selected, "title")}</h1>
                    <p className="text-xs text-secondary">{str(selected, "tag")}</p>
                  </div>
                  <StatusBadge status={projectStatus(selected)} className="ml-auto" />
                </div>

                <div className="flex items-center gap-2">
                  <button onClick={() => handleToggle(selected.id)}
                    className="flex items-center gap-1 px-2 py-1.5 rounded text-xs text-secondary hover:text-primary border border-border-subtle transition-colors">
                    <CheckCircle2 size={13} /> {bool(selected, "is_completed") ? "Reopen" : "Complete"}
                  </button>
                  <button onClick={() => setMode("edit")}
                    className="px-3 py-1.5 rounded text-sm font-medium bg-bg-card text-secondary hover:text-primary border border-border-subtle transition-colors">
                    Edit
                  </button>
                  <button onClick={() => handleDelete(selected.id)}
                    className="p-1.5 rounded text-secondary hover:text-red-400 border border-border-subtle transition-colors">
                    <Trash2 size={14} />
                  </button>
                </div>

                {deleteError && (
                  <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">{deleteError}</div>
                )}

                {str(selected, "description") && <p className="text-sm text-secondary">{str(selected, "description")}</p>}
                <div className="grid grid-cols-2 gap-4">
                  <DetailRow label="Dates" value={dateRange(selected)} />
                  <DetailRow label="Client" value={selectedClient ? str(selectedClient, "name") : "—"} />
                  <DetailRow label="Contract" value={selectedContract ? str(selectedContract, "title") : "—"} />
                  <DetailRow label="Rate" value={selectedContract ? `${str(selectedContract, "rate")} ${str(selectedContract, "currency")}/${str(selectedContract, "unit")}` : "—"} />
                </div>
                {selected.id != null && budgetsMap[selected.id as number] && (
                  <ProgressBar
                    progress={budgetsMap[selected.id as number].progress}
                    label="Time Budget"
                    subtitle={`${budgetsMap[selected.id as number].hours_tracked.toFixed(1)}h / ${budgetsMap[selected.id as number].hours_budget.toFixed(0)}h`}
                  />
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full gap-2 text-tertiary">
                <FolderKanban size={36} strokeWidth={1.2} /><span className="text-sm">Select a project</span>
              </div>
            )}
          </div>
        </div>
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
  const budget = project.id != null ? budgetsMap[project.id as number] : undefined;
  return (
    <div className="space-y-2">
      <div>
        <div className="text-sm font-semibold leading-snug">{str(project, "title")}</div>
        {str(project, "tag") && (
          <span className="text-xs font-medium text-tertiary">{str(project, "tag")}</span>
        )}
      </div>
      {cName && (
        <div className="flex items-center gap-1.5 text-secondary">
          <Building2 size={11} className="text-tertiary shrink-0" />
          <span className="text-xs">{cName}</span>
        </div>
      )}
      {c && str(c, "title") && (
        <div className="flex items-center gap-1.5 text-secondary">
          <FileSignature size={11} className="text-tertiary shrink-0" />
          <span className="text-xs">{str(c, "title")}</span>
        </div>
      )}
      {dateRange(project) && (
        <div className="flex items-center gap-1.5 text-tertiary">
          <Calendar size={11} className="shrink-0" />
          <span className="text-xs">{dateRange(project)}</span>
        </div>
      )}
      {budget && (
        <ProgressBar
          progress={budget.progress}
          subtitle={`${budget.hours_tracked.toFixed(1)}h / ${budget.hours_budget.toFixed(0)}h`}
        />
      )}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-wider text-tertiary mb-0.5">{label}</div>
      <div className="text-sm">{value}</div>
    </div>
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

function ProjectForm({ project, contracts, onSave, onCancel, error }: {
  project?: Entity;
  contracts: Record<string, Entity>;
  onSave: (data: ProjectFormData) => void;
  onCancel: () => void;
  error?: string | null;
}) {
  const existingContract = project ? entity(project, "contract") : null;
  const [form, setForm] = useState<ProjectFormData>(() => {
    if (project) return {
      title: str(project, "title"),
      tag: str(project, "tag"),
      description: str(project, "description"),
      startDate: str(project, "start_date"),
      endDate: str(project, "end_date"),
      contractId: existingContract?.id ?? null,
    };
    return { title: "", tag: "#", description: "", startDate: "", endDate: "", contractId: null };
  });
  const [saving, setSaving] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const isNew = !project;
  const contractList = Object.values(contracts);

  function update<K extends keyof ProjectFormData>(field: K, value: ProjectFormData[K]) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setValidationError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim()) { setValidationError("Title is required"); return; }
    if (!form.tag.match(/^#\S+$/)) { setValidationError("Tag must start with # and contain no spaces"); return; }
    setSaving(true);
    await onSave(form);
    setSaving(false);
  }

  return (
    <form onSubmit={handleSubmit} className="p-5 space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{isNew ? "New Project" : "Edit Project"}</h2>
        <div className="flex items-center gap-2">
          <button type="button" onClick={onCancel}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
            <X size={14} /> Cancel
          </button>
          <button type="submit" disabled={saving}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium text-primary hover:bg-bg-hover transition-colors disabled:opacity-40">
            <Save size={14} /> {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>

      <p className="text-xs text-muted"><span className="text-accent">*</span> Required</p>

      {(validationError || error) && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">{validationError || error}</div>
      )}

      <Section title="Project">
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Title" value={form.title} onChange={(v) => update("title", v)} autoFocus required />
          <FormField label="Tag" value={form.tag} onChange={(v) => update("tag", v)} required />
        </div>
        <div className="mt-3">
          <label className="block text-xs text-tertiary mb-1">Description</label>
          <textarea value={form.description} onChange={(e) => update("description", e.target.value)} rows={3}
            className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors resize-none" />
        </div>
      </Section>

      <Section title="Dates">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-tertiary mb-1">Start Date <span className="text-accent">*</span></label>
            <input type="date" value={form.startDate} onChange={(e) => update("startDate", e.target.value)}
              className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors" />
          </div>
          <div>
            <label className="block text-xs text-tertiary mb-1">End Date <span className="text-accent">*</span></label>
            <input type="date" value={form.endDate} onChange={(e) => update("endDate", e.target.value)}
              className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors" />
          </div>
        </div>
      </Section>

      <Section title="Contract">
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

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-wider text-secondary mb-2">{title}</div>
      {children}
    </div>
  );
}

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

function ToolbarButton({ icon, label, onClick }: {
  icon: React.ReactNode; label?: string; onClick: () => void;
}) {
  return (
    <button onClick={onClick}
      className="flex items-center gap-1.5 px-2 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
      {icon}
      {label && <span>{label}</span>}
    </button>
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

const ACCEPT_EXTENSIONS = [".pdf", ".txt", ".md", ".text"];

function ProjectImportPanel({ parsing, parseError, parsedProjects, contracts, onFileSelected, onAccept, onAcceptAll, onDiscard, onUpdate, onClose }: {
  parsing: boolean;
  parseError: string | null;
  parsedProjects: ParsedProject[];
  contracts: Record<string, Entity>;
  onFileSelected: (file: File) => void;
  onAccept: (p: ParsedProject) => void;
  onAcceptAll: () => void;
  onDiscard: (p: ParsedProject) => void;
  onUpdate: (index: number, p: ParsedProject) => void;
  onClose: () => void;
}) {
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && ACCEPT_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext))) onFileSelected(file);
  }, [onFileSelected]);

  const contractList = Object.values(contracts);

  return (
    <div className="p-5 space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={18} className="text-fuchsia-400" />
          <h2 className="text-lg font-semibold">Import Projects from Document</h2>
        </div>
        <button onClick={onClose}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
          <X size={14} /> Close
        </button>
      </div>

      {parsedProjects.length === 0 && !parsing && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`flex flex-col items-center justify-center gap-3 p-10 rounded-xl border-2 border-dashed cursor-pointer transition-colors
            ${dragOver ? "border-fuchsia-400 bg-fuchsia-500/5" : "border-border-subtle hover:border-fuchsia-400/50 hover:bg-fuchsia-500/5"}`}
        >
          <FileUp size={32} strokeWidth={1.4} className="text-fuchsia-400" />
          <div className="text-center">
            <p className="text-sm font-medium">Drop a document here</p>
            <p className="text-xs text-tertiary mt-1">PDF, TXT, or Markdown — AI will extract projects</p>
          </div>
          <input ref={fileInputRef} type="file" className="hidden" accept=".pdf,.txt,.md,.text" onChange={(e) => { const f = e.target.files?.[0]; if (f) onFileSelected(f); }} />
        </div>
      )}

      {parsing && (
        <div className="flex items-center justify-center gap-3 py-10">
          <Loader2 size={20} className="animate-spin text-fuchsia-400" />
          <span className="text-sm text-secondary">Parsing document with AI…</span>
        </div>
      )}

      {parseError && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">{parseError}</div>
      )}

      {parsedProjects.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-secondary">
              <span className="font-medium text-fuchsia-400">{parsedProjects.length}</span> project{parsedProjects.length !== 1 ? "s" : ""} found
            </p>
            <button onClick={onAcceptAll}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium text-fuchsia-400 hover:bg-fuchsia-500/10 border border-fuchsia-400/30 transition-colors">
              <CheckCheck size={14} /> Accept All
            </button>
          </div>
          {parsedProjects.map((p, i) => (
            <ParsedProjectCard key={i} project={p} contracts={contractList}
              onAccept={() => onAccept(p)}
              onDiscard={() => onDiscard(p)}
              onUpdate={(updated) => onUpdate(i, updated)} />
          ))}
        </div>
      )}
    </div>
  );
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
