"""Tests for JavaScript script validation."""

import pytest

from browser.backend.core.security.script_validator import (
    ScriptValidator,
    ValidationResult,
)


@pytest.fixture
def validator() -> ScriptValidator:
    """Create a script validator instance."""
    return ScriptValidator()


def test_validator_loads_patterns(validator: ScriptValidator) -> None:
    """Test that validator loads patterns from config."""
    assert len(validator.patterns) > 0
    assert validator.enforce is True


def test_window_open_blank_is_forbidden(validator: ScriptValidator) -> None:
    """Test that window.open with _blank is forbidden."""
    script = "window.open('https://reddit.com', '_blank')"
    result = validator.validate(script)

    assert not result.allowed
    assert len(result.errors) > 0
    assert any("_blank" in p.reason for p, _ in result.errors)


def test_window_open_self_is_forbidden(validator: ScriptValidator) -> None:
    """Test that window.open with _self is forbidden."""
    script = "window.open('https://example.com', '_self')"
    result = validator.validate(script)

    assert not result.allowed
    assert len(result.errors) > 0
    assert any("_self" in p.reason for p, _ in result.errors)


def test_plain_window_open_is_warning(validator: ScriptValidator) -> None:
    """Test that plain window.open is a warning."""
    script = "window.open('https://example.com')"
    result = validator.validate(script)

    # Should allow (warning only) unless warnings_are_errors is True
    if validator.warnings_are_errors:
        assert not result.allowed
    else:
        assert result.allowed

    assert len(result.warnings) > 0


def test_window_close_is_forbidden(validator: ScriptValidator) -> None:
    """Test that window.close() is forbidden."""
    script = "window.close()"
    result = validator.validate(script)

    assert not result.allowed
    assert len(result.errors) > 0
    assert any("window.close" in p.reason for p, _ in result.errors)


def test_window_location_assignment_is_warning(validator: ScriptValidator) -> None:
    """Test that window.location assignment is a warning."""
    script = "window.location = 'https://example.com'"
    result = validator.validate(script)

    # Should allow (warning only) unless warnings_are_errors is True
    if validator.warnings_are_errors:
        assert not result.allowed
    else:
        assert result.allowed

    assert len(result.warnings) > 0


def test_eval_is_warning(validator: ScriptValidator) -> None:
    """Test that eval is a warning."""
    script = "eval('console.log(1)')"
    result = validator.validate(script)

    # Should allow (warning only) unless warnings_are_errors is True
    if validator.warnings_are_errors:
        assert not result.allowed
    else:
        assert result.allowed

    assert len(result.warnings) > 0


def test_safe_script_is_allowed(validator: ScriptValidator) -> None:
    """Test that safe scripts are allowed."""
    scripts = [
        "document.querySelector('button').click()",
        "return document.title",
        "console.log('hello')",
        "const x = 1 + 2; return x;",
    ]

    for script in scripts:
        result = validator.validate(script)
        assert result.allowed, f"Script should be allowed: {script}"
        assert len(result.errors) == 0


def test_validate_or_raise_with_forbidden_pattern(validator: ScriptValidator) -> None:
    """Test that validate_or_raise raises on forbidden patterns."""
    script = "window.open('https://reddit.com', '_blank')"

    with pytest.raises(ValueError, match="Script validation failed"):
        validator.validate_or_raise(script)


def test_validate_or_raise_with_safe_script(validator: ScriptValidator) -> None:
    """Test that validate_or_raise doesn't raise on safe scripts."""
    script = "document.querySelector('button').click()"

    # Should not raise
    validator.validate_or_raise(script)


def test_case_insensitive_matching(validator: ScriptValidator) -> None:
    """Test that pattern matching is case-insensitive."""
    scripts = [
        "WINDOW.OPEN('url', '_blank')",
        "Window.Open('url', '_blank')",
        "window.OPEN('url', '_BLANK')",
    ]

    for script in scripts:
        result = validator.validate(script)
        assert not result.allowed, f"Should catch case variant: {script}"
        assert len(result.errors) > 0


def test_multiline_script_validation(validator: ScriptValidator) -> None:
    """Test validation of multiline scripts."""
    script = """
    const url = 'https://example.com';
    window.open(url, '_blank');
    console.log('done');
    """

    result = validator.validate(script)
    assert not result.allowed
    assert len(result.errors) > 0


def test_validation_result_structure(validator: ScriptValidator) -> None:
    """Test that ValidationResult has expected structure."""
    script = "window.open('url', '_blank')"
    result = validator.validate(script)

    assert isinstance(result, ValidationResult)
    assert isinstance(result.allowed, bool)
    assert isinstance(result.violations, list)
    assert isinstance(result.errors, list)
    assert isinstance(result.warnings, list)

    # Check violation tuple structure
    if result.violations:
        pattern, matched_text = result.violations[0]
        assert hasattr(pattern, "pattern")
        assert hasattr(pattern, "reason")
        assert hasattr(pattern, "severity")
        assert hasattr(pattern, "category")
        assert isinstance(matched_text, str)
