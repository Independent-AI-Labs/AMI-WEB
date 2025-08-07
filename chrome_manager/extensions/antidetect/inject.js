/* eslint-env browser */
/* global HTMLMediaElement, Plugin, MimeType */

// Injection script for anti-detection
// This MUST be pure ES5 - no const, let, arrow functions, template literals

(function() {
    'use strict';
    
    // ACTUALLY DELETE the webdriver property
    try {
        // Delete it first
        delete navigator.webdriver;
        
        // Make sure it stays deleted by removing it from the prototype too
        delete Navigator.prototype.webdriver;
        
        // DON'T redefine it! That makes it exist again!
        // Just leave it deleted!
    } catch (e) {
        // Ignore errors
    }
    
    // Fix H264 codec detection
    try {
        var originalCanPlayType = HTMLMediaElement.prototype.canPlayType;
        HTMLMediaElement.prototype.canPlayType = function(type) {
            if (!type) return '';
            if (type.indexOf('h264') !== -1 || 
                type.indexOf('avc1') !== -1 || 
                type.indexOf('mp4') !== -1) {
                return 'probably';
            }
            return originalCanPlayType ? originalCanPlayType.call(this, type) : 'probably';
        };
        
        // Override createElement for dynamically created media elements
        var originalCreateElement = document.createElement;
        document.createElement = function(tagName) {
            var element = originalCreateElement.call(document, tagName);
            if (tagName === 'video' || tagName === 'audio') {
                element.canPlayType = function(type) {
                    if (!type) return '';
                    if (type.indexOf('h264') !== -1 || 
                        type.indexOf('avc1') !== -1 || 
                        type.indexOf('mp4') !== -1) {
                        return 'probably';
                    }
                    return 'probably';
                };
            }
            return element;
        };
        
        // Fix Audio constructor
        if (window.Audio) {
            var OriginalAudio = window.Audio;
            window.Audio = function() {
                var audio = new OriginalAudio();
                audio.canPlayType = function(type) {
                    if (!type) return '';
                    if (type.indexOf('h264') !== -1 || 
                        type.indexOf('avc1') !== -1 || 
                        type.indexOf('mp4') !== -1) {
                        return 'probably';
                    }
                    return 'probably';
                };
                return audio;
            };
        }
    } catch (e) {
        // Ignore errors
    }
    
    // Add realistic plugins
    try {
        var pluginArray = [];
        
        // Chrome PDF Plugin
        var pdfPlugin = {};
        pdfPlugin.name = 'Chrome PDF Plugin';
        pdfPlugin.filename = 'internal-pdf-viewer';
        pdfPlugin.description = 'Portable Document Format';
        pdfPlugin.length = 1;
        pdfPlugin[0] = {
            type: 'application/pdf',
            suffixes: 'pdf',
            description: 'Portable Document Format'
        };
        pdfPlugin.item = function(i) { return this[i]; };
        pdfPlugin.namedItem = function() { return this[0]; };
        pluginArray.push(pdfPlugin);
        
        // Chrome PDF Viewer
        var pdfViewer = {};
        pdfViewer.name = 'Chrome PDF Viewer';
        pdfViewer.filename = 'mhjfbmdgcfjbbpaeojofohoefgiehjai';
        pdfViewer.description = '';
        pdfViewer.length = 1;
        pdfViewer[0] = {
            type: 'application/pdf',
            suffixes: 'pdf',
            description: ''
        };
        pdfViewer.item = function(i) { return this[i]; };
        pdfViewer.namedItem = function() { return this[0]; };
        pluginArray.push(pdfViewer);
        
        // Native Client
        var nativeClient = {};
        nativeClient.name = 'Native Client';
        nativeClient.filename = 'internal-nacl-plugin';
        nativeClient.description = '';
        nativeClient.length = 2;
        nativeClient[0] = {
            type: 'application/x-nacl',
            suffixes: '',
            description: 'Native Client Executable'
        };
        nativeClient[1] = {
            type: 'application/x-pnacl',
            suffixes: '',
            description: 'Portable Native Client Executable'
        };
        nativeClient.item = function(i) { return this[i]; };
        nativeClient.namedItem = function() { return this[0]; };
        pluginArray.push(nativeClient);
        
        // Add array methods
        pluginArray.item = function(i) { 
            return this[i]; 
        };
        pluginArray.namedItem = function(name) {
            for (var i = 0; i < this.length; i++) {
                if (this[i] && this[i].name === name) {
                    return this[i];
                }
            }
            return null;
        };
        pluginArray.refresh = function() {};
        
        Object.defineProperty(navigator, 'plugins', {
            get: function() { 
                return pluginArray; 
            },
            configurable: true,
            enumerable: true
        });
        
        // Add mimeTypes
        var mimeArray = [];
        mimeArray.push({
            type: 'application/pdf',
            suffixes: 'pdf',
            description: 'Portable Document Format',
            enabledPlugin: pdfPlugin
        });
        mimeArray.push({
            type: 'application/x-google-chrome-pdf',
            suffixes: 'pdf',
            description: 'Portable Document Format',
            enabledPlugin: pdfViewer
        });
        
        mimeArray.item = function(i) { 
            return this[i]; 
        };
        mimeArray.namedItem = function(type) {
            for (var i = 0; i < this.length; i++) {
                if (this[i] && this[i].type === type) {
                    return this[i];
                }
            }
            return null;
        };
        
        Object.defineProperty(navigator, 'mimeTypes', {
            get: function() { 
                return mimeArray; 
            },
            configurable: true,
            enumerable: true
        });
    } catch (e) {
        // Ignore errors
    }
})();