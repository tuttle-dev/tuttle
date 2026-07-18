import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { rpc } from "../../api/rpc";

type Props = {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: UserFormData) => void;
  loading?: boolean;
};

export type UserFormData = {
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
  invoice_number_scheme: string;
};

const EMPTY: UserFormData = {
  name: "", subtitle: "", email: "", phone: "", website: "",
  street: "", street_num: "", postal_code: "", city: "", country: "",
  vat_number: "", invoice_number_scheme: "daily",
};

const SCHEME_EXAMPLES: Record<string, string> = {
  daily: "2025-05-17-01",
  yearly: "2025-01",
  plain: "01",
};

export function UserRegistrationDialog({ open, onClose, onSubmit, loading }: Props) {
  const [form, setForm] = useState<UserFormData>({ ...EMPTY });
  const [schemes, setSchemes] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open) {
      rpc<Record<string, string>>("invoicing.available_number_schemes").then((res) => {
        if (res.ok && res.data) setSchemes(res.data);
      });
    }
  }, [open]);

  if (!open) return null;

  function set<K extends keyof UserFormData>(key: K) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) return;
    onSubmit(form);
  }

  const inputCls =
    "w-full rounded-md border border-border-subtle bg-bg-content px-3 py-1.5 text-sm text-primary placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent";
  const labelCls = "block text-xs font-medium text-secondary mb-1";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-bg-sidebar rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[85vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle shrink-0">
          <h2 className="text-base font-semibold">Create new user</h2>
          <button onClick={onClose} className="text-muted hover:text-primary transition-colors" disabled={loading}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-5 py-4 space-y-4 flex-1 overflow-y-auto">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className={labelCls}>Full name *</label>
              <input className={inputCls} value={form.name} onChange={set("name")} placeholder="Jane Doe" autoFocus required />
            </div>
            <div className="col-span-2">
              <label className={labelCls}>Subtitle / profession</label>
              <input className={inputCls} value={form.subtitle} onChange={set("subtitle")} placeholder="Freelance consultant" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Email</label>
              <input className={inputCls} type="email" value={form.email} onChange={set("email")} placeholder="mail@example.com" />
            </div>
            <div>
              <label className={labelCls}>Phone</label>
              <input className={inputCls} value={form.phone} onChange={set("phone")} placeholder="+49 …" />
            </div>
          </div>

          <div>
            <label className={labelCls}>Website</label>
            <input className={inputCls} value={form.website} onChange={set("website")} placeholder="https://…" />
          </div>

          <fieldset className="border border-border-subtle rounded-lg px-4 pb-3 pt-2">
            <legend className="text-xs font-medium text-secondary px-1">Address</legend>
            <div className="grid grid-cols-4 gap-3 mt-1">
              <div className="col-span-3">
                <label className={labelCls}>Street</label>
                <input className={inputCls} value={form.street} onChange={set("street")} />
              </div>
              <div>
                <label className={labelCls}>Nr.</label>
                <input className={inputCls} value={form.street_num} onChange={set("street_num")} />
              </div>
              <div>
                <label className={labelCls}>Postal code</label>
                <input className={inputCls} value={form.postal_code} onChange={set("postal_code")} />
              </div>
              <div className="col-span-2">
                <label className={labelCls}>City</label>
                <input className={inputCls} value={form.city} onChange={set("city")} />
              </div>
              <div>
                <label className={labelCls}>Country</label>
                <input className={inputCls} value={form.country} onChange={set("country")} />
              </div>
            </div>
          </fieldset>

          <div>
            <label className={labelCls}>VAT number</label>
            <input className={inputCls} value={form.vat_number} onChange={set("vat_number")} />
          </div>

          <fieldset className="border border-border-subtle rounded-lg px-4 pb-3 pt-2">
            <legend className="text-xs font-medium text-secondary px-1">Invoice numbering</legend>
            <div className="space-y-2 mt-1">
              {Object.entries(schemes).map(([key, label]) => (
                <label key={key} className="flex items-center gap-2.5 cursor-pointer group">
                  <input
                    type="radio"
                    name="invoice_number_scheme"
                    value={key}
                    checked={form.invoice_number_scheme === key}
                    onChange={set("invoice_number_scheme")}
                    className="accent-accent"
                  />
                  <div>
                    <span className="text-sm text-primary group-hover:text-accent transition-colors">{label}</span>
                    <span className="ml-2 text-xs text-muted font-mono">{SCHEME_EXAMPLES[key]}</span>
                  </div>
                </label>
              ))}
            </div>
          </fieldset>
        </form>

        <div className="flex justify-end gap-2 px-5 py-3 border-t border-border-subtle shrink-0">
          <button type="button" onClick={onClose} disabled={loading}
            className="px-4 py-1.5 text-sm rounded-md text-secondary hover:bg-bg-hover transition-colors">
            Cancel
          </button>
          <button onClick={handleSubmit} disabled={loading || !form.name.trim()}
            className="px-4 py-1.5 text-sm rounded-md bg-accent text-white font-medium hover:bg-accent/90 transition-colors disabled:opacity-40">
            {loading ? "Creating…" : "Create user"}
          </button>
        </div>
      </div>
    </div>
  );
}
