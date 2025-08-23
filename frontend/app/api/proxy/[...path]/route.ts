import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

const API_BASE =
  process.env.API_BASE || process.env.NEXT_PUBLIC_API_BASE || "";

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "content-length",
]);

function clean(h: Headers) {
  const out = new Headers(h);
  HOP_BY_HOP.forEach(k => out.delete(k));
  return out;
}

function makeUrl(req: NextRequest, segments: string[]) {
  const path = "/" + (segments ?? []).map(encodeURIComponent).join("/");
  return new URL(path + req.nextUrl.search, API_BASE).toString();
}

async function forward(req: NextRequest, segments: string[]) {
  if (!API_BASE) {
    return new Response(
      JSON.stringify({
        error: "API base not set",
        hint:
          "Set API_BASE (preferred) or NEXT_PUBLIC_API_BASE to your backend URL, e.g. https://layscience.onrender.com",
      }),
      { status: 500, headers: { "content-type": "application/json" } },
    );
  }

  const needsBody = !["GET", "HEAD"].includes(req.method);
  const body = needsBody ? await req.arrayBuffer() : undefined;

  const upstream = await fetch(makeUrl(req, segments), {
    method: req.method,
    headers: clean(req.headers),
    body,
    redirect: "follow",
    cache: "no-store",
  });

  const h = clean(upstream.headers);
  return new Response(upstream.body, { status: upstream.status, headers: h });
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
