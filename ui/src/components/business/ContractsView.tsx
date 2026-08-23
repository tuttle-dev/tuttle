import { useEffect, useState, useRef, useCallback } from "react";
import {
  FileText, FileSignature, Plus, Trash2, Save, X, DollarSign, Calendar,
  FileUp, Sparkles, Check, CheckCheck, Loader2, CheckCircle2,
  FolderKanban, ReceiptText, ArrowRight, ChevronDown, ChevronRight, XCircle, Milestone,
} from "lucide-react";
import { rpc } from "../../api/rpc";
import { str, num, bool, entity as subEntity, list as entityList, displayName, formatDate } from "../../api/entity";
import { TAX_CATEGORY_LABELS, taxCategory, taxTreatment, type TaxCategory } from "../../api/tax";
import { Toolbar, ToolbarButtonPrimary, ToolbarButtonSecondary, ToolbarFilterGroup, ListDetailLayout, LIST_ROW_PADDING } from "../shared/ToolbarButtons";
import { StatusBadge } from "../shared/StatusBadge";
import { useNavigation } from "../shared/NavigationContext";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import { InfoHint } from "../shared/InfoHint";
import { useFieldRequirements } from "../../hooks/useFieldRequirements";
import type { Entity } from "../../api/types";

type Mode = "view" | "edit" | "create" | "import";
type StatusFilter = "All" | "Active" | "Upcoming" | "Completed";

function contractStatus(c: Entity): string {
  if (bool(c, "is_completed")) return "Completed";
  const start = str(c, "start_date");
  const end = str(c, "end_date");
  const today = new Date().toISOString().slice(0, 10);
  if (start > today) return "Upcoming";
  if (end && end < today) return "Completed";
  return "Active";
}

