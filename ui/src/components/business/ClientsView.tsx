import { useEffect, useState, useRef } from "react";
import {
  Building2, Plus, Trash2, X, Users, FileUp, Sparkles, Check, UserPlus, Save,
} from "lucide-react";
import { rpc } from "../../api/rpc";
import { str, num, entity as subEntity, displayName, fullName, initials } from "../../api/entity";
import { Toolbar, ToolbarButtonPrimary, ToolbarButtonSecondary, ListDetailLayout, LIST_ROW_PADDING } from "../shared/ToolbarButtons";
import { EditableClientContactRole } from "../shared/EditableClientContactRole";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import { DetailHeader, DetailAction, DetailDeleteAction, DetailSubmit, DETAIL_PANE } from "../shared/DetailHeader";
import { DetailFields, DetailField } from "../shared/DetailFields";
import { LoadError, LoadingState } from "../shared/LoadStates";
import { Section } from "../shared/Section";
import { DocumentImportPanel } from "../shared/DocumentImportPanel";
import { useFieldRequirements } from "../../hooks/useFieldRequirements";
import { useAutoSelect } from "../../hooks/useAutoSelect";
import type { Entity } from "../../api/types";

type Mode = "view" | "edit" | "create" | "import";

export function ClientsView() {
  const [clients, setClients] = useState<Entity[]>([]);
  const [contacts, setContacts] = useState<Record<string, Entity>>({});
  const [selected, setSelected] = useState<Entity | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState<Mode>("view");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [parsedClients, setParsedClients] = useState<ParsedClient[]>([]);
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const selectedIdRef = useRef<number | null>(null);

  useEffect(() => { selectedIdRef.current = selected?.id ?? null; }, [selected]);
  useEffect(() => { load(); }, []);

  async function load(selectId?: number) {
    setLoading(true);
    setLoadFailed(false);
    const [res, cRes] = await Promise.all([
      rpc<Entity[]>("clients.get_all"),
      rpc<Record<string, Entity>>("clients.get_all_contacts"),
    ]);
    setLoadFailed(!res.ok || !cRes.ok);
    if (res.ok && res.data) {
      setClients(res.data);
      const currentId = selectId ?? selectedIdRef.current;
      if (currentId != null) {
        const updated = res.data.find((c) => c.id === currentId);
        setSelected(updated || null);
      }
    }
    if (cRes.ok && cRes.data) setContacts(cRes.data);
    setLoading(false);
  }

  function startCreate() { setSelected(null); setMode("create"); setDeleteError(null); }
  function startImport() { setSelected(null); setParsedClients([]); setParseError(null); setMode("import"); }
  function selectClient(c: Entity) { setSelected(c); setMode("view"); setDeleteError(null); }

  async function handleSave(data: ClientFormData) {
    setSaveError(null);
    const nameTrimmed = data.name.trim().toLowerCase();
    const duplicate = clients.find(
      (c) => str(c, "name").trim().toLowerCase() === nameTrimmed && c.id !== selected?.id,
    );
    if (duplicate) { setSaveError("A client with this name already exists."); return; }
    const client: Record<string, unknown> = {
      name: data.name,
      vat_number: data.vatNumber || null,
      invoicing_contact: data.contactId
        ? { id: data.contactId }
        : undefined,
      address: (data.street || data.number || data.city || data.postalCode || data.country)
        ? { street: data.street, number: data.number, city: data.city, postal_code: data.postalCode, country: data.country }
        : undefined,
    };
    if (mode === "edit" && selected) {
      client.id = selected.id;
      const ic = subEntity(selected, "invoicing_contact");
      if (ic && !data.contactId) {
        client.invoicing_contact = { id: ic.id };
      }
    }
    const res = await rpc<Entity>("clients.save", { client });
    if (res.ok) { setSaveError(null); setMode("view"); await load(res.data?.id); }
    else setSaveError(res.error || "Failed to save client.");
  }

  async function handleDelete(id: number) {
    setDeleteError(null);
    const res = await rpc("clients.delete", { id });
    if (res.ok) { setMode("view"); await load(); }
    else if (res.error) setDeleteError(res.error);
  }

  async function handleFileImport(file: File) {
    setParsing(true); setParseError(null); setParsedClients([]);
    try {
      const buffer = await file.arrayBuffer();
      const base64 = btoa(new Uint8Array(buffer).reduce((d, b) => d + String.fromCharCode(b), ""));
      const res = await rpc<ParsedClient[]>("llm.parse_document", {
        file_base64: base64, file_name: file.name, entity_type: "client",
      });
      if (res.ok && res.data) {
        setParsedClients(res.data);
        if (res.data.length === 0) setParseError("No clients found in the document.");
      } else setParseError(res.error || "Failed to parse document.");
    } catch (err) { setParseError(String(err)); }
    setParsing(false);
  }

  async function acceptClient(parsed: ParsedClient) {
    const client: Record<string, unknown> = { name: parsed.name };
    if (parsed.selectedContactId) {
      client.invoicing_contact = { id: parsed.selectedContactId };
    }
    const res = await rpc("clients.save", { client });
    if (res.ok) { setParsedClients((p) => p.filter((c) => c !== parsed)); await load(); }
  }

  async function acceptAll() {
    for (const p of parsedClients) {
      const client: Record<string, unknown> = { name: p.name };
      if (p.selectedContactId) client.invoicing_contact = { id: p.selectedContactId };
      await rpc("clients.save", { client });
    }
    setParsedClients([]); await load(); setMode("view");
  }

  function discardClient(parsed: ParsedClient) {
    setParsedClients((p) => p.filter((c) => c !== parsed));
  }

  function updateParsedClient(index: number, updated: ParsedClient) {
    setParsedClients((p) => p.map((c, i) => i === index ? updated : c));
  }

  const sorted = [...clients].sort((a, b) => {
    const aName = str(a, "name") || "";
    const bName = str(b, "name") || "";
    return aName.localeCompare(bName);
  });

  const filtered = sorted.filter((c) => {
    if (!search) return true;
    const q = search.toLowerCase();
    const name = str(c, "name").toLowerCase();
    const ic = subEntity(c, "invoicing_contact");
    const contactName = ic ? displayName(ic).toLowerCase() : "";
    return name.includes(q) || contactName.includes(q);
  });

  useAutoSelect(clients, filtered, selected, setSelected, { enabled: mode === "view" });

  return (
    <div className="flex flex-col h-full">
      <Toolbar title="Clients"
        actions={<>
          <ToolbarButtonPrimary icon={<Plus size={13} />} label="New" onClick={startCreate} />
          <ToolbarButtonSecondary icon={<FileUp size={13} />} label="Import" onClick={startImport} />
        </>}
        search={{ value: search, onChange: setSearch }}
      />

      {loadFailed && mode === "view" ? (
        <LoadError what="clients" onRetry={load} />
      ) : loading && clients.length === 0 ? (
        <LoadingState />
      ) : clients.length === 0 && mode === "view" ? (
        <EmptyStateIntro icon={Building2} description="A client is a company or person you do business with. Add clients to link them to contracts and invoices." />
      ) : (
      <ListDetailLayout
        footer={<>{filtered.length} client{filtered.length !== 1 ? "s" : ""}</>}
        list={filtered.length === 0
          ? <div className="p-4 text-sm text-center text-tertiary">No matches.</div>
          : filtered.map((c) => (
            <ClientRow key={c.id} client={c}
              isSelected={selected?.id === c.id && mode !== "create" && mode !== "import"}
              onSelect={() => selectClient(c)} />
          ))
        }
        detail={mode === "import" ? (
            <DocumentImportPanel title="Import Clients from Document" noun="client" count={parsedClients.length}
              parsing={parsing} parseError={parseError}
              onFileSelected={handleFileImport} onAcceptAll={acceptAll} onClose={() => setMode("view")}
            >
              {parsedClients.map((c, i) => (
                <ParsedClientCard key={i} client={c} contacts={Object.values(contacts)}
                  onAccept={() => acceptClient(c)}
                  onDiscard={() => discardClient(c)}
                  onUpdate={(updated) => updateParsedClient(i, updated)}
                />
              ))}
            </DocumentImportPanel>
          ) : mode === "create" ? (
            <ClientForm contacts={contacts} onSave={handleSave} onCancel={() => setMode("view")} error={saveError} />
          ) : mode === "edit" && selected ? (
            <ClientForm client={selected} contacts={contacts} onSave={handleSave} onCancel={() => setMode("view")} error={saveError} />
          ) : selected ? (
            <ClientDetail client={selected} contacts={contacts} onEdit={() => setMode("edit")}
              onDelete={() => handleDelete(selected.id)} deleteError={deleteError} onReload={() => load()} />
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-tertiary">
              <Building2 size={36} strokeWidth={1.2} />
              <span className="text-sm">Select a client</span>
            </div>
          )
        }
      />
      )}
    </div>
  );
}

