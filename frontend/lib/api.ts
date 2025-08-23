// frontend/lib/api.ts

// Only use the proxy when explicitly enabled
const USE_PROXY = process.env.NEXT_PUBLIC_USE_PROXY === "1";

const DEFAULT_DEV_BASE = "http://127.0.0.1:8000";

const DIRECT_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) ||
  (process.env.NODE_ENV === "development" ? DEFAULT_DEV_BASE : "");

function api(path: string) {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (USE_PROXY) return `/api/proxy${p}`;
  if (!DIRECT_BASE) {
    throw new Error(
      "API base not set. Define NEXT_PUBLIC_API_BASE or enable the proxy."
    );
  }
  return `${DIRECT_BASE}${p}`;
}

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
    fd.set("pdf", file, file.name); // important: include filename
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
