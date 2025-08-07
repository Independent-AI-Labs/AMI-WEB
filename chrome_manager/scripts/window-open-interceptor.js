// Intercept window.open to inject anti-detection immediately
(function() {
    'use strict';
    
    // Store original window.open
    var originalOpen = window.open;
    
    // Override window.open
    window.open = function() {
        // Call original
        var newWindow = originalOpen.apply(window, arguments);
        
        if (newWindow) {
            // Try to inject our anti-detection immediately
            try {
                // Wait a tiny bit for the window to be ready
                setTimeout(function() {
                    if (newWindow && !newWindow.__completeAntiDetectApplied) {
                        // Get our anti-detection script from the parent window
                        if (window.__antiDetectScript) {
                            try {
                                newWindow.eval(window.__antiDetectScript);
                            } catch(e) {
                                console.debug('Could not inject into new window:', e);
                            }
                        }
                    }
                }, 0);
            } catch(e) {
                console.debug('Error in window.open interceptor:', e);
            }
        }
        
        return newWindow;
    };
})();