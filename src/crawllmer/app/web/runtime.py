"""Streamlit runtime — initialises the API client for the UI."""

from __future__ import annotations

from crawllmer.app.web.api_client import CrawllmerApiClient
from crawllmer.core.config import get_settings

_settings = get_settings()

client = CrawllmerApiClient(base_url=_settings.api_base_url)
