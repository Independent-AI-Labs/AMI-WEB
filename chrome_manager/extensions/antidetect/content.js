/* eslint-env browser */

// Content script - injects our anti-detection code into the page
// This runs at document_start before any page scripts

(function() {
    'use strict';
    
    // Create a script element to inject our code into the page context
    var script = document.createElement('script');
    script.src = chrome.runtime.getURL('inject.js');
    script.onload = function() {
        this.remove();
    };
    
    // Inject as early as possible
    (document.head || document.documentElement).appendChild(script);
    // Empty - all logic is in inject.js
})();