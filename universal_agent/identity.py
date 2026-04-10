# Cross-platform user identity resolver
#
# Each messaging interface uses a different user ID format:
#   Slack:    U12345678  or  user@company.com  (if resolve_user_identity=True)
#   Telegram: 123456789  (numeric string)
#   WhatsApp: +15551234567  (phone number)
#   CLI:      UNIVERSAL_AGENT_USER env var
#   AGUI:     forwarded_props.user_id
#
# This module normalizes them to a canonical format so the same human
# gets the same memories and session context across platforms.

import json
from pathlib import Path
from typing import Optional

from universal_agent.db import DATA_DIR

_LINKS_FILE = DATA_DIR / "identity_links.json"
_links_cache: Optional[dict] = None


def canonicalize(platform: str, raw_id: str) -> str:
    canonical = f"{platform}:{raw_id}"
    links = _load_links()
    return links.get(canonical, canonical)


def link(id_a: str, id_b: str) -> None:
    links = _load_links()
    links[id_b] = id_a
    # Transitivity: anything pointing to id_b should now point to id_a
    for k, v in list(links.items()):
        if v == id_b:
            links[k] = id_a
    _save_links(links)


def unlink(canonical_id: str) -> None:
    links = _load_links()
    links.pop(canonical_id, None)
    _save_links(links)


def get_all_links() -> dict:
    return _load_links()


def resolve_from_request(
    platform: str,
    raw_id: str,
    email: Optional[str] = None,
) -> str:
    # Email is the best cross-platform identifier
    if email:
        canonical = f"email:{email}"
        platform_id = f"{platform}:{raw_id}"
        if _load_links().get(platform_id) != canonical:
            link(canonical, platform_id)
        return canonical

    return canonicalize(platform, raw_id)


def get_agent_session_id(canonical_user_id: str) -> str:
    return f"universal:{canonical_user_id}"


# -- Persistence with in-memory cache ----------------------------------------

def _load_links() -> dict:
    global _links_cache
    if _links_cache is not None:
        return _links_cache
    if _LINKS_FILE.is_file():
        _links_cache = json.loads(_LINKS_FILE.read_text())
    else:
        _links_cache = {}
    return _links_cache


def _save_links(links: dict) -> None:
    global _links_cache
    _LINKS_FILE.write_text(json.dumps(links, indent=2))
    _links_cache = links
