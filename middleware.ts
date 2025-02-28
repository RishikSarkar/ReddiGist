import { NextResponse } from 'next/server'
import { getToken } from 'next-auth/jwt'
import { NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname
  
  const isPublicPath = path === '/signin'
  const isProtectedPath = ['/dashboard', '/saved'].includes(path)
  
  const token = await getToken({ 
    req: request,
    secret: process.env.NEXTAUTH_SECRET
  })
  
  if (isProtectedPath && !token) {
    return NextResponse.redirect(new URL('/signin', request.url))
  }
  
  if (isPublicPath && token) {
    return NextResponse.redirect(new URL('/', request.url))
  }
  
  return NextResponse.next()
}

export const config = {
  matcher: ['/', '/signin', '/dashboard', '/saved']
} 