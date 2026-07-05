import { useEffect, useState, useRef, useCallback } from "react";
import {
  Users, Plus, Trash2, Save, X, Mail, Building2, MapPin,
  FileUp, Sparkles, Check, CheckCheck, Loader2, Tag, UserPlus,
} from "lucide-react";
import { rpc } from "../../api/rpc";
import { str, num, entity as subEntity, fullName, initials, displayName } from "../../api/entity";
import { Toolbar, ToolbarButtonPrimary, ToolbarButtonSecondary, ListDetailLayout, LIST_ROW_PADDING } from "../shared/ToolbarButtons";
import { EditableClientContactRole } from "../shared/EditableClientContactRole";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import type { Entity } from "../../api/types";

type Mode = "view" | "edit" | "create" | "import";

export function ContactsView() {
  const [contacts, setContacts] = useState<Entity[]>([]);
  const [clients, setClients] = useState<Record<string, Entity>>({});
  const [selected, setSelected] = useState<Entity | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState<Mode>("view");
  const [parsedContacts, setParsedContacts] = useState<ParsedContact[]>([]);
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const selectedIdRef = useRef<number | null>(null);

  useEffect(() => { selectedIdRef.current = selected?.id ?? null; }, [selected]);
  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    const [res, clRes] = await Promise.all([
      rpc<Entity[]>("contacts.get_all"),
      rpc<Record<string, Entity>>("contacts.get_all_clients"),
    ]);
    if (res.ok && res.data) {
      setContacts(res.data);
      const currentId = selectedIdRef.current;
      if (currentId != null) {
        const updated = res.data.find((c) => c.id === currentId);
        setSelected(updated || null);
      }
    }
    if (clRes.ok && clRes.data) setClients(clRes.data);
    setLoading(false);
  }

  function startCreate() {
    setSelected(null);
    setMode("create");
  }

  function startImport() {
    setSelected(null);
    setParsedContacts([]);
    setParseError(null);
    setMode("import");
  }

  function selectContact(c: Entity) {
    setSelected(c);
    setMode("view");
  }

  async function handleSave(data: ContactFormData) {
    const contact: Record<string, unknown> = {
      first_name: data.firstName,
      last_name: data.lastName,
      email: data.email,
      address: {
        street: data.street,
        number: data.number,
        city: data.city,
        postal_code: data.postalCode,
        country: data.country,
      },
    };
    if (mode === "edit" && selected) {
      contact.id = selected.id;
      const addr = subEntity(selected, "address");
      if (addr) contact.address = { ...contact.address as object, id: addr.id };
    }
    const res = await rpc("contacts.save", { contact });
    if (res.ok) {
      setMode("view");
      await load();
    }
  }

  async function handleDelete(id: number) {
    const res = await rpc("contacts.delete", { id });
    if (res.ok) {
      setSelected(null);
      setMode("view");
      await load();
    }
  }

  async function handleFileImport(file: File) {
    setParsing(true);
    setParseError(null);
    setParsedContacts([]);
    try {
      const buffer = await file.arrayBuffer();
      const base64 = btoa(
        new Uint8Array(buffer).reduce((data, byte) => data + String.fromCharCode(byte), "")
      );
      const res = await rpc<ParsedContact[]>("llm.parse_document", {
        file_base64: base64,
        file_name: file.name,
        entity_type: "contact",
      });
      if (res.ok && res.data) {
        setParsedContacts(res.data);
        if (res.data.length === 0) {
          setParseError("No contacts found in the document.");
        }
      } else {
        setParseError(res.error || "Failed to parse document.");
      }
    } catch (err) {
      setParseError(String(err));
    }
    setParsing(false);
  }

  async function acceptContact(parsed: ParsedContact) {
    const res = await rpc("contacts.save", { contact: parsed });
    if (res.ok) {
      setParsedContacts((prev) => prev.filter((c) => c !== parsed));
      await load();
    } else {
      setParseError(res.error || "Failed to save contact.");
    }
  }

  async function acceptAll() {
    for (const c of parsedContacts) {
      await rpc("contacts.save", { contact: c });
    }
    setParsedContacts([]);
    await load();
    setMode("view");
  }

  function discardContact(parsed: ParsedContact) {
    setParsedContacts((prev) => prev.filter((c) => c !== parsed));
  }

  function updateParsedContact(index: number, updated: ParsedContact) {
    setParsedContacts((prev) => prev.map((c, i) => i === index ? updated : c));
  }

  const sorted = [...contacts].sort((a, b) => {
    const aLast = str(a, "last_name") || str(a, "company") || str(a, "name") || "";
    const bLast = str(b, "last_name") || str(b, "company") || str(b, "name") || "";
    return aLast.localeCompare(bLast);
  });

  const filtered = sorted.filter((c) => {
    if (!search) return true;
    const q = search.toLowerCase();
    const name = displayName(c).toLowerCase();
    const email = str(c, "email").toLowerCase();
    const company = str(c, "company").toLowerCase();
    return name.includes(q) || email.includes(q) || company.includes(q);
  });

  if (loading && contacts.length === 0)
    return <div className="flex items-center justify-center h-full text-secondary">Loading contacts…</div>;

  return (
    <div className="flex flex-col h-full">
      <Toolbar title="Contacts"
        actions={<>
          <ToolbarButtonPrimary icon={<Plus size={13} />} label="New" onClick={startCreate} />
          <ToolbarButtonSecondary icon={<FileUp size={13} />} label="Import" onClick={startImport} />
        </>}
        search={{ value: search, onChange: setSearch }}
      />

      {contacts.length === 0 && mode === "view" ? (
        <EmptyStateIntro icon={Users} description="Contacts are people in your professional network — colleagues at client companies, or other collaborators." />
      ) : (
      <ListDetailLayout
        footer={<>{filtered.length} contact{filtered.length !== 1 ? "s" : ""}</>}
        list={filtered.length === 0
          ? <div className="p-4 text-sm text-center text-tertiary">No matches.</div>
          : filtered.map((c) => (
            <ContactRow key={c.id} contact={c}
              isSelected={selected?.id === c.id && mode !== "create" && mode !== "import"}
              onSelect={() => selectContact(c)} />
          ))
        }
        detail={mode === "import" ? (
            <DocumentImportPanel
              parsing={parsing}
              parseError={parseError}
              parsedContacts={parsedContacts}
              onFileSelected={handleFileImport}
              onAccept={acceptContact}
              onAcceptAll={acceptAll}
              onDiscard={discardContact}
              onUpdate={updateParsedContact}
              onClose={() => setMode("view")}
            />
          ) : mode === "create" ? (
            <ContactForm clients={clients} onSave={handleSave} onCancel={() => { setMode("view"); }} />
          ) : mode === "edit" && selected ? (
            <ContactForm contact={selected} clients={clients} onSave={handleSave}
              onCancel={() => setMode("view")} />
          ) : selected ? (
            <ContactDetail contact={selected} clients={clients}
              onEdit={() => setMode("edit")}
              onDelete={() => handleDelete(selected.id)} />
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-tertiary">
              <Users size={36} strokeWidth={1.2} />
              <span className="text-sm">Select a contact</span>
            </div>
          )
        }
      />
      )}
    </div>
  );
}

