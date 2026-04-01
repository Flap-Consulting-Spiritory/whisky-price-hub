import { NextRequest, NextResponse } from 'next/server'

export function middleware(request: NextRequest) {
  const authHeader = request.headers.get('authorization')
  const password = process.env.AUTH_PASSWORD

  if (authHeader) {
    const encoded = authHeader.split(' ')[1]
    const decoded = Buffer.from(encoded, 'base64').toString('utf-8')
    const inputPassword = decoded.split(':').slice(1).join(':')
    if (inputPassword === password) {
      return NextResponse.next()
    }
  }

  return new NextResponse('Unauthorized', {
    status: 401,
    headers: { 'WWW-Authenticate': 'Basic realm="WhiskyPriceHub"' },
  })
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
