/**
 * Extracts the Google Drive file ID from a Google Drive share URL.
 * Returns null if the URL is invalid or the ID cannot be found.
 */
export function extractDriveId(url: string | undefined): string | null {
  if (!url) return null;
  const match = url.match(/\/d\/([a-zA-Z0-9_-]+)/);
  return match ? match[1] : null;
}

/**
 * Translates a Google Drive share URL into a direct streaming URL.
 */
export function getDirectVideoUrl(url: string | undefined): string {
  const id = extractDriveId(url);
  return id ? `https://drive.google.com/uc?export=download&id=${id}` : (url || '');
}

/**
 * Translates a Google Drive share URL into our local Vercel proxy URL.
 */
export function getProxyJsonUrl(url: string | undefined): string {
  const id = extractDriveId(url);
  return id ? `/api/drive?id=${id}` : (url || '');
}
