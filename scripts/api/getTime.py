from zoneinfo import ZoneInfo
from datetime import datetime
import asyncio

def get_24hr_time(timezone_str):
    try:
        tz = ZoneInfo(timezone_str)
    except Exception:
        return f"Unknown timezone: {timezone_str}"
    
    now = datetime.now(tz)
    return now.strftime("%H:%M:%S")

def get_12hr_time(timezone_str):
    try:
        tz = ZoneInfo(timezone_str)
    except Exception:
        return f"Unknown timezone: {timezone_str}"
    
    now = datetime.now(tz)
    return now.strftime("%I:%M:%S %p")