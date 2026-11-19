import { str, num, isReminder, isDeposit, isFinalInvoice, depositChainHeadId } from "../../api/entity";
import type { Entity } from "../../api/types";

export type InvoiceChain = { root: Entity; reminders: Entity[]; deposits: Entity[] };

function depositGroupKey(inv: Entity): string {
  return `${num(inv, "contract_id")}-${num(inv, "project_id")}`;
}

export function buildChains(invoices: Entity[]): InvoiceChain[] {
  const roots: Entity[] = [];
  const reminders: Entity[] = [];
  const linkedDeposits: Entity[] = [];
  const orphanDeposits: Entity[] = [];
  const finalsByGroup = new Map<string, Entity>();

  for (const inv of invoices) {
    if (isReminder(inv)) {
      reminders.push(inv);
    } else if (isFinalInvoice(inv)) {
      roots.push(inv);
      finalsByGroup.set(depositGroupKey(inv), inv);
    } else if (isDeposit(inv)) {
      if (depositChainHeadId(inv) != null) linkedDeposits.push(inv);
      else orphanDeposits.push(inv);
    } else {
      roots.push(inv);
    }
  }

  const reminderMap = new Map<number, Entity[]>();
  const depositMap = new Map<number, Entity[]>();
  for (const root of roots) {
    reminderMap.set(root.id, []);
    depositMap.set(root.id, []);
  }

  for (const rem of reminders) {
    const headId = rem.reminder_chain_head_id as number | undefined;
    if (headId != null && reminderMap.has(headId)) {
      reminderMap.get(headId)!.push(rem);
    }
  }

  for (const dep of linkedDeposits) {
    const headId = depositChainHeadId(dep);
    if (headId != null && depositMap.has(headId)) {
      depositMap.get(headId)!.push(dep);
    } else {
      orphanDeposits.push(dep);
    }
  }

  const orphanByGroup = new Map<string, Entity[]>();
  for (const dep of orphanDeposits) {
    const key = depositGroupKey(dep);
    if (!orphanByGroup.has(key)) orphanByGroup.set(key, []);
    orphanByGroup.get(key)!.push(dep);
  }

  for (const [key, deps] of orphanByGroup) {
    const sorted = [...deps].sort(
      (a, b) => str(a, "date").localeCompare(str(b, "date")) || a.id - b.id,
    );
    const finalInv = finalsByGroup.get(key);
    if (finalInv && depositMap.has(finalInv.id)) {
      depositMap.get(finalInv.id)!.push(...sorted);
      continue;
    }
    const [head, ...rest] = sorted;
    roots.push(head);
    reminderMap.set(head.id, []);
    depositMap.set(head.id, rest);
  }

  return roots.map((root) => {
    const rems = (reminderMap.get(root.id) || []).sort(
      (a, b) => num(a, "reminder_level") - num(b, "reminder_level"),
    );
    const deps = (depositMap.get(root.id) || []).sort(
      (a, b) => str(a, "date").localeCompare(str(b, "date")) || a.id - b.id,
    );
    return { root, reminders: rems, deposits: deps };
  });
}
