"""RPE Analysis Platform -- brand constants.

Single source of truth for product name, company, version, and display strings.
All user-facing strings derive from this file.

LEGACY CONVENTION: Session state keys and CSS classes retain the ``uap_`` / ``uap-``
prefix. These are internal to Streamlit and never appear in the UI. Renaming
114 session state refs across 7 files would risk silent data loss with no user
benefit. The prefix stays as a historical artifact.
"""

from __future__ import annotations

# Product identity
PRODUCT_NAME: str = "RPE Analysis Platform"
SHORT_NAME: str = "RPE"
COMPANY_NAME: str = "CSI | Velocity"
VERSION: str = "2.0"

# Display strings (derived from constants above)
PAGE_TITLE: str = SHORT_NAME
TAGLINE: str = f"{SHORT_NAME} v{VERSION} // ANALYSIS PLATFORM"
CLI_DESCRIPTION: str = f"{PRODUCT_NAME}: ARS, Transaction, and ICS pipelines."
