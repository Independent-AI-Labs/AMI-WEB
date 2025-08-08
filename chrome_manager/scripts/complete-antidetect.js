// Complete anti-detection script for ALL tabs
(function antiDetect() {
    'use strict';
    
    // Mark as applied
    window.__completeAntiDetectApplied = true;
    
    // Store this script for reuse in new windows
    window.__antiDetectScript = antiDetect.toString() + '();';
    
    // ========== WEBDRIVER REMOVAL ==========
    // Chrome 141+ sets navigator.webdriver = false instead of true
    // We need to completely remove the property, not just set it to undefined
    
    // Method 1: Delete from Navigator.prototype first
    try {
        delete Navigator.prototype.webdriver;
    } catch(e) {}
    
    // Method 2: Try to delete the property from navigator
    try {
        delete navigator.webdriver;
    } catch(e) {}
    
    // Method 3: If property still exists, override it to be undefined
    // AND make it non-enumerable and report as non-existent
    try {
        // Check if property exists using 'in' operator
        if ('webdriver' in navigator) {
            // First try to delete it
            delete navigator.webdriver;
            
            // If still there, override with getter that returns undefined
            if ('webdriver' in navigator) {
                Object.defineProperty(navigator, 'webdriver', {
                    get: function() { return undefined; },
                    set: function() {},
                    enumerable: false,
                    configurable: true
                });
            }
        }
    } catch(e) {}
    
    // Method 4: Override Navigator.prototype if the property is there
    try {
        if (Navigator.prototype.hasOwnProperty('webdriver')) {
            Object.defineProperty(Navigator.prototype, 'webdriver', {
                get: function() { return undefined; },
                set: function() {},
                enumerable: false,
                configurable: true
            });
        }
    } catch(e) {}
    
    // Method 4: Proxy the entire navigator object
    try {
        // Create a proxy for navigator that intercepts webdriver
        const navProxy = new Proxy(navigator, {
            has: function(target, key) {
                return key === 'webdriver' ? false : key in target;
            },
            get: function(target, key) {
                return key === 'webdriver' ? undefined : target[key];
            }
        });
        
        // Try to replace global navigator
        if (Object.defineProperty) {
            Object.defineProperty(window, 'navigator', {
                value: navProxy,
                writable: false,
                configurable: false
            });
        }
    } catch(e) {}
    
    // Method 6: Monitor and continuously remove
    const checkWebDriver = function() {
        // Check if webdriver property exists at all (even if false)
        if ('webdriver' in navigator) {
            try {
                // Try to delete it
                delete navigator.webdriver;
            } catch(e) {}
            
            // If still exists after delete attempt, override it
            if ('webdriver' in navigator) {
                try {
                    Object.defineProperty(navigator, 'webdriver', {
                        get: function() { return undefined; },
                        set: function() {},
                        enumerable: false,
                        configurable: true
                    });
                } catch(e) {}
            }
        }
    };
    
    // Run immediately
    checkWebDriver();
    
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
        
        // Run periodically for first 2 seconds
        let counter = 0;
        const interval = setInterval(function() {
            checkWebDriver();
            counter++;
            if (counter > 40) clearInterval(interval); // 40 * 50ms = 2 seconds
        }, 50);
    }
    
    // ========== H264 CODEC FIX ==========
    var originalCanPlayType = HTMLMediaElement.prototype.canPlayType;
    HTMLMediaElement.prototype.canPlayType = function(type) {
        if (!type) return '';
        var lowerType = type.toLowerCase();
        if (lowerType.indexOf('h264') !== -1 || 
            lowerType.indexOf('avc1') !== -1 || 
            lowerType.indexOf('mp4') !== -1) {
            return 'probably';
        }
        return originalCanPlayType ? originalCanPlayType.apply(this, arguments) : '';
    };
    
    // ========== PLUGIN CREATION ==========
    // Skip if already have plugins
    if (navigator.plugins && navigator.plugins.length > 0) {
        return; // Already have plugins, don't override
    }
    
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
    
    // ========== WEBGL SPOOFING ==========
    var originalGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function() {
        var context = originalGetContext.apply(this, arguments);
        if (context && (arguments[0] === 'webgl' || arguments[0] === 'webgl2' || arguments[0] === 'experimental-webgl')) {
            if (context.getParameter) {
                var originalGetParameter = context.getParameter.bind(context);
                context.getParameter = function(pname) {
                    if (pname === 0x9245) return 'Google Inc. (Intel)';
                    if (pname === 0x9246) return 'ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)';
                    return originalGetParameter(pname);
                };
            }
        }
        return context;
    };
    
    // ========== WINDOW.OPEN INTERCEPTOR ==========
    // Don't try to intercept window.open - it doesn't work reliably
    // Instead, rely on the SimpleTabInjector to handle new tabs
})();