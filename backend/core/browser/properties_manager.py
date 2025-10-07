"""Browser properties injection and management system."""

import json
from typing import Any

from loguru import logger
from selenium.webdriver.remote.webdriver import WebDriver

from base.backend.utils.standard_imports import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

from browser.backend.models.browser_properties import (  # noqa: E402
    BrowserProperties,
    BrowserPropertiesPreset,
    get_preset_properties,
)
from browser.backend.utils.config import Config  # noqa: E402


class PropertiesManager:
    """Manages browser properties injection and runtime overrides."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self._instance_properties: dict[str, BrowserProperties] = {}
        self._tab_properties: dict[
            str, dict[str, BrowserProperties]
        ] = {}  # instance_id -> {tab_id: properties}
        self._default_properties = self._load_default_properties()

    def _load_default_properties(self) -> BrowserProperties:
        """Load default properties from config."""
        # Get preset name from config
        preset_name = self.config.get("backend.browser_properties.preset", "stealth")

        # Convert string to enum
        try:
            preset = BrowserPropertiesPreset(preset_name.lower())
            properties = get_preset_properties(preset)
        except ValueError:
            logger.warning(f"Invalid preset '{preset_name}', using stealth preset")
            properties = get_preset_properties(BrowserPropertiesPreset.STEALTH)

        # Apply overrides from config
        overrides = self.config.get("backend.browser_properties.overrides", {})
        if overrides:
            # Update properties with overrides
            for key, value in overrides.items():
                if hasattr(properties, key):
                    # Handle nested objects like codec_support
                    if key == "codec_support" and isinstance(value, dict):
                        for codec_key, codec_value in value.items():
                            if hasattr(properties.codec_support, codec_key):
                                setattr(
                                    properties.codec_support, codec_key, codec_value
                                )
                    else:
                        setattr(properties, key, value)
                else:
                    logger.warning(f"Unknown browser property override: {key}")

        logger.info(
            f"Loaded browser properties with preset '{preset_name}' and {len(overrides)} overrides"
        )
        return properties

    def get_default_properties(self) -> BrowserProperties:
        """Get the default properties."""
        return self._default_properties

    def set_default_properties(
        self, properties: BrowserProperties | dict[str, Any]
    ) -> None:
        """Set the default properties."""
        if isinstance(properties, dict):
            # Create new properties from dict, using current defaults as base
            base_props = self._default_properties.model_copy()
            for key, value in properties.items():
                if hasattr(base_props, key):
                    if key == "codec_support" and isinstance(value, dict):
                        for codec_key, codec_value in value.items():
                            if hasattr(base_props.codec_support, codec_key):
                                setattr(
                                    base_props.codec_support, codec_key, codec_value
                                )
                    else:
                        setattr(base_props, key, value)
            self._default_properties = base_props
        else:
            self._default_properties = properties
        logger.info("Updated default browser properties")

    def get_instance_properties(self, instance_id: str) -> BrowserProperties:
        """Get properties for a specific instance."""
        return self._instance_properties.get(instance_id, self._default_properties)

    def set_instance_properties(
        self, instance_id: str, properties: BrowserProperties | dict[str, Any]
    ) -> None:
        """Set properties for a specific instance."""
        if isinstance(properties, dict):
            # Create new properties from dict, using defaults as base
            base_props = self.get_instance_properties(instance_id).model_copy()
            for key, value in properties.items():
                if hasattr(base_props, key):
                    if key == "codec_support" and isinstance(value, dict):
                        for codec_key, codec_value in value.items():
                            if hasattr(base_props.codec_support, codec_key):
                                setattr(
                                    base_props.codec_support, codec_key, codec_value
                                )
                    else:
                        setattr(base_props, key, value)
            self._instance_properties[instance_id] = base_props
        else:
            self._instance_properties[instance_id] = properties

        logger.info(f"Updated properties for instance {instance_id}")

    def get_tab_properties(self, instance_id: str, tab_id: str) -> BrowserProperties:
        """Get properties for a specific tab."""
        if (
            instance_id in self._tab_properties
            and tab_id in self._tab_properties[instance_id]
        ):
            return self._tab_properties[instance_id][tab_id]
        return self.get_instance_properties(instance_id)

    def set_tab_properties(
        self,
        instance_id: str,
        tab_id: str,
        properties: BrowserProperties | dict[str, Any],
    ) -> None:
        """Set properties for a specific tab."""
        if instance_id not in self._tab_properties:
            self._tab_properties[instance_id] = {}

        if isinstance(properties, dict):
            # Create new properties from dict, using instance properties as base
            base_props = self.get_instance_properties(instance_id).model_copy()
            for key, value in properties.items():
                if hasattr(base_props, key):
                    if key == "codec_support" and isinstance(value, dict):
                        for codec_key, codec_value in value.items():
                            if hasattr(base_props.codec_support, codec_key):
                                setattr(
                                    base_props.codec_support, codec_key, codec_value
                                )
                    else:
                        setattr(base_props, key, value)
            self._tab_properties[instance_id][tab_id] = base_props
        else:
            self._tab_properties[instance_id][tab_id] = properties

        logger.info(f"Updated properties for tab {tab_id} in instance {instance_id}")

    def inject_properties(
        self,
        driver: WebDriver,
        properties: BrowserProperties | None = None,
        tab_id: str | None = None,
    ) -> None:
        """Inject browser properties into the current page."""
        if properties is None:
            properties = self._default_properties

        # Generate injection script
        script = properties.to_injection_script()

        # Inject via CDP for persistence across navigation
        try:
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument", {"source": script}
            )
            logger.debug(
                f"Injected browser properties via CDP{f' for tab {tab_id}' if tab_id else ''}"
            )
        except Exception as e:
            logger.error(f"Failed to inject properties via CDP: {e}")
            raise

    def apply_to_chrome_options(
        self, options: Any, properties: BrowserProperties | None = None
    ) -> None:
        """Apply browser properties to Chrome options before launch."""
        if properties is None:
            properties = self._default_properties

        chrome_opts = properties.to_chrome_options()

        # Apply arguments
        for arg in chrome_opts.get("args", []):
            if arg not in options._arguments:  # Avoid duplicates
                options.add_argument(arg)

        # Apply preferences
        if chrome_opts.get("prefs"):
            # Get existing prefs
            existing_prefs = options._experimental_options.get("prefs", {})
            # Merge with new prefs
            existing_prefs.update(chrome_opts["prefs"])
            options.add_experimental_option("prefs", existing_prefs)

        # Handle webdriver visibility
        if not properties.webdriver_visible:
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

        logger.debug("Applied browser properties to Chrome options")

    def generate_extension_injection(
        self, properties: BrowserProperties | None = None
    ) -> str:
        """Generate injection script for the Chrome extension."""
        if properties is None:
            properties = self._default_properties

        # Generate a minimal script for the extension that complements CDP injection
        script = """
