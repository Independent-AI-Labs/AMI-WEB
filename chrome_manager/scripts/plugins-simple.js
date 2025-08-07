// Simple plugin creation without complex logic
(function() {
    'use strict';
    
    // Only create if plugins are empty
    if (navigator.plugins && navigator.plugins.length > 0) {
        return;
    }
    
    try {
        // Create plugin data
        var pluginArray = [];
        
        // Add Chrome PDF Plugin
        var pdfPlugin = {
            name: 'Chrome PDF Plugin',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format',
            length: 2
        };
        
        // Add mime types to plugin
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
        
        // Make it array-like
        pdfPlugin.item = function(i) { return this[i] || null; };
        pdfPlugin.namedItem = function(n) { return this[n] || null; };
        
        pluginArray[0] = pdfPlugin;
        pluginArray[pdfPlugin.name] = pdfPlugin;
        
        // Add Chrome PDF Viewer
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
        
        // Add Native Client
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
        
        // Create mime types array
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
        
        // Set constructor properties
        Object.setPrototypeOf(pluginArray, PluginArray.prototype);
        Object.setPrototypeOf(mimeArray, MimeTypeArray.prototype);
        
        for (var k = 0; k < pluginArray.length; k++) {
            Object.setPrototypeOf(pluginArray[k], Plugin.prototype);
            for (var m = 0; m < pluginArray[k].length; m++) {
                Object.setPrototypeOf(pluginArray[k][m], MimeType.prototype);
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
        
    } catch(e) {
        console.error('[PLUGIN-SIMPLE] Error creating plugins:', e);
    }
})();