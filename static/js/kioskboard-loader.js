// Load KioskBoard dynamically with correct path for nginx proxy support
// Store a promise that resolves when KioskBoard is loaded
window.kioskBoardLoaded = new Promise((resolve, reject) => {
    const basePath = window.location.pathname.startsWith('/pianolog') ? '/pianolog' : '';
    const script = document.createElement('script');
    script.src = basePath + '/static/kioskboard/kioskboard-aio-2.3.0.min.js';
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load KioskBoard'));
    document.head.appendChild(script);
});
