// Unified API client for the frontend.
// If NEXT_PUBLIC_API_BASE is set, requests go directly to the backend.
// Otherwise they are proxied via /api/proxy to avoid CORS in local dev.

export type StartPayload = {
  input: { doi?: string; url?: string; file_id?: string }
  mode: 'micro' | 'extended'
  privacy: 'process-only' | 'private' | 'public'
}

function endpoint(path: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE
  if (base) return `${base}${path.startsWith('/')? '': '/'}${path}`
  return `/api/proxy${path.startsWith('/')? '': '/'}${path}`
}

async function ok(r: Response) {
  if (!r.ok) {
    let text = await r.text().catch(()=> '')
    throw new Error(`HTTP ${r.status}: ${text || r.statusText}`)
  }
  return r.json()
}

export async function upload(file: File) {
  const form = new FormData()
  form.append('file', file)
  const r = await fetch(endpoint('/api/v1/upload'), { method: 'POST', body: form, cache: 'no-store' })
  return ok(r)
}

export async function startJob(payload: StartPayload) {
  const r = await fetch(endpoint('/api/v1/jobs'), {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
    cache: 'no-store',
  })
  return ok(r)
}

export async function getStatus(id: string) {
  const r = await fetch(endpoint(`/api/v1/jobs/${encodeURIComponent(id)}`), { cache: 'no-store' })
  return ok(r)
}

export async function getSummary(id: string) {
  const r = await fetch(endpoint(`/api/v1/summaries/${encodeURIComponent(id)}`), { cache: 'no-store' })
  return ok(r)
}

export async function translateSummary(id: string, target_language: string) {
  const r = await fetch(endpoint(`/api/v1/summaries/${encodeURIComponent(id)}/translate`), {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ target_language }),
    cache: 'no-store'
  })
  return ok(r)
}
