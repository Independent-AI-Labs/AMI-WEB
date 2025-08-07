/* eslint-env browser */
// Ultra-aggressive WebGL spoofing - runs BEFORE any page scripts
(function() {
    'use strict';
    
    // Store original getContext immediately
    var originalGetContext = HTMLCanvasElement.prototype.getContext;
    
    // Create fake WebGL parameter values
    var fakeParams = {
        0x9245: 'Google Inc. (Intel)',  // UNMASKED_VENDOR_WEBGL
        0x9246: 'ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)',  // UNMASKED_RENDERER_WEBGL
        0x1F00: 'WebKit',  // VENDOR
        0x1F01: 'WebKit WebGL',  // RENDERER  
        0x1F02: 'WebGL 1.0 (OpenGL ES 2.0 Chromium)'  // VERSION
    };
    
    // Override getContext immediately
    HTMLCanvasElement.prototype.getContext = function(contextType, contextAttributes) {
        // Get the real context
        var context = originalGetContext.apply(this, arguments);
        
        // If it's a WebGL context, wrap getParameter
        if (context && (contextType === 'webgl' || contextType === 'experimental-webgl' || contextType === 'webgl2')) {
            // Store original getParameter
            var originalGetParameter = context.getParameter.bind(context);
            
            // Override getParameter
            context.getParameter = function(pname) {
                // Check if we have a fake value for this parameter
                if (fakeParams.hasOwnProperty(pname)) {
                    return fakeParams[pname];
                }
                
                // Check for constant values on the context
                if (pname === context.VENDOR) return 'WebKit';
                if (pname === context.RENDERER) return 'WebKit WebGL';
                if (pname === context.VERSION) return 'WebGL 1.0 (OpenGL ES 2.0 Chromium)';
                
                // Return original value
                return originalGetParameter(pname);
            };
        }
        
        return context;
    };
    
    // Also override WebGLRenderingContext if it exists
    if (window.WebGLRenderingContext && WebGLRenderingContext.prototype.getParameter) {
        var originalWebGLGetParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(pname) {
            if (fakeParams.hasOwnProperty(pname)) {
                return fakeParams[pname];
            }
            if (pname === this.VENDOR) return 'WebKit';
            if (pname === this.RENDERER) return 'WebKit WebGL';
            if (pname === this.VERSION) return 'WebGL 1.0 (OpenGL ES 2.0 Chromium)';
            return originalWebGLGetParameter.call(this, pname);
        };
    }
    
    // Also override WebGL2RenderingContext if it exists
    if (window.WebGL2RenderingContext && WebGL2RenderingContext.prototype.getParameter) {
        var originalWebGL2GetParameter = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(pname) {
            if (fakeParams.hasOwnProperty(pname)) {
                return fakeParams[pname];
            }
            if (pname === this.VENDOR) return 'WebKit';
            if (pname === this.RENDERER) return 'WebKit WebGL';
            if (pname === this.VERSION) return 'WebGL 2.0 (OpenGL ES 3.0 Chromium)';
            return originalWebGL2GetParameter.call(this, pname);
        };
    }
})();