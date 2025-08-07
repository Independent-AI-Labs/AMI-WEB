// Unified anti-detection spoofing script - ES5 compatible
// This file contains ALL anti-detection logic in one place

(function() {
    'use strict';
    
    // Mark as applied to prevent conflicts with extension
    window.__antiDetectApplied = true;
    
    // ==================== WEBDRIVER REMOVAL ====================
    // Remove webdriver property completely - MUST RUN FIRST
    
    // First try to delete it
    try {
        delete navigator.webdriver;
    } catch(e) {}
    
    try {
        delete Navigator.prototype.webdriver;
    } catch(e) {}
    
    // Now redefine to always return undefined
    var defineWebdriverProperty = function(obj) {
        try {
            if (obj && obj.webdriver !== undefined) {
                delete obj.webdriver;
            }
            Object.defineProperty(obj, 'webdriver', {
                get: function() { return undefined; },
                set: function() {},
                configurable: false,
                enumerable: false
            });
        } catch(e) {}
    };
    
    defineWebdriverProperty(navigator);
    defineWebdriverProperty(Navigator.prototype);
    
    // Override Object.getOwnPropertyDescriptor to hide webdriver
    var originalGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
    Object.getOwnPropertyDescriptor = function(obj, prop) {
        if (prop === 'webdriver') {
            return undefined;
        }
        return originalGetOwnPropertyDescriptor.apply(this, arguments);
    };
    
    // ==================== CDC PROPERTIES REMOVAL ====================
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
    
    deleteFromObject(window);
    deleteFromObject(document);
    deleteFromObject(navigator);
    
    // Monitor for CDC properties being added later
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
    
    // ==================== H264 CODEC SPOOFING ====================
    // Override canPlayType to always return 'probably' for H264
    var originalCanPlayType = HTMLMediaElement.prototype.canPlayType;
    HTMLMediaElement.prototype.canPlayType = function(type) {
        if (!type) return '';
        // More comprehensive H264 detection
        var lowerType = type.toLowerCase();
        if (lowerType.indexOf('h264') !== -1 || 
            lowerType.indexOf('avc1') !== -1 || 
            lowerType.indexOf('mp4') !== -1 ||
            lowerType.indexOf('video/mp4') !== -1) {
            return 'probably';
        }
        // Fallback to original for other types
        if (originalCanPlayType) {
            return originalCanPlayType.apply(this, arguments);
        }
        return '';
    };
    
    // Fix dynamically created elements
    var _createElement = document.createElement;
    document.createElement = function(tagName) {
        var element = _createElement.apply(document, arguments);
        if (tagName === 'video' || tagName === 'audio') {
            element.canPlayType = function(type) {
                if (!type) return '';
                var lowerType = type.toLowerCase();
                if (lowerType.indexOf('h264') !== -1 || 
                    lowerType.indexOf('avc1') !== -1 || 
                    lowerType.indexOf('mp4') !== -1 ||
                    lowerType.indexOf('video/mp4') !== -1) {
                    return 'probably';
                }
                if (originalCanPlayType) {
                    return originalCanPlayType.apply(this, arguments);
                }
                return '';
            };
        }
        return element;
    };
    
    // Fix Audio constructor
    var _Audio = window.Audio;
    if (_Audio) {
        window.Audio = function(src) {
            var audio = src ? new _Audio(src) : new _Audio();
            audio.canPlayType = function(type) {
                if (!type) return '';
                var lowerType = type.toLowerCase();
                if (lowerType.indexOf('h264') !== -1 || 
                    lowerType.indexOf('avc1') !== -1 || 
                    lowerType.indexOf('mp4') !== -1 ||
                    lowerType.indexOf('video/mp4') !== -1) {
                    return 'probably';
                }
                if (originalCanPlayType) {
                    return originalCanPlayType.apply(this, arguments);
                }
                return '';
            };
            return audio;
        };
    }
    
    // ==================== PLUGIN SPOOFING ====================
    // Only skip if Chrome has ACTUAL plugins (length > 0)
    // In anti-detect mode, Chrome starts with empty PluginArray
    
    // Create fake plugins if they're missing or empty
    if (!navigator.plugins || navigator.plugins.length === 0) {
        // Get original constructors
        var PluginArray = window.PluginArray || Object;
        var Plugin = window.Plugin || Object;
        var MimeTypeArray = window.MimeTypeArray || Object;
        var MimeType = window.MimeType || Object;
        
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
        
        // Create a new PluginArray
        var pluginArray = Object.create(PluginArray.prototype);
        
        // Add our plugins
        for (var j = 0; j < pluginData.length; j++) {
            var p = pluginData[j];
            var plugin = Object.create(Plugin.prototype);
            plugin.name = p.name;
            plugin.filename = p.filename;
            plugin.description = p.description;
            plugin.length = 2;
            
            // Add mime types
            plugin[0] = Object.create(MimeType.prototype);
            plugin[0].type = 'application/pdf';
            plugin[0].suffixes = 'pdf';
            plugin[0].description = 'Portable Document Format';
            plugin[0].enabledPlugin = plugin;
            
            plugin[1] = Object.create(MimeType.prototype);
            plugin[1].type = 'text/pdf';
            plugin[1].suffixes = 'pdf';
            plugin[1].description = 'Portable Document Format';
            plugin[1].enabledPlugin = plugin;
            
            // Add to array
            pluginArray[j] = plugin;
            pluginArray[plugin.name] = plugin;
        }
        
        // Set the length
        Object.defineProperty(pluginArray, 'length', {
            value: pluginData.length,
            writable: false,
            enumerable: false,
            configurable: true
        });
        
        // Add required methods
        pluginArray.item = function(index) {
            return this[index] || null;
        };
        pluginArray.namedItem = function(name) {
            return this[name] || null;
        };
        pluginArray.refresh = function() {};
        
        // Create MimeTypeArray
        var mimeTypeArray = Object.create(MimeTypeArray.prototype);
        var mimeIndex = 0;
        
        for (var m = 0; m < pluginData.length; m++) {
            for (var n = 0; n < pluginArray[m].length; n++) {
                mimeTypeArray[mimeIndex] = pluginArray[m][n];
                mimeTypeArray[pluginArray[m][n].type] = pluginArray[m][n];
                mimeIndex++;
            }
        }
        
        Object.defineProperty(mimeTypeArray, 'length', {
            value: mimeIndex,
            writable: false,
            enumerable: false,
            configurable: true
        });
        
        mimeTypeArray.item = function(index) {
            return this[index] || null;
        };
        mimeTypeArray.namedItem = function(name) {
            return this[name] || null;
        };
        
        // Override navigator.plugins and navigator.mimeTypes
        Object.defineProperty(navigator, 'plugins', {
            get: function() { return pluginArray; },
            configurable: false,
            enumerable: true
        });
        
        Object.defineProperty(navigator, 'mimeTypes', {
            get: function() { return mimeTypeArray; },
            configurable: false,
            enumerable: true
        });
    }
    
    // ==================== WEBGL SPOOFING ====================
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
            }
            
            return context;
        }
        
        // For other context types, use original
        return originalGetContext.call(this, contextType, contextAttributes);
    };
    
    // ==================== CHROME RUNTIME ====================
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
        getManifest: function() {
            return {
                version: '1.0.0',
                manifest_version: 2
            };
        },
        getURL: function(path) {
            return 'chrome-extension://fake-extension-id/' + path;
        }
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
    
    // ==================== NAVIGATOR PROPERTIES ====================
    // Set navigator.languages
    Object.defineProperty(navigator, 'languages', {
        get: function() { return ['en-US', 'en']; },
        configurable: false,
        enumerable: true
    });
    
    // ==================== PERMISSIONS API ====================
    // Fix permissions API
    if (window.navigator.permissions && window.navigator.permissions.query) {
        var originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = function(parameters) {
            return parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters);
        };
    }
    
    // ==================== FUNCTION TOSTRING ====================
    // Override Function.prototype.toString to show native code
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
    
    // ==================== AUDIO CONTEXT ====================
    // Protect against AudioContext fingerprinting
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
    
    // ==================== ERROR STACK TRACES ====================
    // Clean up error stack traces
    if (Error.captureStackTrace) {
        var originalCaptureStackTrace = Error.captureStackTrace;
        Error.captureStackTrace = function(targetObject, constructorOpt) {
            originalCaptureStackTrace.call(this, targetObject, constructorOpt);
            if (targetObject.stack) {
                targetObject.stack = targetObject.stack.replace(/.*eval.*\n/g, '');
            }
        };
    }
})();
