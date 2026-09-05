from .gmail import GmailConnector
from .google_calendar import CalendarConnector
from .google_tasks import TasksConnector
from .registry import SUPPORTED_PROVIDERS

PROVIDER_MAP = {
    "google_calendar": CalendarConnector,
    "google_tasks": TasksConnector,
    "gmail": GmailConnector,
}

__all__ = ["PROVIDER_MAP", "SUPPORTED_PROVIDERS"]