export function ContractsView() {
  const [contracts, setContracts] = useState<Entity[]>([]);
  const [clients, setClients] = useState<Record<string, Entity>>({});
  const [selected, setSelected] = useState<Entity | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("All");
  const [mode, setMode] = useState<Mode>("view");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [defaultCurrency, setDefaultCurrency] = useState("EUR");
  const [currencies, setCurrencies] = useState<string[]>(["EUR", "USD", "GBP", "CHF"]);
  const [parsedContracts, setParsedContracts] = useState<ParsedContract[]>([]);
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [bankAccounts, setBankAccounts] = useState<Entity[]>([]);
  const selectedIdRef = useRef<number | null>(null);

  useEffect(() => { selectedIdRef.current = selected?.id ?? null; }, [selected]);
  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    const [res, clRes, curRes, supRes, accRes] = await Promise.all([
      rpc<Entity[]>("contracts.get_all"),
      rpc<Record<string, Entity>>("contracts.get_all_clients"),
      rpc<string>("contracts.get_default_currency"),
      rpc<{ supported: string[] }>("settings.get_currency"),
      rpc<Entity>("users.get_active"),
    ]);
    if (res.ok && res.data) {
      setContracts(res.data);
      const currentId = selectedIdRef.current;
      if (currentId != null) {
        const updated = res.data.find((c) => c.id === currentId);
        setSelected(updated || null);
      }
    }
    if (clRes.ok && clRes.data) setClients(clRes.data);
    if (curRes.ok && curRes.data) setDefaultCurrency(curRes.data);
    if (supRes.ok && supRes.data?.supported?.length) setCurrencies(supRes.data.supported);
    const profile = accRes.ok && accRes.data ? (accRes.data.profile as Entity | undefined) : undefined;
    setBankAccounts(profile ? entityList(profile, "bank_accounts") : []);
    setLoading(false);
  }

  function startCreate() { setSelected(null); setMode("create"); setDeleteError(null); }
  function startImport() { setSelected(null); setParsedContracts([]); setParseError(null); setMode("import"); }
  function selectContract(c: Entity) { setSelected(c); setMode("view"); setDeleteError(null); }

  async function handleSave(data: ContractFormData, milestones?: MilestoneSavePayload): Promise<boolean> {
    setSaveError(null);
    const titleTrimmed = data.title.trim().toLowerCase();
    const duplicate = contracts.find(
      (c) => str(c, "title").trim().toLowerCase() === titleTrimmed && c.id !== selected?.id,
    );
    if (duplicate) { setSaveError("A contract with this title already exists."); return false; }
    const contract: Record<string, unknown> = {
      title: data.title,
      client_id: data.clientId,
      type: data.type,
      fixed_price: data.type === "fixed_price" ? (data.fixedPrice || null) : null,
      rate: data.type === "time_based" ? (data.rate || null) : null,
      currency: data.currency,
      unit: data.unit,
      billing_cycle: data.billingCycle,
      volume: data.volume || null,
      VAT_rate: data.vatRate,
      VAT_category: data.vatCategory,
      signature_date: data.signatureDate,
      start_date: data.startDate,
      end_date: data.endDate || null,
      term_of_payment: data.termOfPayment || null,
      units_per_workday: data.unitsPerWorkday,
      bank_account_id: data.bankAccountId || null,
      // Always sent, so clearing the last charge clears it server-side too.
      charges: data.charges.map((c) => ({
        id: c.id,
        description: c.description.trim(),
        amount: parseFloat(c.amount),
        basis: c.basis,
      })),
    };
    if (mode === "edit" && selected) contract.id = selected.id;
    const res = await rpc<Entity>("contracts.save", { contract });
    if (!res.ok) {
      setSaveError(res.error || "Failed to save contract.");
      return false;
    }

    const contractId = res.data?.id ?? selected?.id;
    const isFixed = data.type === "fixed_price";
    if (isFixed && milestones?.open && contractId != null) {
      const msRes = await rpc("contracts.save_milestones", {
        contract_id: contractId,
        milestones: milestones.milestones.map((m, i) => ({
          id: m.id,
          title: m.title,
          percentage: parseFloat(m.percentage) || null,
          position: i,
        })),
      });
      if (!msRes.ok) {
        setSaveError(msRes.error || "Contract saved, but payment schedule could not be saved.");
        return false;
      }
    }

    setMode("view");
    await load();
    return true;
  }

  async function handleDelete(id: number) {
    setDeleteError(null);
    const res = await rpc("contracts.delete", { id });
    if (res.ok) { setSelected(null); setMode("view"); await load(); }
    else if (res.error) setDeleteError(res.error);
  }

  async function handleToggle(id: number) {
    await rpc("contracts.toggle_completed", { id });
    await load();
  }

  async function handleFileImport(file: File) {
    setParsing(true); setParseError(null); setParsedContracts([]);
    try {
      const buffer = await file.arrayBuffer();
      const base64 = btoa(new Uint8Array(buffer).reduce((d, b) => d + String.fromCharCode(b), ""));
      const res = await rpc<ParsedContract[]>("llm.parse_document", {
        file_base64: base64, file_name: file.name, entity_type: "contract",
      });
      if (res.ok && res.data) {
        setParsedContracts(res.data);
        if (res.data.length === 0) setParseError("No contracts found in the document.");
      } else setParseError(res.error || "Failed to parse document.");
    } catch (err) { setParseError(String(err)); }
    setParsing(false);
  }

  async function acceptContract(parsed: ParsedContract) {
    const contract: Record<string, unknown> = { ...parsed };
    delete contract.client_name_hint;
    if (parsed.selectedClientId) contract.client_id = parsed.selectedClientId;
    const res = await rpc("contracts.save", { contract });
    if (res.ok) { setParsedContracts((p) => p.filter((c) => c !== parsed)); await load(); }
  }

  async function acceptAll() {
    for (const p of parsedContracts) {
      const contract: Record<string, unknown> = { ...p };
      delete contract.client_name_hint;
      if (p.selectedClientId) contract.client_id = p.selectedClientId;
      await rpc("contracts.save", { contract });
    }
    setParsedContracts([]); await load(); setMode("view");
  }

  function discardContract(parsed: ParsedContract) {
    setParsedContracts((p) => p.filter((c) => c !== parsed));
  }

  function updateParsedContract(index: number, updated: ParsedContract) {
    setParsedContracts((p) => p.map((c, i) => i === index ? updated : c));
  }

  const sorted = [...contracts].sort((a, b) => {
    const aDate = str(a, "start_date") || str(a, "signature_date") || "";
    const bDate = str(b, "start_date") || str(b, "signature_date") || "";
    return bDate.localeCompare(aDate);
  });

  const filtered = sorted.filter((c) => {
    const status = contractStatus(c);
    if (statusFilter !== "All" && status !== statusFilter) return false;
    if (!search) return true;
    const q = search.toLowerCase();
    const title = str(c, "title").toLowerCase();
    const cl = subEntity(c, "client");
    const clientName = cl ? str(cl, "name").toLowerCase() : "";
    return title.includes(q) || clientName.includes(q);
  });

  if (loading && contracts.length === 0)
    return <div className="flex items-center justify-center h-full text-secondary">Loading contracts…</div>;

  return (
    <div className="flex flex-col h-full">
      <Toolbar title="Contracts"
        actions={<>
          <ToolbarButtonPrimary icon={<Plus size={13} />} label="New" onClick={startCreate} />
          <ToolbarButtonSecondary icon={<FileUp size={13} />} label="Import" onClick={startImport} />
        </>}
        center={<ToolbarFilterGroup options={["All", "Active", "Upcoming", "Completed"] as const} value={statusFilter} onChange={setStatusFilter} />}
        search={{ value: search, onChange: setSearch }}
      />

      {contracts.length === 0 && mode === "view" ? (
        <EmptyStateIntro icon={FileText} description="A contract defines the business terms for working with a client — rate, billing cycle, and duration of the agreement." />
      ) : (
      <ListDetailLayout
        footer={<>{filtered.length} contract{filtered.length !== 1 ? "s" : ""}</>}
        list={filtered.length === 0
          ? <div className="p-4 text-sm text-center text-tertiary">No matches.</div>
          : filtered.map((c) => (
            <ContractRow key={c.id} contract={c}
              isSelected={selected?.id === c.id && mode !== "create" && mode !== "import"}
              onSelect={() => selectContract(c)} />
          ))
        }
        detail={mode === "import" ? (
            <ContractImportPanel
              parsing={parsing} parseError={parseError} parsedContracts={parsedContracts}
              clients={clients}
              onFileSelected={handleFileImport} onAccept={acceptContract} onAcceptAll={acceptAll}
              onDiscard={discardContract} onUpdate={updateParsedContract} onClose={() => setMode("view")}
            />
          ) : mode === "create" ? (
            <ContractForm contract={null} clients={clients} defaultCurrency={defaultCurrency} currencies={currencies} bankAccounts={bankAccounts} onSave={handleSave} onCancel={() => setMode("view")} error={saveError} />
          ) : mode === "edit" && selected ? (
            <ContractForm contract={selected} clients={clients} defaultCurrency={defaultCurrency} currencies={currencies} bankAccounts={bankAccounts} onSave={handleSave} onCancel={() => setMode("view")} error={saveError} />
          ) : selected ? (
            <ContractDetail contract={selected}
              onEdit={() => setMode("edit")}
              onDelete={() => handleDelete(selected.id)}
              onToggle={() => handleToggle(selected.id)}
              deleteError={deleteError} />
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-tertiary">
              <FileText size={36} strokeWidth={1.2} />
              <span className="text-sm">Select a contract</span>
            </div>
          )
        }
      />
      )}
    </div>
  );
}

/* ---------- List row ---------- */

