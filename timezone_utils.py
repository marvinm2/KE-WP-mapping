"""
Timezone utilities for consistent local time display
"""

from datetime import datetime
import pytz


def get_local_timezone():
    """Get the Europe/Amsterdam timezone"""
    return pytz.timezone('Europe/Amsterdam')


def get_local_now():
    """Get current datetime in Europe/Amsterdam timezone"""
    local_tz = get_local_timezone()
    return datetime.now(local_tz)


def format_local_datetime(dt=None, format_str="%Y-%m-%d %H:%M:%S %Z"):
    """
    Format datetime for local timezone display
    
    Args:
        dt: datetime object (if None, uses current time)
        format_str: strftime format string
        
    Returns:
        Formatted datetime string in Europe/Amsterdam timezone
    """
    if dt is None:
        dt = get_local_now()
    elif dt.tzinfo is None:
        # Assume UTC if no timezone info
        utc_tz = pytz.UTC
        dt = utc_tz.localize(dt)
    
    local_tz = get_local_timezone()
    local_dt = dt.astimezone(local_tz)
    return local_dt.strftime(format_str)


def get_utc_timestamp():
    """Get UTC timestamp for database storage (compatibility)"""
    return datetime.utcnow()


def utc_to_local(utc_dt):
    """Convert UTC datetime to local timezone"""
    if utc_dt.tzinfo is None:
        utc_dt = pytz.UTC.localize(utc_dt)
    local_tz = get_local_timezone()
    return utc_dt.astimezone(local_tz)


def format_export_timestamp():
    """Get formatted timestamp for data exports"""
    return format_local_datetime(format_str="%Y-%m-%d %H:%M:%S %Z (%z)")


def format_admin_timestamp():
    """Get formatted timestamp for admin interface"""
    return format_local_datetime(format_str="%Y-%m-%d %H:%M:%S %Z")


def format_proposal_timestamp():
    """Get formatted timestamp for proposal system"""
    return format_local_datetime(format_str="%Y-%m-%d %H:%M:%S %Z")