/* ---------- List row ---------- */

function ClientRow({ client, isSelected, onSelect }: {
  client: Entity; isSelected: boolean; onSelect: () => void;
}) {
  const name = str(client, "name");
  const ic = subEntity(client, "invoicing_contact");
  const contactName = ic ? displayName(ic) : "";

  return (
    <button onClick={onSelect}
      className={`w-full text-left ${LIST_ROW_PADDING} border-b border-border-subtle transition-colors flex items-center gap-3
        ${isSelected ? "bg-bg-selected" : "hover:bg-bg-hover"}`}>
      <div className="w-9 h-9 rounded-full bg-bg-card flex items-center justify-center text-sm font-semibold text-secondary shrink-0">
        {initials(client)}
      </div>
      <div className="min-w-0">
        <div className="text-sm font-medium truncate">{name}</div>
        {contactName && <div className="text-xs text-tertiary truncate">{contactName}</div>}
      </div>
    </button>
  );
}

/* ---------- Detail view ---------- */

function ClientDetail({ client, contacts, onEdit, onDelete, deleteError, onReload }: {
  client: Entity; contacts: Record<string, Entity>;
  onEdit: () => void; onDelete: () => void; deleteError: string | null;
  onReload: () => void;
}) {
  const name = str(client, "name");
  const ic = subEntity(client, "invoicing_contact");
  const contactName = ic ? displayName(ic) : "";
  const email = ic ? str(ic, "email") : "";
  const company = ic ? str(ic, "company") : "";

  const clientAddr = subEntity(client, "address");
  const clientAddrParts = clientAddr ? [
    [str(clientAddr, "street"), str(clientAddr, "number")].filter(Boolean).join(" "),
    [str(clientAddr, "postal_code"), str(clientAddr, "city")].filter(Boolean).join(" "),
    str(clientAddr, "country"),
  ].filter(Boolean) : [];

  const contactAddr = ic ? subEntity(ic, "address") : null;
  const contactAddrParts = contactAddr ? [
    [str(contactAddr, "street"), str(contactAddr, "number")].filter(Boolean).join(" "),
    [str(contactAddr, "postal_code"), str(contactAddr, "city")].filter(Boolean).join(" "),
    str(contactAddr, "country"),
  ].filter(Boolean) : [];

  const [assocs, setAssocs] = useState<Entity[]>([]);
  const [addingContact, setAddingContact] = useState(false);
  const [newContactId, setNewContactId] = useState<number | null>(null);
  const [newRole, setNewRole] = useState("");

  useEffect(() => { loadAssocs(); }, [client.id]);

  async function loadAssocs() {
    const res = await rpc<Entity[]>("clients.get_contacts_for_client", { client_id: client.id });
    if (res.ok && res.data) setAssocs(res.data);
  }

  async function addContact() {
    if (!newContactId) return;
    await rpc("clients.add_contact_to_client", {
      client_id: client.id, contact_id: newContactId, role: newRole || null,
    });
    setNewContactId(null);
    setNewRole("");
    setAddingContact(false);
    await loadAssocs();
  }

  async function removeAssoc(id: number) {
    await rpc("clients.remove_client_contact", { association_id: id });
    await loadAssocs();
  }

  const contactList = Object.values(contacts);
  const linkedContactIds = new Set(assocs.map((a) => num(a, "contact_id")));

  return (
    <div className={`${DETAIL_PANE} space-y-6`}>
      <DetailHeader avatar={initials(client)} title={name}
        actions={<>
          <DetailAction label="Edit" onClick={onEdit} />
          <DetailDeleteAction key={client.id} label="Delete client" onDelete={onDelete} />
        </>} />

      {deleteError && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">{deleteError}</div>
      )}

      {(str(client, "vat_number") || clientAddrParts.length > 0) && (
        <DetailFields>
          {str(client, "vat_number") && <DetailField label="VAT Number">{str(client, "vat_number")}</DetailField>}
          {clientAddrParts.length > 0 && (
            <DetailField label="Address">
              {clientAddrParts.map((line, i) => <div key={i}>{line}</div>)}
            </DetailField>
          )}
        </DetailFields>
      )}

      {(contactName || email || company || contactAddrParts.length > 0) && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-secondary mb-3">Invoicing Contact</div>
          <DetailFields>
            {contactName && <DetailField label="Name">{contactName}</DetailField>}
            {email && <DetailField label="Email">{email}</DetailField>}
            {company && <DetailField label="Company">{company}</DetailField>}
            {contactAddrParts.length > 0 && (
              <DetailField label="Address">
                {contactAddrParts.map((line, i) => <div key={i}>{line}</div>)}
              </DetailField>
            )}
          </DetailFields>
        </div>
      )}

      {/* Contacts (many-to-many) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-xs font-semibold uppercase tracking-wider text-secondary">Contacts</div>
          {!addingContact && (
            <button onClick={() => setAddingContact(true)}
              className="flex items-center gap-1 text-xs text-secondary hover:text-primary transition-colors">
              <UserPlus size={13} /> Add
            </button>
          )}
        </div>

        {assocs.length === 0 && !addingContact && (
          <div className="text-sm text-tertiary">No contacts linked yet.</div>
        )}

        {assocs.map((a) => {
          const ct = contacts[String(num(a, "contact_id"))];
          const ctName = ct ? displayName(ct) : `Contact #${num(a, "contact_id")}`;
          const role = str(a, "role");
          return (
            <div key={a.id} className="flex items-center gap-3 p-3 rounded-lg bg-bg-card border border-border-subtle group">
              <span className="text-tertiary"><Users size={14} /></span>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{ctName}</div>
                <EditableClientContactRole associationId={a.id} role={role} onUpdated={loadAssocs}
                  updateMethod="clients.update_client_contact_role" />
              </div>
              <button onClick={() => removeAssoc(a.id)}
                className="opacity-0 group-hover:opacity-100 p-1 rounded text-secondary hover:text-red-400 transition-all"
                title="Remove contact">
                <X size={14} />
              </button>
            </div>
          );
        })}

        {addingContact && (
          <div className="p-3 rounded-lg bg-bg-card border border-border-subtle space-y-2">
            <select value={newContactId ?? ""} onChange={(e) => setNewContactId(e.target.value ? Number(e.target.value) : null)}
              className="w-full px-3 py-2 rounded-md text-sm bg-bg-sidebar text-primary border border-border-subtle outline-none focus:border-accent transition-colors">
              <option value="">— Select contact —</option>
              {contactList.filter((c) => !linkedContactIds.has(c.id)).map((c) => (
                <option key={c.id} value={c.id}>{displayName(c)}</option>
              ))}
            </select>
            <input type="text" placeholder="Role (optional), e.g. project lead, accountant" value={newRole}
              onChange={(e) => setNewRole(e.target.value)}
              className="w-full px-3 py-2 rounded-md text-sm bg-bg-sidebar text-primary border border-border-subtle outline-none focus:border-accent transition-colors placeholder:text-muted" />
            <div className="flex items-center gap-2 justify-end">
              <button onClick={() => { setAddingContact(false); setNewContactId(null); setNewRole(""); }}
                className="px-2.5 py-1 rounded text-xs text-secondary hover:text-primary transition-colors">Cancel</button>
              <button onClick={addContact} disabled={!newContactId}
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

/* ---------- Form ---------- */

interface ClientFormData {
  name: string;
  contactId: number | null;
  street: string;
  number: string;
  city: string;
  postalCode: string;
  country: string;
  vatNumber: string;
}

function ClientForm({ client, contacts, onSave, onCancel, error }: {
  client?: Entity;
  contacts: Record<string, Entity>;
  onSave: (data: ClientFormData) => void;
  onCancel: () => void;
  error?: string | null;
}) {
  const { isRequired } = useFieldRequirements("clients");
  const ic = client ? subEntity(client, "invoicing_contact") : null;
  const addr = client ? subEntity(client, "address") : null;
  const [name, setName] = useState(client ? str(client, "name") : "");
  const [contactId, setContactId] = useState<number | null>(ic?.id ?? null);
  const [street, setStreet] = useState(addr ? str(addr, "street") : "");
  const [number, setNumber] = useState(addr ? str(addr, "number") : "");
  const [city, setCity] = useState(addr ? str(addr, "city") : "");
  const [postalCode, setPostalCode] = useState(addr ? str(addr, "postal_code") : "");
  const [country, setCountry] = useState(addr ? str(addr, "country") : "");
  const [vatNumber, setVatNumber] = useState(client ? str(client, "vat_number") : "");
  const [saving, setSaving] = useState(false);
  const isNew = !client;

  const contactList = Object.values(contacts);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    await onSave({ name, contactId, street, number, city, postalCode, country, vatNumber });
    setSaving(false);
  }

  return (
    <form onSubmit={handleSubmit} className={`${DETAIL_PANE} space-y-5`}>
      <DetailHeader title={isNew ? "New Client" : "Edit Client"}
        actions={<>
          <DetailAction label="Cancel" onClick={onCancel} />
          <DetailSubmit label={saving ? "Saving…" : "Save"} disabled={saving || !name.trim()} />
        </>} />

      <p className="text-xs text-muted"><span className="text-accent">*</span> Required</p>

      <Section title="Client">
        <FormField label="Name" value={name} onChange={setName} autoFocus required={isRequired("name")} />
        <div className="mt-3">
          <FormField label="VAT Number" value={vatNumber} onChange={setVatNumber} />
        </div>
      </Section>

      <Section title="Address">
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Street" value={street} onChange={setStreet} />
          <FormField label="Number" value={number} onChange={setNumber} />
          <FormField label="Postal Code" value={postalCode} onChange={setPostalCode} />
          <FormField label="City" value={city} onChange={setCity} />
        </div>
        <div className="mt-3">
          <FormField label="Country" value={country} onChange={setCountry} />
        </div>
      </Section>

      <Section title="Invoicing Contact (Optional)">
        <label className="block text-xs text-tertiary mb-1">Select Contact</label>
        <select value={contactId ?? ""} onChange={(e) => setContactId(e.target.value ? Number(e.target.value) : null)}
          className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors">
          <option value="">— No contact —</option>
          {contactList.map((c) => (
            <option key={c.id} value={c.id}>{displayName(c)}</option>
          ))}
        </select>
      </Section>

      {error && <p className="text-xs text-red-400">{error}</p>}
    </form>
  );
}