function ContractRow({ contract, isSelected, onSelect }: {
  contract: Entity; isSelected: boolean; onSelect: () => void;
}) {
  const title = str(contract, "title");
  const cl = subEntity(contract, "client");
  const clientName = cl ? str(cl, "name") : "";
  const fixedPrice = num(contract, "fixed_price");
  const rate = num(contract, "rate");
  const currency = str(contract, "currency") || "EUR";
  const status = contractStatus(contract);
  const priceLabel = fixedPrice > 0
    ? `${fixedPrice} ${currency}`
    : rate > 0 ? `${rate} ${currency}/${str(contract, "unit_abbrev") || "h"}` : "";

  return (
    <button onClick={onSelect}
      className={`w-full text-left ${LIST_ROW_PADDING} border-b border-border-subtle transition-colors flex items-center gap-3
        ${isSelected ? "bg-bg-selected" : "hover:bg-bg-hover"}`}>
      <div className="w-9 h-9 rounded-full bg-bg-card flex items-center justify-center text-sm font-semibold text-secondary shrink-0">
        <FileSignature size={16} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <div className="text-sm font-medium truncate">{title}</div>
          <StatusBadge status={status} />
        </div>
        <div className="flex items-center gap-2 text-xs text-tertiary mt-0.5">
          {clientName && <span>{clientName}</span>}
          {clientName && priceLabel && <span>·</span>}
          {priceLabel && <span>{priceLabel}</span>}
        </div>
      </div>
    </button>
  );
}

/* ---------- Detail ---------- */

function ContractDetail({ contract, onEdit, onDelete, onToggle, deleteError }: {
  contract: Entity; onEdit: () => void; onDelete: () => void; onToggle: () => void; deleteError: string | null;
}) {
  const { navigate } = useNavigation();
  const title = str(contract, "title");
  const cl = subEntity(contract, "client");
  const clientName = cl ? str(cl, "name") : "—";
  const status = contractStatus(contract);
  const fixedPrice = num(contract, "fixed_price");
  const rate = num(contract, "rate");
  const currency = str(contract, "currency") || "EUR";
  const unit = str(contract, "unit") || "hour";
  const isFixed = fixedPrice > 0;
  const projects = entityList(contract, "projects");
  const invoices = entityList(contract, "invoices");
  const charges = entityList(contract, "charges");

  const startDate = str(contract, "start_date");
  const endDate = str(contract, "end_date");
  const durationLabel = endDate
    ? `${formatDate(startDate)} – ${formatDate(endDate)}`
    : `From ${formatDate(startDate)}`;

  return (
    <div className="p-6 max-w-2xl space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-semibold">{title}</h1>
          <div className="text-sm text-secondary mt-0.5">{clientName}</div>
        </div>
        <StatusBadge status={status} />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button onClick={onToggle}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs text-secondary hover:text-primary border border-border-subtle transition-colors">
          <CheckCircle2 size={13} /> {bool(contract, "is_completed") ? "Reopen" : "Mark Complete"}
        </button>
        <button onClick={onEdit}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-bg-card text-secondary hover:text-primary border border-border-subtle transition-colors">
          Edit
        </button>
        <button onClick={onDelete}
          className="p-1.5 rounded-md text-secondary hover:text-red-400 border border-border-subtle transition-colors">
          <Trash2 size={14} />
        </button>
      </div>

      {deleteError && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">{deleteError}</div>
      )}

      {/* Terms */}
      <DetailSection label="Terms">
        <div className="grid grid-cols-3 gap-x-6 gap-y-3">
          {isFixed && <TermItem label="Fixed Price" value={`${fixedPrice} ${currency}`} />}
          {rate > 0 && <TermItem label="Rate" value={`${rate} ${currency}`} sub={`per ${unit}`} />}
          {!isFixed && <TermItem label="Volume" value={str(contract, "volume") || "—"} sub={str(contract, "volume") ? `${unit}s` : ""} />}
          {!isFixed && <TermItem label="Billing" value={str(contract, "billing_cycle") || "—"} />}
          <TermItem
            label="VAT"
            value={taxTreatment(
              taxCategory(str(contract, "VAT_category")),
              num(contract, "VAT_rate"),
            )}
          />
          <TermItem label="Payment" value={str(contract, "term_of_payment") ? `${str(contract, "term_of_payment")} days` : "—"} />
          {!isFixed && <TermItem label="Workday" value={`${str(contract, "units_per_workday") || "8"} ${unit}s`} />}
        </div>
      </DetailSection>

      {/* Additional charges — only shown when this contract actually uses them */}
      {charges.length > 0 && (
        <DetailSection label="Additional Charges">
          <div className="space-y-2">
            {charges.map((charge) => (
              <div key={charge.id} className="flex items-center justify-between gap-3 px-3 py-2 rounded-lg bg-bg-card border border-border-subtle">
                <div className="min-w-0">
                  <div className="text-sm truncate">{str(charge, "description")}</div>
                  <div className="text-xs text-tertiary mt-0.5">
                    {CHARGE_BASIS_LABELS[(str(charge, "basis") as ChargeBasis)] || str(charge, "basis")}
                  </div>
                </div>
                <div className="text-sm font-medium tabular-nums shrink-0">
                  {num(charge, "amount")} {currency}
                </div>
              </div>
            ))}
          </div>
        </DetailSection>
      )}

      {/* Period */}
      <DetailSection label="Period">
        <div className="flex items-center gap-3">
          <Calendar size={14} className="text-tertiary" />
          <div>
            <div className="text-sm">{durationLabel}</div>
            {str(contract, "signature_date") && (
              <div className="text-xs text-tertiary mt-0.5">Signed {formatDate(str(contract, "signature_date"))}</div>
            )}
          </div>
        </div>
      </DetailSection>

      {/* Payment Schedule (only shown if milestones exist) */}
      {(() => {
        const ms = entityList(contract, "payment_milestones");
        if (ms.length === 0) return null;
        return (
          <DetailSection label="Payment Schedule">
            <div className="space-y-1.5">
              {ms.map((m) => (
                <div key={m.id} className="flex items-center justify-between px-3 py-2 rounded-md bg-bg-card border border-border-subtle">
                  <div className="flex items-center gap-2">
                    <Milestone size={12} className="text-tertiary" />
                    <span className="text-sm">{str(m, "title") || "Untitled"}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-secondary tabular-nums">{num(m, "percentage")}%</span>
                    {bool(m, "invoiced")
                      ? <span className="text-[10px] text-green-500 font-medium px-1.5 py-0.5 rounded bg-green-500/10">Invoiced</span>
                      : <span className="text-[10px] text-tertiary font-medium px-1.5 py-0.5 rounded bg-bg-hover">Open</span>}
                  </div>
                </div>
              ))}
            </div>
          </DetailSection>
        );
      })()}

      {/* Related */}
      <DetailSection label="Related">
        <div className="flex items-center gap-3">
          <RelatedCard icon={<FolderKanban size={16} />} count={projects.length} label="Projects"
            onClick={projects.length > 0 ? () => navigate("projects", { contractId: contract.id }) : undefined} />
          <RelatedCard icon={<ReceiptText size={16} />} count={invoices.length} label="Invoices"
            onClick={invoices.length > 0 ? () => navigate("invoicing", { contractId: contract.id }) : undefined} />
        </div>
      </DetailSection>
    </div>
  );
}

function DetailSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-wider text-tertiary mb-3">{label}</div>
      {children}
    </div>
  );
}

function TermItem({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <div className="text-xs text-tertiary">{label}</div>
      <div className="text-sm font-medium mt-0.5">
        {value}
        {sub && <span className="text-tertiary font-normal ml-1">{sub}</span>}
      </div>
    </div>
  );
}

function RelatedCard({ icon, count, label, onClick }: { icon: React.ReactNode; count: number; label: string; onClick?: () => void }) {
  const interactive = !!onClick;
  const Tag = interactive ? "button" : "div";
  return (
    <Tag onClick={onClick}
      className={`flex items-center gap-3 px-4 py-3 rounded-lg bg-bg-card border border-border-subtle min-w-[120px] transition-colors
        ${interactive ? "hover:border-accent hover:bg-bg-hover cursor-pointer group" : ""}`}>
      <span className={`text-tertiary ${interactive ? "group-hover:text-primary" : ""}`}>{icon}</span>
      <div className="flex-1">
        <div className="text-lg font-semibold leading-none">{count}</div>
        <div className="text-xs text-tertiary">{label}</div>
      </div>
      {interactive && <ArrowRight size={14} className="text-tertiary group-hover:text-primary" />}
    </Tag>
  );
}

/* ---------- Form ---------- */

interface MilestoneRow {
  id?: number;
  title: string;
  percentage: string;
  invoiced?: boolean;
}

interface MilestoneSavePayload {
  open: boolean;
  milestones: MilestoneRow[];
}

interface ContractFormData {
  title: string;
  clientId: number | null;
  type: PricingMode;
  fixedPrice: number | null;
  rate: number | null;
  currency: string;
  unit: string;
  billingCycle: string;
  volume: number | null;
  vatRate: number;
  vatCategory: TaxCategory;
  signatureDate: string;
  startDate: string;
  endDate: string;
  termOfPayment: number | null;
  unitsPerWorkday: number;
  bankAccountId: number | "";
  charges: ChargeRow[];
}

type PricingMode = "time_based" | "fixed_price";

type ChargeBasis = "per_unit" | "per_invoice" | "once";

const CHARGE_BASIS_LABELS: Record<ChargeBasis, string> = {
  per_unit: "Per billed unit",
  per_invoice: "On every invoice",
  once: "Once (first invoice only)",
};

interface ChargeRow {
  id: number | null;
  description: string;
  amount: string;
  basis: ChargeBasis;
}

function chargeRowsFrom(contract?: Entity | null): ChargeRow[] {
  if (!contract) return [];
  return entityList(contract, "charges").map((c) => ({
    id: c.id,
    description: str(c, "description"),
    amount: str(c, "amount"),
    basis: (str(c, "basis") as ChargeBasis) || "per_unit",
  }));
}

function isBlankCharge(row: ChargeRow): boolean {
  return !row.description.trim() && !row.amount.trim();
}

function isBlankMilestone(row: MilestoneRow): boolean {
  return !row.title.trim() && !row.percentage.trim();
}

