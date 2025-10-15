from dotenv import load_dotenv
import os
load_dotenv()

class Settings:

    IFACE: str = os.getenv("IFACE", "Wi-Fi")
    BPF: str = os.getenv("BPF", "tcp")
    SYN_THRESHOLD: int = int(os.getenv("SYN_THRESHOLD", "8"))  # low for testing
    WINDOW_SEC: int = int(os.getenv("WINDOW_SEC", "10"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./alerts.db")

settings = Settings()
print(f"[CONFIG] Using interface: {settings.IFACE}")
print(f"[CONFIG] BPF filter: {settings.BPF}")
print(f"[CONFIG] Threshold: {settings.SYN_THRESHOLD}")
print(f"[CONFIG] Window: {settings.WINDOW_SEC}s")
print(f"[CONFIG] Database: {settings.DATABASE_URL}")
