from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MiniAppManifestEntry:
    """Definition of a mini-app as seen by the UI layer."""

    id: str
    name: str
    description: str
    app_type: str
    embed_url: str
    risk_focus: str  # low, medium, high
    triggers: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, risk_level: str, recommended_flow: str) -> dict[str, Any]:
        """Serialize the entry while injecting runtime recommendations."""
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "app_type": self.app_type,
            "embed_url": self.embed_url.format(risk_level=risk_level),
            "risk_focus": self.risk_focus,
            "triggers": self.triggers,
            "recommended_flow": recommended_flow,
            "aml_cues": self.metadata.get("aml_cues", []),
            "iframe_hint": self.metadata.get("iframe_hint", {"width": "100%", "height": "480px"}),
        }
        data.update(self.metadata.get("extras", {}))
        return data

class MiniAppRegistry:
    """Registry of embedded mini-apps driven by the personal AI + AML stack."""

    HIGH_RISK_LEVELS = {"high", "critical"}
    MEDIUM_RISK_LEVELS = {"medium"}

    def __init__(self):
        self._apps: list[MiniAppManifestEntry] = [
            MiniAppManifestEntry(
                id="community-pulse",
                name="Community Pulse Poll",
                description="Collects trader sentiment per block and keeps a live pulse available for GUIs.",
                app_type="poll",
                embed_url="https://miniapps.xai.network/polls/community-pulse?mode={risk_level}",
                risk_focus="low",
                triggers=["poll", "community", "feedback"],
                metadata={
                    "aml_cues": ["low-risk-fill", "safe-mode"],
                    "iframe_hint": {"width": "100%", "height": "420px"},
                    "extras": {"icon": "poll", "status_badge": "trusted"},
                },
            ),
            MiniAppManifestEntry(
                id="atomic-vote",
                name="One-Transaction Vote",
                description="Fast, privacy-preserving poll/vote flow that settles via HTLC-like swaps.",
                app_type="vote",
                embed_url="https://miniapps.xai.network/votes/atomic-swap?mode={risk_level}",
                risk_focus="medium",
                triggers=["vote", "swaps", "governance"],
                metadata={
                    "aml_cues": ["medium-risk-check", "dual-confirm"],
                    "extras": {"icon": "vote", "status_badge": "tempo"},
                },
            ),
            MiniAppManifestEntry(
                id="treasure-game",
                name="Treasure Hunt Game",
                description="Gamified experience that uses ledger data to describe ownership history and signed backfills.",
                app_type="game",
                embed_url="https://miniapps.xai.network/games/treasure-hunt?mode={risk_level}",
                risk_focus="high",
                triggers=["game", "explorer", "event"],
                metadata={
                    "aml_cues": ["high-risk-guard", "disclosure-overlay"],
                    "iframe_hint": {"width": "100%", "height": "520px"},
                    "extras": {"icon": "map", "status_badge": "adventures"},
                },
            ),
            MiniAppManifestEntry(
                id="aml-guard",
                name="AML Safety Companion",
                description="Shows the last high-risk alerts and lets users trigger compliance-safe next steps.",
                app_type="monitor",
                embed_url="https://miniapps.xai.network/tools/aml-guard?mode={risk_level}",
                risk_focus="high",
                triggers=["aml", "compliance", "alerts"],
                metadata={
                    "aml_cues": ["high-risk-guard", "notify"],
                    "iframe_hint": {"width": "100%", "height": "360px"},
                    "extras": {"icon": "shield", "status_badge": "guarded"},
                },
            ),
        ]

    def _recommend_flow(
        self, entry: MiniAppManifestEntry, risk_level: str, risk_score: float
    ) -> str:
        """Derive a simple flow hint based on the caller's risk context."""
        rl = risk_level.lower()
        if rl in self.HIGH_RISK_LEVELS:
            if entry.risk_focus == "high":
                return "cautious"
            return "limited"
        if rl in self.MEDIUM_RISK_LEVELS:
            if entry.risk_focus == "high":
                return "observe"
            return "balanced"
        if risk_score > 45 and entry.risk_focus == "medium":
            return "balanced"
        return "open"

    def build_manifest(self, risk_context: dict[str, Any]) -> list[dict[str, Any]]:
        """Return the manifest containing AML-aware recommendations."""
        risk_level = (risk_context.get("risk_level") or "clean").lower()
        risk_score = risk_context.get("risk_score", 0)
        return [
            entry.to_dict(
                risk_level=risk_level,
                recommended_flow=self._recommend_flow(entry, risk_level, risk_score),
            )
            for entry in self._apps
        ]