(function() {
    'use strict';

    // This runs in the page context via the extension
    // It provides an additional layer of property spoofing
    """

        # Add webdriver removal
        if not properties.webdriver_visible:
            script += """
    // Remove webdriver property
    delete navigator.webdriver;
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true
    });
    """

        # Add plugin spoofing if needed
        if properties.plugins:
            plugins_json = json.dumps(
                [
                    {
                        "name": p.name,
                        "filename": p.filename,
                        "description": p.description,
                        "mimeTypes": p.mime_types,
                    }
                    for p in properties.plugins
                ],
            )
            script += f"""
    // Plugin spoofing
    (function spoofPlugins() {{
        var pluginData = {plugins_json};
        // Plugin creation code here (simplified for extension context)
    }})();
    """

        script += """
})();
"""
        return script

    def update_extension_script(
        self, properties: BrowserProperties | None = None
    ) -> None:
        """Update the antidetect extension inject.js with current properties."""
        if properties is None:
            properties = self._default_properties

        # Path to extension inject.js
        inject_path = MODULE_ROOT / "extensions" / "antidetect" / "inject.js"

        if not inject_path.exists():
            logger.warning(f"Extension inject.js not found at {inject_path}")
            return

        # Generate new injection script
        new_script = self._generate_full_extension_script(properties)

        # Write to file
        try:
            with inject_path.open("w", encoding="utf-8") as f:
                f.write(new_script)
            logger.info("Updated extension inject.js with new browser properties")
        except Exception as e:
            logger.error(f"Failed to update extension script: {e}")

    def _generate_full_extension_script(self, properties: BrowserProperties) -> str:
        """Generate the full extension injection script."""
        script = """/* eslint-env browser */

