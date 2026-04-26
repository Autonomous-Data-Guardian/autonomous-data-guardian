from app.services.risk_engine import RiskInputs, calculate_risk_score, map_risk_level


def test_risk_level_mapping_boundaries() -> None:
    """Verify score boundaries map to expected risk levels."""
    assert map_risk_level(0) == "Low"
    assert map_risk_level(30) == "Low"
    assert map_risk_level(31) == "Medium"
    assert map_risk_level(60) == "Medium"
    assert map_risk_level(61) == "High"
    assert map_risk_level(80) == "High"
    assert map_risk_level(81) == "Critical"
    assert map_risk_level(100) == "Critical"


def test_calculate_risk_score_includes_all_factors_and_caps_to_100() -> None:
    """Verify all enabled factors are counted and capped to 100."""
    score, risk_level, factors = calculate_risk_score(
        RiskInputs(
            has_downstream_dashboard=True,
            has_sensitive_tag=True,
            has_downstream_table_or_pipeline=True,
            is_owner_missing=True,
            is_description_missing=True,
            has_recent_data_quality_failure=True,
            has_many_downstream_dependencies=True,
            is_glossary_missing=True,
        )
    )
    assert score == 100
    assert risk_level == "Critical"
    assert len(factors) == 8


def test_calculate_risk_score_empty_inputs_returns_low_zero() -> None:
    """Verify no factors produces deterministic zero score."""
    score, risk_level, factors = calculate_risk_score(
        RiskInputs(
            has_downstream_dashboard=False,
            has_sensitive_tag=False,
            has_downstream_table_or_pipeline=False,
            is_owner_missing=False,
            is_description_missing=False,
            has_recent_data_quality_failure=False,
            has_many_downstream_dependencies=False,
            is_glossary_missing=False,
        )
    )
    assert score == 0
    assert risk_level == "Low"
    assert factors == []
