import { Component, type ReactNode } from "react";
import { AlertTriangle, Copy, RotateCcw } from "lucide-react";

interface Props {
  viewName?: string;
  children: ReactNode;
}

interface State {
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  copied: boolean;
}

export class ViewErrorBoundary extends Component<Props, State> {
  state: State = { error: null, errorInfo: null, copied: false };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ errorInfo });
  }

  private handleRetry = () => {
    this.setState({ error: null, errorInfo: null, copied: false });
  };

  private handleCopy = async () => {
    const report = this.buildReport();
    try {
      await navigator.clipboard.writeText(report);
      this.setState({ copied: true });
      setTimeout(() => this.setState({ copied: false }), 2000);
    } catch {
      // fallback: select a textarea (not needed in Electron, but safe)
    }
  };

  private buildReport(): string {
    const { error, errorInfo } = this.state;
    const lines = [
      `## Error Report — ${this.props.viewName || "View"}`,
      "",
      `**Error:** ${error?.message || "Unknown error"}`,
      "",
      "**Stack:**",
      "```",
      error?.stack || "(no stack trace)",
      "```",
      "",
      "**Component Stack:**",
      "```",
      errorInfo?.componentStack?.trim() || "(unavailable)",
      "```",
      "",
      `**Timestamp:** ${new Date().toISOString()}`,
      `**User Agent:** ${navigator.userAgent}`,
    ];
    return lines.join("\n");
  }

  render() {
    if (!this.state.error) {
      return this.props.children;
    }

    const { error } = this.state;
    const viewLabel = this.props.viewName || "This view";

    return (
      <div className="relative flex flex-col items-center justify-center h-full gap-5 px-6">
        <div className="drag-region absolute inset-x-0 top-0 h-13" />
        <div className="flex flex-col items-center gap-3 max-w-md text-center">
          <div className="w-12 h-12 rounded-2xl bg-status-danger/10 flex items-center justify-center">
            <AlertTriangle size={24} strokeWidth={1.5} className="text-status-danger" />
          </div>

          <h3 className="text-base font-semibold text-primary">
            {viewLabel} encountered an error
          </h3>

          <p className="text-xs text-secondary leading-relaxed">
            Something went wrong while rendering this view. You can retry, or copy the error details below to include in a bug report.
          </p>

          <div className="w-full mt-2 rounded-lg border border-border-subtle bg-bg-card p-3 text-left">
            <p className="text-xs font-mono text-status-danger break-all leading-relaxed">
              {error.message}
            </p>
          </div>

          <div className="flex gap-2 mt-3">
            <button
              onClick={this.handleRetry}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-primary bg-bg-card border border-border-subtle hover:bg-bg-hover transition-colors"
            >
              <RotateCcw size={12} />
              Retry
            </button>
            <button
              onClick={this.handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-on-fill bg-accent hover:bg-accent/90 transition-colors"
            >
              <Copy size={12} />
              {this.state.copied ? "Copied!" : "Copy error report"}
            </button>
          </div>
        </div>
      </div>
    );
  }
}
