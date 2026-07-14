/**
 * OnboardingWizard — multi-step first-run setup.
 *
 * COUPLING: Steps 1–4 mirror the tabs in SettingsView.tsx (Profile,
 * Business, Invoicing, AI/LLM). Any field or RPC change in SettingsView
 * must be reflected here, and vice-versa.
 *
 * @see {@link ../settings/SettingsView.tsx}
 */

import { useEffect, useState } from "react";
import { RefreshCw, ChevronRight, ChevronLeft, SkipForward, Check, X } from "lucide-react";
import { rpc } from "../../api/rpc";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WizardProfileData {
  name: string;
  subtitle: string;
  email: string;
  phone: string;
  website: string;
  street: string;
  street_num: string;
  postal_code: string;
  city: string;
  country: string;
  vat_number: string;
  tax_number: string;
  operating_country: string;
  bank_name: string;
  bank_IBAN: string;
  bank_BIC: string;
}

export interface WizardInvoicingData {
  invoice_template: string;
  language: string;
  invoice_number_scheme: string;
}

export interface WizardLLMData {
  provider: string;
  base_url: string;
  model: string;
  api_key: string;
  request_timeout: number;
}

export interface OnboardingData {
  profile: WizardProfileData;
  invoicing: WizardInvoicingData;
  llm: WizardLLMData;
}

type Props = {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: OnboardingData) => void;
  onDemo: () => void;
  loading?: boolean;
  overlay?: boolean;
};

const EMPTY_PROFILE: WizardProfileData = {
  name: "", subtitle: "", email: "", phone: "", website: "",
  street: "", street_num: "", postal_code: "", city: "", country: "Germany",
  vat_number: "", tax_number: "", operating_country: "Germany",
  bank_name: "", bank_IBAN: "", bank_BIC: "",
};

const DEFAULT_INVOICING: WizardInvoicingData = {
  invoice_template: "invoice-modern",
  language: "en",
  invoice_number_scheme: "daily",
};

const DEFAULT_LLM: WizardLLMData = {
  provider: "ollama",
  base_url: "http://localhost:11434",
  model: "",
  api_key: "",
  request_timeout: 600,
};

const SCHEME_EXAMPLES: Record<string, string> = {
  daily: "2025-05-17-01",
  yearly: "2025-01",
  plain: "01",
};

