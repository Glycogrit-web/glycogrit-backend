#!/usr/bin/env python3
"""
Shiprocket Local Proxy Server

This proxy server runs on your local machine and forwards Shiprocket API
requests from Railway backend, bypassing the IP block.

Usage:
    doppler run -- python3 shiprocket_proxy.py

Then update Railway env variable:
    SHIPROCKET_PROXY_URL=https://your-ngrok-url.ngrok.io
"""

import asyncio
import os

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Shiprocket Proxy")

# Allow Railway to call this proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to Railway domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SHIPROCKET_BASE = "https://apiv2.shiprocket.in/v1/external"


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "shiprocket-proxy"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_request(path: str, request: Request):
    """
    Forward all requests to Shiprocket API

    This bypasses Railway's IP block by making requests from your local machine.
    """

    # Build Shiprocket URL
    shiprocket_url = f"{SHIPROCKET_BASE}/{path}"

    # Get headers from original request
    headers = dict(request.headers)

    # Remove host header (will be set automatically)
    headers.pop("host", None)

    # Get request body if present
    body = await request.body()

    # Get query params
    params = dict(request.query_params)

    print(f"📡 Proxying: {request.method} /{path}")
    print(f"   Target: {shiprocket_url}")
    print(f"   Has Auth: {'Authorization' in headers}")

    try:
        # Forward request to Shiprocket (SSL verification disabled for local dev)
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.request(
                method=request.method,
                url=shiprocket_url,
                headers=headers,
                content=body if body else None,
                params=params,
            )

            print(f"   Response: {response.status_code}")

            # Return Shiprocket's response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )

    except Exception as e:
        print(f"❌ Proxy error: {str(e)}")
        return Response(
            content=str(e),
            status_code=500,
        )


if __name__ == "__main__":
    print("=" * 70)
    print("Shiprocket Local Proxy Server")
    print("=" * 70)
    print()
    print("This proxy forwards Shiprocket API requests from Railway backend")
    print("to Shiprocket via your local machine, bypassing the IP block.")
    print()
    print("Setup Instructions:")
    print("=" * 70)
    print()
    print("1. Install ngrok (if not installed):")
    print("   brew install ngrok")
    print()
    print("2. In Terminal 1 - Start this proxy:")
    print("   doppler run -- python3 shiprocket_proxy.py")
    print()
    print("3. In Terminal 2 - Expose proxy via ngrok:")
    print("   ngrok http 8001")
    print()
    print("4. Copy the ngrok HTTPS URL (e.g., https://abc123.ngrok.io)")
    print()
    print("5. Update Railway environment variable:")
    print("   SHIPROCKET_PROXY_URL=https://abc123.ngrok.io")
    print()
    print("6. Redeploy Railway backend")
    print()
    print("7. Test 'Ready to Ship' button")
    print()
    print("=" * 70)
    print()
    print("Starting proxy server on http://localhost:8001")
    print("Press Ctrl+C to stop")
    print()

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