// Browser properties injection - generated by PropertiesManager
(function() {
    'use strict';

"""

        # Webdriver removal
        if not properties.webdriver_visible:
            script += """    // ========== WEBDRIVER REMOVAL ==========
    if (window.navigator && window.navigator.webdriver) {
        delete window.navigator.webdriver;
    }

    var nav = window.Navigator ? window.Navigator.prototype : null;
    if (nav && nav.webdriver) {
        delete nav.webdriver;
    }

    try {
        Object.defineProperty(window.navigator, 'webdriver', {
            get: function() { return undefined; },
            set: function() {},
            configurable: true,
            enumerable: false
        });
    } catch(e) {}

"""

        # H264 codec support
        if properties.codec_support.h264:
            script += """    // ========== H264 CODEC FIX ==========
    var originalCanPlayType = HTMLMediaElement.prototype.canPlayType;
    HTMLMediaElement.prototype.canPlayType = function(type) {
        if (!type) return '';
        var lowerType = type.toLowerCase();
        if (lowerType.indexOf('h264') !== -1 ||
            lowerType.indexOf('avc1') !== -1 ||
            lowerType.indexOf('mp4') !== -1) {
            return 'probably';
        }
        if (originalCanPlayType) {
            return originalCanPlayType.apply(this, arguments);
        }
        return '';
    };

"""

        # Plugin creation
        if properties.plugins:
            script += """    // ========== PLUGIN CREATION ==========
    if (!window.navigator.plugins || window.navigator.plugins.length === 0) {
        try {
            var pluginArray = [];

"""
            for i, plugin in enumerate(properties.plugins):
                script += f"""            // {plugin.name}
            var plugin{i} = {{
                name: '{plugin.name}',
                filename: '{plugin.filename}',
                description: '{plugin.description}',
                length: {len(plugin.mime_types)}
            }};
"""
                for j, mime in enumerate(plugin.mime_types):
                    script += f"""            plugin{i}[{j}] = {{
                type: '{mime.get("type", "")}',
                suffixes: '{mime.get("suffixes", "")}',
                description: '{mime.get("description", "")}',
                enabledPlugin: plugin{i}
            }};
"""
                script += f"""            plugin{i}.item = function(i) {{ return this[i] || null; }};
            plugin{i}.namedItem = function(n) {{ return this[n] || null; }};
            pluginArray[{i}] = plugin{i};
            pluginArray['{plugin.name}'] = plugin{i};

"""

            script += (
                """            pluginArray.length = """
                + str(len(properties.plugins))
                + """;
            pluginArray.item = function(i) { return this[i] || null; };
            pluginArray.namedItem = function(n) { return this[n] || null; };
            pluginArray.refresh = function() {};

            // Set navigator.plugins
            Object.defineProperty(window.navigator, 'plugins', {
                get: function() { return pluginArray; },
                configurable: true,
                enumerable: true
            });
        } catch(e) {}
    }
"""
            )

        script += """})();
"""
        return script

    def clear_instance_properties(self, instance_id: str) -> None:
        """Clear custom properties for an instance."""
        if instance_id in self._instance_properties:
            del self._instance_properties[instance_id]
        if instance_id in self._tab_properties:
            del self._tab_properties[instance_id]
        logger.debug(f"Cleared properties for instance {instance_id}")

    def export_properties(
        self, properties: BrowserProperties | None = None
    ) -> dict[str, Any]:
        """Export properties as a dictionary."""
        if properties is None:
            properties = self._default_properties
        return properties.model_dump()

    def import_properties(self, data: dict[str, Any]) -> BrowserProperties:
        """Import properties from a dictionary."""
        return BrowserProperties(**data)