/* ---------- Shared UI ---------- */

function FormField({ label, value, onChange, type = "text", autoFocus, required, placeholder }: {
  label: string; value: string; onChange: (v: string) => void; type?: string; autoFocus?: boolean; required?: boolean; placeholder?: string;
}) {
  return (
    <div>
      <label className="block text-xs text-tertiary mb-1">{label}{required && <span className="text-accent ml-0.5">*</span>}</label>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} autoFocus={autoFocus} required={required} placeholder={placeholder}
        className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none
          focus:border-accent transition-colors placeholder:text-muted" />
    </div>
  );
}

/* ---------- AI Import ---------- */

interface ParsedClient {
  name: string;
  contact_name_hint: string;
  selectedContactId?: number;
}

function ParsedClientCard({ client, contacts, onAccept, onDiscard, onUpdate }: {
  client: ParsedClient;
  contacts: Entity[];
  onAccept: () => void;
  onDiscard: () => void;
  onUpdate: (c: ParsedClient) => void;
}) {
  return (
    <div className="rounded-xl border-2 border-fuchsia-400/40 bg-fuchsia-500/5 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={14} className="text-fuchsia-400" />
          <span className="text-sm font-semibold">{client.name || "Unnamed"}</span>
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
        <div>
          <label className="block text-xs text-fuchsia-300/70 mb-0.5">Client Name</label>
          <input type="text" value={client.name} onChange={(e) => onUpdate({ ...client, name: e.target.value })}
            className="w-full px-2.5 py-1.5 rounded-md text-sm bg-bg-card text-primary border border-fuchsia-400/30 outline-none focus:border-fuchsia-400 transition-colors" />
        </div>
        <div>
          <label className="block text-xs text-fuchsia-300/70 mb-0.5">
            Invoicing Contact {client.contact_name_hint && <span className="text-fuchsia-400/60">(hint: {client.contact_name_hint})</span>}
          </label>
          <select value={client.selectedContactId ?? ""} onChange={(e) => onUpdate({ ...client, selectedContactId: e.target.value ? Number(e.target.value) : undefined })}
            className="w-full px-2.5 py-1.5 rounded-md text-sm bg-bg-card text-primary border border-fuchsia-400/30 outline-none focus:border-fuchsia-400 transition-colors">
            <option value="">— Select —</option>
            {contacts.map((c) => <option key={c.id} value={c.id}>{displayName(c)}</option>)}
          </select>
        </div>
      </div>
    </div>
  );
}
