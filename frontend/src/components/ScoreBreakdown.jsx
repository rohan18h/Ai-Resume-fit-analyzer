import Icon, { StatusBadge } from './Icon.jsx';
import { IMPORTANCE_LABEL } from '../utils/format.js';
import { QUALIFICATION_STATUS, formatPoints, skillGroups } from '../utils/breakdown.js';

function CategoryRow({ category }) {
  const share = category.max_points ? Math.round((100 * category.points) / category.max_points) : 0;
  return (
    <li className={`breakdown__category${category.applicable ? '' : ' breakdown__category--na'}`}>
      <div className="breakdown__row">
        <span className="breakdown__name">{category.title}</span>
        <span className="breakdown__points">
          {category.applicable ? (
            <>
              <strong>{formatPoints(category.points)}</strong> / {formatPoints(category.max_points)}
            </>
          ) : (
            'Not applicable'
          )}
        </span>
      </div>
      {category.applicable && (
        <div
          className="bar bar--thin"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={share}
          aria-label={`${category.title}: ${formatPoints(category.points)} of ${formatPoints(category.max_points)} points`}
        >
          <div className="bar__fill" style={{ width: `${share}%` }} />
        </div>
      )}
      <p className="muted small breakdown__summary">{category.summary}</p>
    </li>
  );
}

function SkillGroup({ group }) {
  return (
    <>
      <h4 className="subheading">{group.title}</h4>
      <ul className="skill-chips" aria-label={group.title}>
        {group.items.map((skill) => (
          <li key={skill.name} className={`chip chip--${group.variant}`} title={skill.evidence || undefined}>
            {skill.display_name}
            {skill.via && <span className="chip__via">via {skill.via}</span>}
            {group.variant === 'missing' && (
              <span className={`badge badge--${skill.importance}`}>{IMPORTANCE_LABEL[skill.importance]}</span>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}

/** The weighted fit score explained: points per category (they add up to the main score), skills by evidence,
 * job duties, qualifications and recommendations. */
export default function ScoreBreakdown({ breakdown }) {
  const groups = skillGroups(breakdown.skills);
  return (
    <div className="breakdown">
      <ul className="breakdown__categories">
        {breakdown.categories.map((category) => (
          <CategoryRow key={category.id} category={category} />
        ))}
      </ul>
      <p className="breakdown__total">
        Total: <strong>{formatPoints(breakdown.score)}</strong> / 100
      </p>

      {breakdown.recommendations.length > 0 && (
        <>
          <h4 className="subheading">How to improve this score</h4>
          <ol className="breakdown__tips">
            {breakdown.recommendations.map((tip) => (
              <li key={tip}>{tip}</li>
            ))}
          </ol>
        </>
      )}

      {groups.map((group) => (
        <SkillGroup key={group.key} group={group} />
      ))}

      {breakdown.qualifications.length > 0 && (
        <>
          <h4 className="subheading">Qualifications</h4>
          <ul className="ats__checks">
            {breakdown.qualifications.map((q) => {
              const meta = QUALIFICATION_STATUS[q.status];
              return (
                <li key={`${q.kind}-${q.requirement}`} className="ats-check breakdown__qualification">
                  <div className="ats-check__row">
                    <StatusBadge status={meta.badge} />
                    <span className="ats-check__title">
                      {meta.text}: {q.detail}
                      {q.importance === 'preferred' && <span className="muted small"> (preferred)</span>}
                    </span>
                  </div>
                </li>
              );
            })}
          </ul>
        </>
      )}

      {breakdown.responsibilities.length > 0 && (
        <details className="breakdown__duties">
          <summary className="subheading">
            Job duties compared with your bullets ({breakdown.similarity_method})
          </summary>
          <ul className="breakdown__duty-list">
            {breakdown.responsibilities.map((duty) => (
              <li key={duty.requirement} className="breakdown__duty">
                <p className="explain__snippet">
                  <Icon name={duty.credit >= 0.5 ? 'check' : 'cross'} size={14} />{' '}
                  {duty.requirement}{' '}
                  <span className="muted small">({Math.round(duty.credit * 100)}% credit)</span>
                </p>
                <p className="muted small">
                  {duty.best_evidence ? `Closest bullet: ${duty.best_evidence}` : 'No bullet in your Experience or Projects matches this.'}
                </p>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
