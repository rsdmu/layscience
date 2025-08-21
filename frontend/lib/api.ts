export type StartPayload = {
  input: { doi?: string; url?: string; s3_key?: string };
  mode: 'micro' | 'extended';
  privacy: 'process-only' | 'private' | 'public';
}
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL!

async function ok(res: Response) {
  if (!res.ok) {
    const text = await res.text().catch(()=> '')
    throw new Error(text || res.statusText)
  }
  return res.json()
}

export async function getUploadUrl() {
  const r = await fetch(`${API_BASE}/upload-url`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ content_type: 'application/pdf' }) })
  return ok(r) as Promise<{ key: string, url: string }>
}

export async function startJob(payload: StartPayload) {
  const r = await fetch(`${API_BASE}/summaries`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) })
  return ok(r) as Promise<{ id: string, status: string }>
}

export async function getStatus(id: string) {
  const r = await fetch(`${API_BASE}/summaries/status?id=${encodeURIComponent(id)}`)
  return ok(r) as Promise<{ id: string, status: string }>
}

export async function getSummary(id: string) {
  const r = await fetch(`${API_BASE}/summaries/${id}`)
  return ok(r)
}

export async function translateSummary(id: string, target: string) {
  const r = await fetch(`${API_BASE}/summaries/${id}/translate`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ target_language: target }) })
  return ok(r)
}
