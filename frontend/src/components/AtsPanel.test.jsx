import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import AtsPanel from './AtsPanel.jsx';

// The `ats` part of the real POST /api/analyze response for tests/fixtures/ats_bad_resume.pdf.
const checks = [
  ['text_extractable', 'pass', 1], ['multi_column', 'warn', 0.5], ['tables', 'warn', 0.5], ['images', 'pass', 1],
  ['section_headings', 'fail', 0], ['contact_info', 'warn', 0.5], ['length', 'pass', 1], ['fonts', 'warn', 0.5],
  ['special_chars', 'warn', 0.5], ['bullets', 'warn', 0.5],
].map(([id, status, credit]) => ({ id, title: id, status, detail: `${id} detail`, fix: status === 'pass' ? null : 'Fix it.', credit }));
const API_ATS = { score: 60, passed: 3, total: 10, checks };

describe('AtsPanel', () => {
  it('shows the API score as is, with no fallback or transformation', () => {
    for (const score of [0, 37, 60, 61, 95, 100]) {
      const html = renderToStaticMarkup(<AtsPanel ats={{ ...API_ATS, score }} />);
      expect(html).toContain(`>${score}%<`);
      expect(html).toContain(`ATS formatting score ${score} percent`);
    }
  });

  it('shows the counts from the API and every check', () => {
    const html = renderToStaticMarkup(<AtsPanel ats={API_ATS} />);
    expect(html).toContain('3 of 10');
    for (const check of checks) expect(html).toContain(check.id);
  });

  it('marks checks that were not run instead of counting them', () => {
    const ats = { score: 61, passed: 5, total: 9, checks: [...checks.slice(0, 9), { ...checks[9], status: 'na', credit: null, fix: null }] };
    const html = renderToStaticMarkup(<AtsPanel ats={ats} />);
    expect(html).toContain('Not checked');
    expect(html).toContain('(1 not checked)');
    expect(html).toContain('>61%<');
  });
});
