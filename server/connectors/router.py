"""Backward-compatible import path; router implementation lives in `connectors.routes`."""

from connectors.routes import router

__all__ = ["router"]
