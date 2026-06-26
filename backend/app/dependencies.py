# Rate limiting utilities

import time
from fastapi import Request, HTTPException
from typing import Callable

# In‑memory store: {"client_ip_endpoint": [timestamp1, timestamp2, ...]}
_rate_store: dict[str, list[float]] = {}

def rate_limiter(endpoint: str, limit: str = "5/minute") -> Callable[[Request], None]:
    """Return a FastAPI dependency that enforces a simple rate limit.

    `limit` format: "N/minute" or "N/second". Currently only minute granularity is used.
    """
    parts = limit.split('/')
    max_requests = int(parts[0])
    period = 60 if 'minute' in parts[1] else 1

    async def dependency(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{endpoint}"
        now = time.time()
        timestamps = _rate_store.get(key, [])
        # Remove timestamps older than period
        timestamps = [ts for ts in timestamps if now - ts < period]
        if len(timestamps) >= max_requests:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        timestamps.append(now)
        _rate_store[key] = timestamps
    return dependency
