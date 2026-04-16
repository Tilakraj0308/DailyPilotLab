from .google_calendar import CalendarConnector
from .google_tasks import TasksConnector

PROVIDER_MAP = {
    "google_calendar": CalendarConnector,
    "google_tasks": TasksConnector,
}
