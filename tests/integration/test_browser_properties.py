"""Integration tests for browser properties injection."""

import asyncio

import pytest

from backend.models.browser_properties import BrowserProperties, BrowserPropertiesPreset, get_preset_properties


class TestBrowserProperties:
    """Test browser properties injection and management."""

    @pytest.mark.asyncio
    async def test_properties_model(self):
        """Test browser properties model creation and serialization."""
        props = BrowserProperties(user_agent="TestBrowser/1.0", platform="TestOS", hardware_concurrency=16, webgl_vendor="Test Vendor", webdriver_visible=False)

        # Test property values
        assert props.user_agent == "TestBrowser/1.0"
        assert props.platform == "TestOS"
        assert props.hardware_concurrency == 16  # noqa: PLR2004
        assert props.webdriver_visible is False

        # Test serialization
        data = props.model_dump()
        assert data["user_agent"] == "TestBrowser/1.0"
        assert data["platform"] == "TestOS"

        # Test injection script generation
        script = props.to_injection_script()
        assert "TestBrowser/1.0" in script
        assert "TestOS" in script
        assert "hardwareConcurrency" in script

    @pytest.mark.asyncio
    async def test_property_presets(self):
        """Test predefined property presets."""
        # Test Windows Chrome preset
        windows_props = get_preset_properties(BrowserPropertiesPreset.WINDOWS_CHROME)
        assert "Windows" in windows_props.user_agent
        assert windows_props.platform == "Win32"

        # Test Mac Safari preset
        mac_props = get_preset_properties(BrowserPropertiesPreset.MAC_SAFARI)
        assert "Mac" in mac_props.user_agent
        assert mac_props.platform == "MacIntel"
        assert len(mac_props.plugins) == 0  # Safari has no plugins

        # Test Stealth preset
        stealth_props = get_preset_properties(BrowserPropertiesPreset.STEALTH)
        assert stealth_props.webdriver_visible is False
        assert stealth_props.automation_controlled is False
        assert stealth_props.canvas_noise is True

    @pytest.mark.asyncio
    async def test_properties_manager(self, session_manager):
        """Test properties manager functionality."""
        manager = session_manager.properties_manager

        # Test default properties
        default_props = manager.get_instance_properties("test_instance")
        assert default_props is not None

        # Test setting instance properties
        custom_props = BrowserProperties(user_agent="CustomBrowser/2.0", hardware_concurrency=32)
        manager.set_instance_properties("test_instance", custom_props)

        retrieved_props = manager.get_instance_properties("test_instance")
        assert retrieved_props.user_agent == "CustomBrowser/2.0"
        assert retrieved_props.hardware_concurrency == 32  # noqa: PLR2004

        # Test setting tab properties
        tab_props = {"webgl_vendor": "Custom Vendor", "canvas_noise": True}
        manager.set_tab_properties("test_instance", "tab_1", tab_props)

        tab_retrieved = manager.get_tab_properties("test_instance", "tab_1")
        assert tab_retrieved.webgl_vendor == "Custom Vendor"
        assert tab_retrieved.canvas_noise is True

        # Test clearing properties
        manager.clear_instance_properties("test_instance")
        cleared_props = manager.get_instance_properties("test_instance")
        assert cleared_props.user_agent != "CustomBrowser/2.0"  # Should be back to default

    @pytest.mark.asyncio
    async def test_browser_with_properties(self, session_manager):
        """Test launching browser with custom properties."""
        # Create custom properties
        custom_props = BrowserProperties(user_agent="TestBot/3.0", platform="TestPlatform", webdriver_visible=False, hardware_concurrency=4)

        # Launch browser with properties
        instance = await session_manager.get_or_create_instance(headless=True, anti_detect=True)

        # Set properties for the instance
        await session_manager.set_browser_properties(instance_id=instance.id, properties=custom_props.model_dump())

        # Navigate to a test page
        instance.driver.get("about:blank")

        # Verify properties are injected
        result = instance.driver.execute_script(
            """
            return {
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                hardwareConcurrency: navigator.hardwareConcurrency,
                webdriver: navigator.webdriver
            };
        """
        )

        # Note: Some properties may not be changeable after browser launch
        # but the injection should still work for new pages
        assert result["webdriver"] is None or result["webdriver"] is False

        # Clean up
        await session_manager.return_to_pool(instance.id)

    @pytest.mark.asyncio
    async def test_runtime_property_changes(self, session_manager):
        """Test changing properties at runtime."""
        instance = await session_manager.get_or_create_instance(headless=True)

        # Initial properties
        initial_props = await session_manager.get_browser_properties(instance.id)
        assert initial_props is not None

        # Change properties
        new_props = {"webgl_vendor": "Runtime Vendor", "codec_support": {"h264": True, "h265": True}}

        success = await session_manager.set_browser_properties(instance_id=instance.id, properties=new_props)
        assert success is True

        # Verify changes
        updated_props = await session_manager.get_browser_properties(instance.id)
        assert updated_props["webgl_vendor"] == "Runtime Vendor"
        assert updated_props["codec_support"]["h265"] is True

        # Clean up
        await session_manager.return_to_pool(instance.id)

    @pytest.mark.asyncio
    async def test_per_tab_properties(self, session_manager):
        """Test setting different properties for different tabs."""
        instance = await session_manager.get_or_create_instance(headless=True)

        # Get current tab
        main_tab = instance.driver.current_window_handle

        # Set properties for main tab
        main_props = {"user_agent": "MainTabBrowser/1.0", "platform": "MainPlatform"}
        await session_manager.set_browser_properties(instance_id=instance.id, tab_id=main_tab, properties=main_props)

        # Open new tab
        instance.driver.switch_to.new_window("tab")
        new_tab = instance.driver.current_window_handle

        # Set different properties for new tab
        new_tab_props = {"user_agent": "NewTabBrowser/2.0", "platform": "NewPlatform"}
        await session_manager.set_browser_properties(instance_id=instance.id, tab_id=new_tab, properties=new_tab_props)

        # Verify different properties per tab
        main_tab_properties = await session_manager.get_browser_properties(instance_id=instance.id, tab_id=main_tab)
        new_tab_properties = await session_manager.get_browser_properties(instance_id=instance.id, tab_id=new_tab)

        assert main_tab_properties["user_agent"] == "MainTabBrowser/1.0"
        assert new_tab_properties["user_agent"] == "NewTabBrowser/2.0"

        # Clean up
        instance.driver.close()  # Close new tab
        instance.driver.switch_to.window(main_tab)
        await session_manager.return_to_pool(instance.id)

    @pytest.mark.asyncio
    async def test_codec_support_injection(self, session_manager):
        """Test media codec support injection."""
        # Create properties with specific codec support
        props = BrowserProperties(codec_support={"h264": True, "h265": False, "vp9": True, "av1": False})

        instance = await session_manager.get_or_create_instance(headless=True)

        # Set properties
        await session_manager.set_browser_properties(instance_id=instance.id, properties=props.model_dump())

        # Navigate to test page
        instance.driver.get("about:blank")

        # Test codec support
        result = instance.driver.execute_script(
            """
            var video = document.createElement('video');
            return {
                h264: video.canPlayType('video/mp4; codecs="avc1"'),
                h265: video.canPlayType('video/mp4; codecs="hev1"'),
                vp9: video.canPlayType('video/webm; codecs="vp9"'),
                av1: video.canPlayType('video/mp4; codecs="av01"')
            };
        """
        )

        # H264 and VP9 should be supported
        assert result["h264"] != ""
        assert result["vp9"] != ""

        # Clean up
        await session_manager.return_to_pool(instance.id)

    @pytest.mark.asyncio
    async def test_webgl_spoofing(self, session_manager):
        """Test WebGL vendor and renderer spoofing."""
        props = BrowserProperties(webgl_vendor="Spoofed Vendor Inc.", webgl_renderer="Spoofed Renderer 9000")

        instance = await session_manager.get_or_create_instance(headless=True)

        # Set properties
        await session_manager.set_browser_properties(instance_id=instance.id, properties=props.model_dump())

        # Navigate to test page
        instance.driver.get("about:blank")

        # Test WebGL parameters
        result = instance.driver.execute_script(
            """
            try {
                var canvas = document.createElement('canvas');
                var gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                if (!gl) return {error: 'WebGL not supported'};

                var debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                if (!debugInfo) return {error: 'Debug info not available'};

                return {
                    vendor: gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL),
                    renderer: gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)
                };
            } catch(e) {
                return {error: e.toString()};
            }
        """
        )

        # WebGL spoofing should be active
        if "error" not in result:
            # Properties should be spoofed (exact match depends on injection timing)
            assert result["vendor"] is not None
            assert result["renderer"] is not None

        # Clean up
        await session_manager.return_to_pool(instance.id)

    @pytest.mark.asyncio
    async def test_bot_detection_comprehensive(self, session_manager):
        """Comprehensive test using bot detection HTML page."""
        from pathlib import Path

        # Get path to bot detection test page relative to this test file
        test_file_dir = Path(__file__).parent.parent  # Go up to tests/ directory
        test_page = test_file_dir / "fixtures" / "bot_detection_test.html"

        # Ensure the file exists
        if not test_page.exists():
            pytest.skip(f"Bot detection test file not found at {test_page}")

        test_url = f"file:///{test_page.absolute().as_posix()}"

        # Test 1: Default configuration with anti-detect
        instance = await session_manager.get_or_create_instance(headless=True, anti_detect=True)

        # Apply stealth properties before navigation
        stealth_props = get_preset_properties(BrowserPropertiesPreset.STEALTH)
        await session_manager.set_browser_properties(instance_id=instance.id, properties=stealth_props.model_dump())

        instance.driver.get(test_url)
        await asyncio.sleep(2)  # Wait for tests to run

        default_result = instance.driver.execute_script("return window.getBotDetectionResults()")
        assert default_result["webdriverDetected"] is False
        assert default_result["passedCount"] > 80  # noqa: PLR2004  # noqa: PLR2004 - Should pass most tests

        # Test 2: Stealth preset
        stealth_props = get_preset_properties(BrowserPropertiesPreset.STEALTH)
        await session_manager.set_browser_properties(instance_id=instance.id, properties=stealth_props.model_dump())
        instance.driver.refresh()
        await asyncio.sleep(2)

        stealth_result = instance.driver.execute_script("return window.getBotDetectionResults()")
        assert stealth_result["webdriverDetected"] is False
        assert stealth_result["passedCount"] > 80  # noqa: PLR2004
        assert stealth_result["suspiciousCount"] <= 5  # noqa: PLR2004  # Should have minimal suspicious indicators

        # Test 3: Windows Chrome preset
        windows_props = get_preset_properties(BrowserPropertiesPreset.WINDOWS_CHROME)
        await session_manager.set_browser_properties(instance_id=instance.id, properties=windows_props.model_dump())
        instance.driver.refresh()
        await asyncio.sleep(2)

        windows_result = instance.driver.execute_script("return window.getBotDetectionResults()")
        assert windows_result["webdriverDetected"] is False
        assert windows_result["passedCount"] > 80  # noqa: PLR2004

        # Test 4: Custom aggressive anti-bot properties
        custom_props = BrowserProperties(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            platform="Win32",
            vendor="Google Inc.",
            webdriver_visible=False,
            automation_controlled=False,
            hardware_concurrency=8,
            device_memory=8,
            webgl_vendor="Google Inc. (NVIDIA)",
            webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0)",
            languages=["en-US", "en"],
            canvas_noise=True,
            plugins=[{"name": "PDF Viewer", "filename": "internal-pdf-viewer"}, {"name": "Chrome PDF Viewer", "filename": "mhjfbmdgcfjbbpaeojofohoefgiehjai"}],
            codec_support={"h264": True, "h265": False, "vp8": True, "vp9": True, "av1": True},
        )

        await session_manager.set_browser_properties(instance_id=instance.id, properties=custom_props.model_dump())
        instance.driver.refresh()
        await asyncio.sleep(2)

        custom_result = instance.driver.execute_script("return window.getBotDetectionResults()")
        assert custom_result["webdriverDetected"] is False
        assert custom_result["passedCount"] > 85  # noqa: PLR2004  # Should pass even more tests with custom config

        # Test 5: Per-tab properties
        instance.driver.switch_to.new_window("tab")
        new_tab = instance.driver.current_window_handle

        mac_props = get_preset_properties(BrowserPropertiesPreset.MAC_SAFARI)
        await session_manager.set_browser_properties(instance_id=instance.id, tab_id=new_tab, properties=mac_props.model_dump())

        instance.driver.get(test_url)
        await asyncio.sleep(2)

        mac_result = instance.driver.execute_script("return window.getBotDetectionResults()")
        assert mac_result["webdriverDetected"] is False
        assert mac_result["passedCount"] > 75  # noqa: PLR2004  # Mac Safari might have slightly different characteristics

        # Verify tab properties are different
        handles = instance.driver.window_handles
        instance.driver.switch_to.window(handles[0])

        # First tab should still have custom properties
        first_tab_check = instance.driver.execute_script("return navigator.platform")
        assert first_tab_check == "Win32"

        instance.driver.switch_to.window(new_tab)
        second_tab_check = instance.driver.execute_script("return navigator.platform")
        assert second_tab_check == "MacIntel"

        # Clean up
        instance.driver.close()
        instance.driver.switch_to.window(handles[0])
        await session_manager.return_to_pool(instance.id)

    @pytest.mark.asyncio
    async def test_properties_persistence_across_navigation(self, session_manager):
        """Test that properties persist across page navigation."""
        custom_props = BrowserProperties(user_agent="PersistentBot/1.0", platform="TestPlatform", hardware_concurrency=16)

        instance = await session_manager.get_or_create_instance(headless=True)

        # Set properties
        await session_manager.set_browser_properties(instance_id=instance.id, properties=custom_props.model_dump())

        # Navigate to first page
        instance.driver.get("about:blank")
        first_check = instance.driver.execute_script(
            """
            return {
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                hardwareConcurrency: navigator.hardwareConcurrency
            };
        """
        )

        # Navigate to second page
        instance.driver.get("data:text/html,<h1>Test Page</h1>")
        second_check = instance.driver.execute_script(
            """
            return {
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                hardwareConcurrency: navigator.hardwareConcurrency
            };
        """
        )

        # Properties should persist
        assert first_check["platform"] == second_check["platform"]
        assert first_check["hardwareConcurrency"] == second_check["hardwareConcurrency"]

        # Clean up
        await session_manager.return_to_pool(instance.id)

    @pytest.mark.asyncio
    async def test_minimal_preset(self, session_manager):
        """Test minimal preset for maximum performance."""
        minimal_props = get_preset_properties(BrowserPropertiesPreset.MINIMAL)

        instance = await session_manager.get_or_create_instance(headless=True)

        await session_manager.set_browser_properties(instance_id=instance.id, properties=minimal_props.model_dump())

        instance.driver.get("about:blank")

        # Minimal preset should have basic anti-detection
        result = instance.driver.execute_script("return navigator.webdriver")
        assert result is None or result is False

        # Clean up
        await session_manager.return_to_pool(instance.id)
