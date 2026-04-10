"""Scheduled task delivery helper.

The Agno scheduler runs the agent and stores results in the DB,
but does NOT auto-send to messaging platforms. This module wraps
schedule creation to inject delivery instructions into the prompt
so the agent sends results to the right place.
"""

from typing import Optional


def build_delivered_prompt(
    task: str,
    platform: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> str:
    """Wrap a task prompt with delivery instructions.

    If platform/chat_id are provided, the agent is told to send results
    there after completing the task. Otherwise, results are stored in DB only.
    """
    if not platform or not chat_id:
        return task

    delivery = (
        f"\n\nAfter completing the task above, send the result as a message "
        f"to {platform} chat {chat_id}."
    )
    return task + delivery


def build_schedule_payload(
    message: str,
    platform: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> dict:
    """Build a schedule payload with delivery metadata.

    The message field is required by Agno's SchedulerTools validation.
    Delivery metadata is stored alongside for tracking.
    """
    prompt = build_delivered_prompt(message, platform, chat_id)
    payload = {"message": prompt}
    if platform:
        payload["_delivery_platform"] = platform
    if chat_id:
        payload["_delivery_chat_id"] = chat_id
    return payload
