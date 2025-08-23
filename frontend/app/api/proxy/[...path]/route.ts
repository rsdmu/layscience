import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
// If your account allows, give more time for large uploads
export const maxDuration = 60;

const DEFAULT_DEV_BASE = "http://127.0.0.1:8000";

// Prefer server-only API_BASE, fall back to NEXT_PUBLIC for convenience
const RAW_BASE =
  process.env.API_BASE ??
  process.env.NEXT_PUBLIC_API_BASE ??
  (process.env.NODE_ENV === "development" ? DEFAULT_DEV_BASE : "");

const HOP_BY_HOP = [
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
  // Strip origin so backend CORS rules don't see the browser origin
  "origin",
];

function cleanReqHeaders(h: Headers) {
  const out = new Headers(h);
  for (const k of HOP_BY_HOP) out.delete(k);
  return out;
}

function makeUrl(base: string, segments: string[], search: string) {
  const path = "/" + (segments ?? []).map(s => encodeURIComponent(s)).join("/");
  return new URL(path + (search || ""), base).toString();
}

async function forwardOnce(
  req: NextRequest,
  base: string,
  segments: string[],
  bodyBuf?: ArrayBuffer
) {
  const needsBody = req.method !== "GET" && req.method !== "HEAD";
  const url = makeUrl(base, segments, req.nextUrl.search);

  // Send to upstream
  const upstream = await fetch(url, {
    method: req.method,
    headers: cleanReqHeaders(req.headers),
    body: needsBody ? bodyBuf : undefined,
    redirect: "follow",
    cache: "no-store",
  });

  // ---- Buffer the response so we don't lose the body ----
  const buf = await upstream.arrayBuffer();

  // Build safe response headers
  const out = new Headers(upstream.headers);
  // We provide raw, decoded bytes here; remove conflicting encoding headers
  out.delete("content-encoding");
  out.delete("transfer-encoding");
  // Set correct length (helps curl & some browsers)
  out.set("content-length", String(buf.byteLength));
  // CORS not strictly needed for same-origin proxy, harmless anyway:
  out.set("Access-Control-Allow-Origin", "*");
  // Optional: expose a debug header
  out.set("x-proxy-target", url);

  return new Response(buf, { status: upstream.status, headers: out });
}

async function handle(req: NextRequest, ctx: { params: { path?: string[] } }) {
  if (!RAW_BASE) {
    return new Response(
      JSON.stringify(
        {
          error: "API base not set",
          hint:
            "Set API_BASE (preferred) or NEXT_PUBLIC_API_BASE to your backend URL, e.g. https://layscience.onrender.com",
        },
        null,
        2
      ),
      { status: 500, headers: { "content-type": "application/json" } }
    );
  }

  const segments = ctx.params.path ?? [];
  const needsBody = req.method !== "GET" && req.method !== "HEAD";
  const bodyBuf = needsBody ? await req.arrayBuffer() : undefined;

  try {
    return await forwardOnce(req, RAW_BASE, segments, bodyBuf);
  } catch (err: any) {
    // Dev nicety: retry localhost with IPv4
    try {
      const u = new URL(RAW_BASE);
      if (u.hostname === "localhost") {
        u.hostname = "127.0.0.1";
        return await forwardOnce(req, u.toString(), segments, bodyBuf);
      }
    } catch {}
    return new Response(
      JSON.stringify(
        {
          error: "Upstream fetch failed",
          message: String(err?.message || err),
          base: RAW_BASE,
          hint: RAW_BASE.includes("localhost")
            ? "In prod, localhost points to Vercel. Use your public backend URL."
            : "Verify API_BASE and ALLOWED_ORIGINS on the backend.",
        },
        null,
        2
      ),
      { status: 502, headers: { "content-type": "application/json" } }
    );
  }
}

export function GET(req: NextRequest, ctx: { params: { path?: string[] } }) {
  return forward(req, ctx.params.path ?? []);
}
export function POST(req: NextRequest, ctx: { params: { path?: string[] } }) {
  return forward(req, ctx.params.path ?? []);
}
export function PUT(req: NextRequest, ctx: { params: { path?: string[] } }) {
  return forward(req, ctx.params.path ?? []);
}
export function PATCH(req: NextRequest, ctx: { params: { path?: string[] } }) {
  return forward(req, ctx.params.path ?? []);
}
export function DELETE(req: NextRequest, ctx: { params: { path?: string[] } }) {
  return forward(req, ctx.params.path ?? []);
}
export function OPTIONS(req: NextRequest, ctx: { params: { path?: string[] } }) {
  return forward(req, ctx.params.path ?? []);
}
export function HEAD(req: NextRequest, ctx: { params: { path?: string[] } }) {
  return forward(req, ctx.params.path ?? []);
}