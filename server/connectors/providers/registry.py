from __future__ import annotations

from enum import Enum
from pydantic import BaseModel

class ProviderKey(str, Enum):
    gmail = "gmail"
    google_calendar = "google_calendar"
    google_tasks = "google_tasks"

class ProviderConfig(BaseModel):
    key: ProviderKey
    display_name: str
    icon_name: str

SUPPORTED_PROVIDERS = {
    ProviderKey.google_calendar.value: ProviderConfig(
        key=ProviderKey.google_calendar,
        display_name="Google Calendar",
        icon_name="event",
    ),
    ProviderKey.google_tasks.value: ProviderConfig(
        key=ProviderKey.google_tasks,
        display_name="Google Tasks",
        icon_name="check-circle",
    ),
    ProviderKey.gmail.value: ProviderConfig(
        key=ProviderKey.gmail,
        display_name="Gmail",
        icon_name="mail",
    ),
}
