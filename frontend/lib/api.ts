// frontend/lib/api.ts

// Only use the proxy when explicitly enabled
const USE_PROXY =
  String(process.env.NEXT_PUBLIC_USE_PROXY ?? "").toLowerCase() === "1" ||
  String(process.env.NEXT_PUBLIC_USE_PROXY ?? "").toLowerCase() === "true";

const DEFAULT_DEV_BASE = "http://127.0.0.1:8000";

// Resolve the direct base (only used when not proxying)
const RAW_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "").trim();
const DIRECT_BASE: string =
  RAW_BASE || (process.env.NODE_ENV === "development" ? DEFAULT_DEV_BASE : "");

function api(path: string) {
  const p = path.startsWith("/") ? path : `/${path}`;

  if (USE_PROXY) return `/api/proxy${p}`;

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

  // Avoid double slashes and handle query strings
  return new URL(p, DIRECT_BASE).toString();
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
type ModeOpt = "default" | "detailed" | "funny";
type LanguageOpt = "en" | "fa" | "fr" | "es" | "de";

export async function startJob({
  ref,
  file,
  length = "default",
  mode = "default",
  language = "en",
}: {
  ref?: string;
  file?: File | null;
  length?: LengthOpt;
  mode?: ModeOpt;
  language?: LanguageOpt;
}) {
  if (file) {
    const fd = new FormData();
    if (ref) fd.set("ref", ref);
    fd.set("length", length);
    fd.set("mode", mode);
    fd.set("language", language);
    fd.set("pdf", file, file.name);
    const res = await fetch(api("/api/v1/summaries"), {
      method: "POST",
      body: fd,
      cache: "no-store",
    });
    return asJson(res);
  } else {
    const res = await fetch(api("/api/v1/summaries"), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ ref, length, mode, language }),
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

export async function registerAccount({ username, email }: { username: string; email: string }) {
  const res = await fetch(api("/api/v1/register"), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ username, email }),
    cache: "no-store",
  });
  return asJson(res);
}

export async function verifyCode({ email, code }: { email: string; code: string }) {
  const res = await fetch(api("/api/v1/verify"), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, code }),
    cache: "no-store",
  });
  return asJson(res);
}

export async function resendCode(email: string) {
  const res = await fetch(api("/api/v1/resend"), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email }),
    cache: "no-store",
  });
  return asJson(res);
}

export async function deleteAccount() {
  const res = await fetch(api("/api/v1/account"), {
    method: "DELETE",
    cache: "no-store",
  });
  return asJson(res);
}

export async function listMySummaries(page = 1) {
  const res = await fetch(api(`/api/v1/summaries?me=true&page=${page}`), {
    cache: "no-store",
  });
  return asJson(res);
}

export async function listFeedbackTopics(page = 1) {
  const res = await fetch(api(`/api/v1/feedback/topics?page=${page}`), {
    cache: "no-store",
  });
  return asJson(res);
}

export async function createFeedbackTopic({ title, body }: { title: string; body: string }) {
  const res = await fetch(api("/api/v1/feedback/topics"), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ title, body }),
    cache: "no-store",
  });
  return asJson(res);
}

export async function listFeedbackReplies(topicId: number) {
  const res = await fetch(api(`/api/v1/feedback/topics/${topicId}/replies`), {
    cache: "no-store",
  });
  return asJson(res);
}

export async function createFeedbackReply(topicId: number, body: string) {
  const res = await fetch(api(`/api/v1/feedback/topics/${topicId}/replies`), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ body }),
    cache: "no-store",
  });
  return asJson(res);
}

export async function submitFeedbackSurvey(q1: string, q2: number, q3: string) {
  const res = await fetch(api("/api/v1/feedback/survey"), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ q1, q2, q3 }),
    cache: "no-store",
  });
  return asJson(res);
}

