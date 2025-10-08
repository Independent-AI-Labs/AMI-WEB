"""JavaScript script validation to prevent dangerous operations."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from base.scripts.env.paths import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

import yaml  # noqa: E402
from loguru import logger  # noqa: E402


@dataclass
class ForbiddenPattern:
    """A forbidden JavaScript pattern."""

    pattern: str
    reason: str
    severity: Literal["error", "warning"]
    category: str
    compiled: re.Pattern[str] | None = None


@dataclass
class ValidationResult:
    """Result of script validation."""

    allowed: bool
    violations: list[tuple[ForbiddenPattern, str]]  # (pattern, matched_text)
    errors: list[tuple[ForbiddenPattern, str]]
    warnings: list[tuple[ForbiddenPattern, str]]


class ScriptValidator:
    """Validates JavaScript code against forbidden patterns."""

    def __init__(self, config_path: Path | str | None = None) -> None:
        """Initialize script validator.

        Args:
            config_path: Path to forbidden patterns YAML config. If None, uses default.
        """
        if config_path is None:
            # Default to res/forbidden_script_patterns.yaml
            config_path = MODULE_ROOT / "res" / "forbidden_script_patterns.yaml"

        self.config_path = Path(config_path)
        self.patterns: list[ForbiddenPattern] = []
        self.enforce = True
        self.log_checks = False
        self.warnings_are_errors = False

        self._load_config()

    def _load_config(self) -> None:
        """Load forbidden patterns from YAML config."""
        if not self.config_path.exists():
            logger.warning(f"Script validation config not found: {self.config_path}")
            return

        try:
            with self.config_path.open() as f:
                config = yaml.safe_load(f)

            # Load configuration
            if "config" in config:
                cfg = config["config"]
                self.enforce = cfg.get("enforce", True)
                self.log_checks = cfg.get("log_checks", False)
                self.warnings_are_errors = cfg.get("warnings_are_errors", False)

            # Load patterns
            if "patterns" in config:
                for p in config["patterns"]:
                    try:
                        pattern = ForbiddenPattern(
                            pattern=p["pattern"],
                            reason=p["reason"],
                            severity=p["severity"],
                            category=p["category"],
                        )
                        # Compile the regex pattern
                        pattern.compiled = re.compile(pattern.pattern, re.IGNORECASE | re.MULTILINE)
                        self.patterns.append(pattern)
                    except (KeyError, re.error) as e:
                        logger.error(f"Failed to load pattern {p}: {e}")

            logger.info(f"Loaded {len(self.patterns)} forbidden script patterns from {self.config_path}")

        except Exception as e:
            logger.error(f"Failed to load script validation config: {e}")

    def validate(self, script: str) -> ValidationResult:
        """Validate JavaScript code against forbidden patterns.

        Args:
            script: JavaScript code to validate

        Returns:
            ValidationResult with violations
        """
        violations: list[tuple[ForbiddenPattern, str]] = []
        errors: list[tuple[ForbiddenPattern, str]] = []
        warnings: list[tuple[ForbiddenPattern, str]] = []

        if self.log_checks:
            logger.debug(f"Validating script: {script[:100]}...")

        # Check each pattern
        for pattern in self.patterns:
            if pattern.compiled is None:
                continue

            match = pattern.compiled.search(script)
            if match:
                matched_text = match.group(0)
                violations.append((pattern, matched_text))

                if pattern.severity == "error":
                    errors.append((pattern, matched_text))
                elif pattern.severity == "warning":
                    warnings.append((pattern, matched_text))

                logger.warning(f"Script validation {pattern.severity}: {pattern.category} - {pattern.reason}\nMatched: {matched_text}")

        # Determine if script is allowed
        allowed = True
        if self.enforce:
            if errors:
                allowed = False
            if self.warnings_are_errors and warnings:
                allowed = False

        return ValidationResult(
            allowed=allowed,
            violations=violations,
            errors=errors,
            warnings=warnings,
        )

    def validate_or_raise(self, script: str) -> None:
        """Validate script and raise exception if forbidden patterns found.

        Args:
            script: JavaScript code to validate

        Raises:
            ValueError: If forbidden patterns are found and enforcement is enabled
        """
        result = self.validate(script)

        if not result.allowed:
            error_msgs = []
            for pattern, matched in result.errors:
                error_msgs.append(f"  - [{pattern.category}] {pattern.reason}\n    Matched: {matched}")

            if self.warnings_are_errors:
                for pattern, matched in result.warnings:
                    error_msgs.append(f"  - [{pattern.category}] {pattern.reason}\n    Matched: {matched}")

            raise ValueError(f"Script validation failed with {len(result.errors)} error(s):\n" + "\n".join(error_msgs))


class _ValidatorRegistry:
    """Registry for global validator instance without using global statement."""

    def __init__(self) -> None:
        self._instance: ScriptValidator | None = None

    def get(self) -> ScriptValidator:
        """Get or create validator instance."""
        if self._instance is None:
            self._instance = ScriptValidator()
        return self._instance


_registry = _ValidatorRegistry()


def get_validator() -> ScriptValidator:
    """Get or create global script validator instance."""
    return _registry.get()


def validate_script(script: str) -> ValidationResult:
    """Validate script using global validator.

    Args:
        script: JavaScript code to validate

    Returns:
        ValidationResult
    """
    return get_validator().validate(script)


def validate_script_or_raise(script: str) -> None:
    """Validate script and raise if forbidden patterns found.

    Args:
        script: JavaScript code to validate

    Raises:
        ValueError: If forbidden patterns found
    """
    get_validator().validate_or_raise(script)
