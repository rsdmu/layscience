import { NextRequest, NextResponse } from 'next/server'

// Catch-all proxy: /api/proxy/* -> NEXT_PUBLIC_API_BASE/* (defaults to http://localhost:8000)
export async function GET(req: NextRequest) { return handle(req) }
export async function POST(req: NextRequest) { return handle(req) }
export async function PUT(req: NextRequest) { return handle(req) }
export async function DELETE(req: NextRequest) { return handle(req) }
export async function PATCH(req: NextRequest) { return handle(req) }
export async function OPTIONS(req: NextRequest) { return handle(req) }

async function handle(req: NextRequest) {
  const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'
  const path = req.nextUrl.pathname.replace(/^\/api\/proxy/, '')
  const url = base.replace(/\/$/,'') + path
  const headers = new Headers(req.headers)
  headers.set('host', new URL(base).host) // helpful when behind proxies

  const init: RequestInit = {
    method: req.method,
    headers,
    body: ['GET','HEAD'].includes(req.method) ? undefined : await req.arrayBuffer(),
    cache: 'no-store',
    credentials: 'include'
  }
  const r = await fetch(url, init)
  const respHeaders = new Headers(r.headers)
  respHeaders.delete('content-encoding')
  const data = await r.arrayBuffer()
  return new NextResponse(data, { status: r.status, headers: respHeaders })
}

export const dynamic = 'force-dynamic'
