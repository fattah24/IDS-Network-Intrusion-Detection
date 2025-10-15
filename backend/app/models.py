from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .db import Base

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    type = Column(String, index=True)     # e.g., PORT_SCAN
    src = Column(String, index=True)      # source IP
    details = Column(String)              # JSON string
