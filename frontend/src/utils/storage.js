// "Mark as done" state for roadmap cards. Kept only in this browser; storage can be blocked, so never throw.
const KEY = 'rfa-roadmap-done';

export function loadDone(storage = globalThis.localStorage) {
  try {
    const value = JSON.parse(storage?.getItem(KEY) || '{}');
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  } catch {
    return {};
  }
}

export function saveDone(done, storage = globalThis.localStorage) {
  try {
    storage?.setItem(KEY, JSON.stringify(done));
    return true;
  } catch {
    return false;
  }
}
