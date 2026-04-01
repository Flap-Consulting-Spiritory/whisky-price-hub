import { NextRequest, NextResponse } from 'next/server'
import { createHash } from 'crypto'

export function middleware(request: NextRequest) {
  const expectedUsername = process.env.AUTH_USERNAME
  const expectedPassword = process.env.AUTH_PASSWORD

  const expectedToken = createHash('sha256')
    .update(`${expectedUsername}:${expectedPassword}`)
    .digest('hex')

  const sessionCookie = request.cookies.get('wph_session')?.value

  if (sessionCookie === expectedToken) {
    return NextResponse.next()
  }

  const loginUrl = new URL('/login', request.url)
  return NextResponse.redirect(loginUrl)
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|login|api/auth).*)'],
}
