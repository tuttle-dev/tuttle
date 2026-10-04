import type { ReactNode } from "react";
import { Sparkles, Loader2, X, CheckCheck } from "lucide-react";
import { DocumentDropzone } from "./DocumentDropzone";

/**
 * Detail-pane panel for importing one entity type from a document with AI.
 * `children` are the approval cards for the `count` parsed items.
 */
export function DocumentImportPanel({ title, noun, count, parsing, parseError, onFileSelected, onAcceptAll, onClose, children }: {
  title: string;
  /** Singular, lower-case entity name, e.g. "client". */
  noun: string;
  count: number;
  parsing: boolean;
  parseError: string | null;
  onFileSelected: (file: File) => void;
  onAcceptAll: () => void;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div className="p-5 space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={18} className="text-status-purple" />
          <h2 className="text-lg font-semibold">{title}</h2>
        </div>
        <button onClick={onClose}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
          <X size={14} /> Close
        </button>
      </div>

      {count === 0 && !parsing && (
        <DocumentDropzone hint={`PDF, TXT, or Markdown — AI will extract ${noun}s`} onFileSelected={onFileSelected} />
      )}

      {parsing && (
        <div className="flex items-center justify-center gap-3 py-10">
          <Loader2 size={20} className="animate-spin text-status-purple" />
          <span className="text-sm text-secondary">Parsing document with AI…</span>
        </div>
      )}

      {parseError && (
        <div className="p-3 rounded-lg bg-status-danger/10 border border-status-danger/30 text-sm text-status-danger">{parseError}</div>
      )}

      {count > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-secondary">
              <span className="font-medium text-status-purple">{count}</span> {noun}{count !== 1 ? "s" : ""} found
            </p>
            <button onClick={onAcceptAll}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium text-status-purple hover:bg-status-purple/10 border border-status-purple/30 transition-colors">
              <CheckCheck size={14} /> Accept All
            </button>
          </div>
          {children}
        </div>
      )}
    </div>
  );
}
