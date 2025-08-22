// app/api/proxy/[...path]/route.ts
import type { NextRequest } from "next/server";

// Force Node runtime; safer for multipart/form-data pass-through
export const runtime = "nodejs";

const DEFAULT_DEV_BASE = "http://127.0.0.1:8000";

// Prefer server-only env; fall back to NEXT_PUBLIC for convenience
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
  const noLeading = rel.replace(/^\/+/, "");
  return new URL(noLeading + qs, base).toString();
}

async function handle(req: NextRequest, ctx: { params: { path?: string[] } }) {
  if (!RAW_BASE) {
    return new Response(
      JSON.stringify(
        {
          error: "API base is not set",
          hint:
            "Set API_BASE (preferred) or NEXT_PUBLIC_API_BASE to your backend URL e.g. https://layscience.onrender.com",
        },
        null,
        2
      ),
      { status: 500, headers: { "content-type": "application/json" } }
    );
  }

  const segments = ctx.params.path ?? [];
  const needsBody = req.method !== "GET" && req.method !== "HEAD";

  // Read request body once so we can retry without losing the stream.
  // (NOTE: For very large PDFs this buffers in memory; direct calls to backend
  // are better for huge files.)
  let bodyBuf: ArrayBuffer | undefined;
  if (needsBody) {
    bodyBuf = await req.arrayBuffer();
  }

  const forward = async (base: string) => {
    const url = buildUpstreamUrl(base, req, segments);
    const res = await fetch(url, {
      method: req.method,
      headers: sanitizeHeaders(req.headers),
      body: needsBody ? bodyBuf : undefined,
      redirect: "follow",
      cache: "no-store",
    });

    const outHeaders = new Headers(res.headers);
    // Not strictly required (same origin), but harmless:
    outHeaders.set("Access-Control-Allow-Origin", "*");

    return new Response(res.body, { status: res.status, headers: outHeaders });
  };

  try {
    return await forward(RAW_BASE);
  } catch (err: any) {
    // Dev nicety: if someone set localhost, retry with 127.0.0.1
    try {
      const u = new URL(RAW_BASE);
      if (u.hostname === "localhost") {
        u.hostname = "127.0.0.1";
        return await forward(u.toString());
      }
    } catch {
      /* ignore */
    }
    return new Response(
      JSON.stringify(
        {
          error: "Upstream fetch failed",
          message: String(err?.message || err),
          base: RAW_BASE,
          hint: RAW_BASE.includes("localhost")
            ? "In prod, localhost points to Vercel, not your machine. Use a public URL like https://layscience.onrender.com"
            : "Ensure API_BASE is correct and backend allows your origin in ALLOWED_ORIGINS.",
        },
        null,
        2
      ),
      { status: 502, headers: { "content-type": "application/json" } }
    );
  }
}

export { handle as GET, handle as POST, handle as PUT, handle as PATCH, handle as DELETE, handle as OPTIONS };
