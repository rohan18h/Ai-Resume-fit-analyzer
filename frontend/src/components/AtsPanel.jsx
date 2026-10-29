import ScoreGauge from './ScoreGauge.jsx';
import { StatusBadge } from './Icon.jsx';
import { scoreColor } from './charts.js';

/** ATS score ring, "7 of 10 checks passed", and every check; warn/fail rows expand to show detail and fix. */
export default function AtsPanel({ ats }) {
  return (
    <div className="ats">
      <div className="ats__summary">
        <ScoreGauge
          score={ats.score}
          color={scoreColor(ats.score, 80, 60)}
          size={130}
          label={`ATS score ${ats.score} percent, ${ats.passed} of ${ats.total} checks passed`}
        />
        <p className="ats__count">
          <strong>
            {ats.passed} of {ats.total}
          </strong>{' '}
          checks passed
        </p>
      </div>
      <ul className="ats__checks">
        {ats.checks.map((check) =>
          check.status === 'pass' ? (
            <li key={check.id} className="ats-check">
              <div className="ats-check__row">
                <StatusBadge status="pass" />
                <span className="ats-check__title">{check.title}</span>
              </div>
            </li>
          ) : (
            <li key={check.id} className={`ats-check ats-check--${check.status}`}>
              <details>
                <summary className="ats-check__row">
                  <StatusBadge status={check.status} />
                  <span className="ats-check__title">{check.title}</span>
                </summary>
                <p className="ats-check__detail">{check.detail}</p>
                <p className="ats-check__fix">
                  <strong>Fix:</strong> {check.fix}
                </p>
              </details>
            </li>
          ),
        )}
      </ul>
    </div>
  );
}
