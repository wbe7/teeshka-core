"""Prompts and constants for Agents (Phase 11).

This module contains:
- Router Classification Prompts
- Router Category Constants
"""

from enum import StrEnum

DEFAULT_ROUTER_PROMPT = """Classify the user request into ONE category.

Categories:
- SRE: Kubernetes, pods, logs, cluster, deployments, nodes
- PERSONAL: Calendar, reminders, notes, memory ("запомни", "напомни")
- CRITIC: Architecture review, tech evaluation ("оцени", "стоит ли")
- GENERAL: Chit-chat, world knowledge, simple questions ("hi", "why is sky blue")
- UNKNOWN: Ambiguous, needs clarification

Examples:
- "почему под nginx в pending" → SRE
- "поставь встречу на 10:00" → PERSONAL
- "стоит ли переходить на monorepo" → CRITIC
- "привет, как дела?" → GENERAL
- "почему небо голубое" → GENERAL
- "sdafasdf" → UNKNOWN

User request: {query}

Output ONLY the category name.
"""


class RouterCategory(StrEnum):
    """Categories for Intent Classification."""

    SRE = "SRE"
    PERSONAL = "PERSONAL"
    CRITIC = "CRITIC"
    GENERAL = "GENERAL"
    UNKNOWN = "UNKNOWN"
