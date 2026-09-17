import { t } from "@/i18n/ru";
import { getAccessToken } from "@/lib/supabase";
import { useNetwork } from "@/store/ui";

export const API_URL = ((import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000").replace(/\/$/, "");
const SLOW_MS = 3000;
const HEALTH_POLL_MS = 8000;

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

let pendingSlow = 0;
let healthTimer: ReturnType<typeof setInterval> | null = null;
const recoveryListeners = new Set<() => void>();

export function onBackendRecovered(cb: () => void): () => void {
  recoveryListeners.add(cb);
  return () => recoveryListeners.delete(cb);
}

function markOnline() {
  const net = useNetwork.getState();
  if (net.offline) {
    net.setOffline(false);
    recoveryListeners.forEach((cb) => cb());
  }
  if (healthTimer) {
    clearInterval(healthTimer);
    healthTimer = null;
  }
}

function markOffline() {
  useNetwork.getState().setOffline(true);
  if (healthTimer) return;
  healthTimer = setInterval(async () => {
    try {
      const res = await fetch(`${API_URL}/health`);
      if (res.ok) markOnline();
    } catch {
      /* still offline */
    }
  }, HEALTH_POLL_MS);
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  auth?: boolean;
}

async function send(path: string, { method = "GET", body, auth = true }: RequestOptions): Promise<Response> {
  let slowTimer: ReturnType<typeof setTimeout> | null = setTimeout(() => {
    slowTimer = null;
    pendingSlow++;
    useNetwork.getState().setSlow(true);
  }, SLOW_MS);
  try {
    const headers: Record<string, string> = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (auth) {
      const token = await getAccessToken();
      if (token) headers.Authorization = `Bearer ${token}`;
    }
    const res = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    markOnline();
    return res;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    markOffline();
    throw new ApiError(0, "NETWORK", t.errors.network);
  } finally {
    if (slowTimer) clearTimeout(slowTimer);
    else if (--pendingSlow <= 0) {
      pendingSlow = 0;
      useNetwork.getState().setSlow(false);
    }
  }
}

async function toError(res: Response): Promise<ApiError> {
  try {
    const data = (await res.json()) as { error?: { code?: string; message?: string } };
    return new ApiError(res.status, data.error?.code ?? "HTTP_ERROR", data.error?.message ?? t.errors.generic);
  } catch {
    return new ApiError(res.status, "HTTP_ERROR", t.errors.generic);
  }
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const res = await send(path, options);
  if (!res.ok) throw await toError(res);
  return (await res.json()) as T;
}

export async function apiBlob(path: string): Promise<Blob> {
  const res = await send(path, {});
  if (!res.ok) throw await toError(res);
  return res.blob();
}

export function isNotFound(e: unknown): boolean {
  return e instanceof ApiError && e.status === 404;
}
