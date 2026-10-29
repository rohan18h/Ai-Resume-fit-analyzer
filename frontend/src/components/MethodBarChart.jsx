import { Bar } from 'react-chartjs-2';
import { colors, FONT } from './charts.js';
import { percent } from '../utils/format.js';

/** TF-IDF score vs embeddings score for this resume and job description. */
export default function MethodBarChart({ fit }) {
  const c = colors();
  const tfidf = percent(fit.tfidf_score) ?? 0;
  const embeddings = percent(fit.embedding_score) ?? 0;
  return (
    <div>
      <div
        className="chart chart--methods"
        role="img"
        aria-label={`Method comparison: TF-IDF ${tfidf} percent, embeddings ${embeddings} percent.`}
      >
        <Bar
          aria-hidden="true"
          data={{
            labels: ['TF-IDF', 'Embeddings'],
            datasets: [{ data: [tfidf, embeddings], backgroundColor: [c.mint, c.primary], borderRadius: 4, maxBarThickness: 56 }],
          }}
          options={{
            maintainAspectRatio: false,
            scales: { y: { min: 0, max: 100, ticks: { callback: (v) => `${v}%`, font: FONT } }, x: { ticks: { font: FONT } } },
            plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx) => ` ${ctx.parsed.y}%` } } },
          }}
        />
      </div>
      <p className="muted small">
        TF-IDF only counts the exact same words, so it usually scores lower; embeddings also match words that mean the
        same thing.
      </p>
    </div>
  );
}
