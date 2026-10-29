import { useId } from 'react';
import Icon from './Icon.jsx';
import { IMPORTANCE_LABEL } from '../utils/format.js';

const TYPE_LABEL = { docs: 'Docs', course: 'Course', video: 'Video', tutorial: 'Tutorial', book: 'Book' };

/** One missing skill with its learning links and a "Mark as done" checkbox. */
export default function RoadmapCard({ skill, done, onToggle }) {
  const checkboxId = useId();
  return (
    <li className={`roadmap-card${done ? ' roadmap-card--done' : ''}`}>
      <div className="roadmap-card__head">
        <h4 className="roadmap-card__title">{skill.display_name}</h4>
        <span className={`badge badge--${skill.importance}`}>{IMPORTANCE_LABEL[skill.importance]} importance</span>
      </div>
      <p className="muted small">
        Mentioned {skill.mentions} time{skill.mentions === 1 ? '' : 's'} in the job description
      </p>
      <ul className="resources">
        {skill.resources.map((resource) => (
          <li key={resource.url} className="resource">
            <Icon name={resource.resource_type} size={18} />
            <div>
              <a href={resource.url} target="_blank" rel="noopener noreferrer" className="resource__link">
                {resource.title}
                <Icon name="external" size={13} />
                <span className="visually-hidden"> (opens in a new tab)</span>
              </a>
              <span className="resource__meta">
                {resource.provider} · {TYPE_LABEL[resource.resource_type]} · {resource.level}
                {resource.is_free && <span className="tag-free">Free</span>}
              </span>
            </div>
          </li>
        ))}
      </ul>
      <div className="roadmap-card__done no-print">
        <input id={checkboxId} type="checkbox" checked={done} onChange={onToggle} />
        <label htmlFor={checkboxId}>Mark as done</label>
      </div>
    </li>
  );
}
