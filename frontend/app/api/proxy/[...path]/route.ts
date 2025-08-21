import { NextRequest, NextResponse } from 'next/server'

/*
 * Generic proxy route for the LayScience frontend.  All requests made to
 * `/api/proxy/<path>` are forwarded to the serverless backend defined by
 * the API_BASE environment variable.  This allows the frontend to avoid
 * cross‑origin (CORS) issues by keeping network requests on the same
 * origin as the Next.js app.  When deploying, set NEXT_PUBLIC_API_BASE
 * or NEXT_PUBLIC_API_BASE_URL in your environment.  An optional API_BASE
 * variable is also checked to support server‐side execution.
 */
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.API_BASE ||
  ''

if (!API_BASE) {
  console.warn(
    '[proxy] API_BASE is not configured; requests will fail. Set NEXT_PUBLIC_API_BASE or API_BASE in your environment.'
  )
}

async function forward(req: NextRequest, params: { path?: string[] }): Promise<NextResponse> {
  if (!API_BASE) {
    return new NextResponse('API_BASE not configured', { status: 500 })
  }
  const segments = params.path ?? []
  // Construct the target URL by concatenating segments and preserving the query string.
  const path = segments.join('/')
  const search = req.nextUrl.search
  const url = `${API_BASE}/${path}${search}`

  // Clone the request body if present.  Note: some methods (e.g. GET)
  // may not have a body.
  let body: any = undefined
  if (req.method !== 'GET' && req.method !== 'HEAD' && req.body) {
    const raw = await req.text()
    body = raw
  }

  // Forward the request to the backend.  Copy most headers except
  // host‑related headers which can interfere with API Gateway.
  const headers: Record<string, string> = {}
  req.headers.forEach((value, key) => {
    if (!['host', 'connection', 'content-length'].includes(key.toLowerCase())) {
      headers[key] = value
    }
  })

  const backendResp = await fetch(url, {
    method: req.method,
    headers,
    body,
    // Always enable CORS on the fetch call; API Gateway will honour CORS
    // configuration and return the appropriate headers.
    mode: 'cors',
  })

  // Create a NextResponse with the same status and body.
  const resBody = await backendResp.arrayBuffer()
  const response = new NextResponse(resBody, {
    status: backendResp.status,
    statusText: backendResp.statusText,
  })
  // Copy backend headers to the proxy response.
  backendResp.headers.forEach((value, key) => {
    response.headers.set(key, value)
  })
  // Always allow frontend to read the response from the proxy.
  response.headers.set('Access-Control-Allow-Origin', '*')
  return response
}

export async function GET(req: NextRequest, { params }: { params: { path: string[] } }) {
  return forward(req, params)
}

export async function POST(req: NextRequest, { params }: { params: { path: string[] } }) {
  return forward(req, params)
}

export async function PUT(req: NextRequest, { params }: { params: { path: string[] } }) {
  return forward(req, params)
}

export async function DELETE(req: NextRequest, { params }: { params: { path: string[] } }) {
  return forward(req, params)
}

export async function OPTIONS() {
  // Preflight response to satisfy CORS
  return new NextResponse(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': '*',
      'Access-Control-Max-Age': '86400',
    },
  })
}