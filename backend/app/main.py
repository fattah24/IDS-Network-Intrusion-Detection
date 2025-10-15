from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .db import Base, engine, get_db, SessionLocal
from .models import Alert
from .schemas import AlertOut
from .capture import CaptureService
from .websocket_manager import ws_manager
from .config import settings
import logging
from fastapi import HTTPException
app = FastAPI(title="IDS-Pro Backend")

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# --- Database setup ---
Base.metadata.create_all(bind=engine)

# --- Capture service ---
capture = CaptureService(SessionLocal)

@app.on_event("startup")
def on_startup():
    logging.getLogger("uvicorn").info(
        f"[Startup] IDS starting on interface='{settings.IFACE}' "
        f"(BPF='{settings.BPF}', threshold={settings.SYN_THRESHOLD}, window={settings.WINDOW_SEC}s)"
    )
    capture.start()

@app.on_event("shutdown")
def on_shutdown():
    logging.getLogger("uvicorn").info("[Shutdown] Stopping packet capture...")
    capture.stop()

# --- API endpoints ---
@app.get("/health")
def health():
    return {"ok": True}

@app.get("/alerts", response_model=list[AlertOut])
def list_alerts(limit: int = 200, db: Session = Depends(get_db)):
    q = db.query(Alert).order_by(Alert.id.desc()).limit(limit)
    return list(reversed(q.all()))

@app.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive messages
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)

@app.get("/", include_in_schema=False)
def home():
    return {"message": "Welcome to IDS-Pro Backend!", "routes": ["/health", "/alerts", "/docs"]}
@app.delete("/alerts")
def delete_alerts(db: Session = Depends(get_db)):
    try:
        n = db.query(Alert).delete()
        db.commit()
        return {"deleted": n}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))