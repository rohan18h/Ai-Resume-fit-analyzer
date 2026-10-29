// Shapes eval/report.json for the Evaluation page. Unlabelled pairs never count as right or wrong.
export const METHODS = [
  { key: 'tfidf', name: 'TF-IDF' },
  { key: 'embeddings', name: 'Embeddings' },
  { key: 'weighted', name: 'Weighted (main score)' },
];

export function summarize(report) {
  const target = report.objective_3?.target_percent ?? 70;
  const metric = (key) => report.methods?.[key] ?? null;
  return {
    pairs: report.pairs,
    labelled: report.labelled_pairs ?? report.rows.filter((row) => row.label).length,
    tfidf: metric('tfidf'),
    embeddings: metric('embeddings'),
    weighted: metric('weighted'),
    target,
    met: report.objective_3?.met ?? null, // null = not evaluated yet
    labelOrder: report.label_order ?? ['poor', 'average', 'good'],
  };
}

/** true / false when the pair has a hand label, null when it does not. */
export function isCorrect(row, method) {
  if (!row.label || row[`${method}_pred`] === undefined) return null;
  return row[`${method}_pred`] === row.label;
}

/** "75%" or "n/a" for a missing number. */
export function formatPercent(value) {
  return value === null || value === undefined ? 'n/a' : `${Math.round(value * 10) / 10}%`;
}
