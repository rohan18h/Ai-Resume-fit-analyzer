import { Bar, Radar } from 'react-chartjs-2';
import { colors, FONT } from './charts.js';

/** "Web Backend & APIs" -> ["Web Backend", "& APIs"], so long names fit around a radar on a phone. */
export function wrapLabel(text, maxChars = 12) {
  const lines = [];
  for (const word of text.split(' ')) {
    const last = lines[lines.length - 1];
    if (last !== undefined && `${last} ${word}`.length <= maxChars) lines[lines.length - 1] = `${last} ${word}`;
    else lines.push(word);
  }
  return lines;
}

/** Skill coverage per category (matched / required). Radar with 3+ categories, horizontal bars otherwise. */
export default function CategoryRadar({ byCategory }) {
  const c = colors();
  const labels = byCategory.map((row) => wrapLabel(row.category));
  const values = byCategory.map((row) => Math.round((100 * row.matched) / row.required));
  const summary = byCategory.map((row) => `${row.category}: ${row.matched} of ${row.required}`).join('; ');
  const tooltip = {
    callbacks: {
      label: (ctx) => {
        const row = byCategory[ctx.dataIndex];
        return ` ${row.matched} of ${row.required} skills (${ctx.parsed.r ?? ctx.parsed.x}%)`;
      },
    },
  };

  if (byCategory.length < 3) {
    return (
      <div className="chart chart--bar-h" role="img" aria-label={`Skill coverage by category. ${summary}`}>
        <Bar
          data={{ labels, datasets: [{ data: values, backgroundColor: c.teal, borderRadius: 4, maxBarThickness: 28 }] }}
          options={{
            indexAxis: 'y',
            maintainAspectRatio: false,
            scales: { x: { min: 0, max: 100, ticks: { callback: (v) => `${v}%`, font: FONT } }, y: { ticks: { font: FONT } } },
            plugins: { legend: { display: false }, tooltip },
          }}
        />
      </div>
    );
  }

  return (
    <div className="chart chart--radar" role="img" aria-label={`Skill coverage by category. ${summary}`}>
      <Radar
        data={{
          labels,
          datasets: [
            {
              label: 'Matched',
              data: values,
              backgroundColor: 'rgba(28, 114, 147, 0.25)',
              borderColor: c.teal,
              pointBackgroundColor: c.teal,
              borderWidth: 2,
            },
          ],
        }}
        options={{
          maintainAspectRatio: false,
          scales: {
            r: {
              min: 0,
              max: 100,
              ticks: { stepSize: 25, callback: (v) => `${v}%`, backdropColor: 'transparent', font: { ...FONT, size: 10 } },
              pointLabels: { font: { ...FONT, size: 11 }, color: c.text },
            },
          },
          plugins: { legend: { display: false }, tooltip },
        }}
      />
    </div>
  );
}
