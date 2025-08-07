// Complete anti-detection script for ALL tabs
(function() {
    'use strict';
    
    // Mark as applied
    window.__completeAntiDetectApplied = true;
    
    // ========== WEBDRIVER REMOVAL ==========
    // Remove webdriver completely
    try {
        delete Object.getPrototypeOf(navigator).webdriver;
    } catch(e) {}
    
    Object.defineProperty(navigator, 'webdriver', {
        get: function() { return undefined; },
        set: function() {},
        configurable: false,
        enumerable: false
    });
    
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
    // Only create if empty
    if (!navigator.plugins || navigator.plugins.length === 0) {
        var pluginArray = [];
        
        // Chrome PDF Plugin
        var pdfPlugin = {
            name: 'Chrome PDF Plugin',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format',
            length: 2
        };
        pdfPlugin[0] = {
            type: 'application/pdf',
            suffixes: 'pdf',
            description: 'Portable Document Format',
            enabledPlugin: pdfPlugin
        };
        pdfPlugin[1] = {
            type: 'text/pdf',
            suffixes: 'pdf',
            description: 'Portable Document Format',
            enabledPlugin: pdfPlugin
        };
        pdfPlugin.item = function(i) { return this[i] || null; };
        pdfPlugin.namedItem = function(n) { return this[n] || null; };
        
        pluginArray[0] = pdfPlugin;
        pluginArray[pdfPlugin.name] = pdfPlugin;
        
        // Chrome PDF Viewer
        var viewerPlugin = {
            name: 'Chrome PDF Viewer',
            filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
            description: '',
            length: 2
        };
        viewerPlugin[0] = {
            type: 'application/pdf',
            suffixes: 'pdf',
            description: 'Portable Document Format',
            enabledPlugin: viewerPlugin
        };
        viewerPlugin[1] = {
            type: 'text/pdf',
            suffixes: 'pdf',
            description: 'Portable Document Format',
            enabledPlugin: viewerPlugin
        };
        viewerPlugin.item = function(i) { return this[i] || null; };
        viewerPlugin.namedItem = function(n) { return this[n] || null; };
        
        pluginArray[1] = viewerPlugin;
        pluginArray[viewerPlugin.name] = viewerPlugin;
        
        // Native Client
        var naclPlugin = {
            name: 'Native Client',
            filename: 'internal-nacl-plugin',
            description: '',
            length: 2
        };
        naclPlugin[0] = {
            type: 'application/x-nacl',
            suffixes: '',
            description: 'Native Client Executable',
            enabledPlugin: naclPlugin
        };
        naclPlugin[1] = {
            type: 'application/x-pnacl',
            suffixes: '',
            description: 'Portable Native Client Executable',
            enabledPlugin: naclPlugin
        };
        naclPlugin.item = function(i) { return this[i] || null; };
        naclPlugin.namedItem = function(n) { return this[n] || null; };
        
        pluginArray[2] = naclPlugin;
        pluginArray[naclPlugin.name] = naclPlugin;
        
        // Set array properties
        pluginArray.length = 3;
        pluginArray.item = function(i) { return this[i] || null; };
        pluginArray.namedItem = function(n) { return this[n] || null; };
        pluginArray.refresh = function() {};
        
        // Create mime array
        var mimeArray = [];
        var mimeIdx = 0;
        
        for (var i = 0; i < pluginArray.length; i++) {
            var plugin = pluginArray[i];
            for (var j = 0; j < plugin.length; j++) {
                var mime = plugin[j];
                mimeArray[mimeIdx++] = mime;
                mimeArray[mime.type] = mime;
            }
        }
        
        mimeArray.length = mimeIdx;
        mimeArray.item = function(i) { return this[i] || null; };
        mimeArray.namedItem = function(n) { return this[n] || null; };
        
        // Set prototypes
        if (window.PluginArray) {
            Object.setPrototypeOf(pluginArray, PluginArray.prototype);
        }
        if (window.MimeTypeArray) {
            Object.setPrototypeOf(mimeArray, MimeTypeArray.prototype);
        }
        
        for (var k = 0; k < pluginArray.length; k++) {
            if (window.Plugin) {
                Object.setPrototypeOf(pluginArray[k], Plugin.prototype);
            }
            for (var m = 0; m < pluginArray[k].length; m++) {
                if (window.MimeType) {
                    Object.setPrototypeOf(pluginArray[k][m], MimeType.prototype);
                }
            }
        }
        
        // Override navigator.plugins
        Object.defineProperty(navigator, 'plugins', {
            get: function() { return pluginArray; },
            configurable: true,
            enumerable: true
        });
        
        // Override navigator.mimeTypes
        Object.defineProperty(navigator, 'mimeTypes', {
            get: function() { return mimeArray; },
            configurable: true,
            enumerable: true
        });
    }
    
    // ========== WEBGL FIX ==========
    var originalGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(contextType, contextAttributes) {
        var context = originalGetContext.apply(this, arguments);
        if (context && (contextType === 'webgl' || contextType === 'experimental-webgl' || contextType === 'webgl2')) {
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
})();