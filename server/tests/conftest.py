"""Ensure env vars exist before test modules import server packages that touch OpenAI."""

from __future__ import annotations

import os

os.environ.setdefault("OPENAPI", "sk-test-dummy-key-for-pytest")
