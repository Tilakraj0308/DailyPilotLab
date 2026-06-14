from .gmail import GmailConnector
from .google_calendar import CalendarConnector
from .google_tasks import TasksConnector
from .notion import NotionConnector
from .registry import SUPPORTED_PROVIDERS

PROVIDER_MAP = {
    "google_calendar": CalendarConnector,
    "google_tasks": TasksConnector,
    "notion": NotionConnector,
    "gmail": GmailConnector,
}

__all__ = ["PROVIDER_MAP", "SUPPORTED_PROVIDERS"]
