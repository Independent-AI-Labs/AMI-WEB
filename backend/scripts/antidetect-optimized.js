/**
 * Optimized anti-detection script for Chrome automation
 * Removes redundant methods and polling for better performance
 */
(function() {
    'use strict';
    
    // Wrap everything in try-catch for error safety
    try {
        // === WEBDRIVER REMOVAL (Single most effective method) ===
        if ('webdriver' in navigator) {
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                set: () => {},
                enumerable: false,
                configurable: false
            });
        }
        
        // === CHROME OBJECT SPOOFING ===
        if (!window.chrome || !window.chrome.runtime) {
            const chrome = {
                runtime: {
                    connect: () => {},
                    sendMessage: () => {},
                    onMessage: { addListener: () => {} }
                },
                loadTimes: function() {
                    return {
                        requestTime: Date.now() / 1000,
                        startLoadTime: Date.now() / 1000,
                        commitLoadTime: Date.now() / 1000,
                        finishDocumentLoadTime: Date.now() / 1000,
                        finishLoadTime: Date.now() / 1000,
                        firstPaintTime: Date.now() / 1000,
                        firstPaintAfterLoadTime: 0,
                        navigationType: "Other",
                        wasFetchedViaSpdy: false,
                        wasNpnNegotiated: false,
                        npnNegotiatedProtocol: "",
                        wasAlternateProtocolAvailable: false,
                        connectionInfo: "http/1.1"
                    };
                },
                csi: function() {
                    return {
                        onloadT: Date.now(),
                        pageT: Date.now() - 1000,
                        startE: Date.now() - 2000,
                        tran: 15
                    };
                },
                app: {
                    isInstalled: false,
                    InstallState: {
                        DISABLED: "disabled",
                        INSTALLED: "installed",
                        NOT_INSTALLED: "not_installed"
                    },
                    RunningState: {
                        CANNOT_RUN: "cannot_run",
                        READY_TO_RUN: "ready_to_run",
                        RUNNING: "running"
                    }
                }
            };
            
            Object.defineProperty(window, 'chrome', {
                value: chrome,
                writable: false,
                enumerable: true,
                configurable: false
            });
        }
        
        // === PERMISSIONS API OVERRIDE ===
        if (navigator.permissions && navigator.permissions.query) {
            const originalQuery = navigator.permissions.query;
            navigator.permissions.query = function(parameters) {
                // Return granted for common permissions
                const grantedPermissions = ['notifications', 'push', 'midi', 'camera', 'microphone', 
                                           'speaker', 'device-info', 'background-sync', 'bluetooth', 
                                           'persistent-storage', 'ambient-light-sensor', 'accelerometer',
                                           'gyroscope', 'magnetometer', 'clipboard', 'accessibility-events',
                                           'clipboard-read', 'clipboard-write', 'payment-handler'];
                
                if (grantedPermissions.includes(parameters.name)) {
                    return Promise.resolve({ state: 'granted' });
                }
                return originalQuery.apply(this, arguments);
            };
        }
        
        // === PLUGIN SPOOFING ===
        if (navigator.plugins.length === 0) {
            const pluginData = [
                {
                    name: "Chrome PDF Plugin",
                    filename: "internal-pdf-viewer",
                    description: "Portable Document Format"
                },
                {
                    name: "Chrome PDF Viewer",
                    filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                    description: "Portable Document Format"
                },
                {
                    name: "Native Client",
                    filename: "internal-nacl-plugin",
                    description: "Native Client Executable"
                }
            ];
            
            Object.defineProperty(navigator, 'plugins', {
                get: function() {
                    const plugins = [];
                    pluginData.forEach((data, i) => {
                        const plugin = Object.create(Plugin.prototype);
                        plugin.name = data.name;
                        plugin.filename = data.filename;
                        plugin.description = data.description;
                        plugin.length = 1;
                        plugins.push(plugin);
                    });
                    plugins.length = pluginData.length;
                    return plugins;
                },
                enumerable: true,
                configurable: true
            });
        }
        
        // === LANGUAGE SPOOFING ===
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
            enumerable: true
        });
        
        // === WEBGL VENDOR/RENDERER SPOOFING ===
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';  // UNMASKED_VENDOR_WEBGL
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';  // UNMASKED_RENDERER_WEBGL
            }
            return getParameter.apply(this, arguments);
        };
        
        const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter2.apply(this, arguments);
        };
        
        // === CANVAS FINGERPRINTING PROTECTION ===
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function() {
            const context = this.getContext('2d');
            if (context) {
                // Add minimal noise to prevent fingerprinting
                const imageData = context.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    // Add tiny random noise to alpha channel (usually unnoticeable)
                    imageData.data[i + 3] = Math.min(255, imageData.data[i + 3] + (Math.random() * 2 - 1));
                }
                context.putImageData(imageData, 0, 0);
            }
            return originalToDataURL.apply(this, arguments);
        };
        
        // === WEBRTC LEAK PREVENTION ===
        if (window.RTCPeerConnection || window.webkitRTCPeerConnection || window.mozRTCPeerConnection) {
            const RTCPeerConnectionProxy = new Proxy(window.RTCPeerConnection || window.webkitRTCPeerConnection || window.mozRTCPeerConnection, {
                construct(target, args) {
                    const config = args[0] || {};
                    // Remove STUN servers to prevent IP leak
                    if (config.iceServers) {
                        config.iceServers = config.iceServers.filter(server => {
                            const urls = server.urls || server.url;
                            if (typeof urls === 'string') {
                                return !urls.includes('stun:');
                            }
                            if (Array.isArray(urls)) {
                                server.urls = urls.filter(url => !url.includes('stun:'));
                                return server.urls.length > 0;
                            }
                            return true;
                        });
                    }
                    return new target(config, args[1]);
                }
            });
            
            if (window.RTCPeerConnection) window.RTCPeerConnection = RTCPeerConnectionProxy;
            if (window.webkitRTCPeerConnection) window.webkitRTCPeerConnection = RTCPeerConnectionProxy;
            if (window.mozRTCPeerConnection) window.mozRTCPeerConnection = RTCPeerConnectionProxy;
        }
        
        // === BATTERY API SPOOFING ===
        if (navigator.getBattery) {
            navigator.getBattery = async () => ({
                charging: true,
                chargingTime: 0,
                dischargingTime: Infinity,
                level: 1.0,
                addEventListener: () => {},
                removeEventListener: () => {}
            });
        }
        
        // === HARDWARE CONCURRENCY SPOOFING ===
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 4,  // Common value
            enumerable: true
        });
        
        // === DEVICE MEMORY SPOOFING ===
        if ('deviceMemory' in navigator) {
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,  // Common value
                enumerable: true
            });
        }
        
        // === MUTATION OBSERVER FOR DYNAMIC DETECTION ===
        // Use MutationObserver instead of polling
        if (typeof MutationObserver !== 'undefined') {
            const observer = new MutationObserver((mutations) => {
                // Re-check webdriver only if new scripts are added
                for (const mutation of mutations) {
                    if (mutation.type === 'childList') {
                        for (const node of mutation.addedNodes) {
                            if (node.nodeName === 'SCRIPT') {
                                // Re-apply webdriver removal if a script was added
                                if ('webdriver' in navigator) {
                                    Object.defineProperty(navigator, 'webdriver', {
                                        get: () => undefined,
                                        enumerable: false
                                    });
                                }
                                break;
                            }
                        }
                    }
                }
            });
            
            // Start observing when DOM is ready
            if (document.body) {
                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });
            } else {
                document.addEventListener('DOMContentLoaded', () => {
                    observer.observe(document.body, {
                        childList: true,
                        subtree: true
                    });
                });
            }
        }
        
    } catch (err) {
        // Silent fail - don't expose automation through errors
        // Optionally log to a custom logger if needed
    }
})();