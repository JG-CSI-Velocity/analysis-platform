"""Client ID + name input with optional registry auto-fill."""

from __future__ import annotations

import logging

import streamlit as st

logger = logging.getLogger(__name__)


@st.cache_resource(ttl=3600)
def _load_registry() -> dict:
    """Load client registry once, shared across sessions."""
    try:
        from ics_toolkit.client_registry import load_master_config, resolve_master_config_path

        path = resolve_master_config_path()
        if path:
            return load_master_config(path)
    except ImportError:
        logger.debug("ics_toolkit.client_registry not available; manual input only")
    except Exception:
        logger.debug("Failed to load client registry", exc_info=True)
    return {}


def render_client_selector(page_key: str) -> tuple[str, str]:
    """Client ID + name input with registry auto-fill.

    Returns (client_id, client_name) as stripped strings.
    """
    registry = _load_registry()

    c1, c2 = st.columns(2)
    with c1:
        client_id = st.text_input("Client ID", key=f"{page_key}_client_id", placeholder="e.g. 1453")
    with c2:
        default_name = ""
        if client_id.strip() and client_id.strip() in registry:
            cfg = registry[client_id.strip()]
            if hasattr(cfg, "client_name") and cfg.client_name:
                default_name = cfg.client_name
        client_name = st.text_input(
            "Client Name",
            key=f"{page_key}_client_name",
            value=default_name,
            placeholder="e.g. Connex CU",
        )

    return client_id.strip(), client_name.strip()
