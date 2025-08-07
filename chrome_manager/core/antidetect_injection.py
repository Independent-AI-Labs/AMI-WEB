"""Single unified anti-detection injection script."""

ANTI_DETECTION_SCRIPT = """
// INJECT THIS BEFORE ANYTHING ELSE RUNS
(function() {
    // 1. REMOVE WEBDRIVER - NUKE IT FROM ORBIT
    delete navigator.webdriver;
    delete Navigator.prototype.webdriver;
    Object.defineProperty(navigator, 'webdriver', {
        get: function() { return undefined; },
        set: function() {},
        configurable: false,
        enumerable: false
    });

    // Also try on prototype
    try {
        Object.defineProperty(Navigator.prototype, 'webdriver', {
            get: function() { return undefined; },
            set: function() {},
            configurable: false,
            enumerable: false
        });
    } catch(e) {}

    // 2. FIX H264 CODECS - ALWAYS RETURN 'probably'
    const originalCanPlayType = HTMLMediaElement.prototype.canPlayType;
    Object.defineProperty(HTMLMediaElement.prototype, 'canPlayType', {
        value: function(type) {
            if (!type) return '';
            if (type.includes('h264') || type.includes('avc1') || type.includes('mp4')) {
                return 'probably';
            }
            return 'probably';
        },
        writable: false,
        configurable: false
    });

    // Fix createElement to handle dynamically created elements
    const _createElement = document.createElement.bind(document);
    document.createElement = function(tagName) {
        const element = _createElement(tagName);
        if (tagName === 'video' || tagName === 'audio') {
            Object.defineProperty(element, 'canPlayType', {
                value: function(type) {
                    if (!type) return '';
                    if (type.includes('h264') || type.includes('avc1') || type.includes('mp4')) {
                        return 'probably';
                    }
                    return 'probably';
                },
                writable: false,
                configurable: false
            });
        }
        return element;
    };

    // Fix Audio constructor
    const _Audio = window.Audio;
    if (_Audio) {
        window.Audio = function() {
            const audio = new _Audio(...arguments);
            Object.defineProperty(audio, 'canPlayType', {
                value: function(type) {
                    if (!type) return '';
                    if (type.includes('h264') || type.includes('avc1') || type.includes('mp4')) {
                        return 'probably';
                    }
                    return 'probably';
                },
                writable: false,
                configurable: false
            });
            return audio;
        };
    }

    // 3. ADD PLUGINS
    const pluginData = [
        {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format', length: 1},
        {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '', length: 1},
        {name: 'Native Client', filename: 'internal-nacl-plugin', description: '', length: 2}
    ];

    const plugins = [];
    pluginData.forEach((p, i) => {
        const plugin = Object.create(Plugin.prototype);
        Object.assign(plugin, p);

        if (i === 0) {
            plugin[0] = {type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format'};
        } else if (i === 1) {
            plugin[0] = {type: 'application/pdf', suffixes: 'pdf', description: ''};
        } else if (i === 2) {
            plugin[0] = {type: 'application/x-nacl', suffixes: '', description: 'Native Client Executable'};
            plugin[1] = {type: 'application/x-pnacl', suffixes: '', description: 'Portable Native Client Executable'};
        }

        plugin.item = function(i) { return this[i]; };
        plugin.namedItem = function() { return this[0]; };
        plugins.push(plugin);
    });

    plugins.item = function(i) { return this[i]; };
    plugins.namedItem = function(n) { return this.find(p => p.name === n); };
    plugins.refresh = function() {};

    Object.defineProperty(navigator, 'plugins', {
        get: function() { return plugins; },
        configurable: true,
        enumerable: true
    });

    // 4. ADD CHROME OBJECT
    if (!window.chrome) {
        window.chrome = {};
    }
    if (!window.chrome.runtime) {
        window.chrome.runtime = {
            id: 'fake-extension-id',
            connect: function() {},
            sendMessage: function() {}
        };
    }
})();
"""
