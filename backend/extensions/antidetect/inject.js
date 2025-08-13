/* eslint-env browser */

// AGGRESSIVE webdriver removal and anti-detection - runs BEFORE page scripts
(function() {
    'use strict';
    
    // ========== WEBDRIVER REMOVAL ==========
    // Remove webdriver from window FIRST
    if (window.navigator && window.navigator.webdriver) {
        delete window.navigator.webdriver;
    }
    
    // Get the Navigator prototype
    var nav = window.Navigator ? window.Navigator.prototype : null;
    if (nav && nav.webdriver) {
        delete nav.webdriver;
    }
    
    // Force undefined on navigator.webdriver
    try {
        Object.defineProperty(window.navigator, 'webdriver', {
            get: function() { 
                return undefined; 
            },
            set: function() {},
            configurable: true,
            enumerable: false
        });
    } catch(e) {}
    
    // Intercept all property access
    var origGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
    Object.getOwnPropertyDescriptor = function(obj, prop) {
        if (prop === 'webdriver' && (obj === window.navigator || obj === Navigator.prototype)) {
            return undefined;
        }
        return origGetOwnPropertyDescriptor.apply(this, arguments);
    };
    
    // Override hasOwnProperty
    var origHasOwnProperty = Object.prototype.hasOwnProperty;
    Object.prototype.hasOwnProperty = function(prop) {
        if (prop === 'webdriver' && this === window.navigator) {
            return false;
        }
        return origHasOwnProperty.call(this, prop);
    };
    
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
        if (originalCanPlayType) {
            return originalCanPlayType.apply(this, arguments);
        }
        return '';
    };
    
    // ========== PLUGIN CREATION ==========
    // Only create plugins if they're missing or empty
    if (!window.navigator.plugins || window.navigator.plugins.length === 0) {
        try {
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
            
            // Override navigator.plugins and mimeTypes
            Object.defineProperty(window.navigator, 'plugins', {
                get: function() { return pluginArray; },
                configurable: true,
                enumerable: true
            });
            
            Object.defineProperty(window.navigator, 'mimeTypes', {
                get: function() { return mimeArray; },
                configurable: true,
                enumerable: true
            });
        } catch(e) {}
    }
})();