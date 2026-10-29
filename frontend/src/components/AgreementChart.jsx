import { Chart } from 'react-chartjs-2';
import { colors, FONT } from './charts.js';

/** Agreement % for both methods as bars, with a dashed line at the Objective 3 target. */
export default function AgreementChart({ tfidf, embeddings, target }) {
  const c = colors();
  return (
    <div
      className="chart chart--agreement"
      role="img"
      aria-label={`Agreement with hand labels: TF-IDF ${tfidf} percent, embeddings ${embeddings} percent, target ${target} percent.`}
    >
      <Chart
        aria-hidden="true"
        type="bar"
        data={{
          labels: ['TF-IDF', 'Embeddings'],
          datasets: [
            {
              type: 'bar',
              label: 'Agreement',
              data: [tfidf, embeddings],
              backgroundColor: [c.mint, c.primary],
              borderRadius: 4,
              maxBarThickness: 72,
            },
            {
              type: 'line',
              label: `Target (${target}%)`,
              data: [target, target],
              borderColor: c.coral,
              borderDash: [6, 4],
              borderWidth: 2,
              pointRadius: 0,
              fill: false,
            },
          ],
        }}
        options={{
          maintainAspectRatio: false,
          scales: { y: { min: 0, max: 100, ticks: { callback: (v) => `${v}%`, font: FONT } }, x: { ticks: { font: FONT } } },
          plugins: {
            legend: { labels: { font: FONT } },
            tooltip: { callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y}%` } },
          },
        }}
      />
    </div>
  );
}
