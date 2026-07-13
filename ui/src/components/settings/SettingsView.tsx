/**
 * SettingsView — persistent settings panel.
 *
 * COUPLING: The tabs here (Profile, Invoicing, AI/LLM) are mirrored in
 * the onboarding wizard (OnboardingWizard.tsx). Any field or RPC change
 * here must be reflected in the wizard, and vice-versa. EXCEPTION: the
 * logo upload is intentionally Settings-only (optional branding users can
 * add anytime) and is deliberately omitted from onboarding.
 *
 * @see {@link ../layout/OnboardingWizard.tsx}
 */

import { useEffect, useRef, useState } from "react";
import { Settings, RefreshCw, Save, CheckCircle2, AlertCircle, User, Bot, FileText, RotateCcw, Trash2, AlertTriangle, Monitor, Info, Image as ImageIcon, X, Sun, Moon, Laptop, Palette, Terminal, Clipboard, Check } from "lucide-react";
import { useTheme, type ThemeChoice } from "../../hooks/useTheme";
import { rpc } from "../../api/rpc";
import type { Entity } from "../../api/types";
import { str } from "../../api/entity";
import { useStatusBar, type StatusMessage, type MessageType } from "../shared/status-bar-context";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LLMConfig {
  provider: string;
  base_url: string;
  model: string;
  api_key: string;
  request_timeout: number;
}

const DEFAULT_CONFIG: LLMConfig = {
  provider: "ollama",
  base_url: "http://localhost:11434",
  model: "",
  api_key: "",
  request_timeout: 600,
};

interface ProfileForm {
  name: string;
  subtitle: string;
  email: string;
  phone_number: string;
  website: string;
  logo: string;
  signature: string;
  accent_color: string;
  VAT_number: string;
  tax_number: string;
  operating_country: string;
  street: string;
  number: string;
  postal_code: string;
  city: string;
  country: string;
  bank_name: string;
  bank_IBAN: string;
  bank_BIC: string;
}

const EMPTY_PROFILE: ProfileForm = {
  name: "", subtitle: "", email: "", phone_number: "", website: "", logo: "",
  signature: "",
  accent_color: "#2563eb",
  VAT_number: "", tax_number: "", operating_country: "Germany",
  street: "", number: "", postal_code: "", city: "", country: "Germany",
  bank_name: "", bank_IBAN: "", bank_BIC: "",
};

// Reject logos larger than this before upload; the backend also downscales.
const MAX_LOGO_BYTES = 2 * 1024 * 1024;
const MAX_SIGNATURE_BYTES = 2 * 1024 * 1024;

interface InvoicingPrefs {
  invoice_template: string;
  language: string;
  invoice_number_scheme: string;
  e_invoice_profile: string;
  include_logo: boolean;
  include_due_date: boolean;
  include_signature: boolean;
}

const DEFAULT_INVOICING: InvoicingPrefs = {
  invoice_template: "invoice-modern",
  language: "en",
  invoice_number_scheme: "daily",
  e_invoice_profile: "EN16931",
  include_logo: true,
  include_due_date: true,
  include_signature: true,
};

const SCHEME_EXAMPLES: Record<string, string> = {
  daily: "2025-05-17-01",
  yearly: "2025-01",
  plain: "01",
};

type Tab = "profile" | "branding" | "invoicing" | "llm" | "system" | "debug";

