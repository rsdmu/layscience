const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

function api(path: string) {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (typeof window !== "undefined") return `/api/proxy${p}`;
  return `${BASE}${p}`;
}

async function asJson(res: Response) {
  const ct = res.headers.get("content-type") || "";
  const isJson = ct.includes("application/json");
  if (!res.ok) {
    const body = isJson ? await res.json().catch(()=>({})) : await res.text();
    const msg = isJson ? (body.error || JSON.stringify(body)) : body;
    throw new Error(`HTTP ${res.status}: ${msg}`);
  }
  return isJson ? res.json() : res.text();
}

export async function startJob({
  ref,
  file,
  length
}: {
  ref?: string;
  file?: File | null;
  length?: "default" | "extended";
}) {
  const form = new FormData();
  if (ref) form.append("ref", ref);
  if (length) form.append("length", length);
  if (file) form.append("pdf", file);
  const res = await fetch(api("/api/v1/summaries"), {
    method: "POST",
    body: form
  });
  return asJson(res);
}

export async function getJob(id: string) {
  const res = await fetch(api(`/api/v1/jobs/${id}`));
  return asJson(res);
}

export async function getSummary(id: string) {
  const res = await fetch(api(`/api/v1/summaries/${id}`));
  return asJson(res);
}
