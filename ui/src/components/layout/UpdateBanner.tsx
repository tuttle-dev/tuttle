import { useState, useEffect } from "react";
import { Download, X } from "lucide-react";
import { useStatusBar } from "../shared/status-bar-context";

type Update =
  | { status: "downloading"; version: string; percent: number }
  | { status: "ready"; version: string };

export function UpdateBanner() {
  const [update, setUpdate] = useState<Update | null>(null);
  // Dismissal is per version and stage: the banner returns once the download
  // finishes, and again for a newer release.
  const [dismissed, setDismissed] = useState<string | null>(null);
  const { showMessage } = useStatusBar();

  useEffect(() => {
    // Catch up on anything that happened before this component mounted.
    window.tuttle?.getUpdateState?.().then((s) => {
      if (s && s.status !== "idle") setUpdate(s);
    });
    const offs = [
      window.tuttle?.onUpdateAvailable?.((info) =>
        setUpdate({ status: "downloading", version: info.version, percent: 0 }),
      ),
      window.tuttle?.onUpdateProgress?.((info) =>
        setUpdate({ status: "downloading", ...info }),
      ),
      window.tuttle?.onUpdateDownloaded?.((info) =>
        setUpdate({ status: "ready", version: info.version }),
      ),
      window.tuttle?.onUpdateError?.((info) => {
        setUpdate((u) => (u?.status === "downloading" ? null : u));
        showMessage(info.message, { type: "error" });
      }),
    ];
    return () => offs.forEach((off) => off?.());
  }, []);

  const key = update && `${update.status}:${update.version}`;
  if (!update || key === dismissed) return null;

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-accent/10 border-b border-accent/20 text-sm text-primary shrink-0">
      <Download size={16} className="text-accent shrink-0" />
      <span className="flex-1">
        {update.status === "ready" ? (
          <>Tuttle <strong>{update.version}</strong> is ready to install.</>
        ) : (
          <>Downloading Tuttle <strong>{update.version}</strong>… {update.percent}%</>
        )}
      </span>
      {update.status === "ready" && (
        <button
          onClick={() => window.tuttle.quitAndInstall()}
          className="px-3 py-1 rounded-md bg-accent text-white text-xs font-medium hover:bg-accent/90 transition-colors"
        >
          Restart &amp; Update
        </button>
      )}
      <button
        onClick={() => setDismissed(key)}
        className="p-1 rounded hover:bg-white/10 transition-colors text-secondary"
        aria-label="Dismiss"
      >
        <X size={14} />
      </button>
    </div>
  );
}
