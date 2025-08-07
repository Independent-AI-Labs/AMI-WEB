"""Anti-detection features for ChromeDriver."""

import re
import shutil
from pathlib import Path

from loguru import logger


class ChromeDriverPatcher:
    """Patches ChromeDriver binary to avoid detection."""

    def __init__(self, chromedriver_path: str):
        self.original_path = Path(chromedriver_path)
        # Create a patched version with a different name
        self.chromedriver_path = self.original_path.parent / "chromedriver_patched.exe"
        self.backup_path: Path | None = None

    def is_patched(self) -> bool:
        """Check if the ChromeDriver binary is already patched."""
        try:
            with self.chromedriver_path.open("rb") as f:
                content = f.read()
                # Check if the CDC injection code is present
                return not bool(re.search(rb"\{window\.cdc.*?;\}", content))
        except Exception as e:
            logger.error(f"Error checking if ChromeDriver is patched: {e}")
            return False

    def get_patched_path(self) -> Path:
        """Get the path to the patched ChromeDriver."""
        return self.chromedriver_path

    def patch(self) -> bool:
        """
        Patch the ChromeDriver binary to remove detection artifacts.

        This patches the ChromeDriver to remove the window.cdc property
        that websites use to detect automated browsers.
        """
        if self.is_patched():
            logger.info("ChromeDriver is already patched")
            return True

        try:
            # Copy original to create patched version
            if not self.chromedriver_path.exists():
                shutil.copy2(self.original_path, self.chromedriver_path)

            # Read the binary
            with self.chromedriver_path.open("rb") as f:
                content = f.read()

            modified = False

            # ONLY replace the exact CDC variable name - no regex patterns!
            # The specific CDC variable that ChromeDriver uses
            cdc_var = b"cdc_adoQpoasnfa76pfcZLmcfl"
            if cdc_var in content:
                # Replace with same length string to not break offsets
                wdc_var = b"wdc_adoQpoasnfa76pfcZLmcfl"
                content = content.replace(cdc_var, wdc_var)
                modified = True
                logger.debug(f"Replaced CDC variable: {cdc_var!r} -> {wdc_var!r}")

            if modified:
                # Write the patched binary
                with self.chromedriver_path.open("wb") as f:
                    f.write(content)
                logger.info("ChromeDriver patched successfully")
                return True

            logger.warning("No CDC patterns found to patch in ChromeDriver")
            return True  # Still return True as it might be a newer version

        except Exception as e:
            logger.error(f"Error patching ChromeDriver: {e}")
            return False

    def restore(self):
        """Restore the original ChromeDriver from backup."""
        if self.backup_path and self.backup_path.exists():
            shutil.copy2(self.backup_path, self.chromedriver_path)
            logger.info("ChromeDriver restored from backup")


def get_anti_detection_arguments() -> list[str]:
    """
    Get Chrome arguments for anti-detection.

    Returns a list of Chrome arguments that help avoid detection.
    """
    return [
        # Disable automation features
        "--disable-blink-features=AutomationControlled",
        # Exclude switches that indicate automation
        "--exclude-switches=enable-automation",
        # Disable the automation extension
        "--disable-dev-shm-usage",
        # Set user agent to remove HeadlessChrome
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        # Disable the infobar that says Chrome is being controlled
        "--disable-infobars",
        # Start maximized to look more natural
        "--start-maximized",
        # Disable default browser check
        "--no-default-browser-check",
        # Disable first run experience
        "--no-first-run",
        # Disable password saving prompts
        "--password-store=basic",
        # Disable automation-related features
        "--disable-features=ChromeWhatsNewUI,TranslateUI",
        # Use a more natural window size
        "--window-size=1920,1080",
        # Set language
        "--lang=en-US,en;q=0.9",
        # Enable WebGL explicitly
        "--enable-webgl",
        "--enable-webgl2",
        # Use hardware acceleration when available
        "--enable-accelerated-2d-canvas",
        "--enable-accelerated-video-decode",
        # Ignore GPU blocklist to ensure WebGL works
        "--ignore-gpu-blocklist",
        # Don't use software renderer - we want real WebGL
        "--disable-software-rasterizer",
        # Use ANGLE (more compatible on Windows)
        "--use-angle=default",
        # Use GL implementation auto-selection
        "--use-gl=angle",
        # Enable GPU rasterization
        "--enable-gpu-rasterization",
        # Ensure GPU process isn't sandboxed (helps with WebGL)
        "--disable-gpu-sandbox",
        # Additional GPU flags for better WebGL support
        "--enable-gpu",
        "--enable-features=VaapiVideoDecoder",
    ]