/* ---------- List row ---------- */

function ContactRow({ contact, isSelected, onSelect }: {
  contact: Entity; isSelected: boolean; onSelect: () => void;
}) {
  const name = displayName(contact);
  const email = str(contact, "email");
  const company = str(contact, "company");
  const ini = initials(contact);
  const subtitle = company || email;

  return (
    <button onClick={onSelect}
      className={`w-full text-left ${LIST_ROW_PADDING} border-b border-border-subtle transition-colors flex items-center gap-3
        ${isSelected ? "bg-bg-selected" : "hover:bg-bg-hover"}`}>
      <div className="w-9 h-9 rounded-full bg-bg-card flex items-center justify-center text-sm font-semibold text-secondary shrink-0">
        {ini}
      </div>
      <div className="min-w-0">
        <div className="text-sm font-medium truncate">{name}</div>
        {subtitle && (
          <div className="flex items-center gap-1.5 text-xs text-tertiary truncate">
            <span>{subtitle}</span>
          </div>
        )}
      </div>
    </button>
  );
}

/* ---------- Detail view ---------- */

function ContactDetail({ contact, clients, onEdit, onDelete }: {
  contact: Entity; clients: Record<string, Entity>;
  onEdit: () => void; onDelete: () => void;
}) {
  const name = displayName(contact);
  const ini = initials(contact);
  const email = str(contact, "email");
  const addr = subEntity(contact, "address");

  const addrParts = addr ? [
    [str(addr, "street"), str(addr, "number")].filter(Boolean).join(" "),
    [str(addr, "postal_code"), str(addr, "city")].filter(Boolean).join(" "),
    str(addr, "country"),
  ].filter(Boolean) : [];

  const [assocs, setAssocs] = useState<Entity[]>([]);
  const [addingClient, setAddingClient] = useState(false);
  const [newClientId, setNewClientId] = useState<number | null>(null);
  const [newRole, setNewRole] = useState("");

  useEffect(() => { loadAssocs(); }, [contact.id]);

  async function loadAssocs() {
    const res = await rpc<Entity[]>("contacts.get_clients_for_contact", { contact_id: contact.id });
    if (res.ok && res.data) setAssocs(res.data);
    else setAssocs([]);
  }

  async function addClient() {
    if (!newClientId) return;
    await rpc("contacts.add_client_to_contact", {
      contact_id: contact.id, client_id: newClientId, role: newRole || null,
    });
    setNewClientId(null);
    setNewRole("");
    setAddingClient(false);
    await loadAssocs();
  }

  async function removeAssoc(id: number) {
    await rpc("contacts.remove_client_contact", { association_id: id });
    await loadAssocs();
  }

  const clientList = Object.values(clients);
  const linkedClientIds = new Set(assocs.map((a) => num(a, "client_id")));

  return (
    <div className="p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="w-14 h-14 rounded-full bg-bg-card flex items-center justify-center text-xl font-semibold text-secondary">
          {ini}
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-semibold">{name}</h1>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button onClick={onEdit}
            className="px-3 py-1.5 rounded text-sm font-medium bg-bg-card text-secondary hover:text-primary border border-border-subtle transition-colors">
            Edit
          </button>
          <button onClick={onDelete}
            className="p-1.5 rounded text-secondary hover:text-red-400 border border-border-subtle transition-colors"
            title="Delete contact">
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Info cards */}
      <div className="space-y-3">
        {email && (
          <InfoRow icon={<Mail size={14} />} label="Email" value={email} />
        )}
        {addrParts.length > 0 && (
          <div className="flex items-start gap-3 p-3 rounded-lg bg-bg-card border border-border-subtle">
            <span className="text-tertiary mt-0.5"><MapPin size={14} /></span>
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-tertiary mb-1">Address</div>
              {addrParts.map((line, i) => (
                <div key={i} className="text-sm">{line}</div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Companies (many-to-many via ClientContact) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-xs font-semibold uppercase tracking-wider text-secondary">Companies</div>
          {!addingClient && (
            <button onClick={() => setAddingClient(true)}
              className="flex items-center gap-1 text-xs text-secondary hover:text-primary transition-colors">
              <UserPlus size={13} /> Add
            </button>
          )}
        </div>

        {assocs.length === 0 && !addingClient && (
          <div className="text-sm text-tertiary">No companies linked yet.</div>
        )}

        {assocs.map((a) => {
          const clientName = str(a, "client_name");
          const role = str(a, "role");
          return (
            <div key={a.id} className="flex items-center gap-3 p-3 rounded-lg bg-bg-card border border-border-subtle group">
              <span className="text-tertiary"><Building2 size={14} /></span>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{clientName || `Client #${num(a, "client_id")}`}</div>
                <EditableClientContactRole associationId={a.id} role={role} onUpdated={loadAssocs}
                  updateMethod="contacts.update_client_contact_role" />
              </div>
              <button onClick={() => removeAssoc(a.id)}
                className="opacity-0 group-hover:opacity-100 p-1 rounded text-secondary hover:text-red-400 transition-all"
                title="Remove company">
                <X size={14} />
              </button>
            </div>
          );
        })}

        {addingClient && (
          <div className="p-3 rounded-lg bg-bg-card border border-border-subtle space-y-2">
            <select value={newClientId ?? ""} onChange={(e) => setNewClientId(e.target.value ? Number(e.target.value) : null)}
              className="w-full px-3 py-2 rounded-md text-sm bg-bg-sidebar text-primary border border-border-subtle outline-none focus:border-accent transition-colors">
              <option value="">— Select client —</option>
              {clientList.filter((c) => !linkedClientIds.has(c.id)).map((c) => (
                <option key={c.id} value={c.id}>{str(c, "name")}</option>
              ))}
            </select>
            <input type="text" placeholder="Role (optional), e.g. project lead, accountant" value={newRole}
              onChange={(e) => setNewRole(e.target.value)}
              className="w-full px-3 py-2 rounded-md text-sm bg-bg-sidebar text-primary border border-border-subtle outline-none focus:border-accent transition-colors placeholder:text-muted" />
            <div className="flex items-center gap-2 justify-end">
              <button onClick={() => { setAddingClient(false); setNewClientId(null); setNewRole(""); }}
                className="px-2.5 py-1 rounded text-xs text-secondary hover:text-primary transition-colors">Cancel</button>
              <button onClick={addClient} disabled={!newClientId}
                className="px-2.5 py-1 rounded text-xs font-medium text-primary bg-accent/20 hover:bg-accent/30 border border-accent/30 transition-colors disabled:opacity-40">
                Add
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-bg-card border border-border-subtle">
      <span className="text-tertiary">{icon}</span>
      <div>
        <div className="text-xs font-semibold uppercase tracking-wider text-tertiary">{label}</div>
        <div className="text-sm">{value}</div>
      </div>
    </div>
  );
}

/* ---------- Create/Edit form ---------- */

interface ContactFormData {
  firstName: string;
  lastName: string;
  email: string;
  street: string;
  number: string;
  city: string;
  postalCode: string;
  country: string;
}

function formDataFromEntity(contact?: Entity): ContactFormData {
  if (!contact) return { firstName: "", lastName: "", email: "", street: "", number: "", city: "", postalCode: "", country: "" };
  const addr = subEntity(contact, "address");
  return {
    firstName: str(contact, "first_name"),
    lastName: str(contact, "last_name"),
    email: str(contact, "email"),
    street: addr ? str(addr, "street") : "",
    number: addr ? str(addr, "number") : "",
    city: addr ? str(addr, "city") : "",
    postalCode: addr ? str(addr, "postal_code") : "",
    country: addr ? str(addr, "country") : "",
  };
}

function ContactForm({ contact, clients, onSave, onCancel }: {
  contact?: Entity; clients: Record<string, Entity>;
  onSave: (data: ContactFormData) => void; onCancel: () => void;
}) {
  const [form, setForm] = useState<ContactFormData>(() => formDataFromEntity(contact));
  const [saving, setSaving] = useState(false);
  const isNew = !contact;

  const [assocs, setAssocs] = useState<Entity[]>([]);
  const [addingClient, setAddingClient] = useState(false);
  const [newClientId, setNewClientId] = useState<number | null>(null);
  const [newRole, setNewRole] = useState("");

  useEffect(() => { if (contact) loadAssocs(); }, [contact?.id]);

  async function loadAssocs() {
    if (!contact) return;
    const res = await rpc<Entity[]>("contacts.get_clients_for_contact", { contact_id: contact.id });
    if (res.ok && res.data) setAssocs(res.data);
  }

  async function addClient() {
    if (!newClientId || !contact) return;
    await rpc("contacts.add_client_to_contact", {
      contact_id: contact.id, client_id: newClientId, role: newRole || null,
    });
    setNewClientId(null);
    setNewRole("");
    setAddingClient(false);
    await loadAssocs();
  }

  async function removeAssoc(id: number) {
    await rpc("contacts.remove_client_contact", { association_id: id });
    await loadAssocs();
  }

  function update(field: keyof ContactFormData, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    await onSave(form);
    setSaving(false);
  }

  const hasName = form.firstName.trim() || form.lastName.trim();
  const clientList = Object.values(clients);
  const linkedClientIds = new Set(assocs.map((a) => num(a, "client_id")));

  return (
    <form onSubmit={handleSubmit} className="p-5 space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{isNew ? "New Contact" : "Edit Contact"}</h2>
        <div className="flex items-center gap-2">
          <button type="button" onClick={onCancel}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
            <X size={14} /> Cancel
          </button>
          <button type="submit" disabled={saving || !hasName}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium text-primary hover:bg-bg-hover transition-colors disabled:opacity-40">
            <Save size={14} /> {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>

      <Section title="Name">
        <div className="grid grid-cols-2 gap-3">
          <FormField label="First Name" value={form.firstName} onChange={(v) => update("firstName", v)} autoFocus />
          <FormField label="Last Name" value={form.lastName} onChange={(v) => update("lastName", v)} />
        </div>
      </Section>

      <Section title="Details">
        <FormField label="Email" value={form.email} onChange={(v) => update("email", v)} type="email" />
      </Section>

      <Section title="Address">
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Street" value={form.street} onChange={(v) => update("street", v)} />
          <FormField label="Number" value={form.number} onChange={(v) => update("number", v)} />
          <FormField label="City" value={form.city} onChange={(v) => update("city", v)} />
          <FormField label="Postal Code" value={form.postalCode} onChange={(v) => update("postalCode", v)} />
          <FormField label="Country" value={form.country} onChange={(v) => update("country", v)} />
        </div>
      </Section>

      {/* Companies — live-managed via RPC (only for existing contacts) */}
      {contact && (
        <Section title="Companies">
          {assocs.length === 0 && !addingClient && (
            <div className="text-sm text-tertiary">No companies linked yet.</div>
          )}
          <div className="space-y-2">
            {assocs.map((a) => {
              const clientName = str(a, "client_name");
              const role = str(a, "role");
              return (
                <div key={a.id} className="flex items-center gap-3 p-3 rounded-lg bg-bg-card border border-border-subtle group">
                  <span className="text-tertiary"><Building2 size={14} /></span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{clientName || `Client #${num(a, "client_id")}`}</div>
                    <EditableClientContactRole associationId={a.id} role={role} onUpdated={loadAssocs}
                  updateMethod="contacts.update_client_contact_role" />
                  </div>
                  <button type="button" onClick={() => removeAssoc(a.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded text-secondary hover:text-red-400 transition-all"
                    title="Remove company">
                    <X size={14} />
                  </button>
                </div>
              );
            })}
          </div>
          {addingClient ? (
            <div className="p-3 rounded-lg bg-bg-card border border-border-subtle space-y-2 mt-2">
              <select value={newClientId ?? ""} onChange={(e) => setNewClientId(e.target.value ? Number(e.target.value) : null)}
                className="w-full px-3 py-2 rounded-md text-sm bg-bg-sidebar text-primary border border-border-subtle outline-none focus:border-accent transition-colors">
                <option value="">— Select client —</option>
                {clientList.filter((c) => !linkedClientIds.has(c.id)).map((c) => (
                  <option key={c.id} value={c.id}>{str(c, "name")}</option>
                ))}
              </select>
              <input type="text" placeholder="Role (optional), e.g. project lead, accountant" value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                className="w-full px-3 py-2 rounded-md text-sm bg-bg-sidebar text-primary border border-border-subtle outline-none focus:border-accent transition-colors placeholder:text-muted" />
              <div className="flex items-center gap-2 justify-end">
                <button type="button" onClick={() => { setAddingClient(false); setNewClientId(null); setNewRole(""); }}
                  className="px-2.5 py-1 rounded text-xs text-secondary hover:text-primary transition-colors">Cancel</button>
                <button type="button" onClick={addClient} disabled={!newClientId}
                  className="px-2.5 py-1 rounded text-xs font-medium text-primary bg-accent/20 hover:bg-accent/30 border border-accent/30 transition-colors disabled:opacity-40">
                  Add
                </button>
              </div>
            </div>
          ) : (
            <button type="button" onClick={() => setAddingClient(true)}
              className="flex items-center gap-1 text-xs text-secondary hover:text-primary transition-colors mt-2">
              <UserPlus size={13} /> Add company
            </button>
          )}
        </Section>
      )}
    </form>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-wider text-secondary mb-2">{title}</div>
      {children}
    </div>
  );
}

function FormField({ label, value, onChange, type = "text", autoFocus }: {
  label: string; value: string; onChange: (v: string) => void; type?: string; autoFocus?: boolean;
}) {
  return (
    <div>
      <label className="block text-xs text-tertiary mb-1">{label}</label>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} autoFocus={autoFocus}
        className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none
          focus:border-accent transition-colors placeholder:text-muted" />
    </div>
  );
}

/* ---------- AI Document Import ---------- */

interface ParsedContact {
  first_name: string;
  last_name: string;
  company: string;
  email: string;
  address: {
    street: string;
    number: string;
    city: string;
    postal_code: string;
    country: string;
  };
}

const ACCEPT_EXTENSIONS = [".pdf", ".txt", ".md", ".text"];

function DocumentImportPanel({ parsing, parseError, parsedContacts, onFileSelected, onAccept, onAcceptAll, onDiscard, onUpdate, onClose }: {
  parsing: boolean;
  parseError: string | null;
  parsedContacts: ParsedContact[];
  onFileSelected: (file: File) => void;
  onAccept: (c: ParsedContact) => void;
  onAcceptAll: () => void;
  onDiscard: (c: ParsedContact) => void;
  onUpdate: (index: number, c: ParsedContact) => void;
  onClose: () => void;
}) {
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && isAcceptedFile(file.name)) {
      onFileSelected(file);
    }
  }, [onFileSelected]);

  function isAcceptedFile(name: string) {
    const lower = name.toLowerCase();
    return ACCEPT_EXTENSIONS.some((ext) => lower.endsWith(ext));
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) onFileSelected(file);
  }

  const showDropzone = parsedContacts.length === 0 && !parsing;

  return (
    <div className="p-5 space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={18} className="text-fuchsia-400" />
          <h2 className="text-lg font-semibold">Import from Document</h2>
        </div>
        <button onClick={onClose}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
          <X size={14} /> Close
        </button>
      </div>

      {showDropzone && (
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
            <p className="text-xs text-tertiary mt-1">PDF, TXT, or Markdown — AI will extract contacts</p>
          </div>
          <input ref={fileInputRef} type="file" className="hidden"
            accept=".pdf,.txt,.md,.text"
            onChange={handleFileInput} />
        </div>
      )}

      {parsing && (
        <div className="flex items-center justify-center gap-3 py-10">
          <Loader2 size={20} className="animate-spin text-fuchsia-400" />
          <span className="text-sm text-secondary">Parsing document with AI…</span>
        </div>
      )}

      {parseError && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">
          {parseError}
        </div>
      )}

      {parsedContacts.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-secondary">
              <span className="font-medium text-fuchsia-400">{parsedContacts.length}</span> contact{parsedContacts.length !== 1 ? "s" : ""} found
            </p>
            <button onClick={onAcceptAll}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium text-fuchsia-400 hover:bg-fuchsia-500/10 border border-fuchsia-400/30 transition-colors">
              <CheckCheck size={14} /> Accept All
            </button>
          </div>
          {parsedContacts.map((c, i) => (
            <ParsedContactCard key={i} contact={c}
              onAccept={() => onAccept(c)}
              onDiscard={() => onDiscard(c)}
              onUpdate={(updated) => onUpdate(i, updated)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------- Parsed Contact Approval Card ---------- */

function contactIsValid(c: ParsedContact): { valid: boolean; missing: string[] } {
  const missing: string[] = [];
  if (!c.first_name.trim()) missing.push("First Name");
  if (!c.last_name.trim()) missing.push("Last Name");
  const addr = c.address;
  const hasAddress = !!(addr.street || addr.number || addr.city || addr.postal_code || addr.country);
  if (!hasAddress) missing.push("Address (at least one field)");
  return { valid: missing.length === 0, missing };
}

function ParsedContactCard({ contact, onAccept, onDiscard, onUpdate }: {
  contact: ParsedContact;
  onAccept: () => void;
  onDiscard: () => void;
  onUpdate: (c: ParsedContact) => void;
}) {
  function updateField(field: keyof ParsedContact, value: string) {
    onUpdate({ ...contact, [field]: value });
  }

  function updateAddr(field: string, value: string) {
    onUpdate({ ...contact, address: { ...contact.address, [field]: value } });
  }

  const { valid, missing } = contactIsValid(contact);
  const name = [contact.first_name, contact.last_name].filter(Boolean).join(" ") || contact.company || "Unknown";

  return (
    <div className="rounded-xl border-2 border-fuchsia-400/40 bg-fuchsia-500/5 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={14} className="text-fuchsia-400" />
          <span className="text-sm font-semibold">{name}</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={onDiscard}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs text-secondary hover:text-red-400 hover:bg-red-500/10 transition-colors"
            title="Discard">
            <Trash2 size={12} /> Discard
          </button>
          <button onClick={valid ? onAccept : undefined}
            disabled={!valid}
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium border transition-colors ${
              valid
                ? "text-fuchsia-400 hover:bg-fuchsia-500/10 border-fuchsia-400/30"
                : "text-muted border-border-subtle cursor-not-allowed opacity-50"
            }`}
            title={valid ? "Accept and save" : `Missing: ${missing.join(", ")}`}>
            <Check size={12} /> Accept
          </button>
        </div>
      </div>

      {!valid && (
        <p className="text-xs text-amber-400">
          Required: {missing.join(", ")}
        </p>
      )}

      <div className="grid grid-cols-2 gap-2">
        <AiField label="First Name" value={contact.first_name} onChange={(v) => updateField("first_name", v)} required missing={!contact.first_name.trim()} />
        <AiField label="Last Name" value={contact.last_name} onChange={(v) => updateField("last_name", v)} required missing={!contact.last_name.trim()} />
        <AiField label="Company" value={contact.company} onChange={(v) => updateField("company", v)} />
        <AiField label="Email" value={contact.email} onChange={(v) => updateField("email", v)} />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <AiField label="Street" value={contact.address.street} onChange={(v) => updateAddr("street", v)} addressRequired={!contactHasAddress(contact)} />
        <AiField label="Number" value={contact.address.number} onChange={(v) => updateAddr("number", v)} addressRequired={!contactHasAddress(contact)} />
        <AiField label="City" value={contact.address.city} onChange={(v) => updateAddr("city", v)} addressRequired={!contactHasAddress(contact)} />
        <AiField label="Postal Code" value={contact.address.postal_code} onChange={(v) => updateAddr("postal_code", v)} addressRequired={!contactHasAddress(contact)} />
        <AiField label="Country" value={contact.address.country} onChange={(v) => updateAddr("country", v)} addressRequired={!contactHasAddress(contact)} />
      </div>
    </div>
  );
}

function contactHasAddress(c: ParsedContact): boolean {
  const a = c.address;
  return !!(a.street || a.number || a.city || a.postal_code || a.country);
}

function AiField({ label, value, onChange, required, missing, addressRequired }: {
  label: string; value: string; onChange: (v: string) => void;
  required?: boolean; missing?: boolean; addressRequired?: boolean;
}) {
  const showWarning = (required && missing) || addressRequired;
  return (
    <div>
      <label className="block text-xs text-fuchsia-300/70 mb-0.5">
        {label}{required && <span className="text-amber-400 ml-0.5">*</span>}
      </label>
      <input type="text" value={value} onChange={(e) => onChange(e.target.value)}
        className={`w-full px-2.5 py-1.5 rounded-md text-sm bg-bg-card text-primary outline-none
          focus:border-fuchsia-400 transition-colors placeholder:text-muted border ${
          showWarning ? "border-amber-400/60" : "border-fuchsia-400/30"
        }`} />
    </div>
  );
}
