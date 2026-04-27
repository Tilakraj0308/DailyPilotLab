from __future__ import annotations

import pytest

from services.ideas_service import IdeaService


def test_invalid_filter_column_raises() -> None:
    svc = IdeaService()
    with pytest.raises(ValueError, match="Invalid raw_idea filter column"):
        svc.get_ideas_with_filter("user_id; drop table", True, "u1")


def test_remove_idea_topic_relation_requires_clause() -> None:
    svc = IdeaService()
    # Should not raise; no-op without idea_id or topic_id
    svc.remove_idea_topic_relation()
