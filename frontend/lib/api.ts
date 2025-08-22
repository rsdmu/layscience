// frontend/lib/api.ts

// ---- Base resolution ---------------------------------------------------------
const DEFAULT_DEV_BASE = "http://127.0.0.1:8000";

// If you prefer a Vercel proxy (Option B), set NEXT_PUBLIC_USE_PROXY=1
const USE_PROXY =
  typeof process !== "undefined" &&
  process.env.NEXT_PUBLIC_USE_PROXY === "1";

// For direct calls (Option A), set NEXT_PUBLIC_API_BASE to your Render URL
// e.g. NEXT_PUBLIC_API_BASE=https://layscience.onrender.com
const BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) ||
  (process.env.NODE_ENV === "development" ? DEFAULT_DEV_BASE : "");

function api(path: string) {
  const p = path.startsWith("/") ? path : `/${path}`;

  // Option B: proxy only for browser requests (prevents CORS issues),
  // you must implement /api/proxy on Vercel if you enable this.
  if (USE_PROXY && typeof window !== "undefined") return `/api/proxy${p}`;

  if (!BASE) {
    throw new Error(
      "API base URL is not set. Define NEXT_PUBLIC_API_BASE (Render URL) or run in development."
    );
  }
  return `${BASE}${p}`;
}

// ---- Helpers ----------------------------------------------------------------
async function asJson(res: Response) {
  const ct = res.headers.get("content-type") || "";
  const isJson = ct.includes("application/json");
  if (!res.ok) {
    const body = isJson ? await res.json().catch(() => ({})) : await res.text();
    const msg = isJson ? body?.error || JSON.stringify(body) : body;
    throw new Error(`HTTP ${res.status}: ${msg}`);
  }
  return isJson ? res.json() : res.text();
}

// ---- API calls ---------------------------------------------------------------

type LengthOpt = "default" | "extended";

export async function startJob({
  ref,
  file,
  length = "default",
}: {
  ref?: string;
  file?: File | null;
  length?: LengthOpt;
}) {
  // If a file is provided -> multipart; otherwise JSON
  if (file) {
    const fd = new FormData();
    if (ref) fd.set("ref", ref);
    if (length) fd.set("length", length);
    // include filename to help server-side diagnostics
    fd.set("pdf", file, file.name);

    const res = await fetch(api("/api/v1/summaries"), {
      method: "POST",
      body: fd, // do NOT set Content-Type; the browser will set multipart boundary
      cache: "no-store",
    });
    return asJson(res);
  } else {
    const res = await fetch(api("/api/v1/summaries"), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ ref, length }),
      cache: "no-store",
    });
    return asJson(res);
  }
}

export async function getJob(id: string) {
  const res = await fetch(api(`/api/v1/jobs/${id}`), { cache: "no-store" });
  return asJson(res);
}

export async function getSummary(id: string) {
  const res = await fetch(api(`/api/v1/summaries/${id}`), { cache: "no-store" });
  return asJson(res);
}
