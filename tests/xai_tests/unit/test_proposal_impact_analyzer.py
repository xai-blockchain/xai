"""Focused tests for ProposalImpactAnalyzer's production-grade analytics."""

from xai.core.ai_governance import ProposalImpactAnalyzer


def test_analysis_reflects_community_feedback():
    """Adoption likelihood responds to community sentiment and support data."""
    analyzer = ProposalImpactAnalyzer()
    positive_proposal = {
        "proposal_id": "prop-positive",
        "title": "Reduce wallet fees",
        "description": "Improve wallet UX and reduce fees across the ecosystem.",
        "impact_scope": "wallet",
        "community_feedback": {
            "sentiment_score": 0.92,
            "support_votes": 950,
            "opposition_votes": 40,
            "feature_requests": 180,
        },
        "estimated_minutes": 400,
        "expected_benefits": ["Lower fees", "Better wallet retention"],
    }

    negative_proposal = {
        "proposal_id": "prop-negative",
        "title": "Remove legacy RPC features",
        "description": "Breaking change that deprecates RPC endpoints and increases fees.",
        "impact_scope": "api",
        "community_feedback": {
            "sentiment_score": 0.25,
            "support_votes": 12,
            "opposition_votes": 310,
            "feature_requests": 5,
        },
        "estimated_minutes": 120,
        "known_risks": ["Requires client migration"],
    }

    historical = {"avg_feature_requests": 50}
    analysis_positive = analyzer.analyze_proposal_impact(positive_proposal, historical)
    analysis_negative = analyzer.analyze_proposal_impact(negative_proposal, historical)

    assert analysis_positive["community_impact"]["adoption_likelihood"] > 0.8
    assert analysis_negative["community_impact"]["adoption_likelihood"] < 0.5
    assert (
        analysis_positive["community_impact"]["stakeholder_groups"]["users"]["sentiment"]
        == "positive"
    )


def test_financial_analysis_considers_benefits_and_break_even():
    """Financial report must reflect cost/reward dynamics."""
    analyzer = ProposalImpactAnalyzer()
    financial = analyzer._analyze_financial_impact(  # pylint: disable=protected-access
        {
            "impact_scope": "wallet",
            "estimated_minutes": 1800,
            "cost_per_minute": 2.75,
            "specialist_roles": ["zk engineer", "security reviewer"],
            "expected_annual_savings_usd": 900000,
            "expected_revenue_increase_usd": 250000,
        }
    )

    assert financial["implementation_cost_usd"] > 0
    assert financial["cost_benefit_ratio"] > 1.0
    assert "Projected" in financial["expected_roi"]
    assert financial["break_even_period_months"] > 0


def test_security_assessment_detects_critical_surfaces():
    """Security scoring should flag proposals touching keys and consensus."""
    analyzer = ProposalImpactAnalyzer()
    security = analyzer._assess_security_implications(
        {
            "description": "Revamp wallet key management and adjust consensus voting logic.",
            "impact_scope": "consensus",
            "handles_keys": True,
            "introduces_new_crypto": True,
            "deploys_contracts": True,
        }
    )

    assert security["requires_audit"] is True
    assert security["security_score"] < 0.8
    assert any("Key exposure" in vector for vector in security["attack_vectors"])
    assert "HSM" in security["encryption_requirements"]
