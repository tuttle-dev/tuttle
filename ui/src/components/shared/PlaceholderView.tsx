import { Construction } from "lucide-react";

export function PlaceholderView({ title }: { title: string }) {
  return (
    <div className="relative flex flex-col items-center justify-center h-full gap-3 text-secondary">
      <div className="drag-region absolute inset-x-0 top-0 h-13" />
      <Construction size={40} strokeWidth={1.2} />
      <div className="text-lg font-medium">{title}</div>
      <div className="text-sm text-tertiary">This section is not yet implemented.</div>
    </div>
  );
}
