import ScoreGauge from './ScoreGauge.jsx';
import { StatusBadge } from './Icon.jsx';
import { scoreColor } from './charts.js';

/** ATS score ring, "7 of 10 checks passed", and every check; warn/fail rows expand to show detail and fix.
 * Checks that could not be run ("na") are listed as not checked and left out of the score. */
export default function AtsPanel({ ats }) {
  const notChecked = ats.checks.filter((check) => check.status === 'na').length;
  return (
    <div className="ats">
      <div className="ats__summary">
        <ScoreGauge
          score={ats.score}
          color={scoreColor(ats.score, 80, 60)}
          size={130}
          label={`ATS formatting score ${ats.score} percent, ${ats.passed} of ${ats.total} checks passed`}
        />
        <p className="ats__count">
          <strong>
            {ats.passed} of {ats.total}
          </strong>{' '}
          checks passed
          {notChecked > 0 && <span className="muted small"> ({notChecked} not checked)</span>}
        </p>
      </div>
      <p className="muted small">
        How readable this PDF is for resume parsers: text, layout, headings and contact details. It does not use the
        job description and is not any vendor&apos;s official ATS score.
      </p>
      <ul className="ats__checks">
        {ats.checks.map((check) =>
          check.status === 'pass' || check.status === 'na' ? (
            <li key={check.id} className="ats-check">
              <div className="ats-check__row" title={check.status === 'na' ? check.detail : undefined}>
                <StatusBadge status={check.status} />
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
                <p className="ats-check__detail">
                  {check.detail}
                  {typeof check.credit === 'number' && (
                    <span className="muted"> Counts as {check.credit === 0.5 ? 'half' : 'zero'} of this check.</span>
                  )}
                </p>
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
