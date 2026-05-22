export function projectColumnAfterCompletedToggle(currentStatus: string): string {
  return currentStatus === "Completed" ? "Active" : "Completed";
}
