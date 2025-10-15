from pydantic import BaseModel
from datetime import datetime

class AlertOut(BaseModel):
    id: int
    ts: datetime
    type: str
    src: str | None = None
    details: str | None = None
    class Config:
        from_attributes = True
