/** A labelled text input of an entity form. `data-field` names it for the tour. */
export function FormField({ label, value, onChange, type = "text", autoFocus, required, placeholder }: {
  label: string; value: string; onChange: (v: string) => void; type?: string; autoFocus?: boolean; required?: boolean; placeholder?: string;
}) {
  return (
    <div data-field={label}>
      <label className="block text-xs text-tertiary mb-1">{label}{required && <span className="text-accent ml-0.5">*</span>}</label>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} autoFocus={autoFocus} required={required} placeholder={placeholder}
        className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none
          focus:border-accent transition-colors placeholder:text-muted" />
    </div>
  );
}
