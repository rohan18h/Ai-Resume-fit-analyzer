import { describe, expect, it } from 'vitest';
import { analyzeBlockReason, fileProblem, jdProblem, MAX_JD_CHARS } from './validation.js';
import { countWords, formatBytes, formatSeconds, percent } from './format.js';
import { roadmapText } from './roadmap.js';
import { loadDone, saveDone } from './storage.js';

const pdf = (size = 1000, name = 'resume.pdf', type = 'application/pdf') => ({ name, size, type });

describe('validation', () => {
  it('accepts a PDF up to 5 MB', () => {
    expect(fileProblem(pdf())).toBeNull();
    expect(fileProblem(pdf(5 * 1024 * 1024))).toBeNull();
    expect(fileProblem(pdf(1000, 'CV.PDF', ''))).toBeNull(); // some browsers send no MIME type
  });

  it('rejects other file types, big files and empty files', () => {
    expect(fileProblem(pdf(1000, 'resume.docx', 'application/msword'))).toMatch(/PDF/);
    expect(fileProblem(pdf(5 * 1024 * 1024 + 1))).toMatch(/5 MB/);
    expect(fileProblem(pdf(0))).toMatch(/empty/);
  });

  it('checks the job description length after trimming', () => {
    expect(jdProblem('   short   ')).toMatch(/at least 50/);
    expect(jdProblem('x'.repeat(50))).toBeNull();
    expect(jdProblem('x'.repeat(MAX_JD_CHARS + 1))).toMatch(/10,000/);
  });

  it('explains why Analyze is disabled', () => {
    expect(analyzeBlockReason(null, 'x'.repeat(60))).toMatch(/Upload your resume/);
    expect(analyzeBlockReason(pdf(), '')).toMatch(/at least 50/);
    expect(analyzeBlockReason(pdf(), 'x'.repeat(60))).toBeNull();
  });
});

describe('format', () => {
  it('formats sizes, words, seconds and percentages', () => {
    expect(formatBytes(512)).toBe('512 B');
    expect(formatBytes(1536)).toBe('1.5 KB');
    expect(formatBytes(2.5 * 1024 * 1024)).toBe('2.5 MB');
    expect(countWords('  one two\nthree  ')).toBe(3);
    expect(countWords('')).toBe(0);
    expect(formatSeconds(2310)).toBe('2.3 s');
    expect(percent(72.4)).toBe(72);
    expect(percent(null)).toBeNull();
  });
});

describe('roadmapText', () => {
  const missing = [
    {
      name: 'docker',
      display_name: 'Docker',
      importance: 'high',
      mentions: 3,
      resources: [{ title: 'Docker: Get started', provider: 'Docker Docs', level: 'beginner', url: 'https://docs.docker.com/get-started/' }],
    },
    { name: 'aws', display_name: 'AWS', importance: 'low', mentions: 1, resources: [] },
  ];

  it('lists every missing skill with links', () => {
    const text = roadmapText(missing, { aws: true });
    expect(text).toContain('1. Docker - High importance');
    expect(text).toContain('Mentioned 3 times in the job description');
    expect(text).toContain('https://docs.docker.com/get-started/');
    expect(text).toContain('2. AWS - Low importance (done)');
    expect(text).toContain('Mentioned 1 time in the job description');
  });

  it('handles no missing skills', () => {
    expect(roadmapText([])).toMatch(/no missing skills/);
  });
});

describe('storage', () => {
  const memory = () => {
    const data = {};
    return { getItem: (k) => data[k] ?? null, setItem: (k, v) => (data[k] = v) };
  };

  it('saves and loads the done state', () => {
    const store = memory();
    expect(saveDone({ docker: true }, store)).toBe(true);
    expect(loadDone(store)).toEqual({ docker: true });
  });

  it('never throws when storage is blocked or corrupt', () => {
    const blocked = {
      getItem: () => {
        throw new Error('blocked');
      },
      setItem: () => {
        throw new Error('blocked');
      },
    };
    expect(loadDone(blocked)).toEqual({});
    expect(saveDone({ a: true }, blocked)).toBe(false);
    expect(loadDone({ getItem: () => 'not json' })).toEqual({});
    expect(loadDone({ getItem: () => '[1,2]' })).toEqual({});
    expect(loadDone(undefined)).toEqual({});
  });
});
