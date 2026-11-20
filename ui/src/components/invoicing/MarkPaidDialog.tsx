import { useState } from "react";
import { Dialog, DialogHeader, DialogBody, DialogFooter } from "../shared/Dialog";
import { localDateIso } from "../../api/entity";

/** Asks when the payment came in: revenue counts on that date (cash basis). */
export function MarkPaidDialog({ invoiceNumber, onClose, onConfirm }: {
  invoiceNumber: string; onClose: () => void; onConfirm: (paidDate: string) => void;
}) {
  const [paidDate, setPaidDate] = useState(localDateIso());

  return (
    <Dialog onClose={onClose} width="w-[360px]">
      <DialogHeader>
        <h2 className="text-base font-semibold">Mark as paid</h2>
        <p className="text-xs text-tertiary mt-0.5">invoice {invoiceNumber}</p>
      </DialogHeader>
      <DialogBody className="px-5 py-4 space-y-2">
        <label className="block">
          <span className="text-[10px] font-semibold text-muted uppercase">Payment received on</span>
          <input type="date" value={paidDate} onChange={(e) => setPaidDate(e.target.value)}
            className="mt-1 w-full px-3 py-1.5 rounded-md bg-bg-card border border-border-subtle text-sm text-primary" />
        </label>
        <p className="text-xs text-tertiary">Revenue and taxes count the invoice on this date.</p>
      </DialogBody>
      <DialogFooter className="flex justify-end gap-2">
        <button onClick={onClose}
          className="px-4 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
          Cancel
        </button>
        <button onClick={() => onConfirm(paidDate)} disabled={!paidDate}
          className="px-4 py-1.5 rounded-md text-sm font-medium bg-status-success text-on-fill hover:bg-status-success/90 transition-colors disabled:opacity-50">
          Mark as paid
        </button>
      </DialogFooter>
    </Dialog>
  );
}
