"""Cross-platform user identity resolver.

Each messaging interface uses a different user ID format:
  Slack:    U12345678  or  user@company.com  (if resolve_user_identity=True)
  Telegram: 123456789  (numeric string)
  WhatsApp: +15551234567  (phone number)
  CLI:      UNIVERSAL_AGENT_USER env var
  AGUI:     forwarded_props.user_id

This module normalizes them to a canonical format so the same human
gets the same memories, learnings, and session context regardless of
which platform they message from.
"""

import json
import os
from pathlib import Path
from typing import Optional


_DATA_DIR = Path(os.getenv("UNIVERSAL_AGENT_DATA_DIR", "data"))
_LINKS_FILE = _DATA_DIR / "identity_links.json"


def canonicalize(platform: str, raw_id: str) -> str:
    """Convert a platform-specific ID to canonical format.

    Default format: {platform}:{raw_id}
    If the user has linked accounts, returns the primary canonical ID.
    """
    canonical = f"{platform}:{raw_id}"
    links = _load_links()
    # Check if this canonical ID is linked to another
    return links.get(canonical, canonical)


def link(id_a: str, id_b: str) -> None:
    """Link two canonical IDs so they resolve to the same identity.

    The first argument becomes the primary. Both will resolve to id_a.
    Call as: link("slack:user@co.com", "tg:123456")
    """
    links = _load_links()
    links[id_b] = id_a
    # Transitivity: anything pointing to id_b should now point to id_a
    for k, v in links.items():
        if v == id_b:
            links[k] = id_a
    _save_links(links)


def unlink(canonical_id: str) -> None:
    """Remove a linked identity, restoring it to its platform-native ID."""
    links = _load_links()
    links.pop(canonical_id, None)
    _save_links(links)


def get_all_links() -> dict:
    """Return the full identity link map. Useful for debugging."""
    return _load_links()


def resolve_from_request(
    platform: str,
    raw_id: str,
    email: Optional[str] = None,
) -> str:
    """Resolve user identity from interface request context.

    If email is available (Slack with resolve_user_identity), prefer it
    as the canonical ID since email is the most universal identifier.
    """
    if email:
        # Email is the best cross-platform identifier
        canonical = f"email:{email}"
        # Auto-link the platform ID to this email
        platform_id = f"{platform}:{raw_id}"
        links = _load_links()
        if platform_id not in links:
            links[platform_id] = canonical
            _save_links(links)
        return canonical

    return canonicalize(platform, raw_id)


# -- Persistence (simple JSON file) ------------------------------------------

def _load_links() -> dict:
    if _LINKS_FILE.is_file():
        return json.loads(_LINKS_FILE.read_text())
    return {}


def _save_links(links: dict) -> None:
    _LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LINKS_FILE.write_text(json.dumps(links, indent=2))
