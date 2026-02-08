export function getBasePath() {
    return window.location.pathname.startsWith('/pianolog') ? '/pianolog' : '';
}
export function apiUrl(path) {
    const basePath = getBasePath();
    return `${basePath}${path}`;
}
