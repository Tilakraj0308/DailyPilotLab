from .gmail import GmailConnector
from .google_calendar import CalendarConnector
from .google_tasks import TasksConnector
from .notion import NotionConnector

PROVIDER_MAP = {
    "google_calendar": CalendarConnector,
    "google_tasks": TasksConnector,
    "notion": NotionConnector,
    "gmail": GmailConnector,
}
