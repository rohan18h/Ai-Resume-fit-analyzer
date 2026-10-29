import { describe, expect, it } from 'vitest';
import { formatPercent, isCorrect, summarize } from './evaluation.js';

// Shapes match eval/report.json. The labelled one uses made-up numbers for testing only.
const unlabelled = {
  pairs: 2,
  labelled_pairs: 0,
  label_order: ['poor', 'average', 'good'],
  methods: { tfidf: null, embeddings: null },
  objective_3: { target_percent: 70, agreement_percent: null, met: null },
  rows: [
    { id: 'p01', label: null, tfidf_score: 23.4, tfidf_pred: 'poor', embeddings_score: 82.1, embeddings_pred: 'good' },
    { id: 'p02', label: null, tfidf_score: 1.3, tfidf_pred: 'poor', embeddings_score: 39.1, embeddings_pred: 'poor' },
  ],
};

const labelled = {
  ...unlabelled,
  labelled_pairs: 2,
  methods: {
    tfidf: { agreement_percent: 50, spearman: null, confusion: [[1, 0, 0], [0, 0, 0], [1, 0, 0]] },
    embeddings: { agreement_percent: 100, spearman: null, confusion: [[1, 0, 0], [0, 0, 0], [0, 0, 1]] },
  },
  objective_3: { target_percent: 70, agreement_percent: 100, met: true },
  rows: [{ ...unlabelled.rows[0], label: 'good' }, { ...unlabelled.rows[1], label: 'poor' }],
};

describe('summarize', () => {
  it('reports "not evaluated yet" without labels', () => {
    const s = summarize(unlabelled);
    expect(s).toMatchObject({ pairs: 2, labelled: 0, tfidf: null, embeddings: null, target: 70, met: null });
  });

  it('passes metrics through when pairs are labelled', () => {
    const s = summarize(labelled);
    expect(s.labelled).toBe(2);
    expect(s.embeddings.agreement_percent).toBe(100);
    expect(s.met).toBe(true);
    expect(s.labelOrder).toEqual(['poor', 'average', 'good']);
  });
});

describe('isCorrect', () => {
  it('is null for unlabelled rows', () => {
    expect(isCorrect(unlabelled.rows[0], 'tfidf')).toBeNull();
  });

  it('compares the prediction with the hand label', () => {
    expect(isCorrect(labelled.rows[0], 'embeddings')).toBe(true);
    expect(isCorrect(labelled.rows[0], 'tfidf')).toBe(false);
  });

  it('is null when a method was not run', () => {
    expect(isCorrect({ id: 'x', label: 'good' }, 'embeddings')).toBeNull();
  });
});

describe('formatPercent', () => {
  it('formats numbers and missing values', () => {
    expect(formatPercent(75)).toBe('75%');
    expect(formatPercent(66.666)).toBe('66.7%');
    expect(formatPercent(null)).toBe('n/a');
  });
});
