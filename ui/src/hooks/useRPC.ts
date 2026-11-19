import { useState, useCallback } from "react";
import { rpc, type RPCResult } from "../api/rpc";

export function useRPC() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const call = useCallback(
    async <T = unknown>(
      method: string,
      params: Record<string, unknown> = {}
    ): Promise<RPCResult<T>> => {
      setLoading(true);
      setError(null);
      try {
        const result = await rpc<T>(method, params);
        if (!result.ok && result.error) {
          setError(result.error);
        }
        return result;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);
        return { ok: false, data: null as T, error: msg, warning: null };
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return { call, loading, error };
}
