import { NextRequest, NextResponse } from 'next/server';

// Get backend URL from environment with fallbacks
function getBackendUrl(): string {
  const BACKEND_URL = process.env.BACKEND_URL;
  
  if (BACKEND_URL) {
    return BACKEND_URL.replace(/\/$/, ''); // Remove trailing slash
  }
  
  // Fallback logic for different environments
  const isDevelopment = process.env.NODE_ENV === 'development';
  return isDevelopment ? 'http://localhost:8000' : 'http://backend:3100';
}

const BACKEND_URL = getBackendUrl();

export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const resolvedParams = await params;
  return handleProxyRequest(request, resolvedParams, 'GET');
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const resolvedParams = await params;
  return handleProxyRequest(request, resolvedParams, 'POST');
}

export async function PUT(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const resolvedParams = await params;
  return handleProxyRequest(request, resolvedParams, 'PUT');
}

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const resolvedParams = await params;
  return handleProxyRequest(request, resolvedParams, 'DELETE');
}

export async function PATCH(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const resolvedParams = await params;
  return handleProxyRequest(request, resolvedParams, 'PATCH');
}

async function handleProxyRequest(
  request: NextRequest, 
  params: { path: string[] }, 
  method: string
) {
  try {
    // Construct the target URL
    const pathSegments = params.path || [];
    const targetPath = pathSegments.join('/');
    const searchParams = request.nextUrl.searchParams.toString();
    const targetUrl = `${BACKEND_URL}/${targetPath}${searchParams ? `?${searchParams}` : ''}`;

    // Prepare headers (exclude host and other problematic headers)
    const headers = new Headers();
    request.headers.forEach((value, key) => {
      if (!['host', 'x-forwarded-for', 'x-forwarded-proto', 'x-forwarded-host'].includes(key.toLowerCase())) {
        headers.set(key, value);
      }
    });

    // Prepare request body for methods that support it
    let body = undefined;
    if (['POST', 'PUT', 'PATCH'].includes(method) && request.body) {
      body = await request.text();
    }

    // Make the proxied request
    const response = await fetch(targetUrl, {
      method,
      headers,
      body,
    });

    // Handle streaming responses (for SSE endpoints)
    if (response.headers.get('content-type')?.includes('text/event-stream')) {
      return new NextResponse(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: {
          'Content-Type': response.headers.get('content-type') || 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      });
    }

    // Handle regular responses
    const responseBody = await response.text();
    
    return new NextResponse(responseBody, {
      status: response.status,
      statusText: response.statusText,
      headers: {
        'Content-Type': response.headers.get('content-type') || 'application/json',
      },
    });

  } catch (error) {
    console.error('Proxy request failed:', error);
    return NextResponse.json(
      { error: 'Backend request failed', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}