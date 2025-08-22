import type { NextRequest } from "next/server";

// Force Node runtime; safer for multipart/form-data pass-through
export const runtime = "nodejs";
// Disable static caching
export const dynamic = "force-dynamic";
// Give longer time window if needed (Vercel Pro/Enterprise)
export const maxDuration = 60;

const DEFAULT_DEV_BASE = "http://127.0.0.1:8000";

// Prefer server-only env; fall back to public if you really need
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
];

function sanitizeHeaders(src: Headers) {
  const h = new Headers(src);
  for (const k of HOP_BY_HOP) h.delete(k);
  return h;
}

function buildUpstreamUrl(base: string, req: NextRequest, segments: string[]) {
  const rel = (segments ?? []).join("/");
  const qs = req.nextUrl.search ?? "";
  const path = rel.replace(/^\/+/, "");
  return new URL(path + qs, base).toString();
}

async function forwardOnce(req: NextRequest, base: string, bodyBuf?: ArrayBuffer) {
  const needsBody = req.method !== "GET" && req.method !== "HEAD";
  const url = buildUpstreamUrl(base, req, (req as any).params?.path ?? []);
  const res = await fetch(url, {
    method: req.method,
    headers: sanitizeHeaders(req.headers),
    body: needsBody ? bodyBuf : undefined,
    redirect: "follow",
    cache: "no-store",
  });

  const outHeaders = new Headers(res.headers);
  // Same-origin so not strictly required; harmless
  outHeaders.set("Access-Control-Allow-Origin", "*");
  return new Response(res.body, { status: res.status, headers: outHeaders });
}

async function handle(req: NextRequest, ctx: { params: { path?: string[] } }) {
  if (!RAW_BASE) {
    return new Response(
      JSON.stringify(
        {
          error: "API base is not set",
          hint: "Set API_BASE (preferred) or NEXT_PUBLIC_API_BASE to your backend URL (e.g. https://layscience.onrender.com)",
        },
        null,
        2
      ),
      { status: 500, headers: { "content-type": "application/json" } }
    );
  }

  const needsBody = req.method !== "GET" && req.method !== "HEAD";
  // Read once so we can retry without losing the stream
  const bodyBuf = needsBody ? await req.arrayBuffer() : undefined;

  try {
    return await forwardOnce(req, RAW_BASE, bodyBuf);
  } catch (err: any) {
    // Dev nicety
    try {
      const u = new URL(RAW_BASE);
      if (u.hostname === "localhost") {
        u.hostname = "127.0.0.1";
        return await forwardOnce(req, u.toString(), bodyBuf);
      }
    } catch {}
    return new Response(
      JSON.stringify(
        {
          error: "Upstream fetch failed",
          message: String(err?.message || err),
          base: RAW_BASE,
          hint: RAW_BASE.includes("localhost")
            ? "In prod, localhost points to Vercel, not your machine. Use a public URL like https://layscience.onrender.com"
            : "Check API_BASE and that your backend ALLOWED_ORIGINS includes your frontend origin.",
        },
        null,
        2
      ),
      { status: 502, headers: { "content-type": "application/json" } }
    );
  }
}

export { handle as GET, handle as POST, handle as PUT, handle as PATCH, handle as DELETE, handle as OPTIONS };
