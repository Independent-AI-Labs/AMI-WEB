// Complete anti-detection script for ALL tabs
(function antiDetect() {
    'use strict';
    
    // Mark as applied
    window.__completeAntiDetectApplied = true;
    
    // Store this script for reuse in new windows
    window.__antiDetectScript = antiDetect.toString() + '();';
    
    // ========== WEBDRIVER REMOVAL ==========
    // Remove webdriver completely
    try {
        delete Object.getPrototypeOf(navigator).webdriver;
    } catch(e) {}
    
    try {
        Object.defineProperty(navigator, 'webdriver', {
            get: function() { return undefined; },
            set: function() {},
            configurable: false,
            enumerable: false
        });
    } catch(e) {
        // Already defined, that's fine
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
    // Intercept window.open to inject anti-detection into new windows
    var originalOpen = window.open;
    window.open = function() {
        var newWindow = originalOpen.apply(window, arguments);
        
        if (newWindow) {
            // Try to inject our anti-detection immediately
            try {
                // Use a small delay to ensure window is ready
                setTimeout(function() {
                    if (newWindow && !newWindow.__completeAntiDetectApplied) {
                        try {
                            // Inject the entire anti-detection script
                            var script = window.__antiDetectScript;
                            if (script) {
                                newWindow.eval(script);
                            }
                        } catch(e) {
                            // Can't inject cross-origin
                        }
                    }
                }, 10);
            } catch(e) {}
        }
        
        return newWindow;
    };
})();