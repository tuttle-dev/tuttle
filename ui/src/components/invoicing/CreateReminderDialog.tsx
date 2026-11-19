import { useState } from "react";
import { rpc } from "../../api/rpc";
import { Dialog, DialogHeader, DialogBody, DialogFooter } from "../shared/Dialog";
import { localDateIso } from "../../api/entity";

export function CreateReminderDialog({ invoiceId, invoiceNumber, onClose, onCreated }: {
  invoiceId: number; invoiceNumber: string; onClose: () => void; onCreated: (newId?: number, warning?: string | null) => void;
}) {
  const today = localDateIso();
  const inTwoWeeks = new Date();
  inTwoWeeks.setDate(inTwoWeeks.getDate() + 14);
  const twoWeeks = localDateIso(inTwoWeeks);
  const [reminderDate, setReminderDate] = useState(today);
  const [newDueDate, setNewDueDate] = useState(twoWeeks);
  const [fee, setFee] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    if (!newDueDate) { setError("New due date is required"); return; }
    setSubmitting(true);
    setError("");
    const params: Record<string, unknown> = {
      invoice_id: invoiceId,
      reminder_date: reminderDate,
      new_due_date: newDueDate,
    };
    const feeNum = parseFloat(fee);
    if (feeNum > 0) params.reminder_fee = feeNum;
    const res = await rpc<{ id?: number }>("invoicing.create_reminder", params);
    if (res.ok) {
      onCreated(res.data?.id, res.warning);
    } else {
      setError(res.error || "Failed to create reminder");
    }
    setSubmitting(false);
  }

  return (
    <Dialog onClose={onClose} width="w-[420px]">
      <DialogHeader>
        <h2 className="text-base font-semibold">Create Reminder</h2>
        <p className="text-xs text-tertiary mt-0.5">for invoice {invoiceNumber}</p>
      </DialogHeader>
      <DialogBody className="px-5 py-4 space-y-4">
        <p className="text-xs text-muted"><span className="text-accent">*</span> Required</p>
        <label className="block">
          <span className="text-[10px] font-semibold text-muted uppercase">Reminder Date<span className="text-accent ml-0.5">*</span></span>
          <input type="date" value={reminderDate} onChange={(e) => setReminderDate(e.target.value)}
            className="mt-1 w-full px-3 py-1.5 rounded-md bg-bg-card border border-border-subtle text-sm text-primary" />
        </label>
        <label className="block">
          <span className="text-[10px] font-semibold text-muted uppercase">New Due Date<span className="text-accent ml-0.5">*</span></span>
          <input type="date" value={newDueDate} onChange={(e) => setNewDueDate(e.target.value)}
            className="mt-1 w-full px-3 py-1.5 rounded-md bg-bg-card border border-border-subtle text-sm text-primary" />
        </label>
        <label className="block">
          <span className="text-[10px] font-semibold text-muted uppercase">Reminder Fee (optional)</span>
          <input type="number" min="0" step="0.01" placeholder="0.00" value={fee}
            onChange={(e) => setFee(e.target.value)}
            className="mt-1 w-full px-3 py-1.5 rounded-md bg-bg-card border border-border-subtle text-sm text-primary tabular-nums" />
        </label>
        {error && <p className="text-xs text-status-danger">{error}</p>}
      </DialogBody>
      <DialogFooter className="flex justify-end gap-2">
        <button onClick={onClose}
          className="px-4 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
          Cancel
        </button>
        <button onClick={submit} disabled={submitting}
          className="px-4 py-1.5 rounded-md text-sm font-medium bg-status-warning text-on-fill hover:bg-status-warning/90 transition-colors disabled:opacity-50">
          {submitting ? "Creating…" : "Create Reminder"}
        </button>
      </DialogFooter>
    </Dialog>
  );
}
