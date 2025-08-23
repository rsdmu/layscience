// frontend/app/api/proxy/[...path]/route.ts
import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

const DEFAULT_DEV_BASE = "http://127.0.0.1:8000";

const RAW_BASE =
  process.env.API_BASE ??
  process.env.NEXT_PUBLIC_API_BASE ??
  (process.env.NODE_ENV === "development" ? DEFAULT_DEV_BASE : "");

// Hop‑by‑hop headers that must not be forwarded
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

function cleanReqHeaders(h: Headers) {
  const out = new Headers(h);
  for (const k of HOP_BY_HOP) out.delete(k);
  return out;
}

function makeUrl(base: string, segments: string[], search: string) {
  const path = "/" + (segments ?? []).map(s => encodeURIComponent(s)).join("/");
  return new URL(path + (search || ""), base).toString();
}

async function forward(req: NextRequest, segments: string[]) {
  if (!RAW_BASE) {
    return new Response(
      JSON.stringify(
        {
          error: "API base not set",
          hint:
            "Set API_BASE (preferred) or NEXT_PUBLIC_API_BASE to your backend URL, e.g. https://layscience.onrender.com",
        },
        null,
        2,
      ),
      { status: 500, headers: { "content-type": "application/json" } },
    );
  }

  const needsBody = req.method !== "GET" && req.method !== "HEAD";
  const bodyBuf = needsBody ? await req.arrayBuffer() : undefined;
  const url = makeUrl(RAW_BASE, segments, req.nextUrl.search);

  try {
    const upstream = await fetch(url, {
      method: req.method,
      headers: cleanReqHeaders(req.headers),
      body: needsBody ? bodyBuf : undefined,
      redirect: "follow",
      cache: "no-store",
    });

    // Return upstream response, removing hop-by-hop headers
    const h = new Headers(upstream.headers);
    for (const k of HOP_BY_HOP) h.delete(k);
    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: h,
    });
  } catch (err: any) {
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
        2,
      ),
      { status: 502, headers: { "content-type": "application/json" } },
    );
  }
}

// ---- Export explicit handlers (avoid 405 from missing methods) ----
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
