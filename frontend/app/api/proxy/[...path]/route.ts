import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const DEFAULT_DEV_BASE = "http://127.0.0.1:8000";

// Prefer server-only, fall back to NEXT_PUBLIC
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

function cleanHeaders(h: Headers) {
  const out = new Headers(h);
  for (const k of HOP_BY_HOP) out.delete(k);
  return out;
}

function makeUrl(base: string, segments: string[], search: string) {
  const path = "/" + (segments ?? []).map(s => encodeURIComponent(s)).join("/");
  return new URL((path || "/") + (search || ""), base).toString();
}

async function forwardOnce(
  req: NextRequest,
  base: string,
  segments: string[],
  bodyBuf?: ArrayBuffer
) {
  const needsBody = req.method !== "GET" && req.method !== "HEAD";
  const url = makeUrl(base, segments, req.nextUrl.search);
  const res = await fetch(url, {
    method: req.method,
    headers: cleanHeaders(req.headers),
    body: needsBody ? bodyBuf : undefined,
    redirect: "follow",
    cache: "no-store",
  });
  const outHeaders = new Headers(res.headers);
  outHeaders.set("Access-Control-Allow-Origin", "*");
  return new Response(res.body, { status: res.status, headers: outHeaders });
}

async function handle(
  req: NextRequest,
  ctx: { params: { path?: string[] } }
) {
  if (!RAW_BASE) {
    return new Response(
      JSON.stringify(
        {
          error: "API base not set",
          hint:
            "Set API_BASE (preferred) or NEXT_PUBLIC_API_BASE to e.g. https://layscience.onrender.com",
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
            ? "In prod, localhost is Vercel. Use your public backend URL."
            : "Verify API_BASE and ALLOWED_ORIGINS on the backend.",
        },
        null,
        2
      ),
      { status: 502, headers: { "content-type": "application/json" } }
    );
  }
}

export { handle as GET, handle as POST, handle as PUT, handle as PATCH, handle as DELETE, handle as OPTIONS };
