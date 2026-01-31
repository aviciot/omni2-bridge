import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  if (request.nextUrl.pathname.startsWith('/api/')) {
    const backendUrl = process.env.BACKEND_URL || 'http://dashboard-backend:8500';
    const url = new URL(request.nextUrl.pathname, backendUrl);
    url.search = request.nextUrl.search;
    
    return NextResponse.rewrite(url);
  }
}

export const config = {
  matcher: '/api/:path*',
};
