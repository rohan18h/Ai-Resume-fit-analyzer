import { Doughnut } from 'react-chartjs-2';
import { colors } from './charts.js';

/** Circular gauge (Chart.js doughnut) with the score and a caption in the middle. */
export default function ScoreGauge({ score, caption, color, size = 200, label }) {
  const value = Math.max(0, Math.min(100, score));
  const data = {
    datasets: [{ data: [value, 100 - value], backgroundColor: [color, colors().track], borderWidth: 0 }],
  };
  const options = {
    cutout: '78%',
    responsive: true,
    maintainAspectRatio: true,
    animation: { duration: 600 },
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
    events: [],
  };
  return (
    <div className="gauge" style={{ width: size, height: size }} role="img" aria-label={label}>
      <Doughnut data={data} options={options} aria-hidden="true" />
      <div className="gauge__center" aria-hidden="true">
        <span className="gauge__value">{Math.round(value)}%</span>
        {caption && <span className="gauge__caption">{caption}</span>}
      </div>
    </div>
  );
}
