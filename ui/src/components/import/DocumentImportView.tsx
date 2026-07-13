import { useEffect, useState, useRef, useCallback } from "react";
import {
  FileUp, Sparkles, Loader2, X, Check, CheckCheck,
  Trash2, ChevronDown, ChevronRight, Link2, AlertTriangle,
  Users, Building2, FileSignature, FolderKanban, Circle,
  XCircle, ReceiptText, Plus, Minus,
} from "lucide-react";
import { rpc } from "../../api/rpc";

// ---------------------------------------------------------------------------
// Types — RPC response shapes from `imports.parse_document_for_import`.
// Source of truth: tuttle/model.py (SQLModel classes) + tuttle/llm.py (extraction schemas).
// These interfaces only type the JSON returned by the backend; validation and
// required-field logic live server-side. Do NOT add constraints here.
// Only fields accessed by view rendering logic are listed explicitly.
// ---------------------------------------------------------------------------

interface ParsedContact {
  ref: string;
  first_name: string; last_name: string;
  company: string; email: string;
  address: Record<string, string> | null;
  [key: string]: any;
}

interface ParsedClient {
  ref: string; name: string; contact_ref: string;
  [key: string]: any;
}

interface ParsedContract {
  ref: string; title: string; client_ref: string;
  [key: string]: any;
}

interface ParsedProject {
  ref: string; title: string; contract_ref: string;
  [key: string]: any;
}

interface ParsedInvoiceItem {
  [key: string]: any;
}

interface ParsedInvoice {
  ref: string; number: string; date: string;
  contract_ref: string; project_ref: string;
  items: ParsedInvoiceItem[];
  sent: boolean; paid: boolean;
  [key: string]: any;
}

type EntityStatus = "accepted" | "discarded";

interface ImportEntity<T> {
  data: T;
  status: EntityStatus;
  matchedExistingId?: number;
  existingData?: Record<string, unknown>;
  updateExisting?: boolean;
}

interface ExistingEntity {
  id: number;
  [key: string]: unknown;
}

interface ExistingEntities {
  contacts: ExistingEntity[];
  clients: ExistingEntity[];
  contracts: ExistingEntity[];
  projects: ExistingEntity[];
}

type StepStatus = "pending" | "running" | "done" | "error";

interface ImportStep {
  key: string;
  label: string;
  status: StepStatus;
  error: string | null;
}

interface ExtractionResult {
  steps: ImportStep[];
  contacts?: ParsedContact[];
  clients?: ParsedClient[];
  contracts?: ParsedContract[];
  projects?: ParsedProject[];
  invoices?: ParsedInvoice[];
}

type Phase = "upload" | "review" | "committed";

const PIPELINE_STEPS: Omit<ImportStep, "status" | "error">[] = [
  { key: "load_config", label: "Loading LLM configuration" },
  { key: "read_document", label: "Reading document" },
  { key: "connect_llm", label: "Connecting to LLM" },
  { key: "summarize_document", label: "Analysing document" },
  { key: "extract_entities", label: "Extracting structured data" },
  { key: "map_results", label: "Processing results" },
];

function makeSteps(upTo: number, running: number): ImportStep[] {
  return PIPELINE_STEPS.map((s, i) => ({
    ...s,
    status: i < upTo ? "done" : i === running ? "running" : "pending",
    error: null,
  }));
}

// ---------------------------------------------------------------------------
// Main View
// ---------------------------------------------------------------------------

