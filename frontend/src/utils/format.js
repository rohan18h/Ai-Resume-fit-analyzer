/** 1536 -> "1.5 KB", 2_400_000 -> "2.3 MB". */
export function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function countWords(text) {
  const trimmed = (text || '').trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

/** 2310 -> "2.3 s" */
export function formatSeconds(ms) {
  return `${(ms / 1000).toFixed(1)} s`;
}

/** Whole-number percentage for display; null stays null. */
export function percent(value) {
  return value === null || value === undefined ? null : Math.round(value);
}

export const IMPORTANCE_LABEL = { high: 'High', medium: 'Medium', low: 'Low' };
