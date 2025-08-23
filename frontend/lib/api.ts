// frontend/lib/api.ts

// Only use the proxy when explicitly enabled
const USE_PROXY =
  String(process.env.NEXT_PUBLIC_USE_PROXY ?? "").toLowerCase() === "1" ||
  String(process.env.NEXT_PUBLIC_USE_PROXY ?? "").toLowerCase() === "true";

const DEFAULT_DEV_BASE = "http://127.0.0.1:8000";

// Resolve the direct base (only used when not proxying).
// Treat empty string as "unset" so we fall back to DEFAULT_DEV_BASE in development.
const RAW_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "").trim();
const DIRECT_BASE: string =
  RAW_BASE || (process.env.NODE_ENV === "development" ? DEFAULT_DEV_BASE : "");

function api(path: string) {
  const p = path.startsWith("/") ? path : `/${path}`;

  // If proxying is enabled, always hit the local proxy route.
  if (USE_PROXY) return `/api/proxy${p}`;

  // Otherwise we must have a fully-qualified base URL.
  if (!DIRECT_BASE) {
    throw new Error(
      'API base not set. Define NEXT_PUBLIC_API_BASE (e.g. "https://layscience.onrender.com") or enable the proxy.'
    );
  }
  if (!/^https?:\/\//i.test(DIRECT_BASE)) {
    throw new Error(
      `Invalid NEXT_PUBLIC_API_BASE: "${DIRECT_BASE}". It must be a full http(s) URL.`
    );
  }

  return `${DIRECT_BASE}${p}`;
}

async function asJson(res: Response) {
  const ct = res.headers.get("content-type") || "";
  const isJson = ct.includes("application/json");
  if (!res.ok) {
    const body = isJson ? await res.json().catch(() => ({})) : await res.text();
    const msg = isJson ? (body as any)?.error || JSON.stringify(body) : body;
    throw new Error(`HTTP ${res.status}: ${msg}`);
  }
  return isJson ? res.json() : res.text();
}

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
  // If file provided -> multipart; else JSON
  if (file) {
    const fd = new FormData();
    if (ref) fd.set("ref", ref);
    fd.set("length", length);
    fd.set("pdf", file, file.name); // include filename
    const res = await fetch(api("/api/v1/summaries"), {
      method: "POST",
      body: fd, // do NOT set Content-Type manually
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

export async function registerAccount({
  username,
  email,
}: {
  username: string;
  email: string;
}) {
  const res = await fetch(api("/api/v1/register"), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ username, email }),
    cache: "no-store",
  });
  return asJson(res);
}

export async function verifyCode({
  email,
  code,
}: {
  email: string;
  code: string;
}) {
  const res = await fetch(api("/api/v1/verify"), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, code }),
    cache: "no-store",
  });
  return asJson(res);
}
