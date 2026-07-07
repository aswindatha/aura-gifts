from pydantic import BaseModel
from typing import Optional

class WebhookOrderStatusUpdate(BaseModel):
    order_id: str
    step_id: str
    status: str
    proof_url: Optional[str] = None
