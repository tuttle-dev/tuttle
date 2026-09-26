declare global {
  interface Window {
    tuttle: {
      rpc: (method: string, params?: Record<string, unknown>) => Promise<unknown>;
      readFile: (filePath: string) => Promise<{ ok: boolean; data: string | null }>;
      platform: string;
      onUpdateAvailable: (cb: (info: { version: string }) => void) => () => void;
      onUpdateNotAvailable: (cb: (info: { version: string }) => void) => () => void;
      onUpdateDownloaded: (cb: (info: { version: string }) => void) => () => void;
      onUpdateError: (cb: (info: { message: string }) => void) => () => void;
      onUpdateProgress: (cb: (info: { version: string; percent: number }) => void) => () => void;
      getUpdateState: () => Promise<
        | { status: "idle" }
        | { status: "downloading"; version: string; percent: number }
        | { status: "ready"; version: string }
      >;
      checkForUpdate: () => void;
      openExternal: (url: string) => void;
      quitAndInstall: () => void;
    };
  }
}

export async function readFileAsDataURL(filePath: string, mimeType: string): Promise<string | null> {
  try {
    const result = await window.tuttle.readFile(filePath);
    if (result.ok && result.data) return `data:${mimeType};base64,${result.data}`;
    return null;
  } catch { return null; }
}

export interface RPCResult<T = unknown> {
  ok: boolean;
  data: T;
  error: string | null;
  warning: string | null;
}

export async function rpc<T = unknown>(
  method: string,
  params: Record<string, unknown> = {}
): Promise<RPCResult<T>> {
  console.log(`[rpc] → ${method}`, params);
  try {
    const result = (await window.tuttle.rpc(method, params)) as RPCResult<T>;
    console.log(`[rpc] ← ${method}`, result?.ok, result?.error);
    return result;
  } catch (err) {
    console.error(`[rpc] error in ${method}:`, err);
    return { ok: false, data: null as T, error: String(err), warning: null };
  }
}
