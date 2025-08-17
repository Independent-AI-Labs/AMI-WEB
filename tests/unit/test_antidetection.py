"""Test suite for antidetection scripts."""
import json
from pathlib import Path

import pytest


class TestAntidetectionScripts:
    """Test antidetection scripts functionality."""

    @pytest.fixture
    def script_dir(self):
        """Get the scripts directory path."""
        return Path(__file__).parent.parent.parent / "web" / "scripts"

    @pytest.fixture
    def extension_dir(self):
        """Get the extension directory path."""
        return Path(__file__).parent.parent.parent / "web" / "extensions" / "antidetect"

    def test_scripts_exist(self, script_dir):
        """Test that all required scripts exist."""
        required_scripts = ["complete-antidetect.js", "antidetect-optimized.js", "config-loader.js"]

        for script in required_scripts:
            script_path = script_dir / script
            assert script_path.exists(), f"Script {script} not found"

    def test_extension_files_exist(self, extension_dir):
        """Test that extension files exist."""
        required_files = ["manifest.json", "content.js", "inject.js"]

        for file in required_files:
            file_path = extension_dir / file
            assert file_path.exists(), f"Extension file {file} not found"

    def test_manifest_valid(self, extension_dir):
        """Test that manifest.json is valid."""
        manifest_path = extension_dir / "manifest.json"

        with manifest_path.open() as f:
            manifest = json.load(f)

        # Check required fields
        expected_manifest_version = 3
        assert manifest["manifest_version"] == expected_manifest_version
        assert manifest["name"] == "Anti-Detection Helper"
        assert manifest["version"] == "1.0.0"
        assert "description" in manifest

        # Check security settings
        assert "content_security_policy" in manifest
        assert manifest["content_security_policy"]["extension_pages"] == "script-src 'self'; object-src 'none'"

        # Check permissions are limited
        content_scripts = manifest["content_scripts"][0]
        assert content_scripts["matches"] == ["http://*/*", "https://*/*"]
        assert "<all_urls>" not in str(manifest)

    def test_config_file_valid(self):
        """Test that config file is valid JSON."""
        config_path = Path(__file__).parent.parent.parent / "web" / "config" / "antidetect-config.json"

        with config_path.open() as f:
            config = json.load(f)

        # Check structure
        assert "enabled" in config
        assert "features" in config
        assert "injection" in config
        assert "urls" in config

        # Check features
        features = config["features"]
        assert features["webdriver"]["enabled"] is True
        assert features["chrome"]["enabled"] is True
        assert features["permissions"]["enabled"] is True

    def test_scripts_no_syntax_errors(self, script_dir):
        """Test that JavaScript files have no obvious syntax errors."""
        scripts = ["complete-antidetect.js", "config-loader.js"]

        for script_name in scripts:
            script_path = script_dir / script_name
            with script_path.open() as f:
                content = f.read()

            # Basic syntax checks
            assert content.count("(") == content.count(")"), f"Unmatched parentheses in {script_name}"
            assert content.count("{") == content.count("}"), f"Unmatched braces in {script_name}"
            assert content.count("[") == content.count("]"), f"Unmatched brackets in {script_name}"

            # Check for try-catch blocks (error handling)
            assert "try {" in content, f"No error handling in {script_name}"
            assert "} catch" in content, f"No catch blocks in {script_name}"

    def test_no_polling_loops(self, script_dir):
        """Test that scripts don't use polling loops."""
        script_path = script_dir / "complete-antidetect.js"

        with script_path.open() as f:
            content = f.read()

        # Check for polling patterns
        assert "setInterval" not in content or "MutationObserver" in content, "Script uses polling instead of events"
        assert "while (true)" not in content, "Script contains infinite loop"
        assert "while(true)" not in content, "Script contains infinite loop"

    def test_no_global_namespace_pollution(self, extension_dir):
        """Test that inject.js doesn't pollute global namespace."""
        inject_path = extension_dir / "inject.js"

        with inject_path.open() as f:
            content = f.read()

        # Check that the entire script is wrapped in IIFE or try block
        assert (
            content.strip().startswith("/*") or content.strip().startswith("//") or content.strip().startswith("(function")
        ), "Script should start with comment or IIFE"

        # Remove comments for analysis
        import re

        content_no_comments = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        content_no_comments = re.sub(r"//.*$", "", content_no_comments, flags=re.MULTILINE)

        # Check that after comments, it starts with IIFE
        content_stripped = content_no_comments.strip()
        assert content_stripped.startswith("(function"), "Script not wrapped in IIFE after comments"

    def test_webdriver_removal_optimized(self, script_dir):
        """Test that webdriver removal is optimized."""
        script_path = script_dir / "complete-antidetect.js"

        with script_path.open() as f:
            content = f.read()

        # Count methods used for webdriver removal
        method_count = 0
        if "delete Navigator.prototype.webdriver" in content:
            method_count += 1
        if "Object.defineProperty(navigator, 'webdriver'" in content:
            method_count += 1
        if "new Proxy(navigator" in content:
            method_count += 1

        # Should use 1-2 methods max, not 4+
        max_webdriver_methods = 2
        assert method_count <= max_webdriver_methods, f"Too many webdriver removal methods: {method_count}"

    def test_extension_inject_script_wrapped(self, extension_dir):
        """Test that inject.js is properly wrapped."""
        inject_path = extension_dir / "inject.js"

        with inject_path.open() as f:
            content = f.read()

        # Remove comments to check structure
        import re

        content_no_comments = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        content_no_comments = re.sub(r"//.*$", "", content_no_comments, flags=re.MULTILINE)
        content_stripped = content_no_comments.strip()

        # Check for IIFE wrapper
        assert content_stripped.startswith("(function()"), "inject.js not wrapped in IIFE"
        assert content_stripped.endswith("})();"), "inject.js IIFE not properly closed"


class TestAntidetectionIntegration:
    """Integration tests for antidetection with real browser."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_webdriver_property_removed(self, antidetect_browser):
        """Test that webdriver property is removed in browser."""
        driver = antidetect_browser.driver

        # Navigate to a test page
        driver.get("data:text/html,<html><body>Test</body></html>")

        # Inject our antidetect script directly
        script_path = Path(__file__).parent.parent.parent / "web" / "scripts" / "complete-antidetect.js"
        with script_path.open() as f:
            script = f.read()

        driver.execute_script(script)

        # Check webdriver property after our script
        check_result = driver.execute_script(
            """
            return {
                webdriver: navigator.webdriver,
                exists: 'webdriver' in navigator,
                type: typeof navigator.webdriver,
                isUndefined: navigator.webdriver === undefined
            };
        """
        )

        # The script should make webdriver return undefined
        assert check_result["webdriver"] is None or check_result["isUndefined"], f"webdriver property not properly removed: {check_result}"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_chrome_object_exists(self, antidetect_browser):
        """Test that chrome object is properly defined."""
        driver = antidetect_browser.driver

        driver.get("data:text/html,<html><body>Test</body></html>")

        # Inject our script
        script_path = Path(__file__).parent.parent.parent / "web" / "scripts" / "complete-antidetect.js"
        with script_path.open() as f:
            script = f.read()

        driver.execute_script(script)

        # Check chrome object
        has_chrome = driver.execute_script("return typeof window.chrome !== 'undefined'")
        assert has_chrome, "Chrome object not defined"