def get_anti_detection_prefs() -> dict:
    """
    Get Chrome preferences for anti-detection.

    Returns a dictionary of Chrome preferences that help avoid detection.
    """
    return {
        # Disable webdriver flag
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        # Disable Chrome's Save Password popup
        "profile.default_content_setting_values.notifications": 1,
        # Set download behavior
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        # Disable plugins discovery
        "plugins.always_open_pdf_externally": True,
        # Disable automation features
        "useAutomationExtension": False,
    }


def get_anti_detection_experimental_options() -> dict:
    """
    Get experimental Chrome options for anti-detection.

    Returns a dictionary of experimental options that help avoid detection.
    """
    return {
        # Exclude automation switches
        "excludeSwitches": ["enable-automation", "enable-logging"],
        # Disable automation extension
        "useAutomationExtension": False,
        # Disable developer mode extensions warning
        "prefs": get_anti_detection_prefs(),
    }


def setup_anti_detection_capabilities() -> dict:
    """
    Get Chrome capabilities for anti-detection.

    Returns a dictionary of capabilities that help avoid detection.
    """
    return {
        "browserName": "chrome",
        "version": "",
        "platform": "ANY",
        "goog:chromeOptions": {
            "excludeSwitches": ["enable-automation"],
            "useAutomationExtension": False,
        },
    }


