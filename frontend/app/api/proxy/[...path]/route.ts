// app/api/proxy/[...path]/route.ts
const DEFAULT_BASE = "http://127.0.0.1:8000";
const RAW_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  (process.env.NODE_ENV === "development" ? DEFAULT_BASE : "");

function joinUrl(base: string, path: string) {
  const b = new URL(base);
  const full = new URL(path.replace(/^\/+/, ""), b); // safe join
  return full.toString();
}

async function forwardOnce(req: Request, base: string, segments: string[], buf?: ArrayBuffer) {
  const path = (segments || []).join("/");
  const url = joinUrl(base, path);

  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("content-length");

  const bodyNeeded = !(req.method === "GET" || req.method === "HEAD");
  const body = bodyNeeded ? (buf ?? (await req.arrayBuffer())) : undefined;

  const init: RequestInit = {
    method: req.method,
    headers,
    body,
    redirect: "manual",
    // @ts-expect-error: Node fetch streaming flag
    duplex: bodyNeeded ? "half" : undefined
  };

  const resp = await fetch(url, init);
  const proxyHeaders = new Headers(resp.headers);
  proxyHeaders.set("Access-Control-Allow-Origin", "*");
  return new Response(resp.body, { status: resp.status, headers: proxyHeaders });
}

async function handle(req: Request, { params }: { params: { path?: string[] } }) {
  if (!RAW_BASE) {
    return new Response(
      JSON.stringify(
        {
          error: "NEXT_PUBLIC_API_BASE is not set",
          hint: "Set NEXT_PUBLIC_API_BASE to your backend URL"
        },
        null,
        2
      ),
      {
        status: 500,
        headers: { "content-type": "application/json" }
      }
    );
  }

  const segments = params.path || [];
  let buf: ArrayBuffer | undefined;

  // Read body once to allow retry without losing the stream
  if (!(req.method === "GET" || req.method === "HEAD")) {
    buf = await req.arrayBuffer();
  }

  try {
    return await forwardOnce(req, RAW_BASE, segments, buf);
  } catch (err: any) {
    // If the base uses localhost, retry with 127.0.0.1 to avoid IPv6 (::1) pitfalls
    try {
      const u = new URL(RAW_BASE);
      if (u.hostname === "localhost") {
        u.hostname = "127.0.0.1";
        return await forwardOnce(req, u.toString(), segments, buf);
      }
    } catch {
      // ignore URL parsing errors and fall through to diagnostic response
    }

    const info = {
      error: "Upstream fetch failed",
      message: String(err?.message || err),
      base: RAW_BASE,
      hint: RAW_BASE.includes("localhost")
        ? "Your backend may be bound to IPv4 only. Try NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 or start uvicorn with --host ::"
        : "Check that the backend is reachable and ALLOWED_ORIGINS includes your frontend origin."
    };
    return new Response(JSON.stringify(info, null, 2), {
      status: 502,
      headers: { "content-type": "application/json" }
    });
  }
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
export const OPTIONS = handle;
