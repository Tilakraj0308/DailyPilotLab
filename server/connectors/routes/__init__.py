"""Connector HTTP routes composed into a single APIRouter."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from utils.sync_concurrency import connector_slot_dependency

from connectors.routes import gmail_routes
from connectors.routes import google_tasks_routes
from connectors.routes import oauth_routes
from connectors.routes import tool_meta_routes

router = APIRouter(dependencies=[Depends(connector_slot_dependency)])
router.include_router(gmail_routes.router)
router.include_router(google_tasks_routes.router)
router.include_router(oauth_routes.router)
router.include_router(tool_meta_routes.router)