const TABS: { id: Tab; label: string; icon: typeof User }[] = [
  { id: "profile", label: "Profile", icon: User },
  { id: "branding", label: "Branding", icon: Palette },
  { id: "invoicing", label: "Invoicing", icon: FileText },
  { id: "llm", label: "AI / LLM", icon: Bot },
  { id: "system", label: "System", icon: Monitor },
  { id: "debug", label: "Debug", icon: Terminal },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SettingsView() {
  const [tab, setTab] = useState<Tab>("profile");

  const [config, setConfig] = useState<LLMConfig>(DEFAULT_CONFIG);
  const [models, setModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  const [profile, setProfile] = useState<ProfileForm>({ ...EMPTY_PROFILE });
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileStatus, setProfileStatus] = useState<{ type: "success" | "error"; msg: string } | null>(null);
  const [isDemoUser, setIsDemoUser] = useState(false);
  const [resettingDemo, setResettingDemo] = useState(false);
  const [supportedCountries, setSupportedCountries] = useState<string[]>([]);
  const [activeDbFile, setActiveDbFile] = useState<string | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);

  const [invoicing, setInvoicing] = useState<InvoicingPrefs>({ ...DEFAULT_INVOICING });
  const [availableTemplates, setAvailableTemplates] = useState<Record<string, string>>({});
  const [availableLanguages, setAvailableLanguages] = useState<Record<string, string>>({});
  const [availableSchemes, setAvailableSchemes] = useState<Record<string, string>>({});
  const [availableEInvoiceProfiles, setAvailableEInvoiceProfiles] = useState<Record<string, string>>({});
  const [invoicingSaving, setInvoicingSaving] = useState(false);
  const [invoicingStatus, setInvoicingStatus] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  const [savedNotes, setSavedNotes] = useState<Entity[]>([]);
  const [newNoteText, setNewNoteText] = useState("");
  const [addingNote, setAddingNote] = useState(false);
  const invoicingLoadRef = useRef(0);

  useEffect(() => { loadConfig(); loadProfile(); loadSupportedCountries(); loadSavedNotes(); }, []);

  useEffect(() => {
    if (tab === "invoicing") loadInvoicingPrefs();
  }, [tab]);

  // -- LLM config ----------------------------------------------------------

  async function loadConfig() {
    setLoading(true);
    const res = await rpc<LLMConfig>("llm.get_config");
    if (res.ok && res.data) {
      setConfig(res.data);
      if (res.data.base_url) await fetchModels(res.data);
    }
    setLoading(false);
  }

  async function fetchModels(overrides?: Partial<LLMConfig>) {
    const c = { ...config, ...overrides };
    if (!c.base_url) return;
    setFetchingModels(true);
    setStatus(null);
    const res = await rpc<string[]>("llm.get_models", {
      base_url: c.base_url,
      provider: c.provider,
      api_key: c.api_key,
    });
    if (res.ok && res.data) {
      setModels(res.data);
      if (res.data.length === 0) {
        const hint = c.provider === "ollama" ? "Pull a model in Ollama first." : "No models found at this endpoint.";
        setStatus({ type: "error", msg: `No models found. ${hint}` });
      }
    } else {
      setModels([]);
      setStatus({ type: "error", msg: res.error || "Could not connect to server." });
    }
    setFetchingModels(false);
  }

  async function handleSaveLLM() {
    setSaving(true);
    setStatus(null);
    const res = await rpc<LLMConfig>("llm.save_config", { config });
    setStatus(res.ok ? { type: "success", msg: "Settings saved." } : { type: "error", msg: res.error || "Failed to save settings." });
    setSaving(false);
  }

  // -- Profile -------------------------------------------------------------

  async function loadSupportedCountries() {
    const res = await rpc<string[]>("tax.supported_countries");
    if (res.ok && res.data) setSupportedCountries(res.data);
  }

  async function loadProfile() {
    setProfileLoading(true);
    const res = await rpc<Entity>("users.get_active");
    if (res.ok && res.data) {
      const d = res.data as Entity;
      setIsDemoUser(!!d.is_demo);
      if (d.db_file) setActiveDbFile(d.db_file as string);
      const p = d.profile as Entity | undefined;
      if (p) {
        const addr = p.address as Entity | undefined;
        const bank = p.bank_account as Entity | undefined;
        setProfile({
          name: str(p, "name"),
          subtitle: str(p, "subtitle"),
          email: str(p, "email"),
          phone_number: str(p, "phone_number"),
          website: str(p, "website"),
          logo: str(p, "logo"),
          signature: str(p, "signature"),
          accent_color: str(p, "accent_color") || "#2563eb",
          VAT_number: str(p, "VAT_number"),
          tax_number: str(p, "tax_number"),
          operating_country: str(p, "operating_country") || "Germany",
          street: addr ? str(addr, "street") : "",
          number: addr ? str(addr, "number") : "",
          postal_code: addr ? str(addr, "postal_code") : "",
          city: addr ? str(addr, "city") : "",
          country: addr ? str(addr, "country") : "",
          bank_name: bank ? str(bank, "name") : "",
          bank_IBAN: bank ? str(bank, "IBAN") : "",
          bank_BIC: bank ? str(bank, "BIC") : "",
        });
      }
    }
    setProfileLoading(false);
  }

  async function handleSaveProfile() {
    setProfileSaving(true);
    setProfileStatus(null);
    const payload = {
      profile: {
        name: profile.name,
        subtitle: profile.subtitle,
        email: profile.email,
        phone_number: profile.phone_number,
        website: profile.website,
        logo: profile.logo,
        signature: profile.signature,
        accent_color: profile.accent_color,
        VAT_number: profile.VAT_number,
        tax_number: profile.tax_number,
        operating_country: profile.operating_country,
        address: {
          street: profile.street,
          number: profile.number,
          postal_code: profile.postal_code,
          city: profile.city,
          country: profile.country,
        },
        bank_account: {
          name: profile.bank_name,
          IBAN: profile.bank_IBAN,
          BIC: profile.bank_BIC,
        },
      },
    };
    const res = await rpc("users.update_profile", payload);
    setProfileStatus(res.ok ? { type: "success", msg: "Profile saved." } : { type: "error", msg: res.error || "Failed to save profile." });
    setProfileSaving(false);
  }

  async function handleResetDemo() {
    if (!confirm("This will delete all demo data and recreate it from scratch. Continue?")) return;
    setResettingDemo(true);
    setProfileStatus(null);
    const res = await rpc("demo.reset");
    if (res.ok) {
      setProfileStatus({ type: "success", msg: "Demo data has been reset." });
      await loadProfile();
    } else {
      setProfileStatus({ type: "error", msg: res.error || "Failed to reset demo data." });
    }
    setResettingDemo(false);
  }

  function pset<K extends keyof ProfileForm>(key: K) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setProfile((p) => ({ ...p, [key]: e.target.value }));
  }

  const [logoDragOver, setLogoDragOver] = useState(false);
  const [sigDragOver, setSigDragOver] = useState(false);

  async function processImageFile(file: File, field: "logo" | "signature") {
    const maxBytes = field === "logo" ? MAX_LOGO_BYTES : MAX_SIGNATURE_BYTES;
    if (!file.type.startsWith("image/")) {
      setProfileStatus({ type: "error", msg: "File must be an image." });
      return;
    }
    if (file.size > maxBytes) {
      setProfileStatus({ type: "error", msg: `${field === "logo" ? "Logo" : "Signature"} is too large (max 2 MB).` });
      return;
    }
    const dataUri = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
    setProfile((p) => ({ ...p, [field]: dataUri }));
    setProfileStatus(null);
  }

  function handleLogoFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) processImageFile(file, "logo");
  }

  function handleSignatureFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) processImageFile(file, "signature");
  }

  function handleLogoDrop(e: React.DragEvent) {
    e.preventDefault(); setLogoDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) processImageFile(file, "logo");
  }

  function handleSignatureDrop(e: React.DragEvent) {
    e.preventDefault(); setSigDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) processImageFile(file, "signature");
  }

  async function handleDeleteUser() {
    if (!activeDbFile) return;
    setDeleting(true);
    await rpc("users.delete", { db_file: activeDbFile });
    window.location.reload();
  }

  // -- Invoicing preferences -----------------------------------------------

  async function loadInvoicingPrefs() {
    const loadId = ++invoicingLoadRef.current;
    const [prefsRes, tmplRes, langRes, schemeRes, eInvRes] = await Promise.all([
      rpc<InvoicingPrefs>("preferences.get"),
      rpc<Record<string, string>>("invoicing.available_templates"),
      rpc<Record<string, string>>("invoicing.available_languages"),
      rpc<Record<string, string>>("invoicing.available_number_schemes"),
      rpc<Record<string, string>>("invoicing.available_e_invoice_profiles"),
    ]);
    if (loadId !== invoicingLoadRef.current) return;
    if (prefsRes.ok && prefsRes.data) {
      setInvoicing({ ...DEFAULT_INVOICING, ...prefsRes.data });
    }
    if (tmplRes.ok && tmplRes.data) setAvailableTemplates(tmplRes.data);
    if (langRes.ok && langRes.data) setAvailableLanguages(langRes.data);
    if (schemeRes.ok && schemeRes.data) setAvailableSchemes(schemeRes.data);
    if (eInvRes.ok && eInvRes.data) setAvailableEInvoiceProfiles(eInvRes.data);
  }

  async function handleSaveInvoicing() {
    setInvoicingSaving(true);
    setInvoicingStatus(null);
    const res = await rpc("preferences.save", {
      invoice_template: invoicing.invoice_template,
      language: invoicing.language,
      invoice_number_scheme: invoicing.invoice_number_scheme,
      e_invoice_profile: invoicing.e_invoice_profile,
      include_logo: invoicing.include_logo,
      include_due_date: invoicing.include_due_date,
      include_signature: invoicing.include_signature,
    });
    if (res.ok) {
      await loadInvoicingPrefs();
      setInvoicingStatus({ type: "success", msg: "Invoicing preferences saved." });
    } else {
      setInvoicingStatus({ type: "error", msg: res.error || "Failed to save." });
    }
    setInvoicingSaving(false);
  }

  // -- Saved invoice notes -------------------------------------------------

  async function loadSavedNotes() {
    const res = await rpc<Entity[]>("invoice_notes.get_all");
    if (res.ok && res.data) setSavedNotes(res.data);
  }

  async function handleAddNote() {
    const text = newNoteText.trim();
    if (!text) return;
    setAddingNote(true);
    const res = await rpc<Entity>("invoice_notes.create", { text });
    if (res.ok) {
      setNewNoteText("");
      await loadSavedNotes();
    }
    setAddingNote(false);
  }

  async function handleDeleteNote(id: number) {
    await rpc("invoice_notes.delete", { id });
    await loadSavedNotes();
  }

  // -- Render --------------------------------------------------------------

  if (loading || profileLoading) {
    return <div className="flex items-center justify-center h-full text-secondary">Loading settings…</div>;
  }

  const inputCls = "w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors placeholder:text-muted";
  const labelCls = "block text-xs text-tertiary mb-1";

  return (
    <div className="flex h-full">
      {/* Sidebar tabs */}
      <nav className="w-48 shrink-0 border-r border-border-subtle py-4 px-2 space-y-1">
        <div className="flex items-center gap-2 px-3 pb-3">
          <Settings size={18} strokeWidth={1.6} className="text-secondary" />
          <span className="text-sm font-semibold">Settings</span>
        </div>
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 w-full px-3 py-2 rounded-md text-sm transition-colors ${
              tab === id
                ? "bg-accent/10 text-primary font-medium"
                : "text-secondary hover:bg-bg-hover hover:text-primary"
            }`}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <div className={`flex-1 p-6 ${tab === "debug" ? "flex flex-col overflow-hidden" : "overflow-y-auto"}`}>
        <div className={tab === "debug" ? "flex flex-col flex-1 min-h-0" : "max-w-xl"}>

      {tab === "profile" && (
        <section className="space-y-4">
          {isDemoUser && (
            <div className="flex items-center gap-3">
              <span className="inline-block text-[10px] text-muted bg-bg-hover px-2 py-0.5 rounded-full">
                demo user
              </span>
              <button
                onClick={handleResetDemo}
                disabled={resettingDemo}
                className="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs text-secondary hover:text-primary border border-border-subtle hover:bg-bg-hover transition-colors disabled:opacity-40"
              >
                <RotateCcw size={12} className={resettingDemo ? "animate-spin" : ""} />
                {resettingDemo ? "Resetting…" : "Reset demo data"}
              </button>
            </div>
          )}

          <p className="text-xs text-muted"><span className="text-accent">*</span> Required</p>

          <fieldset className="border border-border-subtle rounded-lg px-4 pb-3 pt-2">
            <legend className="text-xs font-medium text-secondary px-1">Contact</legend>
            <div className="space-y-3 mt-1">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className={labelCls}>Full name <span className="text-accent">*</span></label>
                  <input className={inputCls} value={profile.name} onChange={pset("name")} />
                </div>
                <div className="col-span-2">
                  <label className={labelCls}>Subtitle / profession</label>
                  <input className={inputCls} value={profile.subtitle} onChange={pset("subtitle")} placeholder="Freelance consultant" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelCls}>Email <span className="text-accent">*</span></label>
                  <input className={inputCls} type="email" value={profile.email} onChange={pset("email")} />
                </div>
                <div>
                  <label className={labelCls}>Phone</label>
                  <input className={inputCls} value={profile.phone_number} onChange={pset("phone_number")} />
                </div>
              </div>
              <div>
                <label className={labelCls}>Website</label>
                <input className={inputCls} value={profile.website} onChange={pset("website")} placeholder="https://…" />
              </div>
            </div>
          </fieldset>

          <fieldset className="border border-border-subtle rounded-lg px-4 pb-3 pt-2">
            <legend className="text-xs font-medium text-secondary px-1">Address</legend>
            <div className="grid grid-cols-4 gap-3 mt-1">
              <div className="col-span-3">
                <label className={labelCls}>Street</label>
                <input className={inputCls} value={profile.street} onChange={pset("street")} />
              </div>
              <div>
                <label className={labelCls}>Nr.</label>
                <input className={inputCls} value={profile.number} onChange={pset("number")} />
              </div>
              <div>
                <label className={labelCls}>Postal code</label>
                <input className={inputCls} value={profile.postal_code} onChange={pset("postal_code")} />
              </div>
              <div className="col-span-2">
                <label className={labelCls}>City</label>
                <input className={inputCls} value={profile.city} onChange={pset("city")} />
              </div>
              <div>
                <label className={labelCls}>Country</label>
                <input className={inputCls} value={profile.country} onChange={pset("country")} />
              </div>
            </div>
          </fieldset>

          <fieldset className="border border-border-subtle rounded-lg px-4 pb-3 pt-2">
            <legend className="text-xs font-medium text-secondary px-1">Tax &amp; Legal</legend>
            <div className="grid grid-cols-2 gap-3 mt-1">
              <div>
                <label className={labelCls}>VAT number <span className="text-accent">*</span></label>
                <input className={inputCls} value={profile.VAT_number} onChange={pset("VAT_number")} placeholder="DE123456789" />
              </div>
              <div>
                <label className={labelCls}>Tax number</label>
                <input className={inputCls} value={profile.tax_number} onChange={pset("tax_number")} placeholder="21/815/08150" />
                <p className="text-xs text-secondary mt-1">Steuernummer. Used on invoices outside the scope of VAT, where the VAT number may not appear.</p>
              </div>
              <div>
                <label className={labelCls}>Operating country <span className="text-accent">*</span></label>
                <select className={inputCls} value={profile.operating_country} onChange={pset("operating_country")}>
                  {supportedCountries.length > 0 ? (
                    supportedCountries.map((c) => <option key={c} value={c}>{c}</option>)
                  ) : (
                    <option value={profile.operating_country}>{profile.operating_country}</option>
                  )}
                </select>
              </div>
            </div>
          </fieldset>

          <fieldset className="border border-border-subtle rounded-lg px-4 pb-3 pt-2">
            <legend className="text-xs font-medium text-secondary px-1">Bank Account</legend>
            <div className="grid grid-cols-2 gap-3 mt-1">
              <div className="col-span-2">
                <label className={labelCls}>Account holder / Bank name</label>
                <input className={inputCls} value={profile.bank_name} onChange={pset("bank_name")} placeholder="Your Name or Bank Name" />
              </div>
              <div>
                <label className={labelCls}>IBAN</label>
                <input className={inputCls} value={profile.bank_IBAN} onChange={pset("bank_IBAN")} placeholder="DE89 3704 0044 0532 0130 00" />
              </div>
              <div>
                <label className={labelCls}>BIC</label>
                <input className={inputCls} value={profile.bank_BIC} onChange={pset("bank_BIC")} placeholder="COBADEFFXXX" />
              </div>
            </div>
          </fieldset>

          {profileStatus && (
            <div className={`flex items-center gap-2 text-sm ${profileStatus.type === "success" ? "text-green-400" : "text-red-400"}`}>
              {profileStatus.type === "success" ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
              <span>{profileStatus.msg}</span>
            </div>
          )}

          <button
            onClick={handleSaveProfile}
            disabled={profileSaving || !profile.name.trim()}
            className="flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium bg-accent/10 text-primary hover:bg-accent/20 border border-accent/30 transition-colors disabled:opacity-40"
          >
            <Save size={14} />
            {profileSaving ? "Saving…" : "Save Profile"}
          </button>

          {/* Danger zone */}
          <div className="mt-8 pt-6 border-t border-red-500/20">
            <h3 className="text-sm font-semibold text-red-400 mb-2">Danger zone</h3>
            <p className="text-xs text-muted mb-3">
              Permanently delete this user and all associated data (contracts, invoices, time tracking, etc.). This action cannot be undone.
            </p>
            <button
              onClick={() => { setDeleteConfirmOpen(true); setDeleteConfirmText(""); }}
              disabled={deleting}
              className="flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium text-red-400 border border-red-500/30 hover:bg-red-500/10 transition-colors disabled:opacity-40"
            >
              <Trash2 size={14} />
              Delete user and data
            </button>
          </div>
        </section>
      )}

      {/* Delete confirmation modal */}
      {deleteConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-bg-sidebar rounded-xl shadow-2xl w-full max-w-sm mx-4 overflow-hidden">
            <div className="px-5 py-4 space-y-4">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center w-10 h-10 rounded-full bg-red-500/10">
                  <AlertTriangle size={20} className="text-red-400" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-primary">Delete user?</h3>
                  <p className="text-xs text-muted">This will permanently remove all data.</p>
                </div>
              </div>
              <p className="text-sm text-secondary">
                Type <span className="font-mono font-semibold text-primary">{profile.name}</span> to confirm:
              </p>
              <input
                className={inputCls}
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                placeholder={profile.name}
                autoFocus
              />
            </div>
            <div className="flex justify-end gap-2 px-5 py-3 border-t border-border-subtle">
              <button
                onClick={() => setDeleteConfirmOpen(false)}
                disabled={deleting}
                className="px-4 py-1.5 text-sm rounded-md text-secondary hover:bg-bg-hover transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteUser}
                disabled={deleting || deleteConfirmText !== profile.name}
                className="px-4 py-1.5 text-sm rounded-md bg-red-500 text-white font-medium hover:bg-red-600 transition-colors disabled:opacity-40"
              >
                {deleting ? "Deleting…" : "Delete permanently"}
              </button>
            </div>
          </div>
        </div>
      )}

      {tab === "branding" && (
        <section className="space-y-6">
          <p className="text-sm text-muted">Your visual identity — used on invoices, timesheets, and other documents.</p>

          <div className="grid grid-cols-2 gap-6">
            <fieldset
              className={`border rounded-lg px-4 pb-4 pt-2 transition-colors ${logoDragOver ? "border-accent bg-accent/5" : "border-border-subtle"}`}
              onDragOver={(e) => { e.preventDefault(); setLogoDragOver(true); }}
              onDragLeave={() => setLogoDragOver(false)}
              onDrop={handleLogoDrop}
            >
              <legend className="text-xs font-medium text-secondary px-1">Logo</legend>
              <div className="flex items-center gap-4 mt-2">
                <div className="flex items-center justify-center w-16 h-16 shrink-0 rounded-md border border-border-subtle bg-bg-card overflow-hidden">
                  {profile.logo ? (
                    <img src={profile.logo} alt="Logo preview" className="max-w-full max-h-full object-contain" />
                  ) : (
                    <ImageIcon size={18} className="text-muted" />
                  )}
                </div>
                <div className="flex flex-col gap-2">
                  <label className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-bg-card text-secondary hover:text-primary border border-border-subtle hover:bg-bg-hover transition-colors cursor-pointer w-fit">
                    <ImageIcon size={13} />
                    {profile.logo ? "Replace" : "Upload"}
                    <input type="file" accept="image/*" className="hidden" onChange={handleLogoFile} />
                  </label>
                  {profile.logo && (
                    <button
                      type="button"
                      onClick={() => setProfile((p) => ({ ...p, logo: "" }))}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs text-secondary hover:text-red-400 border border-border-subtle hover:bg-bg-hover transition-colors w-fit"
                    >
                      <X size={13} />
                      Remove
                    </button>
                  )}
                </div>
              </div>
              <p className="text-xs text-muted mt-2">PNG or JPG, max 2 MB. Drag and drop or click to upload.</p>
            </fieldset>

            <fieldset className="border border-border-subtle rounded-lg px-4 pb-4 pt-2">
              <legend className="text-xs font-medium text-secondary px-1">Accent color</legend>
              <div className="flex items-center gap-3 mt-2">
                <input
                  type="color"
                  value={profile.accent_color || "#2563eb"}
                  onChange={(e) => setProfile((p) => ({ ...p, accent_color: e.target.value }))}
                  className="w-10 h-10 rounded-md border border-border-subtle bg-bg-card cursor-pointer p-0.5 shrink-0"
                />
                <span className="text-sm text-secondary font-mono">{profile.accent_color || "#2563eb"}</span>
              </div>
              <p className="text-xs text-muted mt-2">Used for headings, rules, and highlights.</p>
            </fieldset>
          </div>

          <fieldset
            className={`border rounded-lg px-4 pb-4 pt-2 transition-colors ${sigDragOver ? "border-accent bg-accent/5" : "border-border-subtle"}`}
            onDragOver={(e) => { e.preventDefault(); setSigDragOver(true); }}
            onDragLeave={() => setSigDragOver(false)}
            onDrop={handleSignatureDrop}
          >
            <legend className="text-xs font-medium text-secondary px-1">Signature</legend>
            <div className="flex items-center gap-4 mt-2">
              <div className="flex items-center justify-center w-32 h-16 shrink-0 rounded-md border border-border-subtle bg-white overflow-hidden">
                {profile.signature ? (
                  <img src={profile.signature} alt="Signature preview" className="max-w-full max-h-full object-contain" />
                ) : (
                  <ImageIcon size={18} className="text-muted" />
                )}
              </div>
              <div className="flex flex-col gap-2">
                <label className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-bg-card text-secondary hover:text-primary border border-border-subtle hover:bg-bg-hover transition-colors cursor-pointer w-fit">
                  <ImageIcon size={13} />
                  {profile.signature ? "Replace" : "Upload"}
                  <input type="file" accept="image/*" className="hidden" onChange={handleSignatureFile} />
                </label>
                {profile.signature && (
                  <button
                    type="button"
                    onClick={() => setProfile((p) => ({ ...p, signature: "" }))}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs text-secondary hover:text-red-400 border border-border-subtle hover:bg-bg-hover transition-colors w-fit"
                  >
                    <X size={13} />
                    Remove
                  </button>
                )}
              </div>
            </div>
            <p className="text-xs text-muted mt-2">Upload a photo or scan of your signature. The background is removed automatically. Drag and drop supported.</p>
          </fieldset>

          <button
            onClick={handleSaveProfile}
            disabled={profileSaving}
            className="flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium bg-accent/10 text-primary hover:bg-accent/20 border border-accent/30 transition-colors disabled:opacity-40"
          >
            <Save size={14} />
            {profileSaving ? "Saving…" : "Save Branding"}
          </button>
          {profileStatus && (
            <div className={`flex items-center gap-2 text-sm ${profileStatus.type === "success" ? "text-green-400" : "text-red-400"}`}>
              {profileStatus.type === "success" ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
              <span>{profileStatus.msg}</span>
            </div>
          )}
        </section>
      )}

      {tab === "invoicing" && (
        <section className="space-y-4">
          <div>
            <label className={labelCls}>Invoice template</label>
            <select
              className={inputCls}
              value={invoicing.invoice_template}
              onChange={(e) => setInvoicing((p) => ({ ...p, invoice_template: e.target.value }))}
            >
              {Object.entries(availableTemplates).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
            <p className="mt-1 text-xs text-muted">Visual style of generated invoices.</p>
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={invoicing.include_logo}
              onChange={(e) => setInvoicing((p) => ({ ...p, include_logo: e.target.checked }))}
              className="rounded border-border-subtle text-accent focus:ring-accent"
            />
            <span className="text-sm text-primary">Include logo on invoices</span>
          </label>
          <p className="mt-1 text-xs text-muted mb-3">When enabled, your uploaded logo appears on generated invoices.</p>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={invoicing.include_due_date}
              onChange={(e) => setInvoicing((p) => ({ ...p, include_due_date: e.target.checked }))}
              className="rounded border-border-subtle text-accent focus:ring-accent"
            />
            <span className="text-sm text-primary">Include payment due dates</span>
          </label>
          <p className="mt-1 text-xs text-muted mb-3">When enabled, a payment due date based on contract terms appears on generated invoices.</p>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={invoicing.include_signature}
              onChange={(e) => setInvoicing((p) => ({ ...p, include_signature: e.target.checked }))}
              className="rounded border-border-subtle text-accent focus:ring-accent"
            />
            <span className="text-sm text-primary">Include signature on invoices</span>
          </label>
          <p className="mt-1 text-xs text-muted mb-3">When enabled, your uploaded signature appears above your name on generated invoices.</p>

          <div>
            <label className={labelCls}>Invoice language</label>
            <select
              className={inputCls}
              value={invoicing.language}
              onChange={(e) => setInvoicing((p) => ({ ...p, language: e.target.value }))}
            >
              {Object.entries(availableLanguages).map(([code, label]) => (
                <option key={code} value={code}>{label}</option>
              ))}
            </select>
            <p className="mt-1 text-xs text-muted">Language for invoice labels, dates, and currency formatting.</p>
          </div>

          <div>
            <label className={labelCls}>Invoice number scheme</label>
            <select
              className={inputCls}
              value={invoicing.invoice_number_scheme}
              onChange={(e) => setInvoicing((p) => ({ ...p, invoice_number_scheme: e.target.value }))}
            >
              {Object.entries(availableSchemes).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
            <p className="mt-1 text-xs text-muted">
              Example: <span className="font-mono text-primary">{SCHEME_EXAMPLES[invoicing.invoice_number_scheme] || "—"}</span>
            </p>
          </div>

          <div>
            <label className={labelCls}>Electronic invoice (e-invoice)</label>
            <select
              className={inputCls}
              value={invoicing.e_invoice_profile}
              onChange={(e) => setInvoicing((p) => ({ ...p, e_invoice_profile: e.target.value }))}
            >
              {Object.entries(availableEInvoiceProfiles).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
            <p className="mt-1 text-xs text-muted">
              When enabled, invoices include machine-readable data (ZUGFeRD/Factur-X) embedded in the PDF. "Standard" works for most B2B invoicing. Use "XRechnung" only for German government clients.
            </p>
          </div>

          {invoicingStatus && (
            <div className={`flex items-center gap-2 text-sm ${invoicingStatus.type === "success" ? "text-green-400" : "text-red-400"}`}>
              {invoicingStatus.type === "success" ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
              <span>{invoicingStatus.msg}</span>
            </div>
          )}

          <button
            onClick={handleSaveInvoicing}
            disabled={invoicingSaving}
            className="flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium bg-accent/10 text-primary hover:bg-accent/20 border border-accent/30 transition-colors disabled:opacity-40"
          >
            <Save size={14} />
            {invoicingSaving ? "Saving…" : "Save Invoicing Preferences"}
          </button>

          <div className="pt-4 border-t border-border-subtle">
            <label className={labelCls}>Saved Invoice Notes</label>
            <p className="text-xs text-muted mb-2">Reusable closing notes for invoices (e.g. VAT exemption, reverse charge). These appear as quick-select options when creating an invoice.</p>

            {savedNotes.length > 0 && (
              <div className="space-y-1.5 mb-3">
                {savedNotes.map((n) => (
                  <div key={n.id} className="flex items-start gap-2 p-2 rounded-lg bg-bg-card border border-border-subtle">
                    <span className="flex-1 text-xs text-primary whitespace-pre-wrap break-words">{str(n, "text")}</span>
                    <button
                      onClick={() => handleDeleteNote(n.id)}
                      className="shrink-0 p-1 rounded text-muted hover:text-red-400 hover:bg-red-400/10 transition-colors"
                      title="Delete note"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-2">
              <input
                type="text"
                value={newNoteText}
                onChange={(e) => setNewNoteText(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleAddNote(); } }}
                placeholder="Add a new note…"
                className="flex-1 px-3 py-1.5 rounded-md bg-bg-card border border-border-subtle text-sm text-primary placeholder:text-muted"
              />
              <button
                onClick={handleAddNote}
                disabled={addingNote || !newNoteText.trim()}
                className="px-3 py-1.5 rounded-md text-sm font-medium bg-accent/10 text-primary hover:bg-accent/20 border border-accent/30 transition-colors disabled:opacity-40"
              >
                {addingNote ? "Adding…" : "Add"}
              </button>
            </div>
          </div>
        </section>
      )}

      {tab === "system" && (
        <SystemTab />
      )}

      {tab === "debug" && (
        <BackendLogs />
      )}

      {tab === "llm" && (
        <section className="space-y-4">
          <div>
            <label className={labelCls}>Provider</label>
            <select
              value={config.provider}
              onChange={(e) => {
                const p = e.target.value;
                setModels([]);
                setConfig((c) => ({
                  ...c,
                  provider: p,
                  base_url: p === "ollama" ? "http://localhost:11434" : c.base_url === "http://localhost:11434" ? "" : c.base_url,
                }));
              }}
              className={inputCls}
            >
              <option value="ollama">Ollama</option>
              <option value="openai">OpenAI API compatible</option>
            </select>
            {config.provider === "openai" && (
              <p className="mt-1 text-xs text-muted">Works with OpenAI, Anthropic, Together, Groq, vLLM, and any OpenAI-compatible endpoint.</p>
            )}
          </div>

          <div>
            <label className={labelCls}>{config.provider === "ollama" ? "Ollama URL" : "API Base URL"}</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={config.base_url}
                onChange={(e) => setConfig((c) => ({ ...c, base_url: e.target.value }))}
                placeholder={config.provider === "ollama" ? "http://localhost:11434" : "https://api.openai.com/v1"}
                className={`flex-1 ${inputCls}`}
              />
              <button
                onClick={() => fetchModels()}
                disabled={fetchingModels || !config.base_url}
                className="flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium bg-bg-card text-secondary hover:text-primary border border-border-subtle transition-colors disabled:opacity-40"
              >
                <RefreshCw size={14} className={fetchingModels ? "animate-spin" : ""} />
                {fetchingModels ? "Fetching…" : "Fetch Models"}
              </button>
            </div>
          </div>

          {config.provider !== "ollama" && (
            <div>
              <label className={labelCls}>API Key</label>
              <input
                type="password"
                value={config.api_key}
                onChange={(e) => setConfig((c) => ({ ...c, api_key: e.target.value }))}
                placeholder="sk-…"
                className={inputCls}
              />
              <p className="mt-1 text-xs text-muted">
                Required for most OpenAI-compatible providers. Leave blank if the endpoint needs no authentication.
              </p>
            </div>
          )}

          <div>
            <label className={labelCls}>Model</label>
            {models.length > 0 ? (
              <select value={config.model} onChange={(e) => setConfig((c) => ({ ...c, model: e.target.value }))} className={inputCls}>
                <option value="">Select a model…</option>
                {models.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            ) : fetchingModels ? (
              <div className="px-3 py-2 rounded-md text-sm bg-bg-card text-muted border border-border-subtle">
                Fetching models…
              </div>
            ) : (
              <input
                type="text"
                value={config.model}
                onChange={(e) => setConfig((c) => ({ ...c, model: e.target.value }))}
                placeholder={config.provider === "ollama" ? "qwen3:8b" : "gpt-4o"}
                className={inputCls}
              />
            )}
            <p className="mt-1 text-xs text-muted">
              {models.length > 0 ? "Choose from fetched models, or type a name manually below." : "Click \"Fetch Models\" to list available models, or type a name directly."}
            </p>
          </div>

          <div>
            <label className={labelCls}>Request Timeout (seconds)</label>
            <input
              type="number"
              min={30}
              step={30}
              value={config.request_timeout}
              onChange={(e) => setConfig((c) => ({ ...c, request_timeout: Math.max(30, Number(e.target.value)) }))}
              className="w-32 px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors"
            />
            <p className="mt-1 text-xs text-muted">How long to wait for LLM responses. Increase for large documents or slow models.</p>
          </div>

          {status && (
            <div className={`flex items-center gap-2 text-sm ${status.type === "success" ? "text-green-400" : "text-red-400"}`}>
              {status.type === "success" ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
              <span>{status.msg}</span>
            </div>
          )}

          <button
            onClick={handleSaveLLM}
            disabled={saving || !config.model}
            className="flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium bg-accent/10 text-primary hover:bg-accent/20 border border-accent/30 transition-colors disabled:opacity-40"
          >
            <Save size={14} />
            {saving ? "Saving…" : "Save LLM Settings"}
          </button>
        </section>
      )}

        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// System tab
// ---------------------------------------------------------------------------

const LOG_TYPE_STYLES: Record<MessageType, string> = {
  info: "text-blue-400",
  error: "text-red-400",
  success: "text-green-400",
};

const LOG_TYPE_ICONS: Record<MessageType, typeof Info> = {
  info: Info,
  error: AlertCircle,
  success: CheckCircle2,
};

const THEME_OPTIONS: { id: ThemeChoice; label: string; icon: typeof Sun }[] = [
  { id: "light", label: "Light", icon: Sun },
  { id: "dark", label: "Dark", icon: Moon },
  { id: "system", label: "System", icon: Laptop },
];

function SystemTab() {
  const { log, showMessage } = useStatusBar();
  const { choice, setChoice } = useTheme();
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    const offs = [
      window.tuttle?.onUpdateNotAvailable?.(() => {
        setChecking(false);
        showMessage("You're on the latest version.", { type: "success" });
      }),
      window.tuttle?.onUpdateAvailable?.((info) => {
        setChecking(false);
        showMessage(`Update ${info.version} available — downloading…`, { type: "info" });
      }),
      window.tuttle?.onUpdateError?.((info) => {
        setChecking(false);
        showMessage(`Update check failed: ${info.message}`, { type: "error" });
      }),
    ];
    return () => offs.forEach((off) => off?.());
  }, []);

  function handleCheckForUpdate() {
    setChecking(true);
    window.tuttle.checkForUpdate();
    setTimeout(() => setChecking(false), 15000);
  }

  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <h3 className="text-sm font-semibold">Appearance</h3>
        <div className="flex rounded-lg border border-border-subtle overflow-hidden w-fit">
          {THEME_OPTIONS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setChoice(id)}
              className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium transition-colors ${
                choice === id
                  ? "bg-accent/10 text-primary border-accent/30"
                  : "text-secondary hover:bg-bg-hover hover:text-primary"
              }`}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-1">
        <h3 className="text-sm font-semibold">About Tuttle</h3>
        <p className="text-sm text-secondary">Version {__APP_VERSION__}</p>
        <p className="text-xs text-muted">Platform: {window.tuttle.platform}</p>
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-semibold">Updates</h3>
        <button
          onClick={handleCheckForUpdate}
          disabled={checking}
          className="flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium bg-accent/10 text-primary hover:bg-accent/20 border border-accent/30 transition-colors disabled:opacity-40"
        >
          <RefreshCw size={14} className={checking ? "animate-spin" : ""} />
          {checking ? "Checking…" : "Check for updates"}
        </button>
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-semibold">Message Log</h3>
        {log.length === 0 ? (
          <p className="text-xs text-muted">No messages yet.</p>
        ) : (
          <div className="border border-border-subtle rounded-md overflow-hidden max-h-64 overflow-y-auto">
            {log.map((msg) => {
              const Icon = LOG_TYPE_ICONS[msg.type];
              return (
                <div
                  key={msg.id}
                  className="flex items-start gap-2 px-3 py-2 text-xs border-b border-border-subtle last:border-b-0"
                >
                  <Icon size={13} className={`shrink-0 mt-0.5 ${LOG_TYPE_STYLES[msg.type]}`} />
                  <span className="text-secondary flex-1">{msg.text}</span>
                  <time className="text-muted shrink-0">
                    {msg.timestamp.toLocaleTimeString()}
                  </time>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Backend Logs
// ---------------------------------------------------------------------------

const LEVEL_STYLES: Record<string, string> = {
  ERROR: "text-red-400",
  WARNING: "text-amber-400",
  INFO: "text-blue-400",
  DEBUG: "text-muted",
};

type LogEntry = {
  ts: string;
  level: string;
  message: string;
  module: string;
  function: string;
  line: number;
  exception?: string;
};

function BackendLogs() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [levelFilter, setLevelFilter] = useState<string>("all");
  const [copied, setCopied] = useState(false);

  async function fetchLogs() {
    setLoading(true);
    const res = await rpc("system.get_logs", { limit: 200 });
    if (res.ok && Array.isArray(res.data)) setLogs(res.data);
    setLoading(false);
  }

  useEffect(() => { fetchLogs(); }, []);

  const filtered = levelFilter === "all" ? logs : logs.filter((e) => e.level === levelFilter);

  async function handleClear() {
    await rpc("system.clear_logs");
    setLogs([]);
  }

  function formatAsText(): string {
    return filtered
      .map((e) => {
        const time = new Date(e.ts).toLocaleTimeString();
        const line = `[${time}] ${e.level.padEnd(7)} ${e.message}`;
        return e.exception ? `${line}\n  ${e.exception}` : line;
      })
      .join("\n");
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(formatAsText());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <section className="h-full flex flex-col gap-3">
      <div className="flex items-center gap-2 shrink-0">
        <select
          value={levelFilter}
          onChange={(e) => setLevelFilter(e.target.value)}
          className="text-xs border border-border-subtle rounded px-2 py-1 bg-bg-primary text-primary"
        >
          <option value="all">All levels</option>
          <option value="ERROR">Error</option>
          <option value="WARNING">Warning</option>
          <option value="INFO">Info</option>
          <option value="DEBUG">Debug</option>
        </select>
        <button
          onClick={fetchLogs}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-bg-hover text-primary hover:bg-border-subtle border border-border-subtle transition-colors disabled:opacity-40"
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          {loading ? "Loading…" : "Refresh"}
        </button>
        <button
          onClick={handleCopy}
          disabled={filtered.length === 0}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-bg-hover text-primary hover:bg-border-subtle border border-border-subtle transition-colors disabled:opacity-40"
        >
          {copied ? <Check size={12} /> : <Clipboard size={12} />}
          {copied ? "Copied!" : "Copy to clipboard"}
        </button>
        <button
          onClick={handleClear}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-muted hover:text-primary hover:bg-bg-hover border border-transparent hover:border-border-subtle transition-colors"
        >
          Clear
        </button>
      </div>
      {filtered.length === 0 ? (
        <p className="text-xs text-muted">No log entries.</p>
      ) : (
        <pre className="flex-1 overflow-auto rounded-md border border-border-subtle bg-bg-primary p-2 text-[11px] leading-tight font-mono text-secondary whitespace-pre-wrap break-words">
          {filtered.map((entry, i) => {
            const time = new Date(entry.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
            const levelCls = LEVEL_STYLES[entry.level] || "";
            const tag = entry.level.slice(0, 4);
            return (
              <span key={i}>
                <span className="text-muted">{time}</span>{" "}
                <span className={levelCls}>{tag}</span>{" "}
                {entry.message}
                {entry.exception && (
                  <span className="text-red-400">{"\n     " + entry.exception}</span>
                )}
                {"\n"}
              </span>
            );
          })}
        </pre>
      )}
    </section>
  );
}
