"""Analytics proxy routes for Plausible Analytics."""
import httpx
from fastapi import APIRouter, Request, Response, HTTPException
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/anonstats", tags=["analytics"])

# Plausible configuration
PLAUSIBLE_BASE_URL = "https://plausible.sbtl.dev"
PLAUSIBLE_SCRIPT_BASE = f"{PLAUSIBLE_BASE_URL}/js"
PLAUSIBLE_EVENT_URL = f"{PLAUSIBLE_BASE_URL}/api/event"

# Create a shared httpx client for connection pooling
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(30.0),
    follow_redirects=True,
    headers={
        "User-Agent": "Portfolio-Analytics-Proxy/1.0"
    }
)


@router.get("/js/{script_name:path}")
async def proxy_analytics_script(script_name: str) -> Response:
    """
    Proxy Plausible analytics scripts.
    
    This endpoint fetches the requested script from Plausible and returns it
    to the client, effectively hiding the actual analytics domain.
    """
    try:
        # Construct the full URL to the Plausible script
        script_url = f"{PLAUSIBLE_SCRIPT_BASE}/{script_name}"
        
        # Fetch the script from Plausible
        response = await http_client.get(script_url)
        response.raise_for_status()
        
        # Return the script with appropriate headers
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers={
                "Content-Type": "application/javascript",
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "X-Proxied-From": "plausible.sbtl.dev",
            }
        )
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to fetch analytics script: {e}")
        # Return a minimal error script that won't break the page
        return Response(
            content='console.warn("Analytics script unavailable");',
            status_code=200,  # Return 200 to prevent console errors
            headers={"Content-Type": "application/javascript"}
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching analytics script: {e}")
        return Response(
            content='console.warn("Analytics script unavailable");',
            status_code=200,
            headers={"Content-Type": "application/javascript"}
        )


@router.post("/event")
async def proxy_analytics_event(request: Request) -> Response:
    """
    Proxy Plausible analytics events.
    
    This endpoint forwards analytics events to Plausible, preserving
    important headers while hiding the actual analytics domain.
    """
    try:
        # Get the request body
        body = await request.body()
        
        # Prepare headers to forward to Plausible
        # We need to preserve certain headers for proper analytics tracking
        headers = {
            "Content-Type": request.headers.get("Content-Type", "application/json"),
            "User-Agent": request.headers.get("User-Agent", ""),
            "X-Forwarded-For": request.headers.get("X-Forwarded-For", request.client.host),
            "X-Forwarded-Proto": request.headers.get("X-Forwarded-Proto", "https"),
            "X-Forwarded-Host": "sbtl.dev",  # Use the actual site domain
        }
        
        # Forward the event to Plausible
        response = await http_client.post(
            PLAUSIBLE_EVENT_URL,
            content=body,
            headers=headers
        )
        
        # Return Plausible's response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers={
                "Content-Type": response.headers.get("Content-Type", "application/json"),
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to forward analytics event: {e}")
        # Return a 200 OK to prevent client-side errors
        # Analytics failures shouldn't break the user experience
        return Response(
            content='{"status":"error","message":"Event processing failed"}',
            status_code=200,
            headers={"Content-Type": "application/json"}
        )


@router.on_event("shutdown")
async def shutdown_event():
    """Close the HTTP client on shutdown."""
    await http_client.aclose()