import { NextRequest, NextResponse } from 'next/server'
import { createHash } from 'crypto'

export async function POST(request: NextRequest) {
  const { username, password } = await request.json()

  const expectedUsername = process.env.AUTH_USERNAME
  const expectedPassword = process.env.AUTH_PASSWORD

  if (username !== expectedUsername || password !== expectedPassword) {
    return NextResponse.json({ error: 'Invalid credentials' }, { status: 401 })
  }

  const token = createHash('sha256')
    .update(`${expectedUsername}:${expectedPassword}`)
    .digest('hex')

  const response = NextResponse.json({ ok: true })
  response.cookies.set('wph_session', token, {
    httpOnly: true,
    sameSite: 'strict',
    path: '/',
    secure: process.env.NODE_ENV === 'production',
  })
  return response
}