def execute_anti_detection_scripts(driver) -> None:
    """
    Execute JavaScript to further mask automation.

    This should be called after the driver is initialized.
    """
    scripts = [
        # FIRST AND MOST CRITICAL: Remove webdriver property completely
        """
        // Remove webdriver immediately - this must run first
        (function() {
            // Delete from navigator object
            delete navigator.webdriver;

            // Delete from Navigator prototype
            delete Navigator.prototype.webdriver;

            // Redefine as undefined getter
            try {
                Object.defineProperty(navigator, 'webdriver', {
                    get: function() { return undefined; },
                    set: function() {},
                    configurable: false,
                    enumerable: false
                });
            } catch(e) {}

            // Also try on the prototype
            try {
                Object.defineProperty(Navigator.prototype, 'webdriver', {
                    get: function() { return undefined; },
                    set: function() {},
                    configurable: false,
                    enumerable: false
                });
            } catch(e) {}

            // Override Object.getOwnPropertyDescriptor to hide it
            var originalGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
            Object.getOwnPropertyDescriptor = function(obj, prop) {
                if (prop === 'webdriver') {
                    return undefined;
                }
                return originalGetOwnPropertyDescriptor.apply(this, arguments);
            };
        })();
        """,
        # CRITICAL: Remove all CDC properties before any page scripts run
        """
        // Delete all CDC properties from window, document, and navigator
        var deleteFromObject = function(obj) {
            if (!obj) return;
            try {
                var props = Object.getOwnPropertyNames(obj);
                for (var i = 0; i < props.length; i++) {
                    var prop = props[i];
                    if (prop.indexOf('cdc') !== -1 || prop.indexOf('$cdc') !== -1) {
                        delete obj[prop];
                    }
                }
            } catch(e) {}
        };

        // Clean window object
        deleteFromObject(window);

        // Clean document
        deleteFromObject(document);

        // Clean navigator
        deleteFromObject(navigator);

        // Also check for properties that might be added later
        var observer = new MutationObserver(function() {
            deleteFromObject(window);
            deleteFromObject(document);
        });

        observer.observe(document, {
            attributes: true,
            childList: true,
            subtree: true
        });

        // Intercept Object.defineProperty to prevent CDC properties
        var originalDefineProperty = Object.defineProperty;
        Object.defineProperty = function(obj, prop, descriptor) {
            if (prop.indexOf('cdc') !== -1 || prop.indexOf('$cdc') !== -1) {
                return obj;
            }
            return originalDefineProperty.call(this, obj, prop, descriptor);
        };
        """,
        # Fix Function.prototype.toString to return native code
        """
        // Override Function.prototype.toString to always show native code
        var nativeToStringFunctionString = Function.prototype.toString.toString();
        var nativeToStringName = Function.prototype.toString.name;

        Function.prototype.toString = new Proxy(Function.prototype.toString, {
            apply: function(target, thisArg, argumentsList) {
                if (thisArg === Function.prototype.toString) {
                    return nativeToStringFunctionString;
                }
                var result = Reflect.apply(target, thisArg, argumentsList);

                // Check if this is a native function that was overridden
                if (result.indexOf('[native code]') !== -1 ||
                    thisArg === Object.defineProperty ||
                    thisArg === Object.getOwnPropertyDescriptor ||
                    thisArg === navigator.webdriver ||
                    thisArg === window.chrome) {
                    return 'function ' + (thisArg.name || '') + '() { [native code] }';
                }
                return result;
            }
        });
        """,
        # Remove webdriver property completely
        """
        // Remove webdriver property
        delete navigator.webdriver;

        // Prevent webdriver from being added
        Object.defineProperty(navigator, 'webdriver', {
            get: function() { return undefined; },
            set: function() {},
            configurable: false,
            enumerable: false
        });
        """,
        # Add proper Chrome runtime object
        """
        // Add chrome.runtime with proper structure
        if (!window.chrome) {
            window.chrome = {};
        }

        window.chrome.runtime = {
            id: 'fake-extension-id',
            connect: function() {},
            sendMessage: function() {},
            onMessage: {
                addListener: function() {}
            },
            onConnect: {
                addListener: function() {}
            },
            onInstalled: {
                addListener: function() {}
            },
            getManifest: function() { return {
                version: '1.0.0',
                manifest_version: 2
            }; },
            getURL: function(path) { return 'chrome-extension://fake-extension-id/' + path; }
        };

        // Add chrome.app
        window.chrome.app = {
            isInstalled: true,
            InstallState: {
                DISABLED: 'disabled',
                INSTALLED: 'installed',
                NOT_INSTALLED: 'not_installed'
            },
            RunningState: {
                CANNOT_RUN: 'cannot_run',
                READY_TO_RUN: 'ready_to_run',
                RUNNING: 'running'
            }
        };
        """,
        # Fix navigator.plugins with real plugin data
        """
        // Create realistic plugin array
        var pluginData = [
            {
                name: 'Chrome PDF Plugin',
                filename: 'internal-pdf-viewer',
                description: 'Portable Document Format'
            },
            {
                name: 'Chrome PDF Viewer',
                filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                description: ''
            },
            {
                name: 'Native Client',
                filename: 'internal-nacl-plugin',
                description: ''
            }
        ];

        var plugins = [];
        for (var j = 0; j < pluginData.length; j++) {
            var p = pluginData[j];
            var plugin = Object.create(Plugin.prototype);
            plugin.name = p.name;
            plugin.filename = p.filename;
            plugin.description = p.description;
            plugin.length = 2;
            plugin[0] = Object.create(MimeType.prototype);
            plugin[0].type = 'application/pdf';
            plugin[0].suffixes = 'pdf';
            plugin[0].description = 'Portable Document Format';
            plugin[1] = Object.create(MimeType.prototype);
            plugin[1].type = 'text/pdf';
            plugin[1].suffixes = 'pdf';
            plugin[1].description = 'Portable Document Format';
            plugins.push(plugin);
        }

        Object.defineProperty(navigator, 'plugins', {
            get: function() { return plugins; },
            configurable: false,
            enumerable: true
        });
        """,
        # Modify navigator.languages properly
        """
        Object.defineProperty(navigator, 'languages', {
            get: function() { return ['en-US', 'en']; },
            configurable: false,
            enumerable: true
        });
        """,
        # Fix permissions API
        """
        var originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = function(parameters) {
            return (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
        };
        """,
        # Clean up error stack traces
        """
        // Override Error.prepareStackTrace to clean traces
        if (Error.captureStackTrace) {
            var originalCaptureStackTrace = Error.captureStackTrace;
            Error.captureStackTrace = function(targetObject, constructorOpt) {
                originalCaptureStackTrace.call(this, targetObject, constructorOpt);
                if (targetObject.stack) {
                    targetObject.stack = targetObject.stack.replace(/.*eval.*\\n/g, '');
                }
            };
        }
        """,
        # Fix H264 codec detection
        """
        // Override canPlayType to always return 'probably' for H264
        (function() {
            HTMLMediaElement.prototype.canPlayType = function(type) {
                if (type && (type.includes('h264') || type.includes('avc1') || type.includes('mp4'))) {
                    return 'probably';
                }
                return type ? 'probably' : '';
            };

            // Also fix dynamically created elements
            var _createElement = document.createElement;
            document.createElement = function(tagName) {
                var element = _createElement.apply(document, arguments);
                if (tagName === 'video' || tagName === 'audio') {
                    element.canPlayType = function(type) {
                        if (type && (type.includes('h264') || type.includes('avc1') || type.includes('mp4'))) {
                            return 'probably';
                        }
                        return type ? 'probably' : '';
                    };
                }
                return element;
            };

            // Fix Audio constructor
            var _Audio = window.Audio;
            if (_Audio) {
                window.Audio = function() {
                    var audio = new _Audio(...arguments);
                    audio.canPlayType = function(type) {
                        if (type && (type.includes('h264') || type.includes('avc1') || type.includes('mp4'))) {
                            return 'probably';
                        }
                        return type ? 'probably' : '';
                    };
                    return audio;
                };
            }
        })();
        """,
        # Fix WebGL context and vendor/renderer
        """
        // Ensure WebGL works and returns proper vendor/renderer info
        (function() {
            // First, ensure WebGL is available
            if (!window.WebGLRenderingContext) {
                window.WebGLRenderingContext = function() {};
            }
            if (!window.WebGL2RenderingContext) {
                window.WebGL2RenderingContext = function() {};
            }

            // Store original getContext
            var originalGetContext = HTMLCanvasElement.prototype.getContext;

            // Override getContext to ensure WebGL contexts work properly
            HTMLCanvasElement.prototype.getContext = function(contextType, contextAttributes) {
                // For WebGL contexts
                if (contextType === 'webgl' || contextType === 'experimental-webgl' || contextType === 'webgl2') {
                    // Get the real context
                    var context = originalGetContext.call(this, contextType, contextAttributes);

                    // If context creation failed, try alternative
                    if (!context && contextType === 'webgl2') {
                        context = originalGetContext.call(this, 'webgl', contextAttributes);
                    }
                    if (!context && contextType === 'webgl') {
                        context = originalGetContext.call(this, 'experimental-webgl', contextAttributes);
                    }

                    // If we have a context, enhance it
                    if (context) {
                        // Wrap getParameter
                        if (context.getParameter) {
                            var originalGetParameter = context.getParameter.bind(context);
                            context.getParameter = function(pname) {
                                // Check for vendor/renderer queries from debug extension
                                if (pname === 0x9245) { // UNMASKED_VENDOR_WEBGL
                                    return 'Google Inc. (Intel)';
                                }
                                if (pname === 0x9246) { // UNMASKED_RENDERER_WEBGL
                                    return 'ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)';
                                }
                                // Default parameters
                                if (pname === context.VENDOR || pname === 0x1F00) {
                                    return 'WebKit';
                                }
                                if (pname === context.RENDERER || pname === 0x1F01) {
                                    return 'WebKit WebGL';
                                }
                                if (pname === context.VERSION || pname === 0x1F02) {
                                    return 'WebGL 1.0 (OpenGL ES 2.0 Chromium)';
                                }
                                // For everything else, use original
                                return originalGetParameter(pname);
                            };
                        }

                        // Wrap getExtension
                        if (context.getExtension) {
                            var originalGetExtension = context.getExtension.bind(context);
                            context.getExtension = function(name) {
                                // Get the real extension first
                                var ext = originalGetExtension(name);

                                // For debug info, ensure it exists
                                if (name === 'WEBGL_debug_renderer_info') {
                                    if (!ext) {
                                        ext = {};
                                    }
                                    // Always provide these constants
                                    ext.UNMASKED_VENDOR_WEBGL = 0x9245;
                                    ext.UNMASKED_RENDERER_WEBGL = 0x9246;
                                }

                                return ext;
                            };
                        }

                        // Add getSupportedExtensions if missing
                        if (!context.getSupportedExtensions) {
                            context.getSupportedExtensions = function() {
                                return [
                                    'ANGLE_instanced_arrays',
                                    'EXT_blend_minmax',
                                    'EXT_color_buffer_half_float',
                                    'EXT_disjoint_timer_query',
                                    'EXT_float_blend',
                                    'EXT_frag_depth',
                                    'EXT_shader_texture_lod',
                                    'EXT_texture_compression_bptc',
                                    'EXT_texture_compression_rgtc',
                                    'EXT_texture_filter_anisotropic',
                                    'WEBKIT_EXT_texture_filter_anisotropic',
                                    'EXT_sRGB',
                                    'KHR_parallel_shader_compile',
                                    'OES_element_index_uint',
                                    'OES_fbo_render_mipmap',
                                    'OES_standard_derivatives',
                                    'OES_texture_float',
                                    'OES_texture_float_linear',
                                    'OES_texture_half_float',
                                    'OES_texture_half_float_linear',
                                    'OES_vertex_array_object',
                                    'WEBGL_color_buffer_float',
                                    'WEBGL_compressed_texture_s3tc',
                                    'WEBKIT_WEBGL_compressed_texture_s3tc',
                                    'WEBGL_compressed_texture_s3tc_srgb',
                                    'WEBGL_debug_renderer_info',
                                    'WEBGL_debug_shaders',
                                    'WEBGL_depth_texture',
                                    'WEBKIT_WEBGL_depth_texture',
                                    'WEBGL_draw_buffers',
                                    'WEBGL_lose_context',
                                    'WEBKIT_WEBGL_lose_context',
                                    'WEBGL_multi_draw'
                                ];
                            };
                        }
                    }

                    return context;
                }

                // For other context types, use original
                return originalGetContext.call(this, contextType, contextAttributes);
            };

            // Fix toString
            HTMLCanvasElement.prototype.getContext.toString = function() {
                return 'function getContext() { [native code] }';
            };
        })();
        """,
        # Fix AudioContext fingerprinting
        """
        // Protect against AudioContext fingerprinting
        (function() {
            var audioContext = window.AudioContext || window.webkitAudioContext;
            if (audioContext) {
                var original = audioContext.prototype.constructor;
                audioContext.prototype.constructor = function() {
                    var ctx = new original();
                    // Add noise to audio fingerprinting
                    var originalCreateOscillator = ctx.createOscillator;
                    if (originalCreateOscillator) {
                        ctx.createOscillator = function() {
                            var osc = originalCreateOscillator.apply(ctx, arguments);
                            // Add tiny frequency variation
                            var originalFrequency = Object.getOwnPropertyDescriptor(OscillatorNode.prototype, 'frequency');
                            if (originalFrequency) {
                                Object.defineProperty(osc, 'frequency', {
                                    get: function() {
                                        return originalFrequency.get.call(this);
                                    },
                                    set: function(value) {
                                        originalFrequency.set.call(this, value * (1 + (Math.random() * 0.0001)));
                                    }
                                });
                            }
                            return osc;
                        };
                    }
                    return ctx;
                };
            }
        })();
        """,
    ]

    for script in scripts:
        try:
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": script})
        except Exception as e:
            logger.warning(f"Failed to execute anti-detection script: {e}")
