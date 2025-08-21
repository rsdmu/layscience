// API client for LayScience frontend
// This module provides functions for interacting with the serverless backend.

export type StartPayload = {
  input: { doi?: string; url?: string; s3_key?: string }
  mode: 'micro' | 'extended'
  privacy: 'process-only' | 'private' | 'public'
}

/*
 * Determine the base URL for the backend API.  When running locally
 * via `npm run dev` this should be set to something like
 * `http://localhost:8000` in your environment (e.g. in `.env.local`).
 * In production the value should be set to your deployed API gateway URL.
 *
 * Earlier versions of this file relied only on NEXT_PUBLIC_API_BASE or
 * NEXT_PUBLIC_API_BASE_URL.  If neither environment variable is present
 * we now fall back to an empty string, which causes fetch to use a
 * relative path.  This allows front‑end code to proxy API calls via
 * Next.js (app/api) routes without running into CORS errors.
 */
export const API_BASE: string =
  (process.env.NEXT_PUBLIC_API_BASE as string | undefined) ||
  (process.env.NEXT_PUBLIC_API_BASE_URL as string | undefined) ||
  ''

/**
 * Throw if the API base is not configured.  We treat an empty string
 * as meaning “relative requests to the current origin” which is fine
 * when using Next.js API routes to proxy backend requests.  Only
 * completely undefined values (which should never happen) will cause
 * an error.
 */
function requireApiBase(): string {
  if (API_BASE === undefined) {
    throw new Error('API base URL not configured')
  }
  return API_BASE
}

/**
 * Ensure the response was successful and parse JSON.  If the request
 * fails (e.g. network error) a friendlier error message will be
 * surfaced to the caller.
 */
async function ok<T = any>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || res.statusText)
  }
  return (await res.json()) as T
}

/**
 * POST to /upload-url.  Returns a presigned S3 URL and associated key
 * used for subsequent summarisation requests.  When API_BASE is empty
 * the request will be routed via a local API endpoint.
 */
export async function getUploadUrl(): Promise<{ key: string; url: string }> {
  const base = requireApiBase()
  const endpoint = base ? `${base}/upload-url` : '/api/proxy/upload-url'
  const r = await fetch(endpoint, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ content_type: 'application/pdf' }),
    // Explicitly disable caching and ensure CORS credentials are included.
    mode: 'cors',
    cache: 'no-store',
  })
  return ok(r)
}

/**
 * Start a summarisation job.  The payload contains the input (DOI, URL
 * or S3 key), the desired summary mode and the privacy level.
 */
export async function startJob(payload: StartPayload): Promise<{ id: string; status: string }> {
  const base = requireApiBase()
  const endpoint = base ? `${base}/summaries` : '/api/proxy/summaries'
  const r = await fetch(endpoint, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
    mode: 'cors',
    cache: 'no-store',
  })
  return ok(r)
}

/**
 * Poll the status of a running summarisation job by ID.  Returns the
 * current status and the job ID.  Once the status returns `done`
 * callers should fetch the summary via getSummary().
 */
export async function getStatus(id: string): Promise<{ id: string; status: string }> {
  const base = requireApiBase()
  const path = `summaries/status?id=${encodeURIComponent(id)}`
  const endpoint = base ? `${base}/${path}` : `/api/proxy/${path}`
  const r = await fetch(endpoint, {
    method: 'GET',
    mode: 'cors',
    cache: 'no-store',
  })
  return ok(r)
}

/**
 * Retrieve a completed summary by ID.  Returns the full summary data
 * including lay summary, evidence sentences and jargon definitions.
 */
export async function getSummary(id: string): Promise<any> {
  const base = requireApiBase()
  const path = `summaries/${encodeURIComponent(id)}`
  const endpoint = base ? `${base}/${path}` : `/api/proxy/${path}`
  const r = await fetch(endpoint, {
    method: 'GET',
    mode: 'cors',
    cache: 'no-store',
  })
  return ok(r)
}

/**
 * Translate a summary to a target language.  Requires a job ID and a
 * target language code (e.g. "fr", "es", etc.).
 */
export async function translateSummary(id: string, target: string): Promise<any> {
  const base = requireApiBase()
  const path = `summaries/${encodeURIComponent(id)}/translate`
  const endpoint = base ? `${base}/${path}` : `/api/proxy/${path}`
  const r = await fetch(endpoint, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ target_language: target }),
    mode: 'cors',
    cache: 'no-store',
  })
  return ok(r)
}