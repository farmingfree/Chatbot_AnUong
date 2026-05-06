import { NextRequest, NextResponse } from 'next/server'

const requestCounts = new Map<string, {count: number, resetAt: number}>()

export function middleware(req: NextRequest) {
  if (req.nextUrl.pathname.startsWith('/api/chat')) {
    const ip = req.headers.get('x-forwarded-for') ?? 'unknown'
    const now = Date.now()
    const record = requestCounts.get(ip)

    if (!record || now > record.resetAt) {
      requestCounts.set(ip, {count: 1, resetAt: now + 60000})
    } else if (record.count >= 30) {
      return NextResponse.json({error: 'Bạn đang gửi quá nhiều yêu cầu, thử lại sau 1 phút nhé!'}, {status: 429})
    } else {
      record.count++
    }
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/api/chat/:path*'],
}
