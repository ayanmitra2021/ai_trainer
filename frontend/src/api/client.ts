/**
 * Base fetch wrapper.
 *
 * In local dev, VITE_API_BASE_URL is unset so BASE resolves to "/api/v1" and
 * Vite's proxy forwards those requests to localhost:8000.
 *
 * In production (GitHub Pages), VITE_API_BASE_URL is set to the Render backend
 * origin (e.g. "https://ai-trainer-pavl.onrender.com") via frontend/.env.production,
 * so every request goes directly to the correct host.
 *
 * credentials:"include" is required for the session cookie to be sent on
 * cross-origin requests (GitHub Pages → Render).  The backend CORS policy
 * explicitly allows the GitHub Pages origin with allow_credentials=True.
 */
const BASE = `${import.meta.env.VITE_API_BASE_URL ?? ""}/api/v1`;

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    /** Machine-readable error code from the response body (e.g. "all_providers_unavailable"). */
    public code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",           // send/receive session cookie cross-origin
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    let code: string | undefined;
    try {
      const body = await res.json();
      detail = body.detail ?? body.message ?? detail;
      code = body.error;  // Phase 15: machine-readable error code from 503 body
    } catch { /* ignore parse failure */ }
    throw new ApiError(res.status, detail, code);
  }
  // 204 No Content
  if (res.status === 204) return undefined as unknown as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
