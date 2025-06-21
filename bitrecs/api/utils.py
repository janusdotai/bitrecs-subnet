import httpx
import bittensor as bt
from typing import Any, Union
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
    

def get_proxy_public_key(proxy_url: str) -> bytes:
    with httpx.Client(timeout=httpx.Timeout(30)) as client:
        response = client.get(
            f"{proxy_url}/public_key",
        )
    response.raise_for_status()
    pub_key = response.json()["public_key"]
    raw_bytes = bytes.fromhex(pub_key)
    return raw_bytes


def _get_api_key_header(request: Request) -> Any:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return auth_header


async def api_key_validator(self, request: Request, call_next) -> Response:
    if request.url.path in ["/favicon.ico"]:
        return await call_next(request)

    api_key = _get_api_key_header(request)
    if not api_key:
        bt.logging.error(f"ERROR - Request has no Authorization {request.client.host}")
        return JSONResponse(status_code=400, content={"detail": "Authorization is missing"})    
    
    bitrecs_api_key = self.bitrecs_api_key
    if not bitrecs_api_key:
        bt.logging.error(f"ERROR - MISSING BITRECS_API_KEY")
        return JSONResponse(status_code=500, content={"detail": "Server error - invalid API key"})
    if api_key != bitrecs_api_key:
        bt.logging.error(f"ERROR - INVALID API request key mismatch {request.client.host}")        
        return JSONResponse(status_code=401, content={"detail": "Invalid API key request"})
    
    #TODO: this gets called even after a RateLimitExeption has been raised
    try:
        response: Response = await call_next(request)
        return response
    except RateLimitExceeded as re:        
        bt.logging.error(f"ERROR api_key_validator 429 - {re}")
        return JSONResponse(status_code=429, 
                            content={"detail": "Rate limit exceeded"})
    except Exception as e:
        bt.logging.error(f"ERROR api_key_validator - {e}")
        return JSONResponse(status_code=500, 
                            content={"detail": "Internal server error - key validator"})


async def json_only_middleware(self, request: Request, call_next) -> Union[JSONResponse, Response]:
    if request.headers.get("Content-Type") != "application/json":
        return JSONResponse(
            status_code=415,  # Unsupported Media Type
            content={"detail": "Only JSON requests are allowed"}
        )
    response = await call_next(request)
    return response