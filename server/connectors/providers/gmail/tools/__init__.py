"""Gmail tools — aggregate CRUD tool definitions."""

from .create import TOOL_DEFINITIONS as _create
from .read import TOOL_DEFINITIONS as _read
from .update import TOOL_DEFINITIONS as _update

TOOL_DEFINITIONS: list[dict] = [*_read, *_create, *_update]
