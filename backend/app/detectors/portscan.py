import time
from collections import defaultdict, deque
from scapy.layers.inet import TCP, IP

class PortScanDetector:
    def __init__(self, syn_threshold: int = 8, window_sec: int = 10):
        self.syn_threshold = syn_threshold
        self.window_sec = window_sec
        self.events = defaultdict(deque)  # src_ip -> deque[timestamps]

    def process(self, pkt):
        now = time.time()
        if pkt.haslayer(TCP) and pkt.haslayer(IP):
            tcp = pkt[TCP]
            # Count SYNs (S flag bit 0x02)
            if tcp.flags & 0x02 and not (tcp.flags & 0x10):  # exclude ACKed packets
                src = pkt[IP].src
                dq = self.events[src]
                dq.append(now)
                while dq and now - dq[0] > self.window_sec:
                    dq.popleft()
                if len(dq) >= self.syn_threshold:
                    return {
                        "type": "PORT_SCAN",
                        "src": src,
                        "count": len(dq),
                        "window_sec": self.window_sec
                    }
        return None
