// Browser Properties Injection Script Template
// This script is injected into every page to spoof browser properties
(function() {
    'use strict';
    
    // ========== USER AGENT & PLATFORM ==========
    {% if user_agent %}
    Object.defineProperty(navigator, 'userAgent', {
        get: () => '{{ user_agent }}',
        configurable: true
    });
    {% endif %}
    
    Object.defineProperty(navigator, 'platform', {
        get: () => '{{ platform }}',
        configurable: true
    });
    
    // ========== HARDWARE PROPERTIES ==========
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => {{ hardware_concurrency }},
        configurable: true
    });
    
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => {{ device_memory }},
        configurable: true
    });
    
    Object.defineProperty(navigator, 'maxTouchPoints', {
        get: () => {{ max_touch_points }},
        configurable: true
    });
    
    // ========== SCREEN PROPERTIES ==========
    Object.defineProperty(screen, 'width', {
        get: () => {{ screen_width }},
        configurable: true
    });
    
    Object.defineProperty(screen, 'height', {
        get: () => {{ screen_height }},
        configurable: true
    });
    
    Object.defineProperty(screen, 'availWidth', {
        get: () => {{ screen_width }},
        configurable: true
    });
    
    Object.defineProperty(screen, 'availHeight', {
        get: () => {{ screen_height }},
        configurable: true
    });
    
    Object.defineProperty(screen, 'colorDepth', {
        get: () => {{ color_depth }},
        configurable: true
    });
    
    Object.defineProperty(screen, 'pixelDepth', {
        get: () => {{ pixel_depth }},
        configurable: true
    });
    
    Object.defineProperty(window, 'devicePixelRatio', {
        get: () => {{ device_pixel_ratio }},
        configurable: true
    });
    
    // ========== LANGUAGES ==========
    {% if languages %}
    Object.defineProperty(navigator, 'languages', {
        get: () => {{ languages_json }},
        configurable: true
    });
    
    Object.defineProperty(navigator, 'language', {
        get: () => '{{ primary_language }}',
        configurable: true
    });
    {% endif %}
    
    // ========== TIMEZONE ==========
    {% if timezone %}
    const originalDateTimeFormat = Intl.DateTimeFormat;
    Intl.DateTimeFormat = new Proxy(originalDateTimeFormat, {
        construct(target, args) {
            if (args.length > 1 && args[1] && typeof args[1] === 'object') {
                args[1].timeZone = '{{ timezone }}';
            }
            return new target(...args);
        }
    });
    
    Date.prototype.getTimezoneOffset = function() {
        // This would need proper timezone offset calculation
        return {{ timezone_offset }};
    };
    {% endif %}
    
    // ========== WEBGL PROPERTIES ==========
    {% if webgl_vendor or webgl_renderer %}
    const getContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function() {
        const context = getContext.apply(this, arguments);
        if (context && (arguments[0] === 'webgl' || arguments[0] === 'webgl2' || arguments[0] === 'experimental-webgl')) {
            const getParameter = context.getParameter.bind(context);
            context.getParameter = function(param) {
                {% if webgl_vendor %}
                if (param === 0x9245) return '{{ webgl_vendor }}';
                {% endif %}
                {% if webgl_renderer %}
                if (param === 0x9246) return '{{ webgl_renderer }}';
                {% endif %}
                return getParameter(param);
            };
        }
        return context;
    };
    {% endif %}
    
    // ========== MEDIA CODECS ==========
    {% if override_codecs %}
    const originalCanPlayType = HTMLMediaElement.prototype.canPlayType;
    HTMLMediaElement.prototype.canPlayType = function(type) {
        const videoCodecs = {{ video_codecs_json }};
        const audioCodecs = {{ audio_codecs_json }};
        
        if (!type) return '';
        
        const normalizedType = type.toLowerCase();
        
        // Check video codecs
        for (const codec of videoCodecs) {
            if (normalizedType.includes(codec.toLowerCase())) {
                return 'probably';
            }
        }
        
        // Check audio codecs
        for (const codec of audioCodecs) {
            if (normalizedType.includes(codec.toLowerCase())) {
                return 'probably';
            }
        }
        
        return originalCanPlayType.apply(this, arguments);
    };
    {% endif %}
    
    // ========== BATTERY API ==========
    {% if battery_charging is not none %}
    navigator.getBattery = async function() {
        return {
            charging: {{ battery_charging_json }},
            chargingTime: {{ battery_charging_time }},
            dischargingTime: {{ battery_discharging_time }},
            level: {{ battery_level }},
            addEventListener: function() {},
            removeEventListener: function() {}
        };
    };
    {% endif %}
    
    // ========== CONNECTION API ==========
    {% if connection_type %}
    Object.defineProperty(navigator, 'connection', {
        get: () => ({
            effectiveType: '{{ connection_effective_type }}',
            type: '{{ connection_type }}',
            downlink: {{ connection_downlink }},
            rtt: {{ connection_rtt }},
            saveData: {{ connection_save_data_json }},
            addEventListener: function() {},
            removeEventListener: function() {}
        }),
        configurable: true
    });
    {% endif %}
    
    // ========== PERMISSIONS ==========
    {% if override_permissions %}
    const originalQuery = navigator.permissions.query;
    navigator.permissions.query = async function(permissionDesc) {
        const permissions = {{ permissions_json }};
        const name = permissionDesc.name || permissionDesc;
        
        if (permissions[name] !== undefined) {
            return {
                state: permissions[name],
                addEventListener: function() {},
                removeEventListener: function() {}
            };
        }
        
        return originalQuery.apply(this, arguments);
    };
    {% endif %}
    
    // ========== CLIENT HINTS ==========
    {% if client_hints %}
    if (navigator.userAgentData) {
        const brands = {{ client_hints_brands_json }};
        const clientHints = {{ client_hints_json }};
        
        Object.defineProperty(navigator.userAgentData, 'brands', {
            get: () => brands,
            configurable: true
        });
        
        Object.defineProperty(navigator.userAgentData, 'mobile', {
            get: () => clientHints.mobile,
            configurable: true
        });
        
        Object.defineProperty(navigator.userAgentData, 'platform', {
            get: () => clientHints.platform,
            configurable: true
        });
        
        navigator.userAgentData.getHighEntropyValues = async function() {
            return clientHints;
        };
    }
    {% endif %}
})();