const STEP_LABELS = ["Welcome", "Profile", "Business", "Invoicing", "AI / LLM", "Finish"];
const TOTAL_STEPS = STEP_LABELS.length;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function OnboardingWizard({ open, onClose, onSubmit, onDemo, loading, overlay = true }: Props) {
  const [step, setStep] = useState(0);
  const [profile, setProfile] = useState<WizardProfileData>({ ...EMPTY_PROFILE });
  const [invoicing, setInvoicing] = useState<WizardInvoicingData>({ ...DEFAULT_INVOICING });
  const [llm, setLlm] = useState<WizardLLMData>({ ...DEFAULT_LLM });

  const [availableTemplates, setAvailableTemplates] = useState<Record<string, string>>({});
  const [availableLanguages, setAvailableLanguages] = useState<Record<string, string>>({});
  const [availableSchemes, setAvailableSchemes] = useState<Record<string, string>>({});
  const [supportedCountries, setSupportedCountries] = useState<string[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [fetchingModels, setFetchingModels] = useState(false);

  useEffect(() => {
    if (!open) {
      setStep(0);
      setProfile({ ...EMPTY_PROFILE });
      setInvoicing({ ...DEFAULT_INVOICING });
      setLlm({ ...DEFAULT_LLM });
      return;
    }
    Promise.all([
      rpc<Record<string, string>>("invoicing.available_templates"),
      rpc<Record<string, string>>("invoicing.available_languages"),
      rpc<Record<string, string>>("invoicing.available_number_schemes"),
      rpc<string[]>("tax.supported_countries"),
    ]).then(([tmpl, lang, scheme, countries]) => {
      if (tmpl.ok && tmpl.data) setAvailableTemplates(tmpl.data);
      if (lang.ok && lang.data) setAvailableLanguages(lang.data);
      if (scheme.ok && scheme.data) setAvailableSchemes(scheme.data);
      if (countries.ok && countries.data) setSupportedCountries(countries.data);
    });
  }, [open]);

  if (!open) return null;

  async function fetchLlmModels() {
    if (!llm.base_url) return;
    setFetchingModels(true);
    const res = await rpc<string[]>("llm.get_models", {
      base_url: llm.base_url,
      provider: llm.provider,
      api_key: llm.api_key,
    });
    if (res.ok && res.data) setModels(res.data);
    else setModels([]);
    setFetchingModels(false);
  }

  function canAdvance(): boolean {
    if (step === 1) {
      return !!(profile.name.trim() && profile.email.trim());
    }
    if (step === 2) {
      return !!(
        profile.street.trim() &&
        profile.city.trim() &&
        profile.country.trim() &&
        // Freelancers awaiting the USt-IdNr have only a Steuernummer.
        (profile.vat_number.trim() || profile.tax_number.trim()) &&
        profile.operating_country.trim()
      );
    }
    return true;
  }

  function next() {
    if (!canAdvance()) return;
    if (step === TOTAL_STEPS - 1) {
      onSubmit({ profile, invoicing, llm });
    } else {
      setStep((s) => s + 1);
    }
  }

  function back() {
    if (step > 0) setStep((s) => s - 1);
  }

  function skip() {
    setStep((s) => Math.min(s + 1, TOTAL_STEPS - 1));
  }

  const isSkippable = step === 3 || step === 4;

  const inputCls =
    "w-full rounded-md border border-border-subtle bg-bg-content px-3 py-1.5 text-sm text-primary placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent";
  const labelCls = "block text-xs font-medium text-secondary mb-1";

  // -- Step renderers -------------------------------------------------------

  function renderWelcome() {
    return (
      <div className="flex flex-col items-center text-center py-4 space-y-6">
        <h1 className="text-2xl font-bold text-primary">Welcome to Tuttle</h1>
        <p className="text-secondary text-sm leading-relaxed max-w-sm">
          The freelancer's command center for clients, contracts, invoicing and
          time tracking. Let's set up your workspace.
        </p>

        <div className="w-full max-w-sm text-left rounded-lg bg-bg-content/50 px-5 py-4" style={{ fontFamily: '"Courier New", Courier, monospace' }}>
          <p className="text-secondary text-xs leading-relaxed">
            <span className="font-bold text-primary">HARRY TUTTLE:</span>{" "}
            <span className="ml-2 inline-block">Bloody paperwork. Huh!</span>
          </p>
          <p className="text-secondary text-xs leading-relaxed mt-2">
            <span className="font-bold text-primary">SAM LOWRY:</span>{" "}
            <span className="ml-2 inline-block">I suppose one has to expect a certain amount.</span>
          </p>
          <p className="text-secondary text-xs leading-relaxed mt-2">
            <span className="font-bold text-primary">HARRY TUTTLE:</span>{" "}
            <span className="ml-2 inline-block">
              Why? I came into this game for the action, the excitement.
              Go anywhere, travel light, get in, get out, wherever there's
              trouble, a man alone.
            </span>
          </p>
        </div>

        <div className="flex flex-col gap-3 w-full max-w-sm pt-2">
          <button
            onClick={next}
            className="w-full px-5 py-2.5 rounded-lg bg-accent text-white font-medium text-sm hover:bg-accent/90 transition-colors"
          >
            Let's get started
          </button>
          <button
            onClick={onDemo}
            disabled={loading}
            className="w-full px-5 py-2.5 rounded-lg border border-border-subtle text-secondary text-sm hover:bg-bg-hover hover:text-primary transition-colors"
          >
            Try with demo data
          </button>
        </div>
      </div>
    );
  }

  function pset<K extends keyof WizardProfileData>(key: K) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setProfile((p) => ({ ...p, [key]: e.target.value }));
  }

  function renderProfile() {
    return (
      <div className="space-y-4">
        <p className="text-secondary text-sm leading-relaxed">
          Tell us about yourself. This information appears on your invoices
          and documents.
        </p>

        <p className="text-xs text-muted"><span className="text-accent">*</span> Required</p>

        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className={labelCls}>Full name <span className="text-accent">*</span></label>
            <input className={inputCls} value={profile.name} onChange={pset("name")} placeholder="Jane Doe" autoFocus required />
          </div>
          <div className="col-span-2">
            <label className={labelCls}>Subtitle / profession</label>
            <input className={inputCls} value={profile.subtitle} onChange={pset("subtitle")} placeholder="Freelance consultant" />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={labelCls}>Email <span className="text-accent">*</span></label>
            <input className={inputCls} type="email" value={profile.email} onChange={pset("email")} placeholder="mail@example.com" />
          </div>
          <div>
            <label className={labelCls}>Phone</label>
            <input className={inputCls} value={profile.phone} onChange={pset("phone")} placeholder="+49 …" />
          </div>
        </div>

        <div>
          <label className={labelCls}>Website</label>
          <input className={inputCls} value={profile.website} onChange={pset("website")} placeholder="https://…" />
        </div>
      </div>
    );
  }

  function renderBusiness() {
    return (
      <div className="space-y-4">
        <p className="text-secondary text-sm leading-relaxed">
          Your business address, tax info, and payment details for invoices.
        </p>

        <p className="text-xs text-muted"><span className="text-accent">*</span> Required</p>

        <fieldset className="border border-border-subtle rounded-lg px-4 pb-3 pt-2">
          <legend className="text-xs font-medium text-secondary px-1">Address <span className="text-accent">*</span></legend>
          <div className="grid grid-cols-4 gap-3 mt-1">
            <div className="col-span-3">
              <label className={labelCls}>Street</label>
              <input className={inputCls} value={profile.street} onChange={pset("street")} autoFocus />
            </div>
            <div>
              <label className={labelCls}>Nr.</label>
              <input className={inputCls} value={profile.street_num} onChange={pset("street_num")} />
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

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={labelCls}>VAT number</label>
            <input className={inputCls} value={profile.vat_number} onChange={pset("vat_number")} placeholder="DE123456789" />
          </div>
          <div>
            <label className={labelCls}>Tax number</label>
            <input className={inputCls} value={profile.tax_number} onChange={pset("tax_number")} placeholder="21/815/08150" />
          </div>
          <p className="col-span-2 text-xs text-muted">
            Enter your VAT number (USt-IdNr.) or, until you receive one, your tax number
            (Steuernummer) <span className="text-accent">*</span>. At least one appears on your invoices.
          </p>
          <div>
            <label className={labelCls}>Operating country <span className="text-accent">*</span></label>
            <select className={inputCls} value={profile.operating_country} onChange={pset("operating_country")}>
              {supportedCountries.length > 0 ? (
                supportedCountries.map((c) => <option key={c} value={c}>{c}</option>)
              ) : (
                <option value={profile.operating_country}>{profile.operating_country}</option>
              )}
            </select>
            <p className="mt-1 text-xs text-muted">Determines tax rules and default currency.</p>
          </div>
        </div>

        <fieldset className="border border-border-subtle rounded-lg px-4 pb-3 pt-2">
          <legend className="text-xs font-medium text-secondary px-1">Bank Account</legend>
          <p className="text-xs text-muted mb-2">Payment details shown on your invoices.</p>
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
      </div>
    );
  }

  function renderInvoicing() {
    return (
      <div className="space-y-4">
        <p className="text-secondary text-sm leading-relaxed">
          Choose how your invoices look and are numbered. Sensible defaults are
          already selected — feel free to skip this step and adjust later.
        </p>

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
      </div>
    );
  }

  function renderLLM() {
    return (
      <div className="space-y-4">
        <p className="text-secondary text-sm leading-relaxed">
          Tuttle can use a local or cloud AI model to help draft invoices and
          analyze contracts. Connect one now or skip and configure later.
        </p>

        <div>
          <label className={labelCls}>Provider</label>
          <select
            value={llm.provider}
            onChange={(e) => {
              const p = e.target.value;
              setModels([]);
              setLlm((c) => ({
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
          {llm.provider === "openai" && (
            <p className="mt-1 text-xs text-muted">Works with OpenAI, Anthropic, Together, Groq, vLLM, and any OpenAI-compatible endpoint.</p>
          )}
        </div>

        <div>
          <label className={labelCls}>{llm.provider === "ollama" ? "Ollama URL" : "API Base URL"}</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={llm.base_url}
              onChange={(e) => setLlm((c) => ({ ...c, base_url: e.target.value }))}
              placeholder={llm.provider === "ollama" ? "http://localhost:11434" : "https://api.openai.com/v1"}
              className={`flex-1 ${inputCls}`}
            />
            <button
              onClick={() => fetchLlmModels()}
              disabled={fetchingModels || !llm.base_url}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-bg-content text-secondary hover:text-primary border border-border-subtle transition-colors disabled:opacity-40"
            >
              <RefreshCw size={14} className={fetchingModels ? "animate-spin" : ""} />
              {fetchingModels ? "Fetching…" : "Fetch Models"}
            </button>
          </div>
        </div>

        {llm.provider !== "ollama" && (
          <div>
            <label className={labelCls}>API Key</label>
            <input
              type="password"
              value={llm.api_key}
              onChange={(e) => setLlm((c) => ({ ...c, api_key: e.target.value }))}
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
            <select value={llm.model} onChange={(e) => setLlm((c) => ({ ...c, model: e.target.value }))} className={inputCls}>
              <option value="">Select a model…</option>
              {models.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          ) : fetchingModels ? (
            <div className="px-3 py-2 rounded-md text-sm bg-bg-content text-muted border border-border-subtle">
              Fetching models…
            </div>
          ) : (
            <input
              type="text"
              value={llm.model}
              onChange={(e) => setLlm((c) => ({ ...c, model: e.target.value }))}
              placeholder={llm.provider === "ollama" ? "qwen3:8b" : "gpt-4o"}
              className={inputCls}
            />
          )}
          <p className="mt-1 text-xs text-muted">
            Click "Fetch Models" to list available models, or type a name directly.
          </p>
        </div>

        <div>
          <label className={labelCls}>Request Timeout (seconds)</label>
          <input
            type="number"
            min={30}
            step={30}
            value={llm.request_timeout}
            onChange={(e) => setLlm((c) => ({ ...c, request_timeout: Math.max(30, Number(e.target.value)) }))}
            className="w-32 rounded-md border border-border-subtle bg-bg-content px-3 py-1.5 text-sm text-primary focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <p className="mt-1 text-xs text-muted">How long to wait for LLM responses.</p>
        </div>
      </div>
    );
  }

  function renderFinish() {
    return (
      <div className="flex flex-col items-center text-center py-8 space-y-4">
        <h2 className="text-xl font-semibold text-primary">You're all set!</h2>
        <p className="text-secondary text-sm leading-relaxed max-w-sm">
          Your workspace is ready. You can always adjust these settings later.
        </p>
      </div>
    );
  }

  // -- Step indicator -------------------------------------------------------

  function renderStepIndicator() {
    return (
      <div className="flex items-center justify-center gap-1.5 py-3">
        {STEP_LABELS.map((label, i) => (
          <div key={label} className="flex items-center gap-1.5">
            <div
              className={`w-2 h-2 rounded-full transition-colors ${
                i === step
                  ? "bg-accent"
                  : i < step
                    ? "bg-accent/40"
                    : "bg-border-subtle"
              }`}
              title={label}
            />
            {i < TOTAL_STEPS - 1 && (
              <div className={`w-6 h-px ${i < step ? "bg-accent/40" : "bg-border-subtle"}`} />
            )}
          </div>
        ))}
      </div>
    );
  }

  // -- Layout ---------------------------------------------------------------

  const stepContent = [renderWelcome, renderProfile, renderBusiness, renderInvoicing, renderLLM, renderFinish][step];
  const showNav = step > 0;

  const content = (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle shrink-0">
        <div className="flex-1">
          {step > 0 && (
            <h2 className="text-base font-semibold">{STEP_LABELS[step]}</h2>
          )}
        </div>
        {renderStepIndicator()}
        <div className="flex-1 flex justify-end">
          {overlay && (
            <button onClick={onClose} className="text-muted hover:text-primary transition-colors" disabled={loading}>
              <X size={18} />
            </button>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-5 py-4">
        {stepContent()}
      </div>

      {/* Footer navigation */}
      {showNav && (
        <div className="flex items-center justify-between px-5 py-3 border-t border-border-subtle shrink-0">
          <button
            onClick={back}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-1.5 text-sm rounded-md text-secondary hover:bg-bg-hover transition-colors"
          >
            <ChevronLeft size={14} />
            Back
          </button>

          <div className="flex items-center gap-2">
            {isSkippable && (
              <button
                onClick={skip}
                disabled={loading}
                className="flex items-center gap-1.5 px-4 py-1.5 text-sm rounded-md text-secondary hover:bg-bg-hover transition-colors"
              >
                Skip
                <SkipForward size={14} />
              </button>
            )}
            <button
              onClick={next}
              disabled={loading || !canAdvance()}
              className="flex items-center gap-1.5 px-4 py-1.5 text-sm rounded-md bg-accent text-white font-medium hover:bg-accent/90 transition-colors disabled:opacity-40"
            >
              {step === TOTAL_STEPS - 1 ? (
                <>
                  {loading ? "Creating…" : "Start using Tuttle"}
                  <Check size={14} />
                </>
              ) : (
                <>
                  Next
                  <ChevronRight size={14} />
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );

  if (overlay) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <div className="bg-bg-sidebar rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[85vh] flex flex-col overflow-hidden">
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-bg-content">
      <div className="bg-bg-sidebar rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[85vh] flex flex-col overflow-hidden">
        {content}
      </div>
    </div>
  );
}
