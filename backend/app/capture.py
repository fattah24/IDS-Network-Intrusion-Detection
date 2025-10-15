import threading, json, asyncio
from scapy.all import sniff
from sqlalchemy.orm import Session
from typing import Callable
from .detectors.portscan import PortScanDetector
from .config import settings
from .models import Alert
from .websocket_manager import ws_manager

class CaptureService:
    def __init__(self, db_factory: Callable[[], Session]):
        self.db_factory = db_factory
        self.detectors = [PortScanDetector(settings.SYN_THRESHOLD, settings.WINDOW_SEC)]
        self._stop = threading.Event()

    def start(self):
        threading.Thread(target=self._sniffer, daemon=True).start()

    def stop(self):
        self._stop.set()

    def _handle(self, pkt):
        print(pkt.summary())  # 👈 debug enabled
        for det in self.detectors:
            alert = det.process(pkt)
            if alert:
                self._persist_and_broadcast(alert)

    def _persist_and_broadcast(self, alert):
        with self.db_factory() as db:
            row = Alert(type=alert["type"], src=alert.get("src"), details=json.dumps(alert))
            db.add(row)
            db.commit()
            db.refresh(row)
            msg = json.dumps({
                "id": row.id,
                "ts": row.ts.isoformat() + "Z",
                "type": row.type,
                "src": row.src,
                "details": alert
            })

        # broadcast on the running loop (ignore if none)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(ws_manager.broadcast(msg))
        except RuntimeError:
            pass

    def _sniffer(self):
        sniff(
            iface=settings.IFACE,
            filter=settings.BPF,
            prn=self._handle,
            store=False,
            stop_filter=lambda _: self._stop.is_set()
        )
