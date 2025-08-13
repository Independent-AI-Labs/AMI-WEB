// Configuration loader for antidetection scripts
(function() {
    'use strict';
    
    // Default configuration (fallback if config file fails to load)
    const DEFAULT_CONFIG = {
        enabled: true,
        features: {
            webdriver: { enabled: true },
            chrome: { enabled: true },
            permissions: { enabled: true },
            plugins: { enabled: true },
            languages: { enabled: true },
            webgl: { enabled: true },
            canvas: { enabled: true },
            media_codecs: { enabled: true },
            webrtc: { enabled: false },
            timezone: { enabled: false },
            screen: { enabled: false },
            fonts: { enabled: false },
            audio: { enabled: false }
        }
    };
    
    // Export configuration getter
    window.__getAntidetectConfig = function() {
        try {
            // Try to load config from localStorage first (can be set by extension)
            const storedConfig = localStorage.getItem('antidetect_config');
            if (storedConfig) {
                return JSON.parse(storedConfig);
            }
        } catch(e) {}
        
        // Return default config
        return DEFAULT_CONFIG;
    };
    
    // Check if a feature is enabled
    window.__isFeatureEnabled = function(featureName) {
        try {
            const config = window.__getAntidetectConfig();
            return config.enabled && 
                   config.features && 
                   config.features[featureName] && 
                   config.features[featureName].enabled;
        } catch(e) {
            // Default to enabled for core features
            return ['webdriver', 'chrome', 'plugins'].includes(featureName);
        }
    };
    
    // Clean up global references after initialization
    setTimeout(function() {
        try {
            delete window.__getAntidetectConfig;
            delete window.__isFeatureEnabled;
        } catch(e) {}
    }, 100);
})();