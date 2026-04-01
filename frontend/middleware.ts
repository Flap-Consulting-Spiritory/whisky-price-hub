import { NextRequest, NextResponse } from 'next/server'

async function computeToken(username: string, password: string): Promise<string> {
  const encoder = new TextEncoder()
  const data = encoder.encode(`${username}:${password}`)
  const hashBuffer = await crypto.subtle.digest('SHA-256', data)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('')
}

export async function middleware(request: NextRequest) {
  const expectedUsername = process.env.AUTH_USERNAME ?? ''
  const expectedPassword = process.env.AUTH_PASSWORD ?? ''

  const expectedToken = await computeToken(expectedUsername, expectedPassword)
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
