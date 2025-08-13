// Complete anti-detection script for ALL tabs
(function antiDetect() {
    'use strict';
    
    try {
    
    // Mark as applied
    window.__completeAntiDetectApplied = true;
    
    // Store this script for reuse in new windows
    window.__antiDetectScript = antiDetect.toString() + '();';
    
    // ========== WEBDRIVER REMOVAL ==========
    // Chrome 141+ sets navigator.webdriver = false instead of true
    // Use the most effective method: Object.defineProperty with prototype cleanup
    
    const removeWebdriver = function() {
        try {
            // First clean up the prototype if needed
            if (Navigator.prototype.hasOwnProperty('webdriver')) {
                delete Navigator.prototype.webdriver;
            }
            
            // Define property to always return undefined
            Object.defineProperty(navigator, 'webdriver', {
                get: function() { return undefined; },
                set: function() {},
                enumerable: false,
                configurable: true
            });
            
            // Also handle Object.getOwnPropertyDescriptor checks
            const origGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
            Object.getOwnPropertyDescriptor = function(obj, prop) {
                if (prop === 'webdriver' && (obj === navigator || obj === Navigator.prototype)) {
                    return undefined;
                }
                return origGetOwnPropertyDescriptor.apply(this, arguments);
            };
        } catch(e) {}
    };
    
    // Function to check and remove if re-added
    const checkWebDriver = function() {
        if ('webdriver' in navigator && navigator.webdriver !== undefined) {
            removeWebdriver();
        }
    };
    
    // Run immediately
    removeWebdriver();
    
    // Run on page events
    if (typeof document !== 'undefined') {
        // Run when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', checkWebDriver);
        } else {
            checkWebDriver();
        }
        
        // Run on readystatechange
        document.addEventListener('readystatechange', checkWebDriver);
        
        // Use MutationObserver instead of polling
        const observer = new MutationObserver(function(mutations) {
            // Check if webdriver property has been added back
            if ('webdriver' in navigator && navigator.webdriver !== undefined) {
                checkWebDriver();
            }
        });
        
        // Observe changes to navigator object and document
        if (document.documentElement) {
            observer.observe(document.documentElement, {
                childList: true,
                subtree: true,
                attributes: true
            });
        }
        
        // Clean up observer after page is fully loaded
        window.addEventListener('load', function() {
            setTimeout(function() {
                observer.disconnect();
            }, 1000); // Give it 1 second after load then stop observing
        });
    }
    
    // ========== H264 CODEC FIX ==========
    try {
        var originalCanPlayType = HTMLMediaElement.prototype.canPlayType;
        HTMLMediaElement.prototype.canPlayType = function(type) {
            if (!type) return '';
            var lowerType = type.toLowerCase();
            
            // Support H264/AVC1/MP4 codecs
            if (lowerType.indexOf('h264') !== -1 || 
                lowerType.indexOf('avc1') !== -1 || 
                lowerType.indexOf('mp4') !== -1) {
                return 'probably';
            }
            
            // Call original for other types
            if (originalCanPlayType) {
                return originalCanPlayType.apply(this, arguments);
            }
            return '';
        };
    } catch(e) {}
    
    // ========== PLUGIN CREATION ==========
    // Skip if already have plugins
    if (navigator.plugins && navigator.plugins.length > 0) {
        // Already have plugins, skip plugin creation only
    } else {
    
    // Create simple fake plugins that pass type checks
    var PluginArray = window.PluginArray || function() {};
    var Plugin = window.Plugin || function() {};
    var MimeType = window.MimeType || function() {};
    var MimeTypeArray = window.MimeTypeArray || function() {};
    
    // Create plugin data
    var pluginData = [
        {
            name: 'Chrome PDF Plugin',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format',
            mimes: [
                { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
                { type: 'text/pdf', suffixes: 'pdf', description: 'Portable Document Format' }
            ]
        },
        {
            name: 'Chrome PDF Viewer',
            filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
            description: '',
            mimes: [
                { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
                { type: 'text/pdf', suffixes: 'pdf', description: 'Portable Document Format' }
            ]
        },
        {
            name: 'Native Client',
            filename: 'internal-nacl-plugin',
            description: '',
            mimes: [
                { type: 'application/x-nacl', suffixes: '', description: 'Native Client Executable' },
                { type: 'application/x-pnacl', suffixes: '', description: 'Portable Native Client Executable' }
            ]
        }
    ];

    var mimeTypes = [];
    var plugins = [];

    // Build plugins using simpler approach
    for (var i = 0; i < pluginData.length; i++) {
        var data = pluginData[i];
        var plugin = {};
        
        // Set plugin properties
        Object.defineProperty(plugin, 'name', { value: data.name, writable: false, enumerable: true });
        Object.defineProperty(plugin, 'filename', { value: data.filename, writable: false, enumerable: true });
        Object.defineProperty(plugin, 'description', { value: data.description, writable: false, enumerable: true });
        Object.defineProperty(plugin, 'length', { value: data.mimes.length, writable: false, enumerable: true });
        
        // Add mimes
        for (var j = 0; j < data.mimes.length; j++) {
            var mimeData = data.mimes[j];
            var mime = {};
            
            Object.defineProperty(mime, 'type', { value: mimeData.type, writable: false, enumerable: true });
            Object.defineProperty(mime, 'suffixes', { value: mimeData.suffixes, writable: false, enumerable: true });
            Object.defineProperty(mime, 'description', { value: mimeData.description, writable: false, enumerable: true });
            Object.defineProperty(mime, 'enabledPlugin', { value: plugin, writable: false, enumerable: true });
            
            // Set prototype
            Object.setPrototypeOf(mime, MimeType.prototype);
            
            mimeTypes.push(mime);
            plugin[j] = mime;
        }
        
        // Add methods
        plugin.item = function(index) { return this[index] || null; };
        plugin.namedItem = function(name) { 
            for (var k = 0; k < this.length; k++) {
                if (this[k] && this[k].type === name) return this[k];
            }
            return null;
        };
        
        // Set prototype
        Object.setPrototypeOf(plugin, Plugin.prototype);
        
        plugins.push(plugin);
    }

    // Create PluginArray
    var pluginArray = [];
    pluginArray.length = plugins.length;
    for (var i = 0; i < plugins.length; i++) {
        pluginArray[i] = plugins[i];
        pluginArray[plugins[i].name] = plugins[i];
    }
    pluginArray.item = function(index) { return this[index] || null; };
    pluginArray.namedItem = function(name) { return this[name] || null; };
    pluginArray.refresh = function() {};
    Object.setPrototypeOf(pluginArray, PluginArray.prototype);

    // Create MimeTypeArray
    var mimeTypeArray = [];
    mimeTypeArray.length = mimeTypes.length;
    for (var i = 0; i < mimeTypes.length; i++) {
        mimeTypeArray[i] = mimeTypes[i];
        mimeTypeArray[mimeTypes[i].type] = mimeTypes[i];
    }
    mimeTypeArray.item = function(index) { return this[index] || null; };
    mimeTypeArray.namedItem = function(name) { return this[name] || null; };
    Object.setPrototypeOf(mimeTypeArray, MimeTypeArray.prototype);

    // Replace navigator.plugins
    try {
        Object.defineProperty(navigator, 'plugins', {
            get: function() { return pluginArray; },
            set: function() {},
            configurable: false,
            enumerable: true
        });
    } catch(e) {
        // Can't override, that's ok
    }

    // Replace navigator.mimeTypes
    try {
        Object.defineProperty(navigator, 'mimeTypes', {
            get: function() { return mimeTypeArray; },
            set: function() {},
            configurable: false,
            enumerable: true
        });
    } catch(e) {
        // Can't override, that's ok
    }
    
    } // End of else block for plugin creation
    
    // ========== WEBGL SPOOFING ==========
    // Store original getContext first
    var originalGetContext = HTMLCanvasElement.prototype.getContext;
    
    // Define WebGL extension constants if not present
    if (typeof WebGLRenderingContext !== 'undefined') {
        // These might not be defined, so define them
        if (!WebGLRenderingContext.prototype.UNMASKED_VENDOR_WEBGL) {
            WebGLRenderingContext.prototype.UNMASKED_VENDOR_WEBGL = 0x9245;
        }
        if (!WebGLRenderingContext.prototype.UNMASKED_RENDERER_WEBGL) {
            WebGLRenderingContext.prototype.UNMASKED_RENDERER_WEBGL = 0x9246;
        }
    }
    
    // Override getContext
    HTMLCanvasElement.prototype.getContext = function() {
        var context = originalGetContext.apply(this, arguments);
        if (context && (arguments[0] === 'webgl' || arguments[0] === 'webgl2' || arguments[0] === 'experimental-webgl')) {
            // Hook getParameter on the context
            if (context.getParameter) {
                var originalGetParameter = context.getParameter.bind(context);
                context.getParameter = function(pname) {
                    // UNMASKED_VENDOR_WEBGL
                    if (pname === 0x9245 || pname === 37445) {
                        return 'Google Inc. (Intel)';
                    }
                    // UNMASKED_RENDERER_WEBGL
                    if (pname === 0x9246 || pname === 37446) {
                        return 'ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)';
                    }
                    return originalGetParameter(pname);
                };
            }
            
            // Also hook getExtension to intercept WEBGL_debug_renderer_info
            if (context.getExtension) {
                var originalGetExtension = context.getExtension.bind(context);
                context.getExtension = function(name) {
                    var extension = originalGetExtension(name);
                    if (name === 'WEBGL_debug_renderer_info' && extension) {
                        // The extension object should have the constants
                        if (!extension.UNMASKED_VENDOR_WEBGL) {
                            extension.UNMASKED_VENDOR_WEBGL = 0x9245;
                        }
                        if (!extension.UNMASKED_RENDERER_WEBGL) {
                            extension.UNMASKED_RENDERER_WEBGL = 0x9246;
                        }
                    }
                    return extension;
                };
            }
        }
        return context;
    };
    
    // Also try to patch WebGLRenderingContext prototype directly
    try {
        if (typeof WebGLRenderingContext !== 'undefined' && WebGLRenderingContext.prototype.getParameter) {
            var originalWebGLGetParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(pname) {
                if (pname === 0x9245 || pname === 37445) {
                    return 'Google Inc. (Intel)';
                }
                if (pname === 0x9246 || pname === 37446) {
                    return 'ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)';
                }
                return originalWebGLGetParameter.call(this, pname);
            };
        }
    } catch(e) {}
    
    // Also try WebGL2
    try {
        if (typeof WebGL2RenderingContext !== 'undefined' && WebGL2RenderingContext.prototype.getParameter) {
            var originalWebGL2GetParameter = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(pname) {
                if (pname === 0x9245 || pname === 37445) {
                    return 'Google Inc. (Intel)';
                }
                if (pname === 0x9246 || pname === 37446) {
                    return 'ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)';
                }
                return originalWebGL2GetParameter.call(this, pname);
            };
        }
    } catch(e) {}
    
    // ========== WINDOW.OPEN INTERCEPTOR ==========
    // Don't try to intercept window.open - it doesn't work reliably
    // Instead, rely on the SimpleTabInjector to handle new tabs
    
    } catch(e) {
        // Silent fail to avoid exposing automation
        // Errors in anti-detection scripts should not be visible
    }
})();