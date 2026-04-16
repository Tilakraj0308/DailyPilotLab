"""Google Tasks tools — auto-collected CRUD definitions."""

from .create import TOOL_DEFINITIONS as _create
from .read import TOOL_DEFINITIONS as _read
from .update import TOOL_DEFINITIONS as _update
from .delete import TOOL_DEFINITIONS as _delete

TOOL_DEFINITIONS: list[dict] = [*_read, *_create, *_update, *_delete]
