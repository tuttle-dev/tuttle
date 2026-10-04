import { useCallback, useRef, useState } from "react";
import { FileUp } from "lucide-react";

const ACCEPT_EXTENSIONS = [".pdf", ".txt", ".md", ".text"];

/** Click-or-drop target for a document to be parsed with AI. */
export function DocumentDropzone({ hint, onFileSelected }: {
  hint: string;
  onFileSelected: (file: File) => void;
}) {
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && ACCEPT_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext))) onFileSelected(file);
  }, [onFileSelected]);

  return (
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
        <p className="text-xs text-tertiary mt-1">{hint}</p>
      </div>
      <input ref={fileInputRef} type="file" className="hidden" accept=".pdf,.txt,.md,.text" onChange={(e) => { const f = e.target.files?.[0]; if (f) onFileSelected(f); }} />
    </div>
  );
}
