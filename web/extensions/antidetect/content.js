/* eslint-env browser */

// MINIMAL content script - ONLY injects webdriver removal
// ALL OTHER SPOOFING IS DONE VIA CDP

(function() {
    'use strict';
    
    try {
        // Inject ONLY the webdriver removal script
        var script = document.createElement('script');
        script.src = chrome.runtime.getURL('inject.js');
        script.onload = function() {
            this.remove();
        };
        
        // Inject as early as possible
        (document.head || document.documentElement).appendChild(script);
    } catch(e) {
        // Silent fail to avoid exposing automation
    }
})();