export function DocumentImportView() {
  const [phase, setPhase] = useState<Phase>("upload");
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [importSteps, setImportSteps] = useState<ImportStep[]>([]);

  const [contacts, setContacts] = useState<ImportEntity<ParsedContact>[]>([]);
  const [clients, setClients] = useState<ImportEntity<ParsedClient>[]>([]);
  const [contracts, setContracts] = useState<ImportEntity<ParsedContract>[]>([]);
  const [projects, setProjects] = useState<ImportEntity<ParsedProject>[]>([]);
  const [invoices, setInvoices] = useState<ImportEntity<ParsedInvoice>[]>([]);

  const [existing, setExisting] = useState<ExistingEntities | null>(null);
  const [fieldMeta, setFieldMeta] = useState<Record<string, { required: string[]; enums: Record<string, string[]> }>>({});
  const [commitResult, setCommitResult] = useState<Record<string, string[]> | null>(null);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [committing, setCommitting] = useState(false);

  // Keep original file content for PDF storage
  const [fileBase64, setFileBase64] = useState<string | null>(null);

  useEffect(() => {
    rpc<ExistingEntities>("imports.get_existing_entities").then((res) => {
      if (res.ok && res.data) setExisting(res.data);
    });
    rpc<Record<string, { required: string[]; enums: Record<string, string[]> }>>("imports.get_field_metadata").then((res) => {
      if (res.ok && res.data) setFieldMeta(res.data);
    });
  }, []);

  async function handleFile(file: File) {
    setParsing(true);
    setParseError(null);

    setImportSteps(makeSteps(0, 0));
    const t1 = setTimeout(() => setImportSteps(makeSteps(1, 1)), 300);
    const t2 = setTimeout(() => setImportSteps(makeSteps(2, 2)), 600);
    const t3 = setTimeout(() => setImportSteps(makeSteps(3, 3)), 1000);

    try {
      const buffer = await file.arrayBuffer();
      const base64 = btoa(
        new Uint8Array(buffer).reduce((d, b) => d + String.fromCharCode(b), "")
      );
      setFileBase64(base64);

      const res = await rpc<ExtractionResult>("llm.parse_document_for_import", {
        file_base64: base64, file_name: file.name,
      });

      clearTimeout(t1); clearTimeout(t2); clearTimeout(t3);
      const data = res.data ?? (res as unknown as { data: ExtractionResult }).data;
      if (data?.steps) setImportSteps(data.steps);

      if (res.ok && data?.contacts) {
        const ex = existing;
        setContacts(data.contacts.map((c) => autoMatch(c, ex?.contacts, "first_name", "last_name")));
        setClients((data.clients ?? []).map((c) => autoMatch(c, ex?.clients, "name")));
        setContracts((data.contracts ?? []).map((c) => autoMatch(c, ex?.contracts, "title")));
        setProjects((data.projects ?? []).map((c) => autoMatch(c, ex?.projects, "title")));
        setInvoices((data.invoices ?? []).map((inv) => ({
          data: { ...inv, sent: true, paid: false },
          status: "accepted",
        })));
        setPhase("review");
      } else {
        const failedStep = data?.steps?.find((s: ImportStep) => s.status === "error");
        setParseError(failedStep?.error || res.error || "Failed to parse document.");
      }
    } catch (err) {
      clearTimeout(t1); clearTimeout(t2); clearTimeout(t3);
      setParseError(String(err));
    }
    setParsing(false);
  }

  function startOver() {
    setPhase("upload");
    setContacts([]); setClients([]); setContracts([]); setProjects([]); setInvoices([]);
    setCommitResult(null); setCommitError(null);
    setImportSteps([]); setParseError(null);
    setFileBase64(null);
  }

  async function handleCommit() {
    setCommitError(null);
    setCommitting(true);

    const payload: Record<string, unknown> = {
      contacts: accepted(contacts).map((e) => commitShape(e)),
      clients: accepted(clients).map((e) => commitShape(e)),
      contracts: accepted(contracts).map((e) => commitShape(e)),
      projects: accepted(projects).map((e) => commitShape(e)),
      invoices: accepted(invoices).map((e) => commitShape(e)),
    };

    if (fileBase64 && accepted(invoices).length > 0) {
      payload.file_base64 = fileBase64;
    }

    const res = await rpc<Record<string, string[]>>("imports.commit_import", { data: payload });
    setCommitting(false);
    if (res.ok && res.data) {
      setCommitResult(res.data);
      setPhase("committed");
    } else {
      setCommitError(res.error || "Commit failed.");
    }
  }

  const totalAccepted = accepted(contacts).length + accepted(clients).length
    + accepted(contracts).length + accepted(projects).length + accepted(invoices).length;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 py-2 shrink-0 border-b border-border-subtle">
        <Sparkles size={16} className="text-fuchsia-400" />
        <h2 className="text-sm font-semibold">Document Import</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        {phase === "upload" && (
          <UploadPhase
            parsing={parsing}
            parseError={parseError}
            importSteps={importSteps}
            onFileSelected={handleFile}
          />
        )}

        {phase === "review" && (
          <div className="space-y-6 max-w-4xl">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Review Extracted Data</h2>
              <div className="flex items-center gap-2">
                <button onClick={startOver}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
                  <X size={14} /> Start Over
                </button>
                <button
                  onClick={handleCommit}
                  disabled={totalAccepted === 0 || committing}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium text-fuchsia-400 hover:bg-fuchsia-500/10 border border-fuchsia-400/30 transition-colors disabled:opacity-40"
                >
                  {committing ? <Loader2 size={14} className="animate-spin" /> : <CheckCheck size={14} />}
                  {committing ? "Committing..." : `Commit ${totalAccepted} Items`}
                </button>
              </div>
            </div>

            {commitError && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400 whitespace-pre-line">
                {commitError}
              </div>
            )}

            {/* Invoice Section (shown first when present) */}
            {invoices.length > 0 && (
              <InvoiceSection
                invoices={invoices}
                setInvoices={setInvoices}
                importedContracts={contracts}
                importedProjects={projects}
                existingContracts={existing?.contracts || []}
                existingProjects={existing?.projects || []}
                requiredFields={fieldMeta.invoices?.required || []}
                itemRequiredFields={fieldMeta.invoice_items?.required || []}
              />
            )}

            <EntitySection<ParsedContact>
              icon={<Users size={16} />}
              title="Contacts"
              items={contacts}
              setItems={setContacts}
              existing={existing?.contacts || []}
              matchFields={["first_name", "last_name"]}
              renderCard={(item, idx, update) => (
                <ContactCard item={item} onUpdate={(u) => update(idx, u)} existing={existing?.contacts || []} />
              )}
            />

            <EntitySection<ParsedClient>
              icon={<Building2 size={16} />}
              title="Clients"
              items={clients}
              setItems={setClients}
              existing={existing?.clients || []}
              matchFields={["name"]}
              renderCard={(item, idx, update) => (
                <ClientCard
                  item={item} onUpdate={(u) => update(idx, u)}
                  existing={existing?.clients || []}
                  contacts={contacts}
                  existingContacts={existing?.contacts || []}
                  requiredFields={fieldMeta.clients?.required || []}
                />
              )}
            />

            <EntitySection<ParsedContract>
              icon={<FileSignature size={16} />}
              title="Contracts"
              items={contracts}
              setItems={setContracts}
              existing={existing?.contracts || []}
              matchFields={["title"]}
              renderCard={(item, idx, update) => (
                <ContractCard
                  item={item} onUpdate={(u) => update(idx, u)}
                  existing={existing?.contracts || []}
                  clients={clients}
                  requiredFields={fieldMeta.contracts?.required || []}
                  enumFields={fieldMeta.contracts?.enums || {}}
                />
              )}
            />

            <EntitySection<ParsedProject>
              icon={<FolderKanban size={16} />}
              title="Projects"
              items={projects}
              setItems={setProjects}
              existing={existing?.projects || []}
              matchFields={["title"]}
              renderCard={(item, idx, update) => (
                <ProjectCard
                  item={item} onUpdate={(u) => update(idx, u)}
                  existing={existing?.projects || []}
                  importedContracts={contracts}
                  requiredFields={fieldMeta.projects?.required || []}
                />
              )}
            />
          </div>
        )}

        {phase === "committed" && commitResult && (
          <CommittedPhase result={commitResult} onDone={startOver} />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Upload Phase
// ---------------------------------------------------------------------------

const ACCEPT_EXTENSIONS = [".pdf", ".txt", ".md", ".text"];

function StepIcon({ status }: { status: StepStatus }) {
  switch (status) {
    case "done":
      return <Check size={14} className="text-emerald-400" />;
    case "running":
      return <Loader2 size={14} className="animate-spin text-fuchsia-400" />;
    case "error":
      return <XCircle size={14} className="text-red-400" />;
    default:
      return <Circle size={14} className="text-tertiary/40" />;
  }
}

function PipelineSteps({ steps, error }: { steps: ImportStep[]; error: string | null }) {
  const hasError = steps.some((s) => s.status === "error");

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        {steps.map((step) => (
          <div
            key={step.key}
            className={`flex items-start gap-3 px-3 py-2 rounded-lg transition-colors ${
              step.status === "running" ? "bg-fuchsia-500/5" :
              step.status === "error" ? "bg-red-500/5" :
              ""
            }`}
          >
            <div className="mt-0.5 shrink-0">
              <StepIcon status={step.status} />
            </div>
            <div className="min-w-0 flex-1">
              <p className={`text-sm ${
                step.status === "done" ? "text-secondary" :
                step.status === "running" ? "text-primary font-medium" :
                step.status === "error" ? "text-red-400 font-medium" :
                "text-tertiary"
              }`}>
                {step.label}
              </p>
              {step.status === "error" && step.error && (
                <p className="text-xs text-red-400/80 mt-1">{step.error}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {hasError && error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">
          {error}
        </div>
      )}
    </div>
  );
}

function UploadPhase({ parsing, parseError, importSteps, onFileSelected }: {
  parsing: boolean; parseError: string | null;
  importSteps: ImportStep[];
  onFileSelected: (f: File) => void;
}) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const hasSteps = importSteps.length > 0;
  const hasError = importSteps.some((s) => s.status === "error");

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && ACCEPT_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext)))
      onFileSelected(file);
  }, [onFileSelected]);

  return (
    <div className="max-w-xl mx-auto mt-12 space-y-5">
      <div className="text-center space-y-2">
        <h2 className="text-xl font-semibold">Import a Document</h2>
        <p className="text-sm text-secondary">
          Import contacts, clients, and contracts from documents using AI-powered extraction.
        </p>
      </div>

      {!parsing && !hasSteps && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`flex flex-col items-center justify-center gap-3 p-10 rounded-xl border-2 border-dashed cursor-pointer transition-colors
            ${dragOver ? "border-fuchsia-400 bg-fuchsia-500/5" : "border-border-subtle hover:border-fuchsia-400/50 hover:bg-fuchsia-500/5"}`}
        >
          <FileUp size={32} strokeWidth={1.4} className="text-fuchsia-400" />
          <div className="text-center">
            <p className="text-sm font-medium">Drop a document here</p>
            <p className="text-xs text-tertiary mt-1">PDF, TXT, or Markdown</p>
          </div>
          <input ref={inputRef} type="file" className="hidden"
            accept=".pdf,.txt,.md,.text" onChange={(e) => { const f = e.target.files?.[0]; if (f) onFileSelected(f); }} />
        </div>
      )}

      {(parsing || hasSteps) && (
        <div className="rounded-xl border border-border-subtle bg-bg-card p-5">
          {hasSteps ? (
            <PipelineSteps steps={importSteps} error={parseError} />
          ) : (
            <div className="flex items-center justify-center gap-3 py-6">
              <Loader2 size={20} className="animate-spin text-fuchsia-400" />
              <span className="text-sm text-secondary">Preparing...</span>
            </div>
          )}
        </div>
      )}

      {!hasSteps && parseError && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">
          {parseError}
        </div>
      )}

      {hasError && (
        <label className="flex items-center gap-2 mx-auto px-4 py-2 rounded-lg text-sm font-medium text-fuchsia-400 hover:bg-fuchsia-500/10 border border-fuchsia-400/30 transition-colors cursor-pointer">
          <FileUp size={14} /> Try Again
          <input type="file" className="hidden"
            accept=".pdf,.txt,.md,.text" onChange={(e) => { const f = e.target.files?.[0]; if (f) onFileSelected(f); }} />
        </label>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Committed Phase
// ---------------------------------------------------------------------------

function CommittedPhase({ result, onDone }: {
  result: Record<string, string[]>; onDone: () => void;
}) {
  const created = result.created || [];
  const linked = result.linked || [];
  const updated = result.updated || [];
  const total = created.length + linked.length + updated.length;

  return (
    <div className="max-w-xl mx-auto mt-12 space-y-5 text-center">
      <div className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto">
        <Check size={32} className="text-emerald-400" />
      </div>
      <h2 className="text-xl font-semibold">Import Complete</h2>
      <p className="text-sm text-secondary">{total} items processed.</p>

      <div className="text-left space-y-2 bg-bg-card rounded-lg border border-border-subtle p-4">
        {created.length > 0 && (
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-1">Created</div>
            {created.map((s, i) => <div key={i} className="text-sm text-secondary">{s}</div>)}
          </div>
        )}
        {linked.length > 0 && (
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-blue-400 mb-1">Linked to existing</div>
            {linked.map((s, i) => <div key={i} className="text-sm text-secondary">{s}</div>)}
          </div>
        )}
        {updated.length > 0 && (
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-amber-400 mb-1">Updated</div>
            {updated.map((s, i) => <div key={i} className="text-sm text-secondary">{s}</div>)}
          </div>
        )}
      </div>

      <button onClick={onDone}
        className="px-5 py-2 rounded-lg bg-bg-card text-primary text-sm font-medium border border-border-subtle hover:bg-bg-hover transition-colors">
        Done
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Invoice Section
// ---------------------------------------------------------------------------

function InvoiceSection({ invoices, setInvoices, importedContracts, importedProjects, existingContracts, existingProjects, requiredFields, itemRequiredFields }: {
  invoices: ImportEntity<ParsedInvoice>[];
  setInvoices: React.Dispatch<React.SetStateAction<ImportEntity<ParsedInvoice>[]>>;
  importedContracts: ImportEntity<ParsedContract>[];
  importedProjects: ImportEntity<ParsedProject>[];
  existingContracts: ExistingEntity[];
  existingProjects: ExistingEntity[];
  requiredFields: string[];
  itemRequiredFields: string[];
}) {
  const [collapsed, setCollapsed] = useState(false);
  if (invoices.length === 0) return null;

  const acceptedCount = invoices.filter((i) => i.status === "accepted").length;

  function update(idx: number, item: ImportEntity<ParsedInvoice>) {
    setInvoices((prev) => prev.map((p, i) => i === idx ? item : p));
  }

  function toggleStatus(idx: number) {
    setInvoices((prev) => prev.map((p, i) =>
      i === idx ? { ...p, status: p.status === "accepted" ? "discarded" : "accepted" } : p
    ));
  }

  return (
    <div>
      <div onClick={() => setCollapsed((c) => !c)}
        className="flex items-center gap-2 w-full py-2 text-left group cursor-pointer" role="button">
        {collapsed ? <ChevronRight size={14} className="text-tertiary" /> : <ChevronDown size={14} className="text-tertiary" />}
        <span className="text-tertiary"><ReceiptText size={16} /></span>
        <span className="text-sm font-semibold">Invoices</span>
        <span className="text-xs text-fuchsia-400 font-medium">
          {acceptedCount}/{invoices.length}
        </span>
      </div>

      {!collapsed && (
        <div className="space-y-3 ml-6">
          {invoices.map((item, idx) => (
            <div key={item.data.ref || `inv-${idx}`} className={`rounded-xl border-2 p-4 transition-all ${
              item.status === "discarded"
                ? "border-border-subtle opacity-50"
                : "border-fuchsia-400/40 bg-fuchsia-500/5"
            }`}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium px-2 py-0.5 rounded bg-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-400/30">
                    <Sparkles size={11} className="inline -mt-0.5 mr-1" />
                    Will create
                  </span>
                </div>
                <button
                  onClick={() => toggleStatus(idx)}
                  className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
                    item.status === "discarded"
                      ? "text-fuchsia-400 hover:bg-fuchsia-500/10"
                      : "text-secondary hover:text-red-400 hover:bg-red-500/10"
                  }`}
                >
                  {item.status === "discarded" ? <><Check size={12} /> Restore</> : <><Trash2 size={12} /> Discard</>}
                </button>
              </div>
              {item.status === "accepted" && (
                <InvoiceCard
                  item={item}
                  onUpdate={(u) => update(idx, u)}
                  importedContracts={importedContracts}
                  importedProjects={importedProjects}
                  existingContracts={existingContracts}
                  existingProjects={existingProjects}
                  requiredFields={requiredFields}
                  itemRequiredFields={itemRequiredFields}
                />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function InvoiceCard({ item, onUpdate, importedContracts, importedProjects, existingContracts, existingProjects, requiredFields, itemRequiredFields }: {
  item: ImportEntity<ParsedInvoice>;
  onUpdate: (u: ImportEntity<ParsedInvoice>) => void;
  importedContracts: ImportEntity<ParsedContract>[];
  importedProjects: ImportEntity<ParsedProject>[];
  existingContracts: ExistingEntity[];
  existingProjects: ExistingEntity[];
  requiredFields: string[];
  itemRequiredFields: string[];
}) {
  const d = item.data;
  const acceptedContracts = importedContracts.filter((c) => c.status === "accepted");
  const acceptedProjects = importedProjects.filter((c) => c.status === "accepted");

  const req = (f: string) => requiredFields.includes(f);
  const ireq = (f: string) => itemRequiredFields.includes(f);

  function set<K extends keyof ParsedInvoice>(field: K, value: ParsedInvoice[K]) {
    onUpdate({ ...item, data: { ...d, [field]: value } });
  }

  function updateItem(idx: number, field: keyof ParsedInvoiceItem, value: string | number | null) {
    const newItems = [...d.items];
    newItems[idx] = { ...newItems[idx], [field]: value };
    set("items", newItems);
  }

  function addItem() {
    set("items", [...d.items, {
      start_date: d.date || "", end_date: "",
      quantity: 1, unit: "hour", unit_price: 0,
      description: "", VAT_rate: 0.19,
    }]);
  }

  function removeItem(idx: number) {
    set("items", d.items.filter((_, i) => i !== idx));
  }

  // Build contract options: imported refs + existing DB records
  const contractOptions: { value: string; label: string; isRef?: boolean }[] = [
    ...acceptedContracts.map((c) => ({
      value: c.data.ref, label: c.data.title || c.data.ref, isRef: true,
    })),
    ...existingContracts.map((c) => ({
      value: `existing:${c.id}`, label: (c.title as string) || `#${c.id}`,
    })),
  ];

  const projectOptions: { value: string; label: string; isRef?: boolean }[] = [
    ...acceptedProjects.map((p) => ({
      value: p.data.ref, label: p.data.title || p.data.ref, isRef: true,
    })),
    ...existingProjects.map((p) => ({
      value: `existing:${p.id}`, label: (p.title as string) || `#${p.id}`,
    })),
  ];

  return (
    <div className="space-y-3">
      {/* Invoice header fields */}
      <div className="grid grid-cols-3 gap-2">
        <AiField label="Invoice Number" value={d.number} onChange={(v) => set("number", v)} required={req("number")} />
        <AiField label="Date" value={d.date} onChange={(v) => set("date", v)} type="date" required={req("date")} />
        <AiField label="Notes" value={d.notes} onChange={(v) => set("notes", v)} required={req("notes")} />
      </div>

      {/* Status flags */}
      <div className="flex items-center gap-4">
        <label className="flex items-center gap-1.5 text-xs text-secondary cursor-pointer">
          <input type="checkbox" checked={d.sent}
            onChange={(e) => set("sent", e.target.checked)}
            className="rounded border-border-subtle" />
          Sent
        </label>
        <label className="flex items-center gap-1.5 text-xs text-secondary cursor-pointer">
          <input type="checkbox" checked={d.paid}
            onChange={(e) => set("paid", e.target.checked)}
            className="rounded border-border-subtle" />
          Paid
        </label>
      </div>

      {/* Contract / Project linking */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-xs text-fuchsia-300/70 mb-0.5">Contract</label>
          <select
            value={d.contract_ref || ""}
            onChange={(e) => set("contract_ref", e.target.value)}
            className="w-full px-2.5 py-1.5 rounded-md text-sm bg-bg-card text-primary border border-fuchsia-400/30 outline-none focus:border-fuchsia-400 transition-colors"
          >
            <option value="">-- Select --</option>
            {contractOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-fuchsia-300/70 mb-0.5">Project</label>
          <select
            value={d.project_ref || ""}
            onChange={(e) => set("project_ref", e.target.value)}
            className="w-full px-2.5 py-1.5 rounded-md text-sm bg-bg-card text-primary border border-fuchsia-400/30 outline-none focus:border-fuchsia-400 transition-colors"
          >
            <option value="">-- Select --</option>
            {projectOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Line items table */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-secondary uppercase tracking-wider">Line Items</span>
          <button onClick={addItem}
            className="flex items-center gap-1 text-xs text-fuchsia-400 hover:text-fuchsia-300 transition-colors">
            <Plus size={12} /> Add Item
          </button>
        </div>
        <div className="space-y-2">
          {d.items.map((li, idx) => {
            const missing = (f: string, v: any) => ireq(f) && (v == null || v === "");
            const borderCls = (f: string, v: any) =>
              missing(f, v) ? "border-red-400/60" : "border-fuchsia-400/20";
            return (
            <div key={idx} className="grid grid-cols-[1fr_80px_60px_90px_70px_28px] gap-1.5 items-end">
              <div>
                <label className="block text-[10px] text-tertiary mb-0.5">
                  Description{ireq("description") && <span className="text-red-400 ml-0.5">*</span>}
                </label>
                <input value={li.description} onChange={(e) => updateItem(idx, "description", e.target.value)}
                  className={`w-full px-2 py-1 rounded text-xs bg-bg-card text-primary border ${borderCls("description", li.description)} outline-none focus:border-fuchsia-400`} />
              </div>
              <div>
                <label className="block text-[10px] text-tertiary mb-0.5">
                  Qty{ireq("quantity") && <span className="text-red-400 ml-0.5">*</span>}
                </label>
                <input type="number" step="any" value={li.quantity ?? ""} onChange={(e) => updateItem(idx, "quantity", e.target.value ? parseFloat(e.target.value) : null)}
                  className={`w-full px-2 py-1 rounded text-xs bg-bg-card text-primary border ${borderCls("quantity", li.quantity)} outline-none focus:border-fuchsia-400`} />
              </div>
              <div>
                <label className="block text-[10px] text-tertiary mb-0.5">
                  Unit{ireq("unit") && <span className="text-red-400 ml-0.5">*</span>}
                </label>
                <input value={li.unit} onChange={(e) => updateItem(idx, "unit", e.target.value)}
                  className={`w-full px-2 py-1 rounded text-xs bg-bg-card text-primary border ${borderCls("unit", li.unit)} outline-none focus:border-fuchsia-400`} />
              </div>
              <div>
                <label className="block text-[10px] text-tertiary mb-0.5">
                  Unit Price{ireq("unit_price") && <span className="text-red-400 ml-0.5">*</span>}
                </label>
                <input type="number" step="any" value={li.unit_price ?? ""} onChange={(e) => updateItem(idx, "unit_price", e.target.value ? parseFloat(e.target.value) : null)}
                  className={`w-full px-2 py-1 rounded text-xs bg-bg-card text-primary border ${borderCls("unit_price", li.unit_price)} outline-none focus:border-fuchsia-400`} />
              </div>
              <div>
                <label className="block text-[10px] text-tertiary mb-0.5">
                  VAT %{ireq("VAT_rate") && <span className="text-red-400 ml-0.5">*</span>}
                </label>
                <input type="number" step="any"
                  value={li.VAT_rate != null ? String(Math.round((li.VAT_rate > 1 ? li.VAT_rate : li.VAT_rate * 100) * 100) / 100) : ""}
                  onChange={(e) => {
                    const pct = e.target.value ? parseFloat(e.target.value) : null;
                    updateItem(idx, "VAT_rate", pct == null ? null : pct / 100);
                  }}
                  className={`w-full px-2 py-1 rounded text-xs bg-bg-card text-primary border ${borderCls("VAT_rate", li.VAT_rate)} outline-none focus:border-fuchsia-400`} />
              </div>
              <button onClick={() => removeItem(idx)}
                className="p-1 rounded text-tertiary hover:text-red-400 hover:bg-red-500/10 transition-colors">
                <Minus size={12} />
              </button>
            </div>
            );
          })}
        </div>
        {d.items.length > 0 && (
          <div className="mt-2 text-right text-xs text-secondary">
            Subtotal: {d.items.reduce((sum, li) => sum + (li.quantity || 0) * (li.unit_price || 0), 0).toFixed(2)}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Generic Entity Section
// ---------------------------------------------------------------------------

function EntitySection<T extends { ref: string }>({ icon, title, items, setItems, existing, matchFields, renderCard }: {
  icon: React.ReactNode;
  title: string;
  items: ImportEntity<T>[];
  setItems: React.Dispatch<React.SetStateAction<ImportEntity<T>[]>>;
  existing: ExistingEntity[];
  matchFields: string[];
  renderCard: (item: ImportEntity<T>, idx: number, update: (idx: number, item: ImportEntity<T>) => void) => React.ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);
  if (items.length === 0) return null;

  const acceptedCount = items.filter((i) => i.status === "accepted").length;

  function update(idx: number, item: ImportEntity<T>) {
    setItems((prev) => prev.map((p, i) => i === idx ? item : p));
  }

  function toggleStatus(idx: number) {
    setItems((prev) => prev.map((p, i) =>
      i === idx ? { ...p, status: p.status === "accepted" ? "discarded" : "accepted" } : p
    ));
  }

  function acceptAll() {
    setItems((prev) => prev.map((p) => ({ ...p, status: "accepted" })));
  }

  return (
    <div>
      <div onClick={() => setCollapsed((c) => !c)}
        className="flex items-center gap-2 w-full py-2 text-left group cursor-pointer" role="button">
        {collapsed ? <ChevronRight size={14} className="text-tertiary" /> : <ChevronDown size={14} className="text-tertiary" />}
        <span className="text-tertiary">{icon}</span>
        <span className="text-sm font-semibold">{title}</span>
        <span className="text-xs text-fuchsia-400 font-medium">
          {acceptedCount}/{items.length}
        </span>
        {acceptedCount < items.length && (
          <button
            onClick={(e) => { e.stopPropagation(); acceptAll(); }}
            className="ml-auto text-xs text-fuchsia-400 hover:text-fuchsia-300 transition-colors"
          >
            Accept All
          </button>
        )}
      </div>

      {!collapsed && (
        <div className="space-y-3 ml-6">
          {items.map((item, idx) => (
            <div key={item.data.ref} className={`rounded-xl border-2 p-4 transition-all ${
              item.status === "discarded"
                ? "border-border-subtle opacity-50"
                : "border-fuchsia-400/40 bg-fuchsia-500/5"
            }`}>
              <div className="flex items-center justify-between mb-3">
                <MatchBadge item={item} existing={existing}
                  onChangeMatch={(id) => update(idx, {
                    ...item,
                    matchedExistingId: id || undefined,
                    existingData: id ? existing.find((e) => e.id === id) : undefined,
                  })}
                />
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toggleStatus(idx)}
                    className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
                      item.status === "discarded"
                        ? "text-fuchsia-400 hover:bg-fuchsia-500/10"
                        : "text-secondary hover:text-red-400 hover:bg-red-500/10"
                    }`}
                  >
                    {item.status === "discarded" ? <><Check size={12} /> Restore</> : <><Trash2 size={12} /> Discard</>}
                  </button>
                </div>
              </div>
              {item.status === "accepted" && renderCard(item, idx, update)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Match Badge + Dropdown
// ---------------------------------------------------------------------------

function MatchBadge<T extends { ref: string }>({ item, existing, onChangeMatch }: {
  item: ImportEntity<T>;
  existing: ExistingEntity[];
  onChangeMatch: (id: number | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const matched = item.matchedExistingId;
  const matchedEntity = matched ? existing.find((e) => e.id === matched) : null;
  const matchLabel = matchedEntity
    ? (matchedEntity.name || matchedEntity.title || `${matchedEntity.first_name} ${matchedEntity.last_name}` || `#${matchedEntity.id}`) as string
    : null;

  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-colors ${
          matched
            ? "text-blue-400 bg-blue-500/10 border border-blue-400/30"
            : "text-fuchsia-400 bg-fuchsia-500/10 border border-fuchsia-400/30"
        }`}
      >
        {matched ? <><Link2 size={11} /> Update: {matchLabel}</> : <><Sparkles size={11} /> Will create</>}
        <ChevronDown size={11} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 z-50 bg-bg-sidebar border border-border-subtle rounded-lg shadow-lg py-1 min-w-[200px] max-h-48 overflow-y-auto">
          <button onClick={() => { onChangeMatch(null); setOpen(false); }}
            className={`w-full text-left px-3 py-1.5 text-xs transition-colors ${!matched ? "text-fuchsia-400 font-medium" : "text-secondary hover:bg-bg-hover"}`}>
            Create as new record
          </button>
          {existing.map((e) => {
            const label = (e.name || e.title || `${e.first_name || ""} ${e.last_name || ""}`.trim() || `#${e.id}`) as string;
            return (
              <button key={e.id} onClick={() => { onChangeMatch(e.id); setOpen(false); }}
                className={`w-full text-left px-3 py-1.5 text-xs transition-colors ${
                  matched === e.id ? "text-blue-400 font-medium" : "text-secondary hover:bg-bg-hover"
                }`}>
                {label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Entity Cards
// ---------------------------------------------------------------------------

function ContactCard({ item, onUpdate, existing }: {
  item: ImportEntity<ParsedContact>;
  onUpdate: (u: ImportEntity<ParsedContact>) => void;
  existing: ExistingEntity[];
}) {
  const d = item.data;
  const ex = item.existingData;
  const addr = d.address ?? { street: "", number: "", city: "", postal_code: "", country: "" };

  function set(field: keyof ParsedContact, value: string) {
    onUpdate({ ...item, data: { ...d, [field]: value } });
  }
  function setAddr(field: string, value: string) {
    onUpdate({ ...item, data: { ...d, address: { ...addr, [field]: value } } });
  }

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-2">
        <AiField label="First Name" value={d.first_name} dbValue={ex?.first_name as string} onChange={(v) => set("first_name", v)} />
        <AiField label="Last Name" value={d.last_name} dbValue={ex?.last_name as string} onChange={(v) => set("last_name", v)} />
        <AiField label="Company" value={d.company} dbValue={ex?.company as string} onChange={(v) => set("company", v)} />
        <AiField label="Email" value={d.email} dbValue={ex?.email as string} onChange={(v) => set("email", v)} />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <AiField label="Street" value={addr.street} onChange={(v) => setAddr("street", v)} />
        <AiField label="Number" value={addr.number} onChange={(v) => setAddr("number", v)} />
        <AiField label="City" value={addr.city} onChange={(v) => setAddr("city", v)} />
        <AiField label="Postal Code" value={addr.postal_code} onChange={(v) => setAddr("postal_code", v)} />
        <AiField label="Country" value={addr.country} onChange={(v) => setAddr("country", v)} />
      </div>
    </div>
  );
}

function ClientCard({ item, onUpdate, existing, contacts, existingContacts, requiredFields }: {
  item: ImportEntity<ParsedClient>;
  onUpdate: (u: ImportEntity<ParsedClient>) => void;
  existing: ExistingEntity[];
  contacts: ImportEntity<ParsedContact>[];
  existingContacts: ExistingEntity[];
  requiredFields: string[];
}) {
  const d = item.data;
  const ex = item.existingData;
  const acceptedContacts = contacts.filter((c) => c.status === "accepted");

  function set(field: keyof ParsedClient, value: string) {
    onUpdate({ ...item, data: { ...d, [field]: value } });
  }

  const req = (f: string) => requiredFields.includes(f);

  const contactOptions = [
    ...acceptedContacts.map((c) => ({
      ref: c.data.ref,
      label: `${c.data.first_name} ${c.data.last_name}`.trim() || c.data.company || c.data.ref,
    })),
    ...existingContacts.map((c) => ({
      ref: `existing:${c.id}`,
      label: `${c.first_name || ""} ${c.last_name || ""}`.trim() || (c.company as string) || `#${c.id}`,
    })),
  ];

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-2">
        <AiField label="Name" value={d.name} dbValue={ex?.name as string} onChange={(v) => set("name", v)} required={req("name")} />
      </div>
      <RefDropdown
        label="Invoicing Contact"
        currentRef={d.contact_ref}
        options={contactOptions}
        onChange={(ref) => set("contact_ref", ref)}
        hint={d.contact_ref}
      />
    </div>
  );
}

function ContractCard({ item, onUpdate, existing, clients, requiredFields, enumFields }: {
  item: ImportEntity<ParsedContract>;
  onUpdate: (u: ImportEntity<ParsedContract>) => void;
  existing: ExistingEntity[];
  clients: ImportEntity<ParsedClient>[];
  requiredFields: string[];
  enumFields: Record<string, string[]>;
}) {
  const d = item.data;
  const ex = item.existingData;
  const acceptedClients = clients.filter((c) => c.status === "accepted");

  function set<K extends keyof ParsedContract>(field: K, value: ParsedContract[K]) {
    onUpdate({ ...item, data: { ...d, [field]: value } });
  }

  const req = (f: string) => requiredFields.includes(f);

  // ``type`` is the single source of truth for pricing. Derive a sensible
  // initial value when the LLM did not set it explicitly, then switching
  // type clears the other value column so we never commit both.
  const ctype: string = d.type || (d.fixed_price && !d.rate ? "fixed_price" : "time_based");
  function switchType(next: string) {
    onUpdate({
      ...item,
      data: {
        ...d,
        type: next,
        rate: next === "time_based" ? d.rate : null,
        fixed_price: next === "fixed_price" ? d.fixed_price : null,
      },
    });
  }
  const isFixed = ctype === "fixed_price";

  return (
    <div className="space-y-2">
      <div className="flex rounded-md border border-fuchsia-400/30 overflow-hidden w-fit">
        {["time_based", "fixed_price"].map((mode) => (
          <button key={mode} type="button" onClick={() => switchType(mode)}
            className={`px-3 py-1 text-xs font-medium transition-colors ${ctype === mode
              ? "bg-fuchsia-500 text-white" : "bg-bg-card text-secondary hover:text-primary hover:bg-bg-hover"}`}>
            {mode === "time_based" ? "Time-Based" : "Fixed Price"}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-2">
        <AiField label="Title" value={d.title} dbValue={ex?.title as string} onChange={(v) => set("title", v)} required={req("title")} />
        {isFixed ? (
          <AiField label="Fixed Price" value={String(d.fixed_price ?? "")} onChange={(v) => set("fixed_price", v ? parseFloat(v) : null)} />
        ) : (
          <AiField label="Rate" value={String(d.rate ?? "")} onChange={(v) => set("rate", v ? parseFloat(v) : null)} />
        )}
        <AiField label="Currency" value={d.currency} onChange={(v) => set("currency", v)} required={req("currency")} />
        {!isFixed && <AiField label="Unit" value={d.unit} onChange={(v) => set("unit", v)} required={req("unit")} options={enumFields.unit} />}
        {!isFixed && <AiField label="Billing Cycle" value={d.billing_cycle} onChange={(v) => set("billing_cycle", v)} required={req("billing_cycle")} options={enumFields.billing_cycle} />}
        {!isFixed && <AiField label="Volume" value={String(d.volume ?? "")} onChange={(v) => set("volume", v ? parseInt(v) : null)} required={req("volume")} />}
      </div>
      <div className="grid grid-cols-3 gap-2">
        <AiField label="Signature Date" value={d.signature_date} onChange={(v) => set("signature_date", v)} type="date" required={req("signature_date")} />
        <AiField label="Start Date" value={d.start_date} onChange={(v) => set("start_date", v)} type="date" required={req("start_date")} />
        <AiField label="End Date" value={d.end_date} onChange={(v) => set("end_date", v)} type="date" required={req("end_date")} />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <AiField
          label="VAT Rate (%)"
          value={
            d.VAT_rate == null
              ? ""
              : String(Math.round((d.VAT_rate > 1 ? d.VAT_rate : d.VAT_rate * 100) * 100) / 100)
          }
          onChange={(v) => {
            const pct = v ? parseFloat(v) : null;
            set("VAT_rate", pct == null || !Number.isFinite(pct) ? null : pct / 100);
          }}
        />
        <AiField label="Term of Payment (days)" value={String(d.term_of_payment ?? "")} onChange={(v) => set("term_of_payment", v ? parseInt(v) : null)} />
      </div>
      <RefDropdown
        label="Client"
        currentRef={d.client_ref}
        options={acceptedClients.map((c) => ({
          ref: c.data.ref,
          label: c.data.name || c.data.ref,
        }))}
        onChange={(ref) => set("client_ref", ref)}
        hint={d.client_ref}
      />
    </div>
  );
}

function ProjectCard({ item, onUpdate, existing, importedContracts, requiredFields }: {
  item: ImportEntity<ParsedProject>;
  onUpdate: (u: ImportEntity<ParsedProject>) => void;
  existing: ExistingEntity[];
  importedContracts: ImportEntity<ParsedContract>[];
  requiredFields: string[];
}) {
  const d = item.data;
  const ex = item.existingData;
  const acceptedContracts = importedContracts.filter((c) => c.status === "accepted");

  function set<K extends keyof ParsedProject>(field: K, value: ParsedProject[K]) {
    onUpdate({ ...item, data: { ...d, [field]: value } });
  }

  const req = (f: string) => requiredFields.includes(f);

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-2">
        <AiField label="Title" value={d.title} dbValue={ex?.title as string} onChange={(v) => set("title", v)} required={req("title")} />
        <AiField label="Tag" value={d.tag} onChange={(v) => set("tag", v)} required={req("tag")} />
      </div>
      <AiField label="Description" value={d.description} onChange={(v) => set("description", v)} required={req("description")} />
      <div className="grid grid-cols-2 gap-2">
        <AiField label="Start Date" value={d.start_date} onChange={(v) => set("start_date", v)} type="date" required={req("start_date")} />
        <AiField label="End Date" value={d.end_date} onChange={(v) => set("end_date", v)} type="date" required={req("end_date")} />
      </div>
      <RefDropdown
        label="Contract"
        currentRef={d.contract_ref}
        options={acceptedContracts.map((c) => ({
          ref: c.data.ref,
          label: c.data.title || c.data.ref,
        }))}
        onChange={(ref) => set("contract_ref", ref)}
        hint={d.contract_ref}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared UI primitives
// ---------------------------------------------------------------------------

function AiField({ label, value, dbValue, onChange, type = "text", required, options }: {
  label: string; value: string | null | undefined; dbValue?: string;
  onChange: (v: string) => void; type?: string; required?: boolean;
  options?: string[];
}) {
  const safeValue = value ?? "";
  const differs = dbValue != null && dbValue !== "" && safeValue !== dbValue;
  const missing = required && !safeValue.trim();

  const fieldCls = `w-full px-2.5 py-1.5 rounded-md text-sm bg-bg-card text-primary outline-none
    focus:border-fuchsia-400 transition-colors placeholder:text-muted border ${
    missing ? "border-red-400/70 bg-red-500/5" :
    differs ? "border-amber-400/60" : "border-fuchsia-400/30"
  }`;

  return (
    <div>
      <label className={`block text-xs mb-0.5 ${missing ? "text-red-400" : "text-fuchsia-300/70"}`}>
        {label}{required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      {options ? (
        <select value={safeValue} onChange={(e) => onChange(e.target.value)} className={fieldCls}>
          <option value="">-- Select --</option>
          {options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <input type={type} value={safeValue} onChange={(e) => onChange(e.target.value)} className={fieldCls} />
      )}
      {missing && (
        <div className="text-[10px] text-red-400 mt-0.5">Required</div>
      )}
      {!missing && differs && (
        <div className="text-[10px] text-amber-400/80 mt-0.5 truncate" title={`DB: ${dbValue}`}>
          DB: {dbValue}
        </div>
      )}
    </div>
  );
}

function RefDropdown({ label, currentRef, options, onChange, hint }: {
  label: string;
  currentRef: string | null | undefined;
  options: { ref: string; label: string }[];
  onChange: (ref: string) => void;
  hint?: string;
}) {
  const safeRef = currentRef ?? "";
  const noLink = !safeRef || !options.some((o) => o.ref === safeRef);

  return (
    <div>
      <label className="block text-xs text-fuchsia-300/70 mb-0.5">
        {label}
        {noLink && options.length > 0 && (
          <span className="ml-1.5 text-amber-400">
            <AlertTriangle size={10} className="inline -mt-0.5" /> not linked
          </span>
        )}
      </label>
      <select
        value={safeRef}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-2.5 py-1.5 rounded-md text-sm bg-bg-card text-primary border border-fuchsia-400/30 outline-none focus:border-fuchsia-400 transition-colors"
      >
        <option value="">-- Select --</option>
        {options.map((o) => (
          <option key={o.ref} value={o.ref}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function autoMatch<T extends { ref: string }>(
  data: T,
  existingList: ExistingEntity[] | undefined,
  ...matchKeys: string[]
): ImportEntity<T> {
  const entity: ImportEntity<T> = { data, status: "accepted" };
  if (!existingList) return entity;

  for (const ex of existingList) {
    const d = data as unknown as Record<string, unknown>;
    const matches = matchKeys.every((k) => {
      const a = String(d[k] || "").toLowerCase().trim();
      const b = String(ex[k] || "").toLowerCase().trim();
      return a && b && a === b;
    });
    if (matches) {
      entity.matchedExistingId = ex.id;
      entity.existingData = ex as Record<string, unknown>;
      break;
    }
  }
  return entity;
}

function accepted<T>(items: ImportEntity<T>[]): ImportEntity<T>[] {
  return items.filter((i) => i.status === "accepted");
}

function commitShape<T extends { ref: string }>(item: ImportEntity<T>): Record<string, unknown> {
  const d: Record<string, unknown> = { ...item.data };
  if (item.matchedExistingId) {
    d.existing_id = item.matchedExistingId;
    d.update_existing = true;
  }
  return d;
}
