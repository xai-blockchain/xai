# Personal AI Assistant Separation Notes

## Purpose
This document explains how the Personal AI assistant is fully separated from the collective AI/governance stack so auditors can verify there is no cross-functionality.

## Key separation points
- **Separate package**: The assistant lives in `ai_assistant/personal_ai_assistant.py`, with only a thin wrapper under `core/personal_ai_assistant.py` to preserve legacy imports.
- **No governance imports**: The assistant package does not reference any DAO, governance proposals, or aggregate AI pools—only the blockchain node it assists and the safety controls.
- **Dedicated API surface**: All `/personal-ai/*` endpoints in `core/api_extensions.py` feed requests into the assistant; they do not execute governance mutations or consensus changes.
- **User-owned AI keys**: Every request carries the user’s AI provider and API key in headers, so the assistant never touches global credentials or shared donation pools.
- **Documentation & tests**: `docs/PERSONAL_AI_FRONTEND_INTEGRATION.md`, the new `AI_ASSISTANT_SEPARATION.md`, and `tests/unit/test_personal_ai_api.py` highlight this split for auditors.

## Auditing tips
1. Inspect `ai_assistant/personal_ai_assistant.py` to see all capabilities run locally against the requesting user’s blockchain context.
2. Trace `/personal-ai` endpoints in `core/api_extensions.py`—they only serialize requests/responses and never modify governance tables.
3. Review `integrate_ai_systems.py` to confirm the assistant is initialized solely for Personal AI features and that governance components use other modules (e.g., `core.ai_governance`).
4. Check logs or safety control hooks; every request is registered via `ai_safety_controls` without cross-calling governance procedures.
