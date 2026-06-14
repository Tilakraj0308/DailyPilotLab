"""Google Calendar tools."""

from .read import TOOL_DEFINITIONS as _read
from .create import TOOL_DEFINITIONS as _create

TOOL_DEFINITIONS: list[dict] = [*_read, *_create]
