// Chart.js setup shared by every chart. Colours come from the CSS design tokens so charts match the slides.
import 'chart.js/auto';

export function token(name, fallback) {
  if (typeof document === 'undefined') return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

export function colors() {
  return {
    primary: token('--primary', '#065A82'),
    teal: token('--teal', '#1C7293'),
    mint: token('--mint', '#5FB9C9'),
    coral: token('--coral', '#C65B3C'),
    success: token('--success', '#2F855A'),
    warning: token('--warning', '#B7791F'),
    muted: token('--muted', '#5B6B79'),
    track: '#E3EBF1',
    text: token('--text', '#1A1A2E'),
  };
}

export const FONT = { family: "'Inter', system-ui, sans-serif" };

/** Colour for a 0-100 score: green for good, amber for average, coral for low (always shown with text too). */
export function scoreColor(score, goodMin = 65, averageMin = 40) {
  const c = colors();
  if (score >= goodMin) return c.success;
  if (score >= averageMin) return c.warning;
  return c.coral;
}
