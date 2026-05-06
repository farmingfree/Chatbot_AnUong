/* v7-safe */
import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function POST(req: NextRequest): Promise<NextResponse> {
  try {
    const apiUrl = process.env.API_URL
    if (!apiUrl) {
      return NextResponse.json(
        { error: '⚠️ Backend chưa cấu hình. Thêm API_URL vào .env.local' },
        { status: 503 }
      )
    }

    let body: unknown
    try {
      body = await req.json()
    } catch {
      return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
    }

    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 5000)

    let backendRes: Response
    try {
      backendRes = await fetch(`${apiUrl}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Internal-Key': process.env.INTERNAL_API_KEY ?? 'dev-key',
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      })
      clearTimeout(timer)
    } catch (fetchErr: unknown) {
      clearTimeout(timer)
      const msg = String(fetchErr)
      console.error('[chat] fetch error:', msg)
      return NextResponse.json(
        { error: '⚠️ Backend không khả dụng. Chạy: docker compose up -d' },
        { status: 503 }
      )
    }

    if (!backendRes.ok) {
      const text = await backendRes.text()
      return NextResponse.json(
        { error: `Backend error ${backendRes.status}: ${text.slice(0, 200)}` },
        { status: backendRes.status }
      )
    }

    // Stream response
    const responseBody = await backendRes.text()
    return NextResponse.json(
      { reply: responseBody },
      { status: 200 }
    )
  } catch (outerErr: unknown) {
    console.error('[chat] outer error:', outerErr)
    return NextResponse.json(
      { error: '⚠️ Lỗi server không xác định' },
      { status: 503 }
    )
  }
}
