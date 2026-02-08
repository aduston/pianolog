export function getBasePath(): string {
  return window.location.pathname.startsWith('/pianolog') ? '/pianolog' : '';
}

export function apiUrl(path: string): string {
  const basePath = getBasePath();
  return `${basePath}${path}`;
}
