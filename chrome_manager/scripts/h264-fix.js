/* eslint-env browser */
// H264 codec fix - ensure it returns "probably" instead of empty or WARN
(function() {
    'use strict';
    
    // Store original canPlayType
    var originalCanPlayType = HTMLMediaElement.prototype.canPlayType;
    
    // Override canPlayType
    HTMLMediaElement.prototype.canPlayType = function(type) {
        if (!type) return '';
        
        var lowerType = type.toLowerCase();
        
        // Check for H264/AVC1/MP4 codecs
        if (lowerType.indexOf('h264') !== -1 || 
            lowerType.indexOf('avc1') !== -1 || 
            lowerType.indexOf('mp4') !== -1 ||
            lowerType.indexOf('video/mp4') !== -1) {
            return 'probably';
        }
        
        // Check for WebM codecs
        if (lowerType.indexOf('webm') !== -1 ||
            lowerType.indexOf('vp8') !== -1 ||
            lowerType.indexOf('vp9') !== -1) {
            return 'probably';
        }
        
        // Check for Ogg codecs
        if (lowerType.indexOf('ogg') !== -1 ||
            lowerType.indexOf('theora') !== -1 ||
            lowerType.indexOf('vorbis') !== -1) {
            return 'probably';
        }
        
        // For other types, use original function
        var result = originalCanPlayType.apply(this, arguments);
        
        // If it returns empty string for a common format, return 'maybe'
        if (!result && (lowerType.indexOf('audio') !== -1 || lowerType.indexOf('video') !== -1)) {
            return 'maybe';
        }
        
        return result;
    };
    
    // Also override for HTMLVideoElement if it has its own implementation
    if (HTMLVideoElement.prototype.canPlayType && HTMLVideoElement.prototype.canPlayType !== HTMLMediaElement.prototype.canPlayType) {
        HTMLVideoElement.prototype.canPlayType = HTMLMediaElement.prototype.canPlayType;
    }
    
    // Also override for HTMLAudioElement if it has its own implementation
    if (HTMLAudioElement.prototype.canPlayType && HTMLAudioElement.prototype.canPlayType !== HTMLMediaElement.prototype.canPlayType) {
        HTMLAudioElement.prototype.canPlayType = HTMLMediaElement.prototype.canPlayType;
    }
})();