function ContractForm({ contract, clients, defaultCurrency, currencies, bankAccounts, onSave, onCancel, error }: {
  contract: Entity | null;
  clients: Record<string, Entity>;
  defaultCurrency: string;
  currencies: string[];
  bankAccounts: Entity[];
  onSave: (data: ContractFormData, milestones?: MilestoneSavePayload) => Promise<boolean>;
  onCancel: () => void;
  error?: string | null;
}) {
  const cl = contract ? subEntity(contract, "client") : null;
  const initFixed = contract ? (num(contract, "fixed_price") || null) : null;
  const initType: PricingMode = contract
    ? ((str(contract, "type") as PricingMode) || (initFixed ? "fixed_price" : "time_based"))
    : "time_based";
  const [pricingMode, setPricingMode] = useState<PricingMode>(initType);
  const contractBankId: number | "" = contract ? (subEntity(contract, "bank_account")?.id ?? "") : "";
  const [form, setForm] = useState<ContractFormData>(() => {
    if (contract) return {
      title: str(contract, "title"),
      clientId: cl?.id ?? null,
      type: initType,
      fixedPrice: initFixed,
      rate: num(contract, "rate") || null,
      currency: str(contract, "currency") || defaultCurrency,
      unit: str(contract, "unit") || "hour",
      billingCycle: str(contract, "billing_cycle") || "monthly",
      volume: num(contract, "volume") || null,
      vatRate: (() => {
        const v = num(contract, "VAT_rate");
        if (!v) return 0;
        return v > 1 ? v / 100 : v;
      })(),
      vatCategory: taxCategory(str(contract, "VAT_category")),
      signatureDate: str(contract, "signature_date"),
      startDate: str(contract, "start_date"),
      endDate: str(contract, "end_date"),
      termOfPayment: num(contract, "term_of_payment") || null,
      unitsPerWorkday: num(contract, "units_per_workday") || 8,
      bankAccountId: contractBankId,
      charges: chargeRowsFrom(contract),
    };
    return {
      title: "", clientId: null, type: "time_based", fixedPrice: null, rate: null, currency: defaultCurrency,
      unit: "hour", billingCycle: "monthly", volume: null, vatRate: 0.19, vatCategory: "S",
      signatureDate: "", startDate: "", endDate: "", termOfPayment: 31, unitsPerWorkday: 8,
      bankAccountId: "",
      charges: [],
    };
  });
  const { isRequired } = useFieldRequirements("contracts");
  const [saving, setSaving] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  // Additional charges are an advanced option: kept out of sight unless this
  // contract already uses them or the user asks for them.
  const [showCharges, setShowCharges] = useState(chargeRowsFrom(contract).length > 0);
  const isNew = !contract;
  const isFixed = pricingMode === "fixed_price";

  // Whether this contract carries a payment schedule at all — distinct from
  // whether the milestone list is collapsed, which is purely visual.
  const [scheduleEnabled, setScheduleEnabled] = useState(() => {
    if (!contract) return false;
    const ms = entityList(contract, "payment_milestones");
    return ms.length > 0;
  });
  const [scheduleCollapsed, setScheduleCollapsed] = useState(false);
  const [milestones, setMilestones] = useState<MilestoneRow[]>(() => {
    if (!contract) return [];
    return entityList(contract, "payment_milestones").map((m) => ({
      id: m.id,
      title: str(m, "title"),
      percentage: String(num(m, "percentage") || ""),
      invoiced: bool(m, "invoiced"),
    }));
  });

  const clientList = Object.values(clients);
  // Keep an existing contract's currency selectable even if it left the list.
  const currencyOptions = currencies.includes(form.currency) ? currencies : [form.currency, ...currencies];

  function update<K extends keyof ContractFormData>(field: K, value: ContractFormData[K]) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  // Only standard-rated supplies carry a VAT rate; the backend rejects any
  // other category with a non-zero rate.
  function setVatCategory(category: TaxCategory) {
    setForm((prev) => ({ ...prev, vatCategory: category, vatRate: category === "S" ? prev.vatRate : 0 }));
    setValidationError(null);
  }

  function switchPricingMode(mode: PricingMode) {
    setPricingMode(mode);
    setValidationError(null);
    if (mode === "fixed_price") {
      // A fixed-price contract has no billed units for a per-unit charge to
      // scale by, so those rows move to the nearest meaningful basis.
      setForm((prev) => ({
        ...prev,
        type: mode,
        rate: null,
        charges: prev.charges.map((c) => (c.basis === "per_unit" ? { ...c, basis: "per_invoice" } : c)),
      }));
    } else {
      setForm((prev) => ({ ...prev, type: mode, fixedPrice: null }));
    }
  }

  function updateCharge(idx: number, patch: Partial<ChargeRow>) {
    setForm((prev) => ({
      ...prev,
      charges: prev.charges.map((c, i) => (i === idx ? { ...c, ...patch } : c)),
    }));
    setValidationError(null);
  }

  function addCharge() {
    setForm((prev) => ({
      ...prev,
      charges: [...prev.charges, { id: null, description: "", amount: "", basis: isFixed ? "per_invoice" : "per_unit" }],
    }));
  }

  function removeCharge(idx: number) {
    setForm((prev) => ({ ...prev, charges: prev.charges.filter((_, i) => i !== idx) }));
    setValidationError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim()) { setValidationError("Title is required"); return; }
    if (isFixed) {
      if (!form.fixedPrice || form.fixedPrice <= 0) { setValidationError("Fixed price is required"); return; }
    } else {
      if (!form.rate || form.rate <= 0) { setValidationError("Rate is required"); return; }
    }
    if (!form.startDate) { setValidationError("Start date is required"); return; }
    if (form.endDate && form.startDate && form.endDate < form.startDate) {
      setValidationError("End date must be on or after start date"); return;
    }
    // An untouched row the user added and ignored is dropped; a half-filled
    // one is a mistake worth reporting rather than silently discarding.
    const charges = form.charges.filter((c) => !isBlankCharge(c));
    if (charges.some((c) => !c.description.trim() || !(parseFloat(c.amount) > 0))) {
      setValidationError("Give every additional charge a description and an amount greater than zero");
      return;
    }
    const schedule = milestones.filter((m) => !isBlankMilestone(m));
    if (isFixed && scheduleEnabled && schedule.length > 0) {
      if (schedule.some((m) => !m.title.trim())) {
        setValidationError("Give every payment milestone a title");
        return;
      }
      const total = schedule.reduce((s, m) => s + (parseFloat(m.percentage) || 0), 0);
      if (Math.abs(total - 100) > 0.01) {
        setValidationError(`Milestone percentages must sum to 100% (currently ${total.toFixed(1)}%)`);
        return;
      }
    }
    setSaving(true);
    const ok = await onSave(
      { ...form, charges },
      isFixed && scheduleEnabled ? { open: true, milestones: schedule } : undefined,
    );
    setSaving(false);
    if (!ok) return;
  }

  const inputCls = "w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors";

  return (
    <form onSubmit={handleSubmit} className="p-5 space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{isNew ? "New Contract" : "Edit Contract"}</h2>
        <div className="flex items-center gap-2">
          <button type="button" onClick={onCancel}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
            <X size={14} /> Cancel
          </button>
          <button type="submit" disabled={saving}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium text-primary hover:bg-bg-hover transition-colors disabled:opacity-40">
            <Save size={14} /> {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>

      <p className="text-xs text-muted"><span className="text-accent">*</span> Required</p>

      {(validationError || error) && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">{validationError || error}</div>
      )}

      <Section title="Basic">
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="block text-xs text-tertiary mb-1">Title{isRequired("title") && <span className="text-accent ml-0.5">*</span>}</label>
            <input type="text" value={form.title} onChange={(e) => update("title", e.target.value)} autoFocus className={inputCls} />
          </div>
          <div>
            <label className="block text-xs text-tertiary mb-1">Client</label>
            <select value={form.clientId ?? ""} onChange={(e) => update("clientId", e.target.value ? Number(e.target.value) : null)} className={inputCls}>
              <option value="">-- Select --</option>
              {clientList.map((c) => <option key={c.id} value={c.id}>{str(c, "name")}</option>)}
            </select>
          </div>
        </div>
      </Section>

      <Section title="Pricing">
        <div className="flex rounded-md border border-border-subtle overflow-hidden mb-4 w-fit">
          {(["time_based", "fixed_price"] as const).map((mode) => (
            <button key={mode} type="button" onClick={() => switchPricingMode(mode)}
              className={`px-4 py-1.5 text-xs font-medium transition-colors ${pricingMode === mode
                ? "bg-accent text-white" : "bg-bg-card text-secondary hover:text-primary hover:bg-bg-hover"}`}>
              {mode === "time_based" ? "Time-Based" : "Fixed Price"}
            </button>
          ))}
        </div>

        {isFixed ? (
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-tertiary mb-1">Fixed Price <span className="text-accent">*</span></label>
              <input type="number" step="0.01" value={form.fixedPrice ?? ""} onChange={(e) => update("fixedPrice", e.target.value ? parseFloat(e.target.value) : null)} className={inputCls} />
            </div>
            <div>
              <label className="block text-xs text-tertiary mb-1">Currency</label>
              <select value={form.currency} onChange={(e) => update("currency", e.target.value)} className={inputCls}>
                {currencyOptions.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-tertiary mb-1">Tax Category</label>
              <select value={form.vatCategory} onChange={(e) => setVatCategory(e.target.value as TaxCategory)} className={inputCls}>
                {(Object.keys(TAX_CATEGORY_LABELS) as TaxCategory[]).map((c) => (
                  <option key={c} value={c}>{TAX_CATEGORY_LABELS[c]}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-tertiary mb-1">VAT Rate (%)</label>
              <input type="number" step="0.1" min="0" max="100"
                disabled={form.vatCategory !== "S"}
                value={Math.round(form.vatRate * 10000) / 100}
                onChange={(e) => { const pct = parseFloat(e.target.value); update("vatRate", Number.isFinite(pct) ? pct / 100 : 0); }}
                className={`${inputCls} disabled:opacity-50 disabled:cursor-not-allowed`} />
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-tertiary mb-1">Rate <span className="text-accent">*</span></label>
              <input type="number" step="0.01" value={form.rate ?? ""} onChange={(e) => update("rate", e.target.value ? parseFloat(e.target.value) : null)} className={inputCls} />
            </div>
            <div>
              <label className="block text-xs text-tertiary mb-1">Currency</label>
              <select value={form.currency} onChange={(e) => update("currency", e.target.value)} className={inputCls}>
                {currencyOptions.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-tertiary mb-1">Unit</label>
              <select value={form.unit} onChange={(e) => update("unit", e.target.value)} className={inputCls}>
                <option value="hour">Hour</option>
                <option value="day">Day</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-tertiary mb-1">Tax Category</label>
              <select value={form.vatCategory} onChange={(e) => setVatCategory(e.target.value as TaxCategory)} className={inputCls}>
                {(Object.keys(TAX_CATEGORY_LABELS) as TaxCategory[]).map((c) => (
                  <option key={c} value={c}>{TAX_CATEGORY_LABELS[c]}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-tertiary mb-1">VAT Rate (%)</label>
              <input type="number" step="0.1" min="0" max="100"
                disabled={form.vatCategory !== "S"}
                value={Math.round(form.vatRate * 10000) / 100}
                onChange={(e) => { const pct = parseFloat(e.target.value); update("vatRate", Number.isFinite(pct) ? pct / 100 : 0); }}
                className={`${inputCls} disabled:opacity-50 disabled:cursor-not-allowed`} />
            </div>
            <div>
              <label className="block text-xs text-tertiary mb-1">Billing Cycle</label>
              <select value={form.billingCycle} onChange={(e) => update("billingCycle", e.target.value)} className={inputCls}>
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="yearly">Yearly</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-tertiary mb-1">Volume</label>
              <input type="number" value={form.volume ?? ""} onChange={(e) => update("volume", e.target.value ? parseInt(e.target.value) : null)} className={inputCls} />
            </div>
          </div>
        )}

        <ChargesEditor
          charges={form.charges}
          expanded={showCharges}
          onToggle={() => setShowCharges((v) => !v)}
          isFixed={isFixed}
          currency={form.currency}
          unitLabel={form.unit}
          onAdd={addCharge}
          onUpdate={updateCharge}
          onRemove={removeCharge}
          inputCls={inputCls}
        />
      </Section>

      <Section title="Dates">
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-xs text-tertiary mb-1">Signature Date <span className="text-muted">(optional)</span></label>
            <input type="date" value={form.signatureDate} onChange={(e) => update("signatureDate", e.target.value)} className={inputCls} />
          </div>
          <div>
            <label className="block text-xs text-tertiary mb-1">Start Date{isRequired("start_date") && <span className="text-accent ml-0.5">*</span>}</label>
            <input type="date" value={form.startDate} onChange={(e) => update("startDate", e.target.value)} className={inputCls} />
          </div>
          <div>
            <label className="block text-xs text-tertiary mb-1">End Date <span className="text-muted">(optional)</span></label>
            <input type="date" value={form.endDate} onChange={(e) => update("endDate", e.target.value)} className={inputCls} />
          </div>
        </div>
      </Section>

      <Section title="Other">
        <div className={`grid gap-3 ${isFixed ? "grid-cols-1 max-w-[50%]" : "grid-cols-2"}`}>
          <div>
            <label className="block text-xs text-tertiary mb-1">Term of Payment (days)</label>
            <input type="number" value={form.termOfPayment ?? ""} onChange={(e) => update("termOfPayment", e.target.value ? parseInt(e.target.value) : null)} className={inputCls} />
          </div>
          {!isFixed && (
            <div>
              <label className="block text-xs text-tertiary mb-1">Units per Workday</label>
              <input type="number" value={form.unitsPerWorkday} onChange={(e) => update("unitsPerWorkday", parseInt(e.target.value) || 8)} className={inputCls} />
            </div>
          )}
        </div>
        <div className="mt-3">
          <label className="block text-xs text-tertiary mb-1">Invoicing Bank Account</label>
          <select
            value={form.bankAccountId}
            onChange={(e) => update("bankAccountId", e.target.value ? parseInt(e.target.value) : "")}
            className={inputCls}
          >
            <option value="">Use my default account</option>
            {bankAccounts.map((acc) => (
              <option key={String(acc.id)} value={String(acc.id)}>
                {str(acc, "name")} — {str(acc, "IBAN")}{bool(acc, "is_default") ? " (default)" : ""}
              </option>
            ))}
          </select>
          <p className="text-xs text-muted mt-1">
            Invoices for this contract pay into this account. Leave unset to pay into the default account.
          </p>
        </div>
      </Section>

      {isFixed && (
        <Section title="Payment Schedule">
          {!scheduleEnabled ? (
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-4 py-3 rounded-lg bg-bg-card border border-dashed border-border-subtle">
              <p className="text-xs text-secondary leading-relaxed">
                Split a fixed-price contract into instalments for deposit and final invoices.
              </p>
              <button
                type="button"
                onClick={() => {
                  setScheduleEnabled(true);
                  setScheduleCollapsed(false);
                  if (milestones.length === 0) {
                    setMilestones([
                      { title: "", percentage: "50" },
                      { title: "", percentage: "50" },
                    ]);
                  }
                }}
                className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-bg-content text-primary border border-border-subtle hover:bg-bg-hover transition-colors shrink-0">
                <Plus size={14} /> Add payment schedule
              </button>
            </div>
          ) : (
            <div>
              <button type="button" onClick={() => setScheduleCollapsed((c) => !c)}
                className="flex items-center gap-1.5 text-xs text-tertiary hover:text-secondary mb-3 transition-colors">
                {scheduleCollapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
                {scheduleCollapsed
                  ? `${milestones.length} milestone${milestones.length === 1 ? "" : "s"}`
                  : "Collapse"}
              </button>
              {!scheduleCollapsed && (
                <>
                  <div className="space-y-2">
                    {milestones.map((m, idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <input type="text" placeholder="Milestone title" value={m.title}
                          onChange={(e) => setMilestones((prev) => prev.map((ms, i) => i === idx ? { ...ms, title: e.target.value } : ms))}
                          disabled={m.invoiced}
                          className={`flex-1 ${inputCls} ${m.invoiced ? "opacity-50" : ""}`} />
                        <div className="flex items-center gap-1">
                          <input type="number" min="0" max="100" step="0.1" placeholder="%" value={m.percentage}
                            onChange={(e) => setMilestones((prev) => prev.map((ms, i) => i === idx ? { ...ms, percentage: e.target.value } : ms))}
                            disabled={m.invoiced}
                            className={`w-20 ${inputCls} ${m.invoiced ? "opacity-50" : ""}`} />
                          <span className="text-xs text-muted">%</span>
                        </div>
                        {m.invoiced ? (
                          <span className="text-[10px] text-green-500 font-medium px-1.5 py-0.5 rounded bg-green-500/10">Invoiced</span>
                        ) : (
                          <button type="button" onClick={() => setMilestones((prev) => prev.filter((_, i) => i !== idx))}
                            disabled={milestones.length <= 1}
                            className="p-1 rounded text-muted hover:text-red-400 disabled:opacity-30 transition-colors">
                            <X size={14} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={() => setMilestones((prev) => [...prev, { title: "", percentage: "" }])}
                    className="mt-3 flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-bg-content text-primary border border-border-subtle hover:bg-bg-hover transition-colors">
                    <Plus size={14} /> Add milestone
                  </button>
                  {milestones.length > 0 && (() => {
                    const total = milestones.reduce((s, m) => s + (parseFloat(m.percentage) || 0), 0);
                    const ok = Math.abs(total - 100) < 0.01;
                    return (
                      <div className={`mt-2 text-xs ${ok ? "text-green-500" : "text-amber-400"}`}>
                        Total: {total.toFixed(1)}%{!ok && " (must be 100%)"}
                      </div>
                    );
                  })()}
                </>
              )}
            </div>
          )}
        </Section>
      )}
    </form>
  );
}

/* ---------- Additional charges ---------- */

function ChargesEditor({ charges, expanded, onToggle, isFixed, currency, unitLabel, onAdd, onUpdate, onRemove, inputCls }: {
  charges: ChargeRow[];
  expanded: boolean;
  onToggle: () => void;
  isFixed: boolean;
  currency: string;
  unitLabel: string;
  onAdd: () => void;
  onUpdate: (idx: number, patch: Partial<ChargeRow>) => void;
  onRemove: (idx: number) => void;
  inputCls: string;
}) {
  // Collapsing while rows exist would hide data the user cannot see is still
  // there, so the toggle only closes an empty editor.
  const canCollapse = charges.length === 0;
  const bases: ChargeBasis[] = isFixed ? ["per_invoice", "once"] : ["per_unit", "per_invoice", "once"];

  return (
    <div className="mt-4 pt-4 border-t border-border-subtle">
      <div className="flex items-center gap-2">
        <button type="button" onClick={expanded && !canCollapse ? undefined : onToggle}
          aria-expanded={expanded}
          className={`flex items-center gap-1.5 text-xs font-medium transition-colors
            ${expanded && !canCollapse ? "text-secondary cursor-default" : "text-tertiary hover:text-primary"}`}>
          <ChevronRight size={13} className={`transition-transform ${expanded ? "rotate-90" : ""}`} />
          Additional charges <span className="text-muted font-normal">(optional)</span>
        </button>
        <InfoHint
          label="additional charges"
          text="Extra charges billed alongside the rate, such as a daily expense allowance that accompanies a day rate, or a one-time setup fee. Each one becomes its own line on the invoice."
        />
      </div>

      {expanded && (
        <div className="mt-3 space-y-2">
          {charges.map((charge, idx) => (
            <div key={idx} className="flex gap-1.5 items-start p-2 rounded-lg bg-bg-card border border-border-subtle">
              <div className="flex-1 min-w-0 space-y-1.5">
                <input type="text" placeholder="Description" value={charge.description}
                  onChange={(e) => onUpdate(idx, { description: e.target.value })}
                  className="w-full px-2 py-1 rounded bg-bg-content border border-border-subtle text-xs text-primary placeholder:text-muted" />
                <div className="flex gap-1.5">
                  <div className="flex items-center gap-1 w-32">
                    <input type="number" min="0" step="0.01" placeholder="Amount" value={charge.amount}
                      onChange={(e) => onUpdate(idx, { amount: e.target.value })}
                      className="w-full px-2 py-1 rounded bg-bg-content border border-border-subtle text-xs text-primary placeholder:text-muted tabular-nums" />
                    <span className="text-[10px] text-muted shrink-0">{currency}</span>
                  </div>
                  <select value={charge.basis} onChange={(e) => onUpdate(idx, { basis: e.target.value as ChargeBasis })}
                    className="flex-1 min-w-0 px-1.5 py-1 rounded bg-bg-content border border-border-subtle text-xs text-primary">
                    {bases.map((b) => <option key={b} value={b}>{CHARGE_BASIS_LABELS[b]}</option>)}
                  </select>
                </div>
                <p className="text-[10px] text-muted">
                  {charge.basis === "per_unit"
                    ? `Billed once per ${unitLabel} worked, matching the quantity of the ${unitLabel} rate.`
                    : charge.basis === "per_invoice"
                      ? "Billed once on every invoice from this contract."
                      : "Billed a single time, on the first invoice from this contract."}
                </p>
              </div>
              <button type="button" onClick={() => onRemove(idx)}
                className="mt-1 p-1 rounded text-muted hover:text-red-400 hover:bg-red-400/10 transition-colors"
                title="Remove charge">
                <XCircle size={14} />
              </button>
            </div>
          ))}
          <button type="button" onClick={onAdd}
            className="flex items-center gap-1 text-xs text-accent hover:text-accent/80 transition-colors">
            <Plus size={12} /> Add charge
          </button>
        </div>
      )}
    </div>
  );
}

/* ---------- Shared ---------- */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-wider text-secondary mb-2">{title}</div>
      {children}
    </div>
  );
}

/* ---------- AI Import ---------- */

interface ParsedContract {
  title: string;
  fixed_price: number | null;
  rate: number | null;
  currency: string;
  unit: string;
  billing_cycle: string;
  volume: number | null;
  signature_date: string;
  start_date: string;
  end_date: string;
  VAT_rate: number | null;
  VAT_category: string | null;
  term_of_payment: number | null;
  client_name_hint: string;
  selectedClientId?: number;
}

const ACCEPT_EXTENSIONS = [".pdf", ".txt", ".md", ".text"];

function ContractImportPanel({ parsing, parseError, parsedContracts, clients, onFileSelected, onAccept, onAcceptAll, onDiscard, onUpdate, onClose }: {
  parsing: boolean;
  parseError: string | null;
  parsedContracts: ParsedContract[];
  clients: Record<string, Entity>;
  onFileSelected: (file: File) => void;
  onAccept: (c: ParsedContract) => void;
  onAcceptAll: () => void;
  onDiscard: (c: ParsedContract) => void;
  onUpdate: (index: number, c: ParsedContract) => void;
  onClose: () => void;
}) {
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && ACCEPT_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext))) onFileSelected(file);
  }, [onFileSelected]);

  const clientList = Object.values(clients);

  return (
    <div className="p-5 space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={18} className="text-fuchsia-400" />
          <h2 className="text-lg font-semibold">Import Contracts from Document</h2>
        </div>
        <button onClick={onClose}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
          <X size={14} /> Close
        </button>
      </div>

      {parsedContracts.length === 0 && !parsing && (
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
            <p className="text-xs text-tertiary mt-1">PDF, TXT, or Markdown — AI will extract contracts</p>
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

      {parsedContracts.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-secondary">
              <span className="font-medium text-fuchsia-400">{parsedContracts.length}</span> contract{parsedContracts.length !== 1 ? "s" : ""} found
            </p>
            <button onClick={onAcceptAll}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium text-fuchsia-400 hover:bg-fuchsia-500/10 border border-fuchsia-400/30 transition-colors">
              <CheckCheck size={14} /> Accept All
            </button>
          </div>
          {parsedContracts.map((c, i) => (
            <ParsedContractCard key={i} contract={c} clients={clientList}
              onAccept={() => onAccept(c)}
              onDiscard={() => onDiscard(c)}
              onUpdate={(updated) => onUpdate(i, updated)} />
          ))}
        </div>
      )}
    </div>
  );
}

function ParsedContractCard({ contract, clients, onAccept, onDiscard, onUpdate }: {
  contract: ParsedContract; clients: Entity[];
  onAccept: () => void; onDiscard: () => void; onUpdate: (c: ParsedContract) => void;
}) {
  return (
    <div className="rounded-xl border-2 border-fuchsia-400/40 bg-fuchsia-500/5 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={14} className="text-fuchsia-400" />
          <span className="text-sm font-semibold">{contract.title || "Untitled"}</span>
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

      <div className="grid grid-cols-3 gap-2">
        <AiField label="Title" value={contract.title} onChange={(v) => onUpdate({ ...contract, title: v })} />
        <AiField label="Rate" value={String(contract.rate ?? "")} onChange={(v) => onUpdate({ ...contract, rate: parseFloat(v) || null })} />
        <AiField label="Currency" value={contract.currency} onChange={(v) => onUpdate({ ...contract, currency: v })} />
        <AiField label="Unit" value={contract.unit} onChange={(v) => onUpdate({ ...contract, unit: v })} />
        <AiField label="Start Date" value={contract.start_date} onChange={(v) => onUpdate({ ...contract, start_date: v })} />
        <AiField label="End Date" value={contract.end_date} onChange={(v) => onUpdate({ ...contract, end_date: v })} />
      </div>
      <div>
        <label className="block text-xs text-fuchsia-300/70 mb-0.5">
          Client {contract.client_name_hint && <span className="text-fuchsia-400/60">(hint: {contract.client_name_hint})</span>}
        </label>
        <select value={contract.selectedClientId ?? ""} onChange={(e) => onUpdate({ ...contract, selectedClientId: e.target.value ? Number(e.target.value) : undefined })}
          className="w-full px-2.5 py-1.5 rounded-md text-sm bg-bg-card text-primary border border-fuchsia-400/30 outline-none focus:border-fuchsia-400 transition-colors">
          <option value="">— Select —</option>
          {clients.map((c) => <option key={c.id} value={c.id}>{str(c, "name")}</option>)}
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
