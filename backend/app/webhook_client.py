import httpx
from pydantic import BaseModel
import hmac
import hashlib
from typing import Any
import json
import uuid

# Define this in the cloud config, or hardcode for now
WEBHOOK_SECRET = "your_webhook_secret_key"
NAS_URL = "http://localhost:8001/api/webhooks"

async def send_webhook(endpoint: str, payload: dict):
    """
    Sends a webhook payload to the NAS backend asynchronously.
    """
    try:
        # We need to serialize UUIDs properly before hashing
        def uuid_convert(obj):
            if isinstance(obj, uuid.UUID):
                return str(obj)
            raise TypeError
            
        body = json.dumps(payload, default=uuid_convert).encode('utf-8')
        signature = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{NAS_URL}{endpoint}",
                content=body,
                headers={
                    "X-Webhook-Signature": signature,
                    "Content-Type": "application/json"
                },
                timeout=5.0
            )
            print(f"Webhook {endpoint} sent successfully.")
    except Exception as e:
        print(f"Failed to send webhook {endpoint}: {e}")
