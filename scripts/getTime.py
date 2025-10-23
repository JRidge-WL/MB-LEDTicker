# input: timezone (e.g., "America/New_York")
# outputs the current time in 24hr format for that timezone

import pytz
from datetime import datetime

def get_24hr_time(timezone_str):
    try:
        timezone = pytz.timezone(timezone_str)
    except pytz.UnknownTimeZoneError:
        return f"Unknown timezone: {timezone_str}"
    
    now = datetime.now(timezone)
    return now.strftime("%H:%M")

def get_12hr_time(timezone_str):
    try:
        timezone = pytz.timezone(timezone_str)
    except pytz.UnknownTimeZoneError:
        return f"Unknown timezone: {timezone_str}"
    
    now = datetime.now(timezone)
    return now.strftime("%I:%M %p")