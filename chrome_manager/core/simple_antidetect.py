"""Simple working anti-detection scripts."""

def inject_antidetect(driver):
    """Inject working anti-detection scripts."""
    
    # Simple script that actually works - no const, no arrow functions, just ES5
    script = """
    (function() {
        // Remove webdriver
        delete navigator.webdriver;
        
        // Fix H264 codec
        HTMLMediaElement.prototype.canPlayType = function(type) {
            if (!type) return '';
            if (type.indexOf('h264') !== -1 || type.indexOf('avc1') !== -1 || type.indexOf('mp4') !== -1) {
                return 'probably';
            }
            return 'probably';
        };
        
        // Fix createElement for video/audio
        var originalCreateElement = document.createElement;
        document.createElement = function(tagName) {
            var element = originalCreateElement.call(document, tagName);
            if (tagName === 'video' || tagName === 'audio') {
                element.canPlayType = function(type) {
                    if (!type) return '';
                    if (type.indexOf('h264') !== -1 || type.indexOf('avc1') !== -1 || type.indexOf('mp4') !== -1) {
                        return 'probably';
                    }
                    return 'probably';
                };
            }
            return element;
        };
        
        // Add plugins
        var pluginArray = [];
        pluginArray.push({
            name: 'Chrome PDF Plugin',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format',
            length: 1,
            0: {type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format'}
        });
        pluginArray.push({
            name: 'Chrome PDF Viewer',
            filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
            description: '',
            length: 1,
            0: {type: 'application/pdf', suffixes: 'pdf', description: ''}
        });
        pluginArray.push({
            name: 'Native Client',
            filename: 'internal-nacl-plugin',
            description: '',
            length: 2,
            0: {type: 'application/x-nacl', suffixes: '', description: 'Native Client Executable'},
            1: {type: 'application/x-pnacl', suffixes: '', description: 'Portable Native Client Executable'}
        });
        
        // Add methods to plugins
        for (var i = 0; i < pluginArray.length; i++) {
            pluginArray[i].item = function(index) { return this[index]; };
            pluginArray[i].namedItem = function() { return this[0]; };
        }
        
        pluginArray.item = function(index) { return this[index]; };
        pluginArray.namedItem = function(name) {
            for (var i = 0; i < this.length; i++) {
                if (this[i].name === name) return this[i];
            }
            return null;
        };
        pluginArray.refresh = function() {};
        
        Object.defineProperty(navigator, 'plugins', {
            get: function() { return pluginArray; },
            configurable: true,
            enumerable: true
        });
        
        // Add mimeTypes
        var mimeArray = [
            {type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format'},
            {type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format'}
        ];
        mimeArray.item = function(i) { return this[i]; };
        mimeArray.namedItem = function(type) {
            for (var i = 0; i < this.length; i++) {
                if (this[i].type === type) return this[i];
            }
            return null;
        };
        
        Object.defineProperty(navigator, 'mimeTypes', {
            get: function() { return mimeArray; },
            configurable: true,
            enumerable: true
        });
    })();
    """
    
    try:
        # Enable CDP
        driver.execute_cdp_cmd("Page.enable", {})
        driver.execute_cdp_cmd("Runtime.enable", {})
        
        # Add script to run on EVERY new document (including new tabs)
        result = driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": script,
            "worldName": "",  # Empty means main world
            "includeCommandLineAPI": False,
            "runImmediately": True
        })
        
        print(f"Script registered with ID: {result.get('identifier', 'unknown')}")
        
        # Also execute immediately for current page
        driver.execute_cdp_cmd("Runtime.evaluate", {
            "expression": script,
            "userGesture": True,
            "awaitPromise": False
        })
        
        print("Anti-detection scripts injected successfully")
    except Exception as e:
        print(f"Failed to inject: {e}")