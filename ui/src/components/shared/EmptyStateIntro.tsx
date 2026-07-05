import type { LucideIcon } from "lucide-react";

export function EmptyStateIntro({ icon: Icon, description }: {
  icon: LucideIcon;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-secondary px-6 text-center">
      <Icon size={40} strokeWidth={1.2} />
      <div className="text-sm text-tertiary max-w-md">{description}</div>
    </div>
  );
}
