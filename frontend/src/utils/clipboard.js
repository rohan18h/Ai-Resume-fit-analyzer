/** Copy text to the clipboard. Tries the Clipboard API, then the older execCommand route. Returns true on success. */
export async function copyText(text, { clipboard = globalThis.navigator?.clipboard, doc = globalThis.document } = {}) {
  try {
    await clipboard.writeText(text);
    return true;
  } catch {
    // Clipboard API missing or blocked (permissions, older browsers): fall back to a hidden textarea.
  }
  if (!doc?.body) return false;
  const area = doc.createElement('textarea');
  area.value = text;
  area.setAttribute('readonly', '');
  area.style.position = 'fixed';
  area.style.opacity = '0';
  doc.body.appendChild(area);
  area.select();
  try {
    return Boolean(doc.execCommand && doc.execCommand('copy'));
  } catch {
    return false;
  } finally {
    doc.body.removeChild(area);
  }
}
