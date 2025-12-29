"""
Wrapper so `core.personal_ai_assistant` resolves to the existing `ai_assistant` package.
"""

from ai_assistant.personal_ai_assistant import PersonalAIAssistant

__all__ = ["PersonalAIAssistant"]
