/* eslint-env browser */
// Plugin array spoofing to pass type checks
(function() {
    'use strict';
    
    console.log('[PLUGINS-FIX] Starting. Current plugins:', navigator.plugins ? navigator.plugins.length : 'undefined');
    
    // Only skip if Chrome has ACTUAL plugins (length > 0)
    if (navigator.plugins && navigator.plugins.length > 0) {
        console.log('[PLUGINS-FIX] Chrome has', navigator.plugins.length, 'plugins. Skipping.');
        return; // Chrome already has valid plugins, don't break them!
    }
    
    console.log('[PLUGINS-FIX] Creating fake plugins...');
    // Create fake plugins if they're missing or empty
    if (!navigator.plugins || navigator.plugins.length === 0) {
    
    // Create fake plugin data
    var pluginData = [
        {
            name: 'Chrome PDF Viewer',
            filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
            description: 'Portable Document Format',
            mimeTypes: [
                {type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format'},
                {type: 'text/pdf', suffixes: 'pdf', description: 'Portable Document Format'}
            ]
        },
        {
            name: 'Chromium PDF Viewer', 
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format',
            mimeTypes: [
                {type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format'},
                {type: 'text/pdf', suffixes: 'pdf', description: 'Portable Document Format'}
            ]
        },
        {
            name: 'Microsoft Edge PDF Viewer',
            filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', 
            description: 'Portable Document Format',
            mimeTypes: [
                {type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format'}
            ]
        },
        {
            name: 'PDF Viewer',
            filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
            description: 'Portable Document Format', 
            mimeTypes: [
                {type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format'}
            ]
        },
        {
            name: 'WebKit built-in PDF',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format',
            mimeTypes: [
                {type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format'}
            ]
        }
    ];
    
    // Create MimeType objects
    var mimeTypes = [];
    var mimeTypeArray = Object.create(MimeTypeArray.prototype);
    
    // Create Plugin objects
    var plugins = [];
    pluginData.forEach(function(p) {
        var plugin = Object.create(Plugin.prototype);
        plugin.name = p.name;
        plugin.filename = p.filename;
        plugin.description = p.description;
        plugin.length = p.mimeTypes.length;
        
        // Add mime types to the plugin
        p.mimeTypes.forEach(function(mt, i) {
            var mimeType = Object.create(MimeType.prototype);
            mimeType.type = mt.type;
            mimeType.suffixes = mt.suffixes;
            mimeType.description = mt.description;
            mimeType.enabledPlugin = plugin;
            
            plugin[i] = mimeType;
            plugin[mt.type] = mimeType;
            
            mimeTypes.push(mimeType);
            mimeTypeArray[mt.type] = mimeType;
        });
        
        // Add item method to plugin
        plugin.item = function(index) {
            return this[index] || null;
        };
        
        // Add namedItem method to plugin
        plugin.namedItem = function(name) {
            return this[name] || null;
        };
        
        plugins.push(plugin);
    });
    
    // Create PluginArray
    var pluginArray = Object.create(PluginArray.prototype);
    pluginArray.length = plugins.length;
    
    // Add plugins to array by index and name
    plugins.forEach(function(p, i) {
        pluginArray[i] = p;
        pluginArray[p.name] = p;
    });
    
    // Add item method to pluginArray
    pluginArray.item = function(index) {
        return this[index] || null;
    };
    
    // Add namedItem method to pluginArray
    pluginArray.namedItem = function(name) {
        return this[name] || null;
    };
    
    // Add refresh method to pluginArray
    pluginArray.refresh = function() {};
    
    // Set up mimeTypeArray
    mimeTypeArray.length = mimeTypes.length;
    mimeTypes.forEach(function(mt, i) {
        mimeTypeArray[i] = mt;
    });
    
    // Add item method to mimeTypeArray
    mimeTypeArray.item = function(index) {
        return this[index] || null;
    };
    
    // Add namedItem method to mimeTypeArray
    mimeTypeArray.namedItem = function(name) {
        return this[name] || null;
    };
    
    // Override navigator.plugins
    Object.defineProperty(navigator, 'plugins', {
        get: function() { return pluginArray; },
        configurable: true,
        enumerable: true
    });
    
    // Override navigator.mimeTypes
    Object.defineProperty(navigator, 'mimeTypes', {
        get: function() { return mimeTypeArray; },
        configurable: true,
        enumerable: true
    });
    
    console.log('[PLUGINS-FIX] Created', pluginArray.length, 'plugins successfully');
    